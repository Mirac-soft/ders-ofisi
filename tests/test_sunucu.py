import json
import os
import threading
import time
import unittest
import urllib.error
import urllib.request
from urllib.parse import quote

from ofis import sunucu
from tests.test_cevirme import CEVAP
from tests.test_pdf_isleme import ornek_pdf
from tests.yardim import SahteClaudeTest


class SunucuTest(SahteClaudeTest):
    def setUp(self):
        super().setUp()
        self.srv = sunucu.olustur(self.ayar | {"port": 0}, self.kok)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        super().tearDown()

    def istek(self, yol, govde=None, yontem=None, basliklar=None):
        veri = json.dumps(govde).encode() if isinstance(govde, (dict, list)) else govde
        r = urllib.request.Request(self.url + yol, data=veri, method=yontem, headers=basliklar or {})
        try:
            with urllib.request.urlopen(r, timeout=10) as y:
                icerik = y.read()
                return y.status, json.loads(icerik) if y.headers.get_content_type() == "application/json" else icerik
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read()

    def ders(self, ad="CS", konular=("Limit", "Türev")):
        return self.istek("/api/dersler", {"ad": ad, "sinav_tarihi": "2027-01-15", "konular": list(konular)})

    def test_ders_akisi(self):
        self.assertEqual(self.ders()[0], 200)
        self.assertEqual(self.ders()[0], 409)
        self.assertEqual(self.istek("/api/dersler", {"ad": "X", "sinav_tarihi": "yarın", "konular": []})[0], 400)
        self.assertEqual(self.istek("/api/dersler")[1]["dersler"], ["CS"])
        self.assertEqual(self.istek("/api/ders/CS/not", {"metin": "önemli şey"})[0], 200)
        self.assertEqual(self.istek("/api/ders/CS/konu", {"konu": "Limit", "bitti": True})[0], 200)
        self.assertEqual(self.istek("/api/ders/CS/sure", {"olay": "basla"})[0], 200)
        d = self.istek("/api/ders/CS")[1]
        self.assertIn("önemli şey", d["notlar"][0])
        self.assertTrue(d["konular"][0]["bitti"])
        self.assertIsNone(d["oturumlar"][0]["bitis"])
        self.assertIn("yorum", d["analiz"])
        self.assertEqual(self.istek("/api/ders/Yok")[0], 404)

    def test_konular_guncelle(self):
        self.ders()
        self.istek("/api/ders/CS/konu", {"konu": "Limit", "bitti": True})
        self.istek("/api/ders/CS/konular", {"konular": ["Limit", "Seriler"]})
        k = self.istek("/api/ders/CS")[1]["konular"]
        self.assertEqual(k, [{"ad": "Limit", "bitti": True}, {"ad": "Seriler", "bitti": False}])

    def test_statik(self):
        s, icerik = self.istek("/")
        self.assertEqual(s, 200)
        self.assertIn(b"Ders Ofisi", icerik)
        self.assertEqual(self.istek("/ofis.js")[0], 200)

    def test_yol_kacisi(self):
        self.ders()
        for yol in ["/api/ders/..%2F..%2Fofis", "/api/ders/CS/dosya/..%2F..%2F..%2Fayarlar.json",
                    "/api/ders/CS/dosya/../../ayarlar.json", "/..%2Fayarlar.json", "/%2e%2e/ayarlar.json"]:
            self.assertIn(self.istek(yol)[0], (400, 404), yol)

    def test_pdf_degil(self):
        self.ders()
        s, _ = self.istek("/api/ders/CS/pdf", b"merhaba", "POST", {"X-Dosya-Adi": "a.pdf"})
        self.assertEqual(s, 400)
        s, _ = self.istek("/api/ders/CS/pdf", b"%PDF-1.4", "POST", {"X-Dosya-Adi": quote("../a.pdf")})
        self.assertEqual(s, 400)

    def test_pdf_yukle_olaylar(self):
        self.ders(konular=["Limit"])
        self.cevaplar(cevirici=CEVAP, ozetci={"ozet_md": "özet"}, formulcu={"formuller": []})
        olaylar = []

        def dinle():
            with urllib.request.urlopen(self.url + "/api/olaylar", timeout=15) as y:
                for satir in y:
                    if satir.startswith(b"data: "):
                        olaylar.append(json.loads(satir[6:]))

        threading.Thread(target=dinle, daemon=True).start()
        time.sleep(0.3)
        pdf = ornek_pdf(self.kok.parent / "Ders Notu.pdf", sayfa=25)
        s, _ = self.istek("/api/ders/CS/pdf", pdf.read_bytes(), "POST", {"X-Dosya-Adi": quote("Ders Notu.pdf")})
        self.assertEqual(s, 200)
        bitis = time.time() + 20
        while time.time() < bitis:
            gorulen = {(o["asistan"], o["durum"]) for o in olaylar}
            if {("cevirici", "calisiyor"), ("ozetci", "bitti"), ("formulcu", "bitti")} <= gorulen and \
                    sum(o == ("ozetci", "bitti") for o in [(x["asistan"], x["durum"]) for x in olaylar]) >= 2:
                break
            time.sleep(0.1)
        gorulen = {(o["asistan"], o["durum"]) for o in olaylar}
        self.assertIn(("cevirici", "calisiyor"), gorulen)
        self.assertIn(("ozetci", "bitti"), gorulen)
        d = self.istek("/api/ders/CS")[1]
        self.assertEqual(d["pdfler"], [{"ad": "Ders Notu", "tamam": 2, "toplam": 2}])
        self.assertIn("Ders Notu", d["ozetler"])
        s, png = self.istek("/api/ders/CS/dosya/gorseller/Ders%20Notu-s2-1.png")
        self.assertEqual((s, png[:4]), (200, b"\x89PNG"))
        s, png = self.istek("/api/ders/CS/sayfa/Ders%20Notu/3")
        self.assertEqual((s, png[:4]), (200, b"\x89PNG"))
        self.assertEqual(self.istek("/api/ders/CS/pdf", pdf.read_bytes(), "POST", {"X-Dosya-Adi": quote("Ders Notu.pdf")})[0], 409)

    def test_limit_429(self):
        self.ders()
        os.environ["SAHTE_CLAUDE_MOD"] = "limit"
        s, govde = self.istek("/api/ders/CS/soru", {"mesaj": "limit ne?"})
        self.assertEqual(s, 429)
        self.assertEqual(json.loads(govde)["hata"], "limit")

    def test_sinav(self):
        self.ders()
        self.cevaplar(sinavci={"mesaj": "Soru 1?", "bitti": False, "sonuc": None})
        s, g = self.istek("/api/ders/CS/sinav", {"mesaj": "başla", "konular": ["Limit"]})
        self.assertEqual((s, g["mesaj"]), (200, "Soru 1?"))


if __name__ == "__main__":
    unittest.main()
