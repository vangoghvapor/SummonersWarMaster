# app/logic/runes_io.py
from pathlib import Path
import json
import pandas as pd
from app.model.runes import SET
from app.logic.formatting.formatters import fmt_eff
from app.logic.calc.rune_calc import rune_score_300

def load_runes_df(profile_path: Path) -> pd.DataFrame:
    data = json.loads(profile_path.read_text(encoding='utf-8'))
    runes = data.get('runes') or data.get('runes_info') or []
    rows = []
    for r in runes:
        subs = [fmt_eff(e) for e in (r.get('sec_eff') or []) if e and e[0] != 0]
        rows.append({
            'rune_id': r.get('rune_id'),
            'slot': r.get('slot_no'),
            'set': SET.get(r.get('set_id'), f"Set{r.get('set_id')}"),
            'grade★': r.get('class', 0),
            'level': r.get('upgrade_curr', 0),
            'main': fmt_eff(r.get('pri_eff')),
            'innate': fmt_eff(r.get('prefix_eff')),
            'subs': ', '.join(subs),
            'equipped': bool(r.get('occupied_id')),
            'equipped_unit_id': r.get('occupied_id') or '',
            'score': rune_score_300(r),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        for col in ['main','innate','subs','set']:
            df[col] = df[col].fillna('').astype(str)
        df = df.sort_values(['score','slot','set','level'], ascending=[False, True, True, False])
    return df
