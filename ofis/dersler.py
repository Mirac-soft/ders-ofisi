"""Ders klasörleri ve ders.json. Ders adı URL'den gelir: her yol buradan doğrulanarak üretilir."""
import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path

ALT_KLASORLER = ["pdf", "metin", "ozet", "formuller", "sorular", "sinavlar", "gorseller"]
_YASAK = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_AYRILMIS = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


KILIT = threading.RLock()  # ders.json gibi dosyalarda oku-değiştir-yaz bölümleri için


def tekrarla(fn, deneme=50):
    """Windows: başka iş parçacığı dosyayı okurken os.replace/okuma PermissionError verebilir; kısa bekleyip yeniden dene."""
    for i in range(deneme):
        try:
            return fn()
        except PermissionError:
            if i == deneme - 1:
                raise
            time.sleep(0.02)


class GecersizAd(ValueError):
    pass


def ad_gecerli_mi(ad: str) -> bool:
    return bool(
        isinstance(ad, str) and ad.strip() and len(ad) <= 60 and not _YASAK.search(ad)
        and not ad.startswith(".") and not ad.endswith((".", " ")) and ad.split(".")[0].lower() not in _AYRILMIS
    )


def ders_yolu(kok: Path, ad: str) -> Path:
    if not ad_gecerli_mi(ad):
        raise GecersizAd(ad)
    return Path(kok) / ad


def guvenli_dosya(kok: Path, ad: str, goreli: str) -> Path:
    taban = ders_yolu(kok, ad).resolve()
    hedef = (taban / goreli).resolve()
    if not hedef.is_relative_to(taban):
        raise GecersizAd(goreli)
    return hedef


def json_yaz(yol: Path, veri) -> None:
    """Atomik yazım: yarım kalmış dosya bırakmaz."""
    yol.parent.mkdir(parents=True, exist_ok=True)
    fd, gecici = tempfile.mkstemp(dir=yol.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    try:
        tekrarla(lambda: os.replace(gecici, yol))
    finally:
        if os.path.exists(gecici):
            os.remove(gecici)


def ders_olustur(kok: Path, ad: str, sinav_tarihi: str, konular: list[str]) -> dict:
    yol = ders_yolu(kok, ad)
    if (yol / "ders.json").exists():
        raise FileExistsError(ad)
    for alt in ALT_KLASORLER:
        (yol / alt).mkdir(parents=True, exist_ok=True)
    veri = {"ad": ad, "sinav_tarihi": sinav_tarihi,
            "konular": [{"ad": k.strip(), "bitti": False} for k in konular if k.strip()],
            "oturumlar": [], "sohbetler": {}}
    json_yaz(yol / "ders.json", veri)
    return veri


def listele(kok: Path) -> list[str]:
    kok = Path(kok)
    if not kok.is_dir():
        return []
    return sorted(p.name for p in kok.iterdir() if (p / "ders.json").is_file())


def oku(kok: Path, ad: str) -> dict:
    yol = ders_yolu(kok, ad) / "ders.json"
    if not yol.is_file():
        raise FileNotFoundError(ad)
    return json.loads(tekrarla(lambda: yol.read_text("utf-8")))


def yaz(kok: Path, ad: str, veri: dict) -> None:
    json_yaz(ders_yolu(kok, ad) / "ders.json", veri)
