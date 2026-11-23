import os
import threading
import time
import unittest
from pathlib import Path

from ofis import claude_calistir, dersler
from ofis.olaylar import Yayinci
from tests.yardim import SahteClaudeTest

TALIMAT = Path(__file__).resolve().parent.parent / "talimatlar" / "ozetci.md"


class CagirTest(SahteClaudeTest):
    def cagir(self, ders="CS", **k):
        dersler.ders_olustur(self.kok, ders, "2027-01-15", []) if ders not in dersler.listele(self.kok) else None
        return claude_calistir.cagir(self.ayar, dersler.ders_yolu(self.kok, ders), "istem", "sonnet", TALIMAT,
                                     {"type": "object"}, ["Read"], **k)

    def test_argumanlar_ve_cwd(self):
        self.cevaplar(**{"*": {"a": 1}})
        sonuc, oturum = self.cagir()
        self.assertEqual(sonuc, {"a": 1})
        self.assertEqual(oturum, "s-CS")
        c = self.cagrilar()[0]
        for arg in ["-p", "istem", "--output-format", "json", "--model", "sonnet", "--json-schema", "--allowedTools", "Read(./**)",
                    "--append-system-prompt-file"]:
            self.assertIn(arg, c["argv"])
        self.assertNotIn("--resume", c["argv"])
        self.assertEqual(Path(c["cwd"]).resolve(), (self.kok / "CS").resolve())

    def test_resume(self):
        self.cagir(oturum="abc")
        argv = self.cagrilar()[0]["argv"]
        self.assertEqual(argv[argv.index("--resume") + 1], "abc")

    def test_limit(self):
        os.environ["SAHTE_CLAUDE_MOD"] = "limit"
        with self.assertRaises(claude_calistir.LimitDolu):
            self.cagir()

    def test_hata(self):
        os.environ["SAHTE_CLAUDE_MOD"] = "hata"
        with self.assertRaises(claude_calistir.ClaudeHatasi):
            self.cagir()


class KuyrukTest(unittest.TestCase):
    def setUp(self):
        self.y = Yayinci()
        self.q = self.y.abone()
        self.k = claude_calistir.Kuyruk(2, self.y)

    def olaylar(self, n, sure=5):
        sonuc = []
        bitis = time.time() + sure
        while len(sonuc) < n and time.time() < bitis:
            try:
                sonuc.append(self.q.get(timeout=0.1))
            except Exception:
                pass
        return sonuc

    def test_kuyruk_en_fazla_iki(self):
        kilit = threading.Lock()
        sayac = {"simdi": 0, "en_cok": 0}
        serbest = threading.Event()

        def is_():
            with kilit:
                sayac["simdi"] += 1
                sayac["en_cok"] = max(sayac["en_cok"], sayac["simdi"])
            serbest.wait(2)
            time.sleep(0.05)
            with kilit:
                sayac["simdi"] -= 1

        for i in range(5):
            self.k.ekle("CS", f"a{i}", is_)
        time.sleep(0.3)
        self.assertEqual(sayac["en_cok"], 2)
        serbest.set()
        bitti = [o for o in self.olaylar(10) if o["durum"] == "bitti"]
        self.assertEqual(len(bitti), 5)
        self.assertEqual(sayac["en_cok"], 2)

    def test_kuyruk_durumlari(self):
        def limit():
            raise claude_calistir.LimitDolu("limit")

        def bozuk():
            raise ValueError("x")

        self.k.ekle("CS", "ozetci", limit)
        self.k.ekle("CS", "formulcu", bozuk)
        self.k.ekle("Math 1", "arastirmaci", lambda: None)
        son = {}
        for o in self.olaylar(6):
            son[o["asistan"]] = o
            self.assertIn(o["ders"], ("CS", "Math 1"))
        self.assertEqual(son["ozetci"]["durum"], "bekliyor")
        self.assertEqual(son["formulcu"]["durum"], "hata")
        self.assertEqual(son["arastirmaci"]["durum"], "bitti")
        self.assertEqual(son["arastirmaci"]["ders"], "Math 1")

    def test_senkron(self):
        self.assertEqual(self.k.senkron("CS", "sinavci", lambda: 42), 42)
        with self.assertRaises(claude_calistir.LimitDolu):
            self.k.senkron("CS", "sinavci", lambda: (_ for _ in ()).throw(claude_calistir.LimitDolu("x")))
        self.assertEqual([o["durum"] for o in self.olaylar(4)], ["calisiyor", "bitti", "calisiyor", "bekliyor"])


class KendiDersineYazarTest(SahteClaudeTest):
    def test_is_kendi_dersine_yazar(self):
        for d in ("CS", "Math 1"):
            dersler.ders_olustur(self.kok, d, "2027-01-15", [])
        y = Yayinci()
        q = y.abone()
        k = claude_calistir.Kuyruk(2, y)
        os.environ["SAHTE_CLAUDE_BEKLE"] = "0.3"

        def is_(ders):
            return lambda: claude_calistir.cagir(self.ayar, dersler.ders_yolu(self.kok, ders), "x", "sonnet", TALIMAT,
                                                 {"type": "object"}, ["Read"])

        k.ekle("CS", "ozetci", is_("CS"))
        time.sleep(0.05)  # kullanıcı derse geçti
        k.ekle("Math 1", "ozetci", is_("Math 1"))
        olaylar = []
        bitis = time.time() + 10
        while sum(o["durum"] == "bitti" for o in olaylar) < 2 and time.time() < bitis:
            try:
                olaylar.append(q.get(timeout=0.1))
            except Exception:
                pass
        cwdler = sorted(Path(c["cwd"]).name for c in self.cagrilar())
        self.assertEqual(cwdler, ["CS", "Math 1"])
        self.assertEqual(sorted(o["ders"] for o in olaylar if o["durum"] == "bitti"), ["CS", "Math 1"])


if __name__ == "__main__":
    unittest.main()
