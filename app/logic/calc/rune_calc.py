# app/logic/rune_scoring.py
import pandas as pd


def _accumulate(stats, eff):
    if not eff or eff[0] == 0: return
    t, v = int(eff[0]), int(eff[1])
    if   t == 1: stats['hp_flat']  += v
    elif t == 2: stats['hp_pct']   += v
    elif t == 3: stats['atk_flat'] += v
    elif t == 4: stats['atk_pct']  += v
    elif t == 5: stats['def_flat'] += v
    elif t == 6: stats['def_pct']  += v
    elif t == 8: stats['spd']      += v
    elif t == 9: stats['cr']       += v
    elif t == 10: stats['cd']      += v
    elif t == 11: stats['res']     += v
    elif t == 12: stats['acc']     += v

def totals_from_rune_no_main(r):
    s = {'hp_flat':0,'hp_pct':0,'atk_flat':0,'atk_pct':0,'def_flat':0,'def_pct':0,'spd':0,'cr':0,'cd':0,'res':0,'acc':0}
    _accumulate(s, r.get('prefix_eff'))
    for e in (r.get('sec_eff') or []): _accumulate(s, e)
    return s

def rune_score_300(r):
    s = totals_from_rune_no_main(r)
    part_pct = (s['hp_pct'] + s['atk_pct'] + s['def_pct'] + s['acc'] + s['res']) / 40.0
    part_spd = (s['spd'] + s['cr']) / 30.0
    part_cd  = s['cd'] / 35.0
    part_flat = 0.35 * ((s['hp_flat']/1875.0) + ((s['atk_flat']+s['def_flat'])/100.0))
    return round((part_pct + part_spd + part_cd + part_flat) * 100.0, 1)


# app/logic/calc/rune_calc.py

def agg_from_eff(tot: dict, eff):
    """Mutate tot with one SW eff entry [type, value, ...]."""
    if not eff or eff[0] == 0:
        return
    t, v = int(eff[0]), int(eff[1])
    if   t == 1:  tot['hp_flat']  += v
    elif t == 2:  tot['hp_pct']   += v
    elif t == 3:  tot['atk_flat'] += v
    elif t == 4:  tot['atk_pct']  += v
    elif t == 5:  tot['def_flat'] += v
    elif t == 6:  tot['def_pct']  += v
    elif t == 8:  tot['spd']      += v
    elif t == 9:  tot['cr']       += v
    elif t == 10: tot['cd']       += v
    elif t == 11: tot['res']      += v
    elif t == 12: tot['acc']      += v

def totals_from_rune_dict(r: dict) -> dict:
    """Return totals for one rune (main + innate + subs)."""
    tot = {'hp_flat':0,'hp_pct':0,'atk_flat':0,'atk_pct':0,'def_flat':0,'def_pct':0,'spd':0,'cr':0,'cd':0,'res':0,'acc':0}
    agg_from_eff(tot, r.get('pri_eff'))
    agg_from_eff(tot, r.get('prefix_eff'))
    for e in (r.get('sec_eff') or []):
        agg_from_eff(tot, e)
    return tot


def unit_rune_totals(runes_df: pd.DataFrame, unit_id: int) -> dict:
    tot = {'hp_flat':0,'hp_pct':0,'atk_flat':0,'atk_pct':0,'def_flat':0,'def_pct':0,'spd':0,'cr':0,'cd':0,'res':0,'acc':0}
    if runes_df.empty: return tot
    eq = runes_df[runes_df['unit_id'] == unit_id]
    if eq.empty: return tot
    for r in eq['_raw']:
        agg_from_eff(tot, r.get('pri_eff'))
        agg_from_eff(tot, r.get('prefix_eff'))
        for e in (r.get('sec_eff') or []):
            agg_from_eff(tot, e)
    return tot

