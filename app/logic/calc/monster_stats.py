import pandas as pd


def apply_runes_to_base(base_row: pd.Series, tot: dict) -> dict:
    hp  = int(base_row.get('HP', 0))
    atk = int(base_row.get('ATK', 0))
    de  = int(base_row.get('DEF', 0))
    spd = int(base_row.get('SPD', 0))
    cr  = int(base_row.get('CR%', 0))
    cd  = int(base_row.get('CD%', 0))
    res = int(base_row.get('RES%', 0))
    acc = int(base_row.get('ACC%', 0))

    hp_with  = hp  + tot['hp_flat']  + int(hp  * tot['hp_pct']  / 100)
    atk_with = atk + tot['atk_flat'] + int(atk * tot['atk_pct'] / 100)
    def_with = de  + tot['def_flat'] + int(de  * tot['def_pct'] / 100)
    spd_with = spd + tot['spd']
    cr_with  = cr  + tot['cr']
    cd_with  = cd  + tot['cd']
    res_with = res + tot['res']
    acc_with = acc + tot['acc']

    return {
        'HP_with': hp_with, 'ATK_with': atk_with, 'DEF_with': def_with, 'SPD_with': spd_with,
        'CR%_with': cr_with, 'CD%_with': cd_with, 'RES%_with': res_with, 'ACC%_with': acc_with,
    }