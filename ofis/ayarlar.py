import json
from pathlib import Path

PROJE = Path(__file__).resolve().parent.parent


def yukle(yol: Path | None = None) -> dict:
    return json.loads((yol or PROJE / "ayarlar.json").read_text("utf-8"))
