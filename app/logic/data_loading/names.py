from functools import lru_cache
import json
from app.config import MONSTER_NAME_MAP

@lru_cache(maxsize=1)
def _name_map() -> dict[int, str]:
    if not MONSTER_NAME_MAP.exists():
        return {}
    try:
        raw = json.loads(MONSTER_NAME_MAP.read_text(encoding='utf-8'))
        return {int(k): str(v) for k, v in raw.items()}
    except Exception:
        return {}

def monster_name(master_id: int) -> str:
    mid = int(master_id)
    return _name_map().get(mid, f"ID:{mid}")
