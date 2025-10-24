# app/logic/data_loading/profiles.py
from pathlib import Path
import json, os, time
from typing import List, Tuple



def load_profile(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))



def find_profiles(dir_path: Path) -> List[Tuple[str, str]]:
    if not dir_path.exists(): return []
    files = sorted(dir_path.glob('*.json'), key=os.path.getmtime, reverse=True)
    out = []
    for p in files:
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
            wiz = data.get('wizard_info') or {}
            if not wiz: continue
            name = wiz.get('wizard_name') or '(unknown)'
            wid  = wiz.get('wizard_id') or '?'
            lvl  = wiz.get('wizard_level') or '?'
            ts   = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime))
            out.append((f"{name} [{wid}] Lv{lvl} — {ts} — {p.name}", str(p)))
        except Exception:
            continue
    return out
