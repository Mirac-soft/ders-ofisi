import json
import os
import unittest

from ofis import asistanlar, dersler
from tests.yardim import SahteClaudeTest


class AsistanlarTest(SahteClaudeTest):
    def setUp(self):
        super().setUp()
        for d, konular in (("CS", ["Döngüler", "Diziler"]), ("Math 1", ["Limit", "Türev"])):
            dersler.ders_olustur(self.kok, d, "2027-01-15", konular)
        m = self.kok / "Math 1" / "metin" / "notlar"
        m.mkdir(parents=True)
        (m / "parca-01.md").write_text("Limit metni ![F](../../gorseller/notlar-s3-1.png)", "utf-8")
        (m / "parca-02.md").write_text("Türev metni", "utf-8")
        (m / "konular.json").write_text(json.dumps({"1": ["Limit"], "2": ["Türev"]}), "utf-8")
        (m / "gorseller.json").write_text(json.dumps([
            {"dosya": "notlar-s3-1.png", "sayfa": 3, "tur": "formul", "aciklama": "F=ma", "parca": 1},
            {"dosya": "notlar-s4-1.png", "sayfa": 4, "tur": "sekil", "aciklama": "grafik", "parca": 1}]), "utf-8")

    def istem(self, i=-1):
        a = self.cagrilar()[i]["argv"]
        return a[a.index("-p") + 1]

    def argv(self, i=-1):
        return self.cagrilar()[i]["argv"]

    def test_ozet_eklenir(self):
        self.cevaplar(ozetci={"ozet_md": "Özet\n> ⭐ önemli ![F](../../gorseller/notlar-s3-1.png)"})
        asistanlar.ozetle(self.ayar, self.kok, "Math 1", "notlar", 2)
        asistanlar.ozetle(self.ayar, self.kok, "Math 1", "notlar", 1)
        asistanlar.ozetle(self.ayar, self.kok, "Math 1", "notlar", 1)  # tekrar: çiftlenmez
        ozet = (self.kok / "Math 1/ozet/notlar.md").read_text("utf-8")
        self.assertEqual(ozet.count("## Parça 01"), 1)
        self.assertLess(ozet.index("## Parça 01"), ozet.index("## Parça 02"))
        self.assertIn("](../gorseller/notlar-s3-1.png)", ozet)  # ozet/ klasöründen doğru göreli yol
        self.assertIn("metin/notlar/parca-01.md", self.istem())
        self.assertEqual(self.argv()[self.argv().index("--allowedTools") + 1], "Read(./**)")

    def test_formul_goruntu(self):
        self.cevaplar(formulcu={"formuller": [
            {"dosya": "notlar-s3-1.png", "ad": "F=ma", "anlam": "kuvvet", "ne_zaman": "dinamik", "soru_tipi": "ivme bul"},
            {"dosya": "uydurma.png", "ad": "X", "anlam": "", "ne_zaman": "", "soru_tipi": ""}]})
        asistanlar.formul_cikar(self.ayar, self.kok, "Math 1", "notlar", 1)
        f = (self.kok / "Math 1/formuller/notlar.md").read_text("utf-8")
        self.assertIn("![F=ma](../gorseller/notlar-s3-1.png)", f)
        self.assertNotIn("uydurma.png", f)
        self.assertIn("ivme bul", f)
        self.assertIn("notlar-s3-1.png", self.istem())
        self.assertNotIn("notlar-s4-1.png", self.istem())  # şekil formül listesine girmez

    def test_formul_yoksa_claude_cagrilmaz(self):
        asistanlar.formul_cikar(self.ayar, self.kok, "Math 1", "notlar", 2)
        self.assertEqual(self.cagrilar(), [])
        self.assertIn("formül yok", (self.kok / "Math 1/formuller/notlar.md").read_text("utf-8"))

    def test_soru_kaynak_temizlenir(self):
        self.cevaplar(arastirmaci={"sorular": [
            {"metin": "S1", "zorluk": "kolay", "kaynak": "uydurma", "konu": "Limit"},
            {"metin": "S2", "zorluk": "zor", "kaynak": "https://ocw.mit.edu/x", "konu": "Limit"}]})
        asistanlar.soru_ara(self.ayar, self.kok, "Math 1", ["Limit"])
        dosyalar = list((self.kok / "Math 1/sorular").glob("*.json"))
        self.assertEqual(len(dosyalar), 1)
        s = json.loads(dosyalar[0].read_text("utf-8"))["sorular"]
        self.assertIsNone(s[0]["kaynak"])
        self.assertEqual(s[1]["kaynak"], "https://ocw.mit.edu/x")
        a = self.argv()
        self.assertEqual(a[a.index("--model") + 1], "haiku")
        self.assertEqual(a[a.index("--allowedTools") + 1], "Read(./**) WebSearch WebFetch")
        self.assertIn("metin/notlar/parca-01.md", self.istem())
        self.assertNotIn("parca-02", self.istem())

    def test_sinav_ders_basina_oturum(self):
        self.cevaplar(sinavci={"mesaj": "Soru 1?", "bitti": False, "sonuc": None})
        r = asistanlar.sinav(self.ayar, self.kok, "CS", "başla", ["Döngüler"])
        self.assertEqual(r["mesaj"], "Soru 1?")
        asistanlar.sinav(self.ayar, self.kok, "Math 1", "başla", ["Limit"])
        asistanlar.sinav(self.ayar, self.kok, "CS", "cevabım B", None)
        a = self.argv()
        self.assertEqual(a[a.index("--resume") + 1], "s-CS")
        self.assertNotIn("--resume", self.argv(0))
        self.assertIn("metin/notlar/parca-01.md", self.istem(1))
        self.assertEqual(dersler.oku(self.kok, "Math 1")["sohbetler"]["sinavci"], "s-Math 1")

    def test_sinav_bitince_tekrar(self):
        self.cevaplar(sinavci={"mesaj": "Bitti", "bitti": True,
                               "sonuc": {"dogru": 3, "yanlis": 2, "eksik_konular": ["Limit", "Yok"]}})
        asistanlar.sinav(self.ayar, self.kok, "Math 1", "başla", ["Limit"])
        tekrar = json.loads((self.kok / "Math 1/tekrar.json").read_text("utf-8"))
        self.assertEqual({e["konu"] for e in tekrar}, {"Limit"})
        self.assertEqual(len(tekrar), 3)
        sinav = json.loads(next((self.kok / "Math 1/sinavlar").glob("*.json")).read_text("utf-8"))
        self.assertEqual(sinav["eksik_konular"], ["Limit"])
        self.assertNotIn("sinavci", dersler.oku(self.kok, "Math 1")["sohbetler"])

    def test_soru_sor(self):
        self.cevaplar(soru_cevap={"mesaj": "Limit şudur"})
        self.assertEqual(asistanlar.soru_sor(self.ayar, self.kok, "Math 1", "limit ne?")["mesaj"], "Limit şudur")
        self.assertIn("konular.json", self.istem())
        asistanlar.soru_sor(self.ayar, self.kok, "Math 1", "örnek?")
        a = self.argv()
        self.assertEqual(a[a.index("--resume") + 1], "s-Math 1")


if __name__ == "__main__":
    unittest.main()
