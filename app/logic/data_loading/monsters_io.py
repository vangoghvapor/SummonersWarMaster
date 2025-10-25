# app/logic/data_loading/monsters_io.py
import pandas as pd
from app.logic.api_helpers.swarfarm import fetch_swarfarm_monsters
from app.config import SWARFARM_CACHE

def load_monsters_df(profile: dict) -> pd.DataFrame:
    units = profile.get('unit_list') or []
    com2us_ids = [u.get('unit_master_id') for u in units]
    swarf = fetch_swarfarm_monsters(com2us_ids, SWARFARM_CACHE)

    rows = []
    for u in units:
        mid = int(u.get('unit_master_id') or 0)
        base = swarf.get(mid, {})
        rows.append({
            'unit_id': u.get('unit_id'),
            'com2us_id': mid,
            'name': base.get('name', f'ID:{mid}'),
            '★': u.get('class', 0),
            'level': u.get('unit_level', 0),
            'HP': base.get('hp', 0),
            'ATK': base.get('atk', 0),
            'DEF': base.get('def', 0),
            'SPD': base.get('spd', 0),
            'CR%': base.get('crit_rate', 0),
            'CD%': base.get('crit_dmg', 0),
            'RES%': base.get('resistance', 0),
            'ACC%': base.get('accuracy', 0),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df['name'] = df['name'].fillna('').astype(str)
        df = df.sort_values(['★','level','SPD'], ascending=[False, False, False])
    return df
