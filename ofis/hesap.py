"""Yapay zekâ kullanmayan asistanlar: süre, sınava yetişme analizi, tekrar takvimi, notlar."""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from ofis import dersler

TEKRAR_GUNLERI = (1, 3, 7)


def _iso(t: datetime) -> str:
    return t.replace(microsecond=0).isoformat()


def sure_basla(kok: Path, ders: str, simdi: datetime) -> None:
    for d in dersler.listele(kok):  # aynı anda tek ders sayılır; çökmeden kalan açık oturumlar da kapanır
        sure_dur(kok, d, simdi)
    v = dersler.oku(kok, ders)
    v["oturumlar"].append({"basla": _iso(simdi), "bitis": None})
    dersler.yaz(kok, ders, v)


def sure_dur(kok: Path, ders: str, simdi: datetime) -> None:
    v = dersler.oku(kok, ders)
    degisti = False
    for o in v["oturumlar"]:
        if o["bitis"] is None:
            o["bitis"] = _iso(max(simdi, datetime.fromisoformat(o["basla"])))
            degisti = True
    if degisti:
        dersler.yaz(kok, ders, v)


def _araliklar(v: dict, simdi: datetime):
    for o in v["oturumlar"]:
        yield datetime.fromisoformat(o["basla"]), datetime.fromisoformat(o["bitis"]) if o["bitis"] else simdi


def _ortusme_saat(araliklar, bas: datetime, son: datetime) -> float:
    return sum(max((min(b, son) - max(a, bas)).total_seconds(), 0) for a, b in araliklar) / 3600


def sure_analizi(kok: Path, ders: str, simdi: datetime) -> dict:
    v = dersler.oku(kok, ders)
    araliklar = list(_araliklar(v, simdi))
    toplam = sum((b - a).total_seconds() for a, b in araliklar) / 3600
    bitti = sum(k["bitti"] for k in v["konular"])
    kalan = len(v["konular"]) - bitti
    gun0 = datetime.combine(simdi.date(), datetime.min.time())
    son7 = [{"tarih": (gun0 - timedelta(days=i)).date().isoformat(),
             "saat": _ortusme_saat(araliklar, gun0 - timedelta(days=i), gun0 - timedelta(days=i - 1))}
            for i in range(6, -1, -1)]
    gunluk = sum(g["saat"] for g in son7) / 7
    kalan_gun = max(0, (date.fromisoformat(v["sinav_tarihi"]) - simdi.date()).days)
    kapasite = kalan_gun * gunluk
    sonuc = {"toplam_saat": toplam, "bitti": bitti, "kalan": kalan, "kalan_gun": kalan_gun, "gunluk_ort_saat": gunluk,
             "gereken_saat": None, "kapasite_saat": kapasite, "yetisir": None, "son7": son7,
             "sinav_tarihi": v["sinav_tarihi"]}
    if bitti == 0 or toplam == 0:
        sonuc["yorum"] = "Henüz tahmin için veri yok: bir konuyu bitti olarak işaretle."
        return sonuc
    gereken = kalan / (bitti / toplam)
    sonuc["gereken_saat"] = gereken
    sonuc["yetisir"] = gereken <= kapasite
    if kalan_gun == 0:
        sonuc["yorum"] = "Sınav bugün/geçti."
    elif sonuc["yetisir"]:
        sonuc["yorum"] = f"Bu hızla yetişiyorsun (~{gereken:.0f} saat gerekli, ~{kapasite:.0f} saat var)."
    else:
        sonuc["yorum"] = f"Bu hızla yetişmiyor: günde ~{gereken / kalan_gun:.1f} saat çalışman gerekiyor."
    return sonuc


def _tekrar_yolu(kok: Path, ders: str) -> Path:
    return dersler.ders_yolu(kok, ders) / "tekrar.json"


def _tekrar_oku(kok, ders) -> list[dict]:
    y = _tekrar_yolu(kok, ders)
    return json.loads(y.read_text("utf-8")) if y.exists() else []


def tekrar_ekle(kok: Path, ders: str, konular: list[str], bugun: date) -> None:
    liste = _tekrar_oku(kok, ders)
    var = {(e["konu"], e["tarih"]) for e in liste}
    for konu in konular:
        for g in TEKRAR_GUNLERI:
            t = (bugun + timedelta(days=g)).isoformat()
            if (konu, t) not in var:
                liste.append({"konu": konu, "tarih": t, "yapildi": False})
                var.add((konu, t))
    dersler.json_yaz(_tekrar_yolu(kok, ders), liste)


def bugun_tekrar(kok: Path, ders: str, bugun: date) -> list[dict]:
    return [e for e in _tekrar_oku(kok, ders) if not e["yapildi"] and e["tarih"] <= bugun.isoformat()]


def tekrar_yapildi(kok: Path, ders: str, konu: str, bugun: date) -> None:
    liste = _tekrar_oku(kok, ders)
    for e in liste:
        if e["konu"] == konu and e["tarih"] <= bugun.isoformat():
            e["yapildi"] = True
    dersler.json_yaz(_tekrar_yolu(kok, ders), liste)


def not_ekle(kok: Path, ders: str, metin: str, simdi: datetime) -> None:
    satir = " ".join(metin.split())
    if not satir:
        return
    with (dersler.ders_yolu(kok, ders) / "notlar.md").open("a", encoding="utf-8") as f:
        f.write(f"- [{simdi:%Y-%m-%d %H:%M}] {satir}\n")


def notlar(kok: Path, ders: str) -> list[str]:
    y = dersler.ders_yolu(kok, ders) / "notlar.md"
    return y.read_text("utf-8").splitlines() if y.exists() else []
