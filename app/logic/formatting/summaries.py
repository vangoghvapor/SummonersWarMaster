# app/logic/summaries.py
import re
import pandas as pd



def summary_lines(df_in: pd.DataFrame) -> tuple[str,str,str,str]:
    if df_in.empty:
        return ('No runes','','','')
    n = len(df_in)
    eq = int(df_in['equipped'].sum())
    uneq = n - eq
    eq_pct = (eq / n) * 100 if n else 0.0
    avg_grade = float(df_in['grade★'].mean()) if 'grade★' in df_in.columns else 0.0
    avg_lvl   = float(df_in['level'].mean())  if 'level'  in df_in.columns else 0.0

    top_sets = df_in['set'].value_counts().head(5).to_dict()
    top_sets_str = ' | '.join(f'{k}: {v}' for k, v in top_sets.items())

    slot_counts = df_in['slot'].value_counts().reindex([1,2,3,4,5,6], fill_value=0).to_dict()
    slots_str = ' '.join(f'{s}:{slot_counts[s]}' for s in [1,2,3,4,5,6])

    def col_max_spd(series: pd.Series) -> int:
        vals = []
        for txt in series.fillna('').astype(str):
            vals += [int(x) for x in re.findall(r'\bSPD\s*\+(\d+)', txt)]
        return max(vals) if vals else 0
    spd_max = max(col_max_spd(df_in['main']), col_max_spd(df_in['innate']), col_max_spd(df_in['subs']))
    spd_sub_count = df_in['subs'].str.contains(r'\bSPD\s*\+\d+', case=False, na=False).sum()

    avg_score = float(df_in['score'].mean())
    p95_score = float(df_in['score'].quantile(0.95)) if n >= 2 else avg_score
    top = df_in.sort_values('score', ascending=False).head(1).iloc[0]
    top_desc = f"#{int(top['rune_id'])} {top['set']} s{int(top['slot'])} +{int(top['level'])} (score {top['score']:.1f})"

    line1 = f'Total: {n}   |   Equipped: {eq} ({eq_pct:.1f}%) / Unequipped: {uneq}   |   Avg ★: {avg_grade:.2f}   Avg +: {avg_lvl:.2f}'
    line2 = f'Top sets: {top_sets_str}'
    line3 = f'Slots: {slots_str}   |   Fastest SPD: +{spd_max}   |   Runes w/ SPD sub: {spd_sub_count}'
    line4 = f'Avg score: {avg_score:.1f}   |   p95: {p95_score:.1f}   |   Top: {top_desc}'
    return (line1, line2, line3, line4)


# app/logic/sets_summaries.py
import pandas as pd
from app.model.runes import SET, SET_REQ

def summarize_sets_for_unit(df_unit: pd.DataFrame, set_icon_path: dict[int,str]) -> pd.Series:
    if df_unit.empty:
        return pd.Series({'sets_compact':'', 'sets_icons': []})
    by_set = df_unit['set_id'].value_counts().to_dict()
    parts, icons = [], []
    for sid, cnt in by_set.items():
        req = SET_REQ.get(int(sid), 2)
        completed = cnt // req
        if completed <= 0:
            continue
        name = SET.get(int(sid), f"Set{sid}")
        parts.append(f"{name}×{completed}" if completed > 1 else name)
        path = set_icon_path.get(int(sid), '')
        icons.append({'path': path, 'name': name, 'count': int(completed)})
    parts = sorted(parts, key=str.lower)
    icons = sorted(icons, key=lambda d: d['name'].lower())
    return pd.Series({'sets_compact':' | '.join(parts), 'sets_icons': icons})

def join_equipped(mon_df: pd.DataFrame, runes_df: pd.DataFrame, set_icon_path: dict[int,str]) -> pd.DataFrame:
    if mon_df.empty or runes_df.empty:
        mon_df = mon_df.copy()
        mon_df['runes']=0; mon_df['sets']=''; mon_df['sets_compact']=''; mon_df['sets_icons']=[[]]
        return mon_df
    counts = runes_df.groupby('unit_id').size().rename('runes')
    verbose_sets = (runes_df.groupby('unit_id')['set']
                    .apply(lambda s: ', '.join(sorted(s.tolist())))
                    .rename('sets'))
    per_unit = (runes_df[runes_df['unit_id'] != 0]
                .groupby('unit_id')
                .apply(lambda dfu: summarize_sets_for_unit(dfu, set_icon_path)))
    out = (mon_df.merge(counts, how='left', left_on='unit_id', right_index=True)
                 .merge(verbose_sets, how='left', left_on='unit_id', right_index=True)
                 .merge(per_unit, how='left', left_on='unit_id', right_index=True))
    out['runes'] = out['runes'].fillna(0).astype(int)
    out['sets'] = out['sets'].fillna('')
    out['sets_compact'] = out['sets_compact'].fillna('')
    out['sets_icons'] = out['sets_icons'].apply(lambda v: v if isinstance(v, list) else [])
    return out
