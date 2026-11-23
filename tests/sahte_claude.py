"""Testlerde gerçek `claude` yerine çalışır. Davranış ortam değişkenleriyle:
SAHTE_CLAUDE_MOD        ok | limit | hata (varsayılan ok)
SAHTE_CLAUDE_CEVAPLAR   JSON: {"<talimat dosyası adı (uzantısız)>" | "*": structured_output}
SAHTE_CLAUDE_KAYIT      her çağrının {"argv", "cwd"} satırı bu dosyaya eklenir
SAHTE_CLAUDE_LIMIT_SONRA  N: kayıtta N çağrı varsa sonrakiler limit hatası verir
SAHTE_CLAUDE_BEKLE      saniye: cevaptan önce bekle
"""
import json
import os
import sys
import time
from pathlib import Path

argv = sys.argv[1:]
kayit = os.environ.get("SAHTE_CLAUDE_KAYIT")
onceki = 0
if kayit:
    p = Path(kayit)
    onceki = len(p.read_text("utf-8").splitlines()) if p.exists() else 0
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"argv": argv, "cwd": os.getcwd()}, ensure_ascii=False) + "\n")

time.sleep(float(os.environ.get("SAHTE_CLAUDE_BEKLE", "0")))
mod = os.environ.get("SAHTE_CLAUDE_MOD", "ok")
sinir = os.environ.get("SAHTE_CLAUDE_LIMIT_SONRA")
if sinir is not None and onceki >= int(sinir):
    mod = "limit"

oturum = argv[argv.index("--resume") + 1] if "--resume" in argv else "s-" + Path.cwd().name
if mod == "limit":
    print(json.dumps({"type": "result", "subtype": "error", "is_error": True, "api_error_status": 429,
                      "result": "Claude usage limit reached. Your limit will reset at 5pm.", "session_id": oturum}))
    sys.exit(1)
if mod == "hata":
    print(json.dumps({"type": "result", "subtype": "error", "is_error": True, "result": "beklenmeyen hata", "session_id": oturum}))
    sys.exit(1)

cevaplar = json.loads(os.environ.get("SAHTE_CLAUDE_CEVAPLAR", '{"*": {}}'))
talimat = Path(argv[argv.index("--append-system-prompt-file") + 1]).stem if "--append-system-prompt-file" in argv else "*"
cikti = cevaplar.get(talimat, cevaplar.get("*", {}))
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": json.dumps(cikti),
                  "structured_output": cikti, "session_id": oturum}, ensure_ascii=False))
