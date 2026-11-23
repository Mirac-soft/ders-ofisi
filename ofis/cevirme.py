"""PDF → Markdown metin + orijinal görüntü olarak kesilmiş formül/şekiller. Parça parça, kaldığı yerden devam eder."""
import json
import re
import time
from pathlib import Path
from typing import Callable

from ofis import claude_calistir, dersler, pdf_isleme
from ofis.ayarlar import PROJE

TALIMATLAR = PROJE / "talimatlar"
_YER_TUTUCU = re.compile(r"\[\[(G\d+)\]\]")


def json_oku(yol: Path, varsayilan):
    return json.loads(dersler.tekrarla(lambda: yol.read_text("utf-8"))) if yol.exists() else varsayilan


def sema(ad: str) -> dict:
    return json.loads((TALIMATLAR / f"{ad}.json").read_text("utf-8"))


def cevir(ayar: dict, kok: Path, ders: str, pdf_adi: str, parca_bitti: Callable[[int, Path], None]) -> None:
    dyol = dersler.ders_yolu(kok, ders)
    konu_adlari = [k["ad"] for k in dersler.oku(kok, ders)["konular"]]
    pdf = dyol / "pdf" / f"{pdf_adi}.pdf"
    metin = dyol / "metin" / pdf_adi
    metin.mkdir(parents=True, exist_ok=True)
    parcalar = pdf_isleme.parcala(pdf, dyol / "pdf" / f"{pdf_adi}-parcalar", ayar["parca_sayfa"])
    durum_yolu = metin / "durum.json"
    durum = json_oku(durum_yolu, {"tamam": [], "toplam": len(parcalar)})
    durum["toplam"] = len(parcalar)
    durum.setdefault("sureler", [])
    dersler.json_yaz(durum_yolu, durum)
    sayfalar = dyol / "pdf" / f"{pdf_adi}-sayfalar"

    for no, (parca, ilk, son) in enumerate(parcalar, 1):
        if no in durum["tamam"]:
            continue
        basla = time.monotonic()
        resimler = pdf_isleme.sayfa_gorselleri(pdf, ilk, son, sayfalar)
        metin_dosyasi = sayfalar / f"metin-{no:02d}.txt"
        metin_dosyasi.write_text(pdf_isleme.metin_katmani(pdf, ilk, son), "utf-8")
        liste = "\n".join(f"- sayfa {i}: {r.relative_to(dyol).as_posix()}" for i, r in enumerate(resimler, 1))
        istem = (f"Bu parça orijinal notun {ilk}–{son}. sayfaları. Sayfa resimleri (sırayla, sayfa 1 = ilk resim):\n{liste}\n"
                 f"Seçilebilir metin katmanı (boş olabilir; taranmış sayfalarda resme bak): {metin_dosyasi.relative_to(dyol).as_posix()}\n"
                 f"Ders konu listesi: {json.dumps(konu_adlari, ensure_ascii=False)}")
        sonuc, _ = claude_calistir.cagir(ayar, dyol, istem, ayar["modeller"]["cevirici"], TALIMATLAR / "cevirici.md",
                                         sema("cevirici"), ["Read"])
        if not str(sonuc.get("markdown", "")).strip():  # okunamadıysa "bitti" sayma
            raise claude_calistir.ClaudeHatasi(f"Parça {no} okunamadı (boş metin döndü)")

        gorseller_yolu = metin / "gorseller.json"
        gorseller = [g for g in json_oku(gorseller_yolu, []) if g["parca"] != no]  # yarım kalan tekrar çiftlenmesin
        sayfa_sayac: dict[int, int] = {}
        baglantilar = {}
        for g in sonuc.get("gorseller", []):
            try:
                sayfa = ilk + int(g["sayfa"]) - 1
            except (KeyError, TypeError, ValueError):
                continue
            if not ilk <= sayfa <= son:
                continue
            sayfa_sayac[sayfa] = sayfa_sayac.get(sayfa, 0) + 1
            dosya = f"{pdf_adi}-s{sayfa}-{sayfa_sayac[sayfa]}.png"
            pdf_isleme.kes(pdf, sayfa, g.get("kutu"), dyol / "gorseller" / dosya)
            aciklama = str(g.get("aciklama", "")).replace("]", ")").replace("[", "(")
            baglantilar[g.get("yer_tutucu")] = f"![{aciklama}](../../gorseller/{dosya})"
            gorseller.append({"dosya": dosya, "sayfa": sayfa, "tur": g.get("tur", "sekil"), "aciklama": aciklama, "parca": no})

        md = _YER_TUTUCU.sub(lambda m: baglantilar.get(m.group(1), ""), sonuc.get("markdown", ""))
        md_yolu = metin / f"parca-{no:02d}.md"
        md_yolu.write_text(md, "utf-8")
        dersler.json_yaz(gorseller_yolu, gorseller)
        konular = json_oku(metin / "konular.json", {})
        konular[str(no)] = [k for k in sonuc.get("konular", []) if k in konu_adlari]
        dersler.json_yaz(metin / "konular.json", konular)
        durum["tamam"] = sorted({*durum["tamam"], no})
        durum["sureler"] = (durum["sureler"] + [round(time.monotonic() - basla, 1)])[-20:]
        dersler.json_yaz(durum_yolu, durum)
        parca_bitti(no, md_yolu)
    dersler.json_yaz(durum_yolu, durum)
