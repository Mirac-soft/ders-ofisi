import tempfile
import unittest
from pathlib import Path

from ofis import ayarlar, dersler


class DerslerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_olustur_ve_oku(self):
        dersler.ders_olustur(self.kok, "Math 1", "2027-01-15", ["Limit", "Türev"])
        v = dersler.oku(self.kok, "Math 1")
        self.assertEqual(v["konular"], [{"ad": "Limit", "bitti": False}, {"ad": "Türev", "bitti": False}])
        self.assertEqual(v["sinav_tarihi"], "2027-01-15")
        self.assertEqual(v["oturumlar"], [])
        self.assertEqual(v["sohbetler"], {})
        self.assertEqual(dersler.listele(self.kok), ["Math 1"])
        for alt in ["pdf", "metin", "ozet", "formuller", "sorular", "sinavlar", "gorseller"]:
            self.assertTrue((self.kok / "Math 1" / alt).is_dir(), alt)

    def test_yaz(self):
        dersler.ders_olustur(self.kok, "CS", "2027-01-15", [])
        v = dersler.oku(self.kok, "CS")
        v["konular"].append({"ad": "Döngüler", "bitti": True})
        dersler.yaz(self.kok, "CS", v)
        self.assertEqual(dersler.oku(self.kok, "CS")["konular"][0]["ad"], "Döngüler")

    def test_ayni_ders_iki_kez(self):
        dersler.ders_olustur(self.kok, "CS", "2027-01-15", [])
        with self.assertRaises(FileExistsError):
            dersler.ders_olustur(self.kok, "CS", "2027-01-15", [])

    def test_bilinmeyen_ders(self):
        with self.assertRaises(FileNotFoundError):
            dersler.oku(self.kok, "Yok")

    def test_gecersiz_ad(self):
        for ad in ["..", "../x", "a/b", "a\\b", "C:", "", " ", "con", "COM1", "a*b", ".gizli", "x" * 61]:
            with self.assertRaises(dersler.GecersizAd, msg=repr(ad)):
                dersler.ders_yolu(self.kok, ad)

    def test_guvenli_dosya(self):
        dersler.ders_olustur(self.kok, "Fizik", "2027-01-15", [])
        with self.assertRaises(dersler.GecersizAd):
            dersler.guvenli_dosya(self.kok, "Fizik", "../../ayarlar.json")
        self.assertEqual(dersler.guvenli_dosya(self.kok, "Fizik", "ozet/a.md"),
                         (self.kok / "Fizik" / "ozet" / "a.md").resolve())

    def test_eszamanli_yazma_okuma(self):
        import threading
        dersler.ders_olustur(self.kok, "CS", "2027-01-15", ["A"])
        hatalar, dur = [], threading.Event()

        def oku():
            while not dur.is_set():
                try:
                    dersler.oku(self.kok, "CS")
                except Exception as e:
                    hatalar.append(e)

        t = threading.Thread(target=oku)
        t.start()
        try:
            for i in range(300):
                v = dersler.oku(self.kok, "CS")
                v["konular"][0]["bitti"] = bool(i % 2)
                dersler.yaz(self.kok, "CS", v)
        except Exception as e:
            hatalar.append(e)
        dur.set()
        t.join()
        self.assertEqual(hatalar, [])

    def test_ayarlar(self):
        a = ayarlar.yukle()
        self.assertEqual(a["es_zamanli"], 2)
        self.assertEqual(a["parca_sayfa"], 20)
        self.assertEqual(a["modeller"]["arastirmaci"], "haiku")
        self.assertEqual(a["modeller"]["ozetci"], "sonnet")
        self.assertIsInstance(a["claude_komutu"], list)


if __name__ == "__main__":
    unittest.main()
