"""Yerel HTTP sunucu (yalnızca 127.0.0.1): 3D ofis sayfası, REST uçları, SSE durum yayını."""
import json
import mimetypes
import queue
import re
import shutil
import threading
import traceback
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from ofis import asistanlar, ayarlar, cevirme, dersler, hesap, pdf_isleme
from ofis.ayarlar import PROJE
from ofis.claude_calistir import ClaudeHatasi, Kuyruk, LimitDolu
from ofis.olaylar import Yayinci

WEB = PROJE / "web"
PDF_SINIR = 200 * 1024 * 1024
JSON_SINIR = 1024 * 1024


class Hata(Exception):
    def __init__(self, kod, mesaj):
        super().__init__(mesaj)
        self.kod = kod


class Ofis:
    def __init__(self, ayar: dict, kok: Path):
        self.ayar, self.kok = ayar, Path(kok)
        self.kok.mkdir(parents=True, exist_ok=True)
        self.yayinci = Yayinci()
        self._suren: set[tuple] = set()  # kuyrukta/çalışan işler: aynı iş iki kez limit harcamasın
        self._suren_kilit = threading.Lock()
        self.kuyruk = Kuyruk(ayar["es_zamanli"], self.yayinci)
        self.uyari = None if shutil.which(ayar["claude_komutu"][0]) or Path(ayar["claude_komutu"][0]).exists() else \
            "Claude Code bulunamadı: asistanlar çalışamaz. ayarlar.json içindeki claude_komutu yolunu kontrol et."

    def ders_var(self, ad):
        try:
            dersler.oku(self.kok, ad)
        except dersler.GecersizAd:
            raise Hata(400, "geçersiz ders adı")
        except FileNotFoundError:
            raise Hata(404, "ders yok")

    # --- arka plan işleri ---
    def _tekil(self, anahtar: tuple, ders: str, asistan: str, fn) -> None:
        with self._suren_kilit:
            if anahtar in self._suren:
                return
            self._suren.add(anahtar)

        def calis():
            try:
                fn()
            finally:
                with self._suren_kilit:
                    self._suren.discard(anahtar)

        self.kuyruk.ekle(ders, asistan, calis)

    def parca_isleri(self, ders, pdf_adi, no):
        self._tekil(("ozet", ders, pdf_adi, no), ders, "ozetci", lambda: asistanlar.ozetle(self.ayar, self.kok, ders, pdf_adi, no))
        self._tekil(("formul", ders, pdf_adi, no), ders, "formulcu", lambda: asistanlar.formul_cikar(self.ayar, self.kok, ders, pdf_adi, no))

    def cevir(self, ders, pdf_adi):
        self._tekil(("cevir", ders, pdf_adi), ders, "cevirici", lambda: cevirme.cevir(
            self.ayar, self.kok, ders, pdf_adi, lambda no, _md: self.parca_isleri(ders, pdf_adi, no)))

    def pdfler(self, ders) -> list[dict]:
        dyol = dersler.ders_yolu(self.kok, ders)
        sonuc = []
        for pdf in sorted((dyol / "pdf").glob("*.pdf")):
            d = cevirme.json_oku(dyol / "metin" / pdf.stem / "durum.json", {"tamam": [], "toplam": None})
            sonuc.append({"ad": pdf.stem, "tamam": len(d["tamam"]), "toplam": d["toplam"]})
        return sonuc

    def devam(self, ders):
        dyol = dersler.ders_yolu(self.kok, ders)
        for p in self.pdfler(ders):
            if p["toplam"] is None or p["tamam"] < p["toplam"]:
                self.cevir(ders, p["ad"])
            durum = cevirme.json_oku(dyol / "metin" / p["ad"] / "durum.json", {"tamam": []})
            for no in durum["tamam"]:  # limit yüzünden yarım kalan özet/formüller
                for klasor in ("ozet", "formuller"):
                    y = dyol / klasor / f"{p['ad']}.md"
                    if not (y.exists() and f"## Parça {no:02d}\n" in y.read_text("utf-8")):
                        self.parca_isleri(ders, p["ad"], no)
                        break

    def ders_bilgisi(self, ders) -> dict:
        dyol = dersler.ders_yolu(self.kok, ders)
        simdi = datetime.now()
        sorular = sorted((dyol / "sorular").glob("*.json"))
        return dersler.oku(self.kok, ders) | {
            "pdfler": self.pdfler(ders),
            "ozetler": sorted(p.stem for p in (dyol / "ozet").glob("*.md")),
            "formuller": sorted(p.stem for p in (dyol / "formuller").glob("*.md")),
            "sorular": cevirme.json_oku(sorular[-1], None) if sorular else None,
            "sinavlar": [cevirme.json_oku(p, {}) | {"tarih": p.stem} for p in sorted((dyol / "sinavlar").glob("*.json"))],
            "bugun_tekrar": hesap.bugun_tekrar(self.kok, ders, simdi.date()),
            "analiz": hesap.sure_analizi(self.kok, ders, simdi),
            "notlar": hesap.notlar(self.kok, ders),
        }


def _isleyici(ofis: Ofis):
    class Isleyici(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _gonder(self, kod, govde: bytes, tur="application/json; charset=utf-8"):
            self.send_response(kod)
            self.send_header("Content-Type", tur)
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Cache-Control", "no-store")
            if self.close_connection:
                self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(govde)

        def _json(self, veri, kod=200):
            self._gonder(kod, json.dumps(veri, ensure_ascii=False).encode("utf-8"))

        def _dosya(self, yol: Path):
            if not yol.is_file():
                raise Hata(404, "dosya yok")
            self._gonder(200, yol.read_bytes(), mimetypes.guess_type(yol.name)[0] or "application/octet-stream")

        def _govde(self, sinir=JSON_SINIR) -> bytes:
            n = max(int(self.headers.get("Content-Length") or 0), 0)
            if n > sinir:
                raise Hata(413, "çok büyük")
            self._okundu = True
            return self.rfile.read(n)

        def _json_govde(self) -> dict:
            if self.headers.get_content_type() != "application/json":  # başka sitelerin basit (preflight'sız) isteklerini keser
                raise Hata(415, "Content-Type application/json olmalı")
            try:
                v = json.loads(self._govde() or b"{}")
            except json.JSONDecodeError:
                raise Hata(400, "geçersiz JSON")
            if not isinstance(v, dict):
                raise Hata(400, "geçersiz JSON")
            return v

        def _parcalar(self):
            # Önce böl, sonra çöz: %2F bir parçanın içinde kalır ve ad doğrulamasına takılır
            return [unquote(p) for p in urlsplit(self.path).path.split("/") if p]

        def _govdeyi_at(self):
            """Okunmamış gövdeyle yanıt verilirse Windows bağlantıyı koparır; hata yanıtından önce oku ya da bağlantıyı kapat."""
            if self.command == "POST" and not self._okundu:
                n = max(int(self.headers.get("Content-Length") or 0), 0)
                if n <= JSON_SINIR:
                    self.rfile.read(n)
                else:
                    self.close_connection = True

        def _yerel_mi(self) -> bool:
            """DNS rebinding ve başka sitelerden gelen istekleri engeller: yalnızca bu sunucunun kendi sayfası."""
            port = self.server.server_address[1]
            izinli = {f"127.0.0.1:{port}", f"localhost:{port}"}
            origin = self.headers.get("Origin")
            return self.headers.get("Host", "") in izinli and (origin is None or origin.split("://", 1)[-1] in izinli)

        def _yakala(self, fn):
            self._okundu = False
            try:
                if not self._yerel_mi():
                    raise Hata(403, "yalnızca yerel ofis sayfası")
                fn()
            except Hata as e:
                self._govdeyi_at()
                self._json({"hata": str(e)}, e.kod)
            except dersler.GecersizAd:
                self._json({"hata": "geçersiz ad veya yol"}, 400)
            except LimitDolu:
                self._json({"hata": "limit"}, 429)
            except ClaudeHatasi as e:
                self._json({"hata": str(e)}, 502)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                pass
            except Exception as e:
                traceback.print_exc()
                self._json({"hata": str(e)}, 500)

        def do_GET(self):
            self._yakala(self._get)

        def do_POST(self):
            self._yakala(self._post)

        def _get(self):
            p = self._parcalar()
            if not p or p[0] != "api":
                hedef = (WEB / "/".join(p or ["index.html"])).resolve()
                if not hedef.is_relative_to(WEB.resolve()):
                    raise Hata(404, "yok")
                return self._dosya(hedef)
            if p == ["api", "dersler"]:
                return self._json({"dersler": dersler.listele(ofis.kok), "uyari": ofis.uyari})
            if p == ["api", "olaylar"]:
                return self._sse()
            if len(p) >= 3 and p[1] == "ders":
                ders = p[2]
                ofis.ders_var(ders)
                if len(p) == 3:
                    return self._json(ofis.ders_bilgisi(ders))
                if p[3] == "dosya" and len(p) > 4:
                    return self._dosya(dersler.guvenli_dosya(ofis.kok, ders, "/".join(p[4:])))
                if p[3] == "sayfa" and len(p) == 6 and p[5].isdigit():
                    pdf_adi, sayfa = p[4], int(p[5])
                    if not dersler.ad_gecerli_mi(pdf_adi):
                        raise Hata(400, "geçersiz ad")
                    dyol = dersler.ders_yolu(ofis.kok, ders)
                    pdf = dyol / "pdf" / f"{pdf_adi}.pdf"
                    if not pdf.is_file():
                        raise Hata(404, "pdf yok")
                    hedef = dyol / "gorseller" / "_sayfa" / f"{pdf_adi}-{sayfa}.png"
                    if not hedef.exists():
                        try:
                            pdf_isleme.tam_sayfa(pdf, sayfa, hedef)
                        except ValueError:
                            raise Hata(404, "sayfa yok")
                    return self._dosya(hedef)
            raise Hata(404, "yok")

        def _post(self):
            p = self._parcalar()
            if p == ["api", "dersler"]:
                v = self._json_govde()
                try:
                    date.fromisoformat(str(v.get("sinav_tarihi")))
                except ValueError:
                    raise Hata(400, "sınav tarihi YYYY-AA-GG olmalı")
                konular = v.get("konular") or []
                if not isinstance(konular, list):
                    raise Hata(400, "konular liste olmalı")
                try:
                    return self._json(dersler.ders_olustur(ofis.kok, str(v.get("ad", "")), v["sinav_tarihi"],
                                                           [str(k) for k in konular]))
                except FileExistsError:
                    raise Hata(409, "bu ders zaten var")
            if len(p) == 4 and p[:2] == ["api", "ders"]:
                ders, eylem = p[2], p[3]
                ofis.ders_var(ders)
                simdi = datetime.now()
                if eylem == "pdf":
                    return self._pdf_yukle(ders)
                v = self._json_govde()
                if eylem == "devam":
                    ofis.devam(ders)
                elif eylem == "soru-bul":
                    konular = [str(k) for k in v.get("konular") or []]
                    ofis.kuyruk.ekle(ders, "arastirmaci", lambda: asistanlar.soru_ara(ofis.ayar, ofis.kok, ders, konular))
                elif eylem == "sinav":
                    konular = v.get("konular")
                    return self._json(ofis.kuyruk.senkron(ders, "sinavci", lambda: asistanlar.sinav(
                        ofis.ayar, ofis.kok, ders, str(v.get("mesaj", "")),
                        None if konular is None else [str(k) for k in konular])))
                elif eylem == "soru":
                    return self._json(ofis.kuyruk.senkron(ders, "soru_cevap", lambda: asistanlar.soru_sor(
                        ofis.ayar, ofis.kok, ders, str(v.get("mesaj", "")))))
                elif eylem == "not":
                    hesap.not_ekle(ofis.kok, ders, str(v.get("metin", "")), simdi)
                elif eylem == "konu":
                    with dersler.KILIT:
                        d = dersler.oku(ofis.kok, ders)
                        for k in d["konular"]:
                            if k["ad"] == v.get("konu"):
                                k["bitti"] = bool(v.get("bitti"))
                        dersler.yaz(ofis.kok, ders, d)
                elif eylem == "konular":
                    with dersler.KILIT:
                        d = dersler.oku(ofis.kok, ders)
                        eski = {k["ad"]: k["bitti"] for k in d["konular"]}
                        adlar = list(dict.fromkeys(str(k).strip() for k in v.get("konular") or [] if str(k).strip()))
                        d["konular"] = [{"ad": a, "bitti": eski.get(a, False)} for a in adlar]
                        dersler.yaz(ofis.kok, ders, d)
                elif eylem == "tekrar":
                    hesap.tekrar_yapildi(ofis.kok, ders, str(v.get("konu", "")), simdi.date())
                elif eylem == "sure":
                    if v.get("olay") == "basla":
                        hesap.sure_basla(ofis.kok, ders, simdi)
                    elif v.get("olay") == "dur":
                        hesap.sure_dur(ofis.kok, ders, simdi)
                    elif v.get("olay") == "nabiz":
                        hesap.sure_nabiz(ofis.kok, ders, simdi)
                    else:
                        raise Hata(400, "olay basla/dur/nabiz olmalı")
                else:
                    raise Hata(404, "yok")
                return self._json({"tamam": True})
            raise Hata(404, "yok")

        def _pdf_yukle(self, ders):
            ad = Path(unquote(self.headers.get("X-Dosya-Adi", ""))).name
            if not re.fullmatch(r".+\.pdf", ad, re.I) or not dersler.ad_gecerli_mi(ad[:-4]) or ".." in ad:
                raise Hata(400, "geçersiz PDF adı")
            if "/" in unquote(self.headers.get("X-Dosya-Adi", "")).replace("\\", "/"):
                raise Hata(400, "geçersiz PDF adı")
            govde = self._govde(PDF_SINIR)
            if not govde.startswith(b"%PDF"):
                raise Hata(400, "dosya PDF değil")
            hedef = dersler.ders_yolu(ofis.kok, ders) / "pdf" / f"{ad[:-4]}.pdf"
            if hedef.exists():
                raise Hata(409, "bu adla bir PDF zaten var")
            hedef.write_bytes(govde)
            ofis.cevir(ders, hedef.stem)
            return self._json({"tamam": True, "pdf": hedef.stem})

        def _sse(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            q = ofis.yayinci.abone()
            try:
                for olay in list(ofis.yayinci.son.values()):
                    q.put(olay)
                while True:
                    try:
                        olay = q.get(timeout=15)
                        self.wfile.write(f"data: {json.dumps(olay, ensure_ascii=False)}\n\n".encode("utf-8"))
                    except queue.Empty:
                        self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            finally:
                ofis.yayinci.ayril(q)

    return Isleyici


def olustur(ayar: dict, kok: Path) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer(("127.0.0.1", ayar["port"]), _isleyici(Ofis(ayar, kok)))
    srv.daemon_threads = True
    return srv


def main():
    ayar = ayarlar.yukle()
    srv = olustur(ayar, PROJE / ayar["dersler_klasoru"])
    print(f"Ders Ofisi: http://127.0.0.1:{ayar['port']}/", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
