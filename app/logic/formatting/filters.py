# app/logic/filters.py
import re
import pandas as pd

def filter_runes(df_in: pd.DataFrame, set_value: str, slot_value: str,
                 equipped_value: str, query: str) -> pd.DataFrame:
    if df_in.empty: return df_in
    out = df_in
    if set_value != '(any)':
        out = out[out['set'] == set_value]
    if slot_value != '(any)':
        out = out[out['slot'] == int(slot_value)]
    if equipped_value != '(any)':
        want = (equipped_value == 'equipped')
        out = out[out['equipped'] == want]
    q = (query or '').strip().lower()
    if q:
        terms = [t for t in q.split() if t]
        def contains_all(series: pd.Series) -> pd.Series:
            s = series.fillna('').astype(str)
            mask = pd.Series([True]*len(s), index=s.index)
            for t in terms:
                mask &= s.str.contains(re.escape(t), case=False, na=False, regex=True)
            return mask
        mask = (
            contains_all(out['main']) |
            contains_all(out['innate']) |
            contains_all(out['subs']) |
            contains_all(out['set'])
        )
        out = out[mask]
    return out


def filter_monsters(
    df: pd.DataFrame,
    *,
    stars="(any)",
    lv_min=1,
    lv_max=50,
    min_runes=0,
    query=""
) -> pd.DataFrame:
    if df.empty:
        return df
    out = df

    # stars
    if stars != "(any)":
        try:
            out = out[out["★"] == int(stars)]
        except Exception:
            pass

    # level range
    try:
        lv_min = int(lv_min or 1)
        lv_max = int(lv_max or 50)
        out = out[(out["level"] >= lv_min) & (out["level"] <= lv_max)]
    except Exception:
        pass

    # min runes
    try:
        min_runes = int(min_runes or 0)
        out = out[out["runes"] >= min_runes]
    except Exception:
        pass

    # text query over name / sets
    q = (query or "").strip().lower()
    if q:
        name_mask = out["name"].str.lower().str.contains(q, na=False)
        set_mask  = out["sets_compact"].str.lower().str.contains(q, na=False)
        out = out[name_mask | set_mask]

    return out