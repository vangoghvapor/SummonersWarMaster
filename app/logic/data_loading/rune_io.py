# app/logic/data_loading/rune_io.py  (or wherever your loader lives)

from __future__ import annotations
from pathlib import Path
from typing import Union
import json
import pandas as pd

from app.model.runes import SET
from app.logic.formatting.formatters import fmt_eff
from app.logic.calc.rune_calc import rune_score_300

Src = Union[Path, str, dict]

def load_runes_df(src: Src) -> pd.DataFrame:
    data = _ensure_data(src)

    # Build a map of top-level runes by id (prefer the richer top-level objects)
    top = data.get('runes') or data.get('runes_info') or []
    by_id: dict[int, dict] = {}
    for r in top:
        if isinstance(r, dict):
            rid = _to_int(r.get('rune_id'))
            if rid:
                by_id[rid] = r

    # Some exports attach runes to units either as dicts OR as ids (ints/strings)
    for u in (data.get('unit_list') or []):
        for key in ('runes', 'runes_info'):
            for item in (u.get(key) or []):
                if isinstance(item, dict):
                    rid = _to_int(item.get('rune_id'))
                    if rid and rid not in by_id:
                        by_id[rid] = item
                else:
                    # item is likely a rune_id (int/str); keep placeholder if we don't already have it
                    rid = _to_int(item)
                    if rid and rid not in by_id:
                        by_id[rid] = {'rune_id': rid}  # minimal stub; top-level usually fills details

    equip_map = _build_rune_equip_map(data)

    rows = []
    for rid, r in by_id.items():
        unit_id = _to_int(equip_map.get(rid)) or _to_int(r.get('occupied_id')) or 0
        subs_list = []
        sec = r.get('sec_eff') if isinstance(r, dict) else None
        if isinstance(sec, list):
            for e in sec:
                if isinstance(e, (list, tuple)) and e and e[0] != 0:
                    subs_list.append(fmt_eff(e))

        rows.append({
            'rune_id': rid,
            'slot': (r.get('slot_no') if isinstance(r, dict) else None),
            'set_id': _to_int(r.get('set_id') if isinstance(r, dict) else None) or 0,
            'set': SET.get((r.get('set_id') if isinstance(r, dict) else None), f"Set{_to_int(r.get('set_id') if isinstance(r, dict) else 0)}"),
            'grade★': _to_int(r.get('class') if isinstance(r, dict) else None) or 0,
            'level': _to_int(r.get('upgrade_curr') if isinstance(r, dict) else None) or 0,
            'main': fmt_eff(r.get('pri_eff')) if isinstance(r, dict) else '',
            'innate': fmt_eff(r.get('prefix_eff')) if isinstance(r, dict) else '',
            'subs': ', '.join(subs_list),
            'equipped': bool(unit_id),
            'equipped_unit_id': unit_id or '',
            'score': rune_score_300(r) if isinstance(r, dict) else 0,
            '_raw': r,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        for c in ['main', 'innate', 'subs', 'set']:
            df[c] = df[c].fillna('').astype(str)
        df = df.sort_values(['score', 'slot', 'set', 'level'], ascending=[False, True, True, False])
    return df

# --- helpers ---

def _ensure_data(src: Src) -> dict:
    if isinstance(src, dict):
        return src
    if isinstance(src, (str, Path)):
        p = Path(src)
        return json.loads(p.read_text(encoding='utf-8'))
    raise TypeError(f'Unsupported src type: {type(src)}')

def _to_int(x) -> int:
    try:
        return int(x)
    except (TypeError, ValueError):
        return 0

def _build_rune_equip_map(data: dict) -> dict[int, int]:
    """Return {rune_id -> unit_id} from unit_list, handling dicts or id lists."""
    equip: dict[int, int] = {}
    for u in (data.get('unit_list') or []):
        uid = _to_int(u.get('unit_id'))
        if not uid:
            continue
        for key in ('runes', 'runes_info'):
            for item in (u.get(key) or []):
                if isinstance(item, dict):
                    rid = _to_int(item.get('rune_id'))
                else:
                    rid = _to_int(item)  # item is likely a rune_id (int/str)
                if rid:
                    equip[rid] = uid
    return equip
