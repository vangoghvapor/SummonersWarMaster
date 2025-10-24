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
