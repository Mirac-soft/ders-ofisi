import tempfile
import unittest
from pathlib import Path

import pymupdf

from ofis import pdf_isleme


def ornek_pdf(yol: Path, sayfa=45):
    d = pymupdf.open()
    for i in range(sayfa):
        s = d.new_page(width=600, height=800)
        s.insert_text((72, 72), f"Sayfa {i + 1}  F = m a", fontsize=14)
        if i == 2:
            s.draw_rect(pymupdf.Rect(300, 400, 600, 800), color=(0, 0, 0), fill=(0, 0, 0))
    d.save(yol)
    return yol


class PdfIslemeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.pdf = ornek_pdf(self.d / "notlar.pdf")

    def tearDown(self):
        self.tmp.cleanup()

    def test_sayfa_sayisi(self):
        self.assertEqual(pdf_isleme.sayfa_sayisi(self.pdf), 45)

    def test_parcala(self):
        p = pdf_isleme.parcala(self.pdf, self.d / "parcalar", 20)
        self.assertEqual([(a, b) for _, a, b in p], [(1, 20), (21, 40), (41, 45)])
        self.assertEqual([y.name for y, _, _ in p], ["parca-01.pdf", "parca-02.pdf", "parca-03.pdf"])
        self.assertEqual(pdf_isleme.sayfa_sayisi(p[2][0]), 5)
        zaman = p[0][0].stat().st_mtime_ns
        pdf_isleme.parcala(self.pdf, self.d / "parcalar", 20)  # var olan yeniden üretilmez
        self.assertEqual(p[0][0].stat().st_mtime_ns, zaman)

    def test_kes_boyut(self):
        c = pdf_isleme.kes(self.pdf, 3, [50, 50, 100, 100], self.d / "k.png")
        pix = pymupdf.Pixmap(str(c))
        tam = 600 * 200 / 72
        self.assertAlmostEqual(pix.width / tam, 0.52, delta=0.02)  # %50 + sol tarafta %2 pay; sağ kenarda kırpılır
        self.assertAlmostEqual(pix.height / (800 * 200 / 72), 0.52, delta=0.02)
        # kesilen bölge siyah dikdörtgenin içi: ortadaki piksel koyu
        self.assertLess(sum(pix.pixel(pix.width * 3 // 4, pix.height * 3 // 4)[:3]), 60)

    def test_bozuk_kutu(self):
        tam = pdf_isleme.kes(self.pdf, 3, [0, 0, 100, 100], self.d / "tam.png")
        tam_gen = pymupdf.Pixmap(str(tam)).width
        for i, kutu in enumerate([[90, 10, 10, 90], [-50, 0, 300, 100], [], ["a", 1, 2, 3], [10, 10, 10, 50], None]):
            c = pdf_isleme.kes(self.pdf, 3, kutu, self.d / f"b{i}.png")
            self.assertTrue(c.exists(), kutu)
        # ters kutu düzeltilir: [10,10,90,90] gibi davranır
        self.assertAlmostEqual(pymupdf.Pixmap(str(self.d / "b0.png")).width / tam_gen, 0.84, delta=0.02)
        # alanı 0 → tam sayfa
        self.assertEqual(pymupdf.Pixmap(str(self.d / "b4.png")).width, tam_gen)
        with self.assertRaises(ValueError):
            pdf_isleme.kes(self.pdf, 99, [0, 0, 10, 10], self.d / "x.png")
        with self.assertRaises(ValueError):
            pdf_isleme.kes(self.pdf, 0, [0, 0, 10, 10], self.d / "x.png")

    def test_tam_sayfa(self):
        c = pdf_isleme.tam_sayfa(self.pdf, 1, self.d / "s1.png")
        self.assertEqual(pymupdf.Pixmap(str(c)).width, round(600 * 120 / 72))


if __name__ == "__main__":
    unittest.main()
