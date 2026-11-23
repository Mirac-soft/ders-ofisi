"""Yapay zekâ asistanları. Claude okur ve JSON döndürür; dosyaları burası yazar."""
import json
import re
from datetime import date, datetime
from pathlib import Path

from ofis import claude_calistir, dersler, hesap
from ofis.cevirme import TALIMATLAR, json_oku, sema


def _cagir(ayar, dyol, ad, istem, araclar=("Read",), oturum=None):
    return claude_calistir.cagir(ayar, dyol, istem, ayar["modeller"][ad], TALIMATLAR / f"{ad}.md", sema(ad),
                                 list(araclar), oturum)


def _bolum_yaz(yol: Path, no: int, icerik: str) -> None:
    """`## Parça NN` bölümlerini parça sırasıyla tutar; aynı parça tekrar işlenirse yerine yazar."""
    bolumler = {}
    if yol.exists():
        bol =re.split(r"(?m)^## Parça (\d+)\n", yol.read_text("utf-8"))
        bolumler = {int(bol[i]): bol[i + 1].rstrip("\n") for i in range(1, len(bol), 2)}
    bolumler[no] = icerik.strip()
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text("".join(f"## Parça {n:02d}\n{bolumler[n]}\n\n" for n in sorted(bolumler)), "utf-8")


def _metin_yolu(pdf_adi, parca_no) -> str:
    return f"metin/{pdf_adi}/parca-{parca_no:02d}.md"


def ilgili_metinler(dyol: Path, konular: list[str] | None) -> list[str]:
    """Konuları kapsayan metin parçalarının ders klasörüne göre yolları; konu yoksa hepsi."""
    yollar = []
    for kj in sorted(dyol.glob("metin/*/konular.json")):
        pdf_adi = kj.parent.name
        for no, kapsanan in sorted(json_oku(kj, {}).items(), key=lambda x: int(x[0])):
            if not konular or set(kapsanan) & set(konular):
                yollar.append(_metin_yolu(pdf_adi, int(no)))
    return yollar


def ozetle(ayar, kok, ders, pdf_adi, parca_no) -> None:
    dyol = dersler.ders_yolu(kok, ders)
    sonuc, _ = _cagir(ayar, dyol, "ozetci", f"Ders metni: {_metin_yolu(pdf_adi, parca_no)}")
    ozet = sonuc.get("ozet_md", "").replace("../../gorseller/", "../gorseller/")
    _bolum_yaz(dyol / "ozet" / f"{pdf_adi}.md", parca_no, ozet)


def formul_cikar(ayar, kok, ders, pdf_adi, parca_no) -> None:
    dyol = dersler.ders_yolu(kok, ders)
    hedef = dyol / "formuller" / f"{pdf_adi}.md"
    gorseller = [g for g in json_oku(dyol / "metin" / pdf_adi / "gorseller.json", [])
                 if g["parca"] == parca_no and g["tur"] == "formul"]
    if not gorseller:  # limit harcamaya gerek yok
        _bolum_yaz(hedef, parca_no, "_Bu parçada formül yok._")
        return
    liste = "\n".join(f"- gorseller/{g['dosya']} — {g['aciklama']} (sayfa {g['sayfa']})" for g in gorseller)
    sonuc, _ = _cagir(ayar, dyol, "formulcu", f"Ders metni: {_metin_yolu(pdf_adi, parca_no)}\nFormül görselleri:\n{liste}")
    gecerli = {g["dosya"] for g in gorseller}
    parcalar = []
    for f in sonuc.get("formuller", []):
        dosya = Path(str(f.get("dosya", ""))).name
        if dosya not in gecerli:
            continue
        ad = str(f.get("ad", "")).replace("]", ")").replace("[", "(")
        parcalar.append(f"### {ad}\n![{ad}](../gorseller/{dosya})\n\n**Ne demek:** {f.get('anlam', '')}\n\n"
                        f"**Ne zaman kullanılır:** {f.get('ne_zaman', '')}\n\n**Sınavda nasıl çıkar:** {f.get('soru_tipi', '')}")
    _bolum_yaz(hedef, parca_no, "\n\n".join(parcalar) or "_Formül açıklanamadı._")


def soru_ara(ayar, kok, ders, konular: list[str]) -> None:
    dyol = dersler.ders_yolu(kok, ders)
    metinler = ilgili_metinler(dyol, konular)
    istem = (f"Ders: {ders}\nKonular: {json.dumps(konular, ensure_ascii=False)}\n"
             f"Ders metni dosyaları: {json.dumps(metinler, ensure_ascii=False)}")
    sonuc, _ = _cagir(ayar, dyol, "arastirmaci", istem, ("Read", "WebSearch", "WebFetch"))
    sorular = []
    for s in sonuc.get("sorular", []):
        kaynak = s.get("kaynak")
        sorular.append({"metin": str(s.get("metin", "")), "zorluk": s.get("zorluk", "orta"),
                        "kaynak": kaynak if isinstance(kaynak, str) and kaynak.startswith(("http://", "https://")) else None,
                        "konu": str(s.get("konu", ""))})
    dersler.json_yaz(dyol / "sorular" / f"{datetime.now():%Y-%m-%d-%H%M%S}.json", {"konular": konular, "sorular": sorular})


def _oturum(kok, ders, anahtar, yeni: str | None = None, sil=False) -> str | None:
    v = dersler.oku(kok, ders)
    if sil:
        v["sohbetler"].pop(anahtar, None)
    elif yeni:
        v["sohbetler"][anahtar] = yeni
    else:
        return v["sohbetler"].get(anahtar)
    dersler.yaz(kok, ders, v)
    return None


def sinav(ayar, kok, ders, mesaj: str, konular: list[str] | None) -> dict:
    dyol = dersler.ders_yolu(kok, ders)
    if konular is not None:  # yeni sınav
        _oturum(kok, ders, "sinavci", sil=True)
        tum = [k["ad"] for k in dersler.oku(kok, ders)["konular"]]
        secili = konular or tum
        sorular = sorted(p.relative_to(dyol).as_posix() for p in dyol.glob("sorular/*.json"))[-1:]
        istem = (f"Yeni sınav. Konular: {json.dumps(secili, ensure_ascii=False)}\n"
                 f"Ders konu listesi: {json.dumps(tum, ensure_ascii=False)}\n"
                 f"Ders metni dosyaları: {json.dumps(ilgili_metinler(dyol, konular), ensure_ascii=False)}\n"
                 f"Soru dosyaları: {json.dumps(sorular, ensure_ascii=False)}\nÖğrenci: {mesaj}")
        oturum = None
    else:
        oturum = _oturum(kok, ders, "sinavci")
        istem = f"Öğrenci: {mesaj}"
    sonuc, sid = _cagir(ayar, dyol, "sinavci", istem, oturum=oturum)
    if sonuc.get("bitti") and sonuc.get("sonuc"):
        adlar = {k["ad"] for k in dersler.oku(kok, ders)["konular"]}
        s = sonuc["sonuc"]
        eksik = [k for k in s.get("eksik_konular", []) if k in adlar]
        dersler.json_yaz(dyol / "sinavlar" / f"{datetime.now():%Y-%m-%d-%H%M%S}.json",
                         {"dogru": s.get("dogru", 0), "yanlis": s.get("yanlis", 0), "eksik_konular": eksik,
                          "mesaj": sonuc.get("mesaj", "")})
        hesap.tekrar_ekle(kok, ders, eksik, date.today())
        _oturum(kok, ders, "sinavci", sil=True)
    else:
        _oturum(kok, ders, "sinavci", yeni=sid)
    return sonuc


def soru_sor(ayar, kok, ders, mesaj: str) -> dict:
    dyol = dersler.ders_yolu(kok, ders)
    oturum = _oturum(kok, ders, "soru_cevap")
    if oturum:
        istem = f"Öğrenci: {mesaj}"
    else:
        kj = sorted(p.relative_to(dyol).as_posix() for p in dyol.glob("metin/*/konular.json"))
        istem = f"Ders: {ders}\nKonu eşleştirme dosyaları: {json.dumps(kj, ensure_ascii=False)}\nÖğrenci: {mesaj}"
    sonuc, sid = _cagir(ayar, dyol, "soru_cevap", istem, oturum=oturum)
    _oturum(kok, ders, "soru_cevap", yeni=sid)
    return sonuc
