"""Write docs/openapi.json from the code. Run from backend/: python -m scripts.export_openapi"""

import json
from pathlib import Path

from app.main import app

TARGET = Path(__file__).resolve().parents[2] / "docs" / "openapi.json"


def render() -> str:
    """The OpenAPI document as it is committed."""
    return json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    TARGET.write_text(render())
    print("Wrote", TARGET)
