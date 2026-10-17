"""Write the OpenAPI schema to frontend/src/lib/api/openapi.json.

Run from backend/:  python scripts/export_openapi.py
Then in frontend/:  npm run gen:api
"""

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402  (needs the sys.path entry above)

OUT = BACKEND.parent / "frontend" / "src" / "lib" / "api" / "openapi.json"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
