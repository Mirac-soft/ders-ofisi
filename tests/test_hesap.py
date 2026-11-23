import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from ofis import dersler, hesap


def t(gun, saat, dk=0):
    return datetime(2026, 11, gun, saat, dk)


class HesapTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)
        dersler.ders_olustur(self.kok, "CS", "2026-12-23", [f"K{i}" for i in range(10)])
        dersler.ders_olustur(self.kok, "Math 1", "2027-01-15", ["Limit"])

    def tearDown(self):
        self.tmp.cleanup()

    def oturumlar(self, ders):
        return dersler.oku(self.kok, ders)["oturumlar"]

    def test_ders_degisince_sure(self):
        hesap.sure_basla(self.kok, "CS", t(23, 10))
        hesap.sure_basla(self.kok, "Math 1", t(23, 11))
        self.assertEqual(self.oturumlar("CS"), [{"basla": "2026-11-23T10:00:00", "bitis": "2026-11-23T11:00:00"}])
        self.assertIsNone(self.oturumlar("Math 1")[0]["bitis"])
        hesap.sure_dur(self.kok, "Math 1", t(23, 11, 30))
        self.assertEqual(self.oturumlar("Math 1")[0]["bitis"], "2026-11-23T11:30:00")

    def test_acik_oturum_kapanir(self):
        hesap.sure_basla(self.kok, "CS", t(23, 10))  # sunucu çöktü, oturum açık kaldı
        hesap.sure_basla(self.kok, "CS", t(23, 12))
        o = self.oturumlar("CS")
        self.assertEqual(len(o), 2)
        self.assertEqual(o[0]["bitis"], "2026-11-23T12:00:00")
        self.assertIsNone(o[1]["bitis"])

    def test_dur_acik_yoksa_sessiz(self):
        hesap.sure_dur(self.kok, "CS", t(23, 10))
        self.assertEqual(self.oturumlar("CS"), [])

    def test_analiz(self):
        v = dersler.oku(self.kok, "CS")
        v["konular"][0]["bitti"] = v["konular"][1]["bitti"] = True
        v["oturumlar"] = [{"basla": "2026-11-20T10:00:00", "bitis": "2026-11-20T12:00:00"},
                          {"basla": "2026-11-22T10:00:00", "bitis": "2026-11-22T12:00:00"}]
        dersler.yaz(self.kok, "CS", v)
        a = hesap.sure_analizi(self.kok, "CS", t(23, 9))
        self.assertEqual((a["bitti"], a["kalan"], a["kalan_gun"]), (2, 8, 30))
        self.assertAlmostEqual(a["toplam_saat"], 4)
        self.assertAlmostEqual(a["gereken_saat"], 16)
        self.assertAlmostEqual(a["gunluk_ort_saat"], 4 / 7)
        self.assertAlmostEqual(a["kapasite_saat"], 30 * 4 / 7)
        self.assertTrue(a["yetisir"])
        self.assertIn("yetişiyorsun", a["yorum"])
        self.assertEqual(len(a["son7"]), 7)
        self.assertAlmostEqual(a["son7"][-2]["saat"], 2)  # 22 Kasım

    def test_analiz_yetismez(self):
        v = dersler.oku(self.kok, "CS")
        v["konular"][0]["bitti"] = True
        v["oturumlar"] = [{"basla": "2026-11-22T10:00:00", "bitis": "2026-11-22T14:00:00"}]
        dersler.yaz(self.kok, "CS", v)
        a = hesap.sure_analizi(self.kok, "CS", t(23, 9))
        self.assertFalse(a["yetisir"])  # 9 konu × 4 saat = 36 saat; kapasite 30 × 4/7 ≈ 17
        self.assertIn("günde ~1.2 saat", a["yorum"])

    def test_acik_oturum_sayilir(self):
        hesap.sure_basla(self.kok, "CS", t(23, 8))
        self.assertAlmostEqual(hesap.sure_analizi(self.kok, "CS", t(23, 9, 30))["toplam_saat"], 1.5)

    def test_analiz_veri_yok(self):
        a = hesap.sure_analizi(self.kok, "CS", t(23, 9))
        self.assertIsNone(a["yetisir"])
        self.assertIsNone(a["gereken_saat"])
        self.assertIn("veri yok", a["yorum"])

    def test_sinav_gecti(self):
        v = dersler.oku(self.kok, "CS")
        v["sinav_tarihi"] = "2026-11-01"
        v["konular"][0]["bitti"] = True
        v["oturumlar"] = [{"basla": "2026-11-22T10:00:00", "bitis": "2026-11-22T12:00:00"}]
        dersler.yaz(self.kok, "CS", v)
        a = hesap.sure_analizi(self.kok, "CS", t(23, 9))
        self.assertEqual(a["kalan_gun"], 0)
        self.assertIn("Sınav bugün/geçti", a["yorum"])

    def test_tekrar(self):
        hesap.tekrar_ekle(self.kok, "CS", ["K1"], date(2026, 11, 23))
        hesap.tekrar_ekle(self.kok, "CS", ["K1"], date(2026, 11, 23))  # çiftlenmez
        tekrar = json.loads((self.kok / "CS" / "tekrar.json").read_text("utf-8"))
        self.assertEqual([e["tarih"] for e in tekrar], ["2026-11-24", "2026-11-26", "2026-11-30"])
        self.assertEqual(len(hesap.bugun_tekrar(self.kok, "CS", date(2026, 11, 26))), 2)
        hesap.tekrar_yapildi(self.kok, "CS", "K1", date(2026, 11, 26))
        self.assertEqual(hesap.bugun_tekrar(self.kok, "CS", date(2026, 11, 26)), [])
        self.assertEqual(len(hesap.bugun_tekrar(self.kok, "CS", date(2026, 11, 30))), 1)

    def test_notlar(self):
        hesap.not_ekle(self.kok, "CS", "Big-O sınavda çıkar", t(23, 10, 5))
        hesap.not_ekle(self.kok, "CS", "satır\nkırılımı", t(23, 10, 6))
        self.assertEqual(hesap.notlar(self.kok, "CS"),
                         ["- [2026-11-23 10:05] Big-O sınavda çıkar", "- [2026-11-23 10:06] satır kırılımı"])


if __name__ == "__main__":
    unittest.main()
