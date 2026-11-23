"""`claude -p` çağrısı (abonelik ile) ve en fazla N eşzamanlı iş çalıştıran kuyruk.
Claude yalnızca okur ve şemaya uygun JSON döndürür; dosyaları sunucu yazar."""
import json
import re
import subprocess
import threading
import traceback
from pathlib import Path
from typing import Callable

_LIMIT = re.compile(r"limit|usage|rate", re.I)


class LimitDolu(Exception):
    pass


class ClaudeHatasi(Exception):
    pass


def cagir(ayar: dict, cwd: Path, istem: str, model: str, sistem_dosyasi: Path, sema: dict,
          araclar: list[str], oturum: str | None = None) -> tuple[dict, str]:
    komut = [*ayar["claude_komutu"], "-p", istem, "--output-format", "json", "--model", model,
             "--append-system-prompt-file", str(sistem_dosyasi), "--json-schema", json.dumps(sema, ensure_ascii=False),
             "--allowedTools", " ".join(araclar)]
    if oturum:
        komut += ["--resume", oturum]
    try:
        s = subprocess.run(komut, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=1800, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired as e:
        raise ClaudeHatasi("zaman aşımı") from e
    except FileNotFoundError as e:
        raise ClaudeHatasi(f"Claude Code bulunamadı: {ayar['claude_komutu'][0]}") from e
    try:
        cikti = json.loads(s.stdout.strip().splitlines()[-1]) if s.stdout.strip() else {}
    except json.JSONDecodeError:
        cikti = {}
    if cikti.get("is_error") or s.returncode != 0 or not cikti:
        metin = f"{cikti.get('result', '')} {s.stderr[-2000:]}"
        if cikti.get("api_error_status") == 429 or (cikti.get("is_error") and _LIMIT.search(metin)):
            raise LimitDolu(metin.strip())
        raise ClaudeHatasi(metin.strip() or f"çıkış kodu {s.returncode}")
    sonuc = cikti.get("structured_output")
    if sonuc is None:
        try:
            sonuc = json.loads(cikti.get("result") or "")
        except json.JSONDecodeError as e:
            raise ClaudeHatasi("Claude geçerli JSON döndürmedi") from e
    return sonuc, cikti.get("session_id", "")


class Kuyruk:
    def __init__(self, es_zamanli: int, yayinci):
        self._sem = threading.Semaphore(es_zamanli)
        self._y = yayinci

    def _olay(self, ders, asistan, durum, mesaj=""):
        self._y.yayinla({"ders": ders, "asistan": asistan, "durum": durum, "mesaj": mesaj})

    def senkron(self, ders: str, asistan: str, fn: Callable[[], object]):
        """Çağıranın iş parçacığında çalıştırır, sonucu döndürür, hatayı yukarı iletir."""
        with self._sem:
            self._olay(ders, asistan, "calisiyor")
            try:
                sonuc = fn()
            except LimitDolu as e:
                self._olay(ders, asistan, "bekliyor", str(e))
                raise
            except Exception as e:
                self._olay(ders, asistan, "hata", str(e))
                raise
            self._olay(ders, asistan, "bitti")
            return sonuc

    def ekle(self, ders: str, asistan: str, is_fn: Callable[[], None]) -> None:
        def calis():
            try:
                self.senkron(ders, asistan, is_fn)
            except LimitDolu:
                pass
            except Exception:
                traceback.print_exc()

        threading.Thread(target=calis, daemon=True).start()
