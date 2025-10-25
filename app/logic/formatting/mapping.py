from pathlib import Path
from functools import lru_cache
from app.model.runes import FILENAME_BY_SET

@lru_cache(maxsize=1)
def get_set_icon_map(icons_dir: Path) -> dict[int, str]:
    out: dict[int, str] = {}
    for sid, fname in FILENAME_BY_SET.items():
        p = icons_dir / fname
        if p.exists():
            out[sid] = f'/swex_icons/{p.name}'
            continue
        stem = fname.rsplit('.', 1)[0].lower()
        for ext in ('.png', '.webp', '.svg', '.jpg', '.jpeg'):
            alt = icons_dir / (stem + ext)
            if alt.exists():
                out[sid] = f'/swex_icons/{alt.name}'
                break
    return out