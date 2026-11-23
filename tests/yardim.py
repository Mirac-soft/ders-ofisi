"""Testler için ortak: geçici kök, sahte claude ayarları, kayıt okuma."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from ofis import ayarlar

SAHTE = str(Path(__file__).with_name("sahte_claude.py"))


class SahteClaudeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name) / "Dersler"
        self.kok.mkdir()
        self.kayit = Path(self.tmp.name) / "kayit.jsonl"
        self.ayar = ayarlar.yukle() | {"claude_komutu": [sys.executable, SAHTE]}
        self._eski = {k: os.environ.get(k) for k in ("SAHTE_CLAUDE_MOD", "SAHTE_CLAUDE_CEVAPLAR", "SAHTE_CLAUDE_KAYIT",
                                                     "SAHTE_CLAUDE_LIMIT_SONRA", "SAHTE_CLAUDE_BEKLE")}
        for k in self._eski:
            os.environ.pop(k, None)
        os.environ["SAHTE_CLAUDE_KAYIT"] = str(self.kayit)

    def tearDown(self):
        for k, v in self._eski.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def cevaplar(self, **c):
        os.environ["SAHTE_CLAUDE_CEVAPLAR"] = json.dumps(c, ensure_ascii=False)

    def cagrilar(self) -> list[dict]:
        if not self.kayit.exists():
            return []
        return [json.loads(s) for s in self.kayit.read_text("utf-8").splitlines()]
