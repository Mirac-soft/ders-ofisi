import json
import os
import shutil
import unittest

from ofis import cevirme, dersler
from ofis.claude_calistir import ClaudeHatasi, LimitDolu
from tests.test_pdf_isleme import ornek_pdf
from tests.yardim import SahteClaudeTest

CEVAP = {"markdown": "# Başlık\nNewton: [[G1]] ve olmayan [[G9]] sonu.",
         "gorseller": [{"yer_tutucu": "G1", "sayfa": 2, "kutu": [10, 10, 60, 30], "tur": "formul", "aciklama": "F=ma"},
                       {"yer_tutucu": "G2", "sayfa": 99, "kutu": [0, 0, 10, 10], "tur": "sekil", "aciklama": "bozuk sayfa"}],
         "konular": ["Limit", "Uydurma"]}


class CevirmeTest(SahteClaudeTest):
    def setUp(self):
        super().setUp()
        dersler.ders_olustur(self.kok, "Math 1", "2027-01-15", ["Limit", "Türev"])
        self.ders = self.kok / "Math 1"
        ornek_pdf(self.ders / "pdf" / "notlar.pdf")
        self.cevaplar(cevirici=CEVAP)
        self.geri = []

    def cevir(self):
        cevirme.cevir(self.ayar, self.kok, "Math 1", "notlar", lambda no, md: self.geri.append((no, md)))

    def durum(self):
        return json.loads((self.ders / "metin/notlar/durum.json").read_text("utf-8"))

    def test_uc_parca_cevrilir(self):
        self.cevir()
        self.assertEqual([no for no, _ in self.geri], [1, 2, 3])
        md = (self.ders / "metin/notlar/parca-02.md").read_text("utf-8")
        self.assertIn("](../../gorseller/notlar-s22-1.png)", md)
        self.assertIn("![F=ma]", md)
        self.assertNotIn("[[G", md)
        self.assertTrue((self.ders / "gorseller/notlar-s22-1.png").exists())
        gorseller = json.loads((self.ders / "metin/notlar/gorseller.json").read_text("utf-8"))
        self.assertEqual(len(gorseller), 3)  # her parçadan 1 geçerli görsel; sayfa 99 atılır
        self.assertEqual(gorseller[1], {"dosya": "notlar-s22-1.png", "sayfa": 22, "tur": "formul", "aciklama": "F=ma", "parca": 2})
        konular = json.loads((self.ders / "metin/notlar/konular.json").read_text("utf-8"))
        self.assertEqual(konular["2"], ["Limit"])
        self.assertEqual((self.durum()["tamam"], self.durum()["toplam"]), ([1, 2, 3], 3))
        c = self.cagrilar()[1]
        istem = c["argv"][c["argv"].index("-p") + 1]
        # Claude PDF'i değil, sayfa resimlerini ve metin katmanını okur (Read aracı PDF için poppler ister)
        self.assertIn("pdf/notlar-sayfalar/s-021.png", istem)
        self.assertIn("pdf/notlar-sayfalar/s-040.png", istem)
        self.assertNotIn(".pdf", istem)
        self.assertTrue((self.ders / "pdf/notlar-sayfalar/s-021.png").exists())
        self.assertIn("pdf/notlar-sayfalar/metin-02.txt", istem)
        self.assertIn("Sayfa 21  F = m a", (self.ders / "pdf/notlar-sayfalar/metin-02.txt").read_text("utf-8"))
        self.assertIn("Limit", istem)
        self.assertEqual(c["argv"][c["argv"].index("--model") + 1], "sonnet")

    def test_bos_cevap_tamam_sayilmaz(self):
        self.cevaplar(cevirici={"markdown": "  ", "gorseller": [], "konular": []})
        with self.assertRaises(ClaudeHatasi):
            self.cevir()
        self.assertEqual(self.durum()["tamam"], [])
        self.assertEqual(self.geri, [])
        self.assertFalse((self.ders / "metin/notlar/parca-01.md").exists())

    def test_sure_kaydedilir(self):
        self.cevir()
        self.assertEqual(len(self.durum()["sureler"]), 3)

    def test_limitte_durur_ve_devam_eder(self):
        os.environ["SAHTE_CLAUDE_LIMIT_SONRA"] = "1"
        with self.assertRaises(LimitDolu):
            self.cevir()
        self.assertEqual(self.durum()["tamam"], [1])
        self.assertEqual([no for no, _ in self.geri], [1])
        del os.environ["SAHTE_CLAUDE_LIMIT_SONRA"]
        self.cevir()
        self.assertEqual(self.durum()["tamam"], [1, 2, 3])
        istemler = [c["argv"][c["argv"].index("-p") + 1] for c in self.cagrilar()]
        self.assertEqual(len(istemler), 4)  # 1 başarılı + 1 limit + 2 devam
        self.assertIn("metin-02.txt", istemler[2])
        self.assertIn("metin-03.txt", istemler[3])

    def test_yeniden_baslatmada_devam(self):
        self.cevir()
        shutil.copy(self.kayit, self.kayit.with_suffix(".bak"))
        self.kayit.unlink()
        d = self.durum()
        d["tamam"] = [1, 2]
        (self.ders / "metin/notlar/durum.json").write_text(json.dumps(d), "utf-8")
        self.cevir()
        self.assertEqual(len(self.cagrilar()), 1)
        gorseller = json.loads((self.ders / "metin/notlar/gorseller.json").read_text("utf-8"))
        self.assertEqual(len([g for g in gorseller if g["parca"] == 3]), 1)  # parça 3 görseli çiftlenmez


if __name__ == "__main__":
    unittest.main()
