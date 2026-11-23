"""PDF parçalama ve hocanın notlarından görsel (formül/şekil) kesme."""
from pathlib import Path

import pymupdf


def sayfa_sayisi(pdf: Path) -> int:
    with pymupdf.open(pdf) as d:
        return d.page_count


def parcala(pdf: Path, hedef: Path, parca_sayfa: int) -> list[tuple[Path, int, int]]:
    hedef.mkdir(parents=True, exist_ok=True)
    sonuc = []
    with pymupdf.open(pdf) as d:
        for no, ilk in enumerate(range(0, d.page_count, parca_sayfa), 1):
            son = min(ilk + parca_sayfa, d.page_count)
            yol = hedef / f"parca-{no:02d}.pdf"
            if not yol.exists():
                with pymupdf.open() as p:
                    p.insert_pdf(d, from_page=ilk, to_page=son - 1)
                    p.save(yol)
            sonuc.append((yol, ilk + 1, son))
    return sonuc


def _kutu_duzelt(kutu) -> tuple[float, float, float, float] | None:
    """Yüzde kutuyu sırala ve 0–100'e kırp; geçersiz veya alanı 0 ise None (tam sayfa)."""
    try:
        x0, y0, x1, y1 = (float(v) for v in kutu)
    except (TypeError, ValueError):
        return None
    x0, x1 = sorted((min(max(x0, 0), 100), min(max(x1, 0), 100)))
    y0, y1 = sorted((min(max(y0, 0), 100), min(max(y1, 0), 100)))
    if x1 - x0 <= 0 or y1 - y0 <= 0:
        return None
    return x0, y0, x1, y1


def kes(pdf: Path, sayfa: int, kutu, cikti: Path, dpi: int = 200, pay: float = 2.0) -> Path:
    with pymupdf.open(pdf) as d:
        if not 1 <= sayfa <= d.page_count:
            raise ValueError(f"sayfa {sayfa} yok (1–{d.page_count})")
        s = d[sayfa - 1]
        r = s.rect
        k = _kutu_duzelt(kutu)
        if k is None:
            alan = r
        else:
            x0, y0, x1, y1 = (max(k[0] - pay, 0), max(k[1] - pay, 0), min(k[2] + pay, 100), min(k[3] + pay, 100))
            alan = pymupdf.Rect(r.x0 + r.width * x0 / 100, r.y0 + r.height * y0 / 100,
                                r.x0 + r.width * x1 / 100, r.y0 + r.height * y1 / 100)
        cikti.parent.mkdir(parents=True, exist_ok=True)
        s.get_pixmap(dpi=dpi, clip=alan).save(cikti)
    return cikti


def tam_sayfa(pdf: Path, sayfa: int, cikti: Path, dpi: int = 120) -> Path:
    with pymupdf.open(pdf) as d:
        if not 1 <= sayfa <= d.page_count:
            raise ValueError(f"sayfa {sayfa} yok")
        cikti.parent.mkdir(parents=True, exist_ok=True)
        d[sayfa - 1].get_pixmap(dpi=dpi).save(cikti)
    return cikti


def sayfa_gorselleri(pdf: Path, ilk: int, son: int, hedef: Path, dpi: int = 110) -> list[Path]:
    """Claude'un Read aracı büyük PDF'ler için poppler ister; sayfaları resim olarak veririz (PNG her yerde okunur)."""
    hedef.mkdir(parents=True, exist_ok=True)
    yollar = []
    with pymupdf.open(pdf) as d:
        for no in range(ilk, son + 1):
            yol = hedef / f"s-{no:03d}.png"
            if not yol.exists():
                d[no - 1].get_pixmap(dpi=dpi).save(yol)
            yollar.append(yol)
    return yollar


def metin_katmani(pdf: Path, ilk: int, son: int) -> str:
    """PDF'in seçilebilir metni (varsa): Claude metni resimden değil buradan doğru aktarsın."""
    with pymupdf.open(pdf) as d:
        return "\n".join(f"--- Sayfa {no} ---\n{d[no - 1].get_text().strip()}" for no in range(ilk, son + 1))
