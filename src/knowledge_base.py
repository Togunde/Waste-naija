
import json
from pathlib import Path

DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "waste_guide.json"
)


def load_guide():
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_guidance(category_id):
    guide = load_guide()

    for item in guide:
        if item.get("category_id") == category_id:
            return item

    return None
