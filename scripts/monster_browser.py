# scripts/monster_browser.py
# Run:  .\.venv_wd\Scripts\python scripts\monster_browser.py
# Open: http://127.0.0.1:8081

from nicegui import ui, app
from pathlib import Path
import json, os, time, re
import pandas as pd
import requests

# ---------- config ----------
REPO = Path(__file__).resolve().parents[1]
EXPORT_DIR = REPO / 'data' / 'swex' / 'exports' / 'profile saves'
MONSTER_NAME_MAP = REPO / 'data' / 'swex' / 'monster_names.json'  # optional
CACHE_DIR = REPO / 'data' / 'swex' / 'cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)
SWARFARM_CACHE = CACHE_DIR / 'swarfarm_monsters.json'

# rune set icons (local assets)
ICONS_DIR = REPO / 'tools' / 'sw-exporter' / 'assets' / 'runes'
app.add_static_files('/swex_icons', str(ICONS_DIR.resolve()))

HOST, PORT = '127.0.0.1', 8081

SET = {
    1:"Energy",2:"Guard",3:"Swift",4:"Blade",5:"Rage",6:"Focus",7:"Endure",
    8:"Fatal",10:"Despair",11:"Vampire",13:"Violent",14:"Nemesis",15:"Will",
    16:"Shield",17:"Revenge",18:"Destroy",19:"Fight",20:"Determination",
    21:"Enhance",22:"Accuracy",23:"Tolerance",
}
# how many runes complete each set
SET_REQ = {1:2,2:2,3:4,4:2,5:4,6:2,7:2,8:4,10:4,11:4,13:4,14:2,15:2,16:2,17:2,18:2,19:2,20:2,21:2,22:2,23:2}
STAT = {1:"HP",2:"HP%",3:"ATK",4:"ATK%",5:"DEF",6:"DEF%",8:"SPD",9:"CRI Rate",10:"CRI Dmg",11:"RES",12:"ACC"}

# ---------- icon map from SWEX assets ----------
def _build_icon_map() -> dict[int, str]:
    filename_by_set = {
        1:'Energy.png', 2:'Guard.png', 3:'Swift.png', 4:'Blade.png', 5:'Rage.png',
        6:'Focus.png', 7:'Endure.png', 8:'Fatal.png', 10:'Despair.png', 11:'Vampire.png',
        13:'Violent.png', 14:'Nemesis.png', 15:'Will.png', 16:'Shield.png', 17:'Revenge.png',
        18:'Destroy.png', 19:'Fight.png', 20:'Determination.png', 21:'Enhance.png', 22:'Accuracy.png', 23:'Tolerance.png',
    }
    icon_map = {}
    for sid, fname in filename_by_set.items():
        p = ICONS_DIR / fname
        if p.exists():
            icon_map[sid] = f'/swex_icons/{fname}'
        else:
            for ext in ('.png', '.webp', '.svg', '.jpg', '.jpeg'):
                alt = ICONS_DIR / (fname.rsplit('.', 1)[0].lower() + ext)
                if alt.exists():
                    icon_map[sid] = f'/swex_icons/{alt.name}'
                    break
    return icon_map

SET_ICON_PATH = _build_icon_map()
print('[icons] mapped sets:', sorted(SET_ICON_PATH.keys()))

# ---------- SWARFARM helpers ----------
def _read_sw_cache() -> dict[int, dict]:
    if not SWARFARM_CACHE.exists():
        return {}
    try:
        raw = json.loads(SWARFARM_CACHE.read_text(encoding='utf-8'))
        return {int(k): v for k, v in raw.items()}
    except Exception:
        return {}

def _write_sw_cache(cache: dict[int, dict]) -> None:
    try:
        SWARFARM_CACHE.write_text(
            json.dumps({str(k): v for k, v in cache.items()}, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
    except Exception:
        pass

def fetch_swarfarm_monsters(com2us_ids: list[int]) -> dict[int, dict]:
    """Return {com2us_id: stats/names} via SWARFARM API; cached and merged."""
    out: dict[int, dict] = _read_sw_cache()
    ids = sorted({int(x) for x in com2us_ids if x})
    missing = [i for i in ids if i not in out]
    if not missing:
        return out
    base = 'https://swarfarm.com/api/v2/monsters/'
    for cid in missing:
        try:
            resp = requests.get(base, params={'com2us_id': cid}, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data and data.get('count', 0) >= 1:
                m = data['results'][0]
                out[cid] = {
                    **out.get(cid, {}),
                    'name': m.get('name', f'ID:{cid}'),
                    'hp': m.get('max_lvl_hp', 0),
                    'atk': m.get('max_lvl_attack', 0),
                    'def': m.get('max_lvl_defense', 0),
                    'spd': m.get('speed', 0),
                    'crit_rate': m.get('crit_rate', 0),
                    'crit_dmg': m.get('crit_damage', 0),
                    'resistance': m.get('resistance', 0),
                    'accuracy': m.get('accuracy', 0),
                }
            else:
                out[cid] = out.get(cid, {}) or {'name': f'ID:{cid}','hp':0,'atk':0,'def':0,'spd':0,
                                                'crit_rate':0,'crit_dmg':0,'resistance':0,'accuracy':0}
        except Exception:
            out[cid] = out.get(cid, {}) or {'name': f'ID:{cid}','hp':0,'atk':0,'def':0,'spd':0,
                                            'crit_rate':0,'crit_dmg':0,'resistance':0,'accuracy':0}
    _write_sw_cache(out)
    return out

_slugify_re = re.compile(r'[^a-z0-9]+')

def swarfarm_bestiary_url(com2us_id: int, name: str | None = None) -> str:
    """SWARFARM bestiary uses /bestiary/<com2us_id>-<slug>/, not just the id."""
    if name:
        slug = _slugify_re.sub('-', (name or '').lower()).strip('-')
        return f'https://swarfarm.com/bestiary/{int(com2us_id)}-{slug}/'
    # No name? We'll still return the id-only form (likely 404) so caller can try other strategies.
    return f'https://swarfarm.com/bestiary/{int(com2us_id)}/'


_slug_like_path = re.compile(r'^\d{3,}-[a-z0-9-]+/?$', re.I)

def _bestiary_url_via_api(com2us_id: int) -> str:
    """Return a valid SWARFARM bestiary URL for this monster.

    Handles cases where the API already returns a full '<id>-<slug>' path.
    """
    try:
        resp = requests.get(
            "https://swarfarm.com/api/v2/monsters/",
            params={"com2us_id": int(com2us_id)},
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        if data and data.get("count", 0) >= 1:
            m = data["results"][0]

            # Prefer any explicit URL the API gives us.
            url = (m.get("bestiary_url") or m.get("url") or "").strip()
            if url:
                if url.startswith("/"):
                    return "https://swarfarm.com" + url
                if url.startswith("http"):
                    return url

            # Otherwise, use a slug-ish field.
            for key in ("bestiary_slug", "slug", "name_slug"):
                slug = (m.get(key) or "").strip().strip("/")
                if not slug:
                    continue
                # If slug already looks like '12345-some-monster', don't prepend an id.
                if _slug_like_path.match(slug):
                    return f"https://swarfarm.com/bestiary/{slug}/"

                # If slug is just 'some-monster', prepend the *API’s* com2us_id (not our input).
                api_id = int(m.get("com2us_id") or com2us_id)
                return f"https://swarfarm.com/bestiary/{api_id}-{slug}/"

            # Last-resort: fall back to API’s id with no slug (may 404 for some)
            api_id = int(m.get("com2us_id") or com2us_id)
            return f"https://swarfarm.com/bestiary/{api_id}/"

    except Exception:
        pass

    # Final fallback if API lookup fails entirely
    return f"https://swarfarm.com/bestiary/{int(com2us_id)}/"


def fetch_monster_image_lazy(com2us_id: int) -> str:
    """Fetch portrait directly via SWARFARM API's image_filename field."""
    cache = _read_sw_cache()
    if com2us_id in cache and cache[com2us_id].get('image_url'):
        return cache[com2us_id]['image_url']

    try:
        # Look up by com2us_id
        resp = requests.get(
            "https://swarfarm.com/api/v2/monsters/",
            params={"com2us_id": com2us_id},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        # SWARFARM returns a paginated list under 'results'
        if data and data.get("count", 0) >= 1:
            m = data["results"][0]
        else:
            # fallback: try direct endpoint
            resp2 = requests.get(f"https://swarfarm.com/api/v2/monsters/{com2us_id}/", timeout=10)
            resp2.raise_for_status()
            m = resp2.json()

        image_name = (
            m.get("image_filename")
            or m.get("image_file_name")  # in case of legacy key
            or ""
        ).strip()

        if image_name:
            imgurl = f"https://swarfarm.com/static/herders/images/monsters/{image_name}"
            cache.setdefault(com2us_id, {})["image_url"] = imgurl
            _write_sw_cache(cache)
            print(f"[image fetch] cached {com2us_id} → {imgurl}")
            return imgurl

        print(f"[image fetch] no image filename for {com2us_id}")
        return ""

    except Exception as e:
        print(f"[image fetch] failed for {com2us_id}: {e}")
        return ""



# ---------- rune helpers (same score as runes page; innate+subs only) ----------
def _acc(stats, eff):
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

def _totals_innate_subs(r):
    s = {'hp_flat':0,'hp_pct':0,'atk_flat':0,'atk_pct':0,'def_flat':0,'def_pct':0,'spd':0,'cr':0,'cd':0,'res':0,'acc':0}
    _acc(s, r.get('prefix_eff'))
    for e in (r.get('sec_eff') or []): _acc(s, e)
    return s

def rune_score_300(r):
    s = _totals_innate_subs(r)
    part_pct = (s['hp_pct'] + s['atk_pct'] + s['def_pct'] + s['acc'] + s['res']) / 40.0
    part_spd = (s['spd'] + s['cr']) / 30.0
    part_cd  = s['cd'] / 35.0
    part_flat = 0.35 * ((s['hp_flat']/1875.0) + ((s['atk_flat']+s['def_flat'])/100.0))
    return round((part_pct + part_spd + part_cd + part_flat) * 100.0, 1)

def fmt_eff(e):
    if not e or e[0] == 0: return ""
    t, v = e[0], e[1]
    return f"{STAT.get(t, f'Type{t}')} +{v}"

# ---------- profile I/O ----------
_name_map_cache = None
def monster_name(master_id: int) -> str:
    global _name_map_cache
    if _name_map_cache is None:
        if MONSTER_NAME_MAP.exists():
            try:
                _name_map_cache = {int(k):v for k,v in json.loads(MONSTER_NAME_MAP.read_text(encoding='utf-8')).items()}
            except Exception:
                _name_map_cache = {}
        else:
            _name_map_cache = {}
    return _name_map_cache.get(int(master_id), f"ID:{master_id}")

def find_profiles(dir_path: Path):
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

def load_profile(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def build_rune_equip_map(profile: dict) -> dict[int, int]:
    """Return {rune_id: unit_id} using unit_list[*], equip_info_list, and top-level runes."""
    equip: dict[int, int] = {}
    for u in (profile.get('unit_list') or []):
        uid = int(u.get('unit_id') or 0)
        if not uid: continue
        for key in ('runes', 'runes_info'):
            for item in (u.get(key) or []):
                try:
                    rid = int(item.get('rune_id') if isinstance(item, dict) else item)
                    if rid and uid:
                        equip[rid] = uid
                except Exception:
                    continue
    for block in (profile.get('equip_info_list') or []):
        for key in ('rune_equip_list', 'runes_equip_list', 'rune_equipped_list'):
            for e in (block.get(key) or []):
                try:
                    rid = int(e.get('rune_id') or 0)
                    uid = int(e.get('occupied_id') or 0)
                    otype = int(e.get('occupied_type') or 1)
                    if rid and uid and otype == 1 and rid not in equip:
                        equip[rid] = uid
                except Exception:
                    continue
    for r in (profile.get('runes') or profile.get('runes_info') or []):
        try:
            rid = int(r.get('rune_id') or 0)
            uid = int(r.get('occupied_id') or 0)
            otype = int(r.get('occupied_type') or 1)
            if rid and uid and otype == 1 and rid not in equip:
                equip[rid] = uid
        except Exception:
            continue
    return equip

def load_runes_df(data: dict) -> pd.DataFrame:
    top_runes = data.get('runes') or data.get('runes_info') or []
    by_id: dict[int, dict] = {int(r.get('rune_id') or 0): r for r in top_runes if r.get('rune_id')}
    for u in (data.get('unit_list') or []):
        for key in ('runes', 'runes_info'):
            for item in (u.get(key) or []):
                if isinstance(item, dict):
                    rid = int(item.get('rune_id') or 0)
                    if rid and rid not in by_id:
                        by_id[rid] = item
    equip_map = build_rune_equip_map(data)

    rows = []
    for rid, r in by_id.items():
        unit_id = int(equip_map.get(rid) or r.get('occupied_id') or 0)
        rows.append({
            'rune_id': rid,
            'slot': r.get('slot_no'),
            'set_id': int(r.get('set_id') or 0),
            'set': SET.get(r.get('set_id'), f"Set{r.get('set_id')}"),
            'main': fmt_eff(r.get('pri_eff')),
            'innate': fmt_eff(r.get('prefix_eff')),
            'subs': ', '.join(fmt_eff(e) for e in (r.get('sec_eff') or []) if e and e[0] != 0),
            'unit_id': unit_id,
            'score': rune_score_300(r),
            '_raw': r,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        for c in ['main','innate','subs','set']:
            df[c] = df[c].fillna('').astype(str)
    return df

def load_monsters_df(data: dict) -> pd.DataFrame:
    units = data.get('unit_list') or []
    com2us_ids = [u.get('unit_master_id') for u in units]
    swarf = fetch_swarfarm_monsters(com2us_ids)  # NO image fetch here
    rows = []
    for u in units:
        mid = int(u.get('unit_master_id') or 0)
        base = swarf.get(mid, {})
        rows.append({
            'unit_id': u.get('unit_id'),
            'com2us_id': mid,  # keep for lazy image fetch
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


def _api_get_by_com2us(com2us_id: int) -> dict:
    """Return the first /api/v2/monsters/ result for this com2us_id (or {})."""
    try:
        r = requests.get("https://swarfarm.com/api/v2/monsters/",
                         params={"com2us_id": int(com2us_id)}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data and data.get("count", 0) >= 1:
            return data["results"][0]
    except Exception as e:
        print(f"[api] by com2us failed {com2us_id}: {e}")
    return {}

def _api_get_by_internal_id(internal_id: int) -> dict:
    """Return /api/v2/monsters/<internal_id>/ (or {})."""
    try:
        r = requests.get(f"https://swarfarm.com/api/v2/monsters/{int(internal_id)}/", timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[api] by internal id failed {internal_id}: {e}")
    return {}

def _img_from_filename(filename: str) -> str:
    filename = (filename or "").strip()
    return f"https://swarfarm.com/static/herders/images/monsters/{filename}" if filename else ""

def resolve_unawakened_and_awakened(com2us_id: int) -> dict:
    """
    Return {'base': {'name','com2us_id','img'}, 'awakened': {...}}
    using API fields (awakens_from / awakens_to). Results are cached.
    """
    cache = _read_sw_cache()
    if com2us_id in cache and cache[com2us_id].get("pair_cached"):
        return cache[com2us_id]["pair_cached"]

    cur = _api_get_by_com2us(com2us_id)
    if not cur:
        return {'base': None, 'awakened': None}

    cur_form = {
        'name': cur.get('name', f'ID:{cur.get("com2us_id", com2us_id)}'),
        'com2us_id': cur.get('com2us_id', com2us_id),
        'img': _img_from_filename(cur.get('image_filename') or cur.get('image_file_name') or ''),
    }

    base_form, awak_form = None, None

    if cur.get('awakens_from'):   # current is awakened → fetch base
        b = _api_get_by_internal_id(int(cur['awakens_from']))
        base_form = {
            'name': b.get('name', f'ID:{b.get("com2us_id","?")}'),
            'com2us_id': b.get('com2us_id', 0),
            'img': _img_from_filename(b.get('image_filename') or b.get('image_file_name') or ''),
        }
        awak_form = cur_form

    elif cur.get('awakens_to'):   # current is base → fetch awakened
        a = _api_get_by_internal_id(int(cur['awakens_to']))
        awak_form = {
            'name': a.get('name', f'ID:{a.get("com2us_id","?")}'),
            'com2us_id': a.get('com2us_id', 0),
            'img': _img_from_filename(a.get('image_filename') or a.get('image_file_name') or ''),
        }
        base_form = cur_form
    else:
        base_form = cur_form
        awak_form = None

    pair = {'base': base_form, 'awakened': awak_form}
    cache.setdefault(com2us_id, {})["pair_cached"] = pair
    _write_sw_cache(cache)
    return pair




# ---------- set summaries (text + icons) ----------
def join_equipped(mon_df: pd.DataFrame, runes_df: pd.DataFrame) -> pd.DataFrame:
    if mon_df.empty:
        mon_df['runes']=0; mon_df['sets']=''; mon_df['sets_compact']=''; mon_df['sets_icons']=[[]]
        return mon_df
    if runes_df.empty:
        mon_df['runes']=0; mon_df['sets']=''; mon_df['sets_compact']=''; mon_df['sets_icons']=[[]]
        return mon_df

    counts = runes_df.groupby('unit_id').size().rename('runes')
    verbose_sets = (runes_df.groupby('unit_id')['set']
                    .apply(lambda s: ', '.join(sorted(s.tolist())))
                    .rename('sets'))

    def compact_and_icons(df_unit: pd.DataFrame):
        if df_unit.empty:
            return pd.Series({'sets_compact':'', 'sets_icons': []})
        by_set = df_unit['set_id'].value_counts().to_dict()
        parts, icons = [], []
        for sid, cnt in by_set.items():
            req = SET_REQ.get(int(sid), 2)
            completed = cnt // req
            if completed <= 0: continue
            name = SET.get(int(sid), f"Set{sid}")
            parts.append(f"{name}×{completed}" if completed > 1 else name)
            path = SET_ICON_PATH.get(int(sid), '')
            icons.append({'path': path, 'name': name, 'count': int(completed)})
        parts = sorted(parts, key=lambda s: s.lower())
        icons = sorted(icons, key=lambda d: d['name'].lower())
        return pd.Series({'sets_compact': ' | '.join(parts), 'sets_icons': icons})

    per_unit = (runes_df[runes_df['unit_id'] != 0]
                .groupby('unit_id')
                .apply(compact_and_icons))

    out = (mon_df.merge(counts, how='left', left_on='unit_id', right_index=True)
                 .merge(verbose_sets, how='left', left_on='unit_id', right_index=True)
                 .merge(per_unit, how='left', left_on='unit_id', right_index=True))

    out['runes'] = out['runes'].fillna(0).astype(int)
    out['sets'] = out['sets'].fillna('')
    out['sets_compact'] = out['sets_compact'].fillna('')
    out['sets_icons'] = out['sets_icons'].apply(lambda v: v if isinstance(v, list) else [])
    return out

# --- aggregate rune contributions (main + innate + subs) ---
def _agg_from_eff(tot, eff):
    if not eff or eff[0] == 0: return
    t, v = int(eff[0]), int(eff[1])
    if   t == 1: tot['hp_flat']  += v
    elif t == 2: tot['hp_pct']   += v
    elif t == 3: tot['atk_flat'] += v
    elif t == 4: tot['atk_pct']  += v
    elif t == 5: tot['def_flat'] += v
    elif t == 6: tot['def_pct']  += v
    elif t == 8: tot['spd']      += v
    elif t == 9: tot['cr']       += v
    elif t == 10: tot['cd']      += v
    elif t == 11: tot['res']     += v
    elif t == 12: tot['acc']     += v

def unit_rune_totals(runes_df: pd.DataFrame, unit_id: int) -> dict:
    tot = {'hp_flat':0,'hp_pct':0,'atk_flat':0,'atk_pct':0,'def_flat':0,'def_pct':0,'spd':0,'cr':0,'cd':0,'res':0,'acc':0}
    if runes_df.empty: return tot
    eq = runes_df[runes_df['unit_id'] == unit_id]
    if eq.empty: return tot
    for r in eq['_raw']:
        _agg_from_eff(tot, r.get('pri_eff'))
        _agg_from_eff(tot, r.get('prefix_eff'))
        for e in (r.get('sec_eff') or []): _agg_from_eff(tot, e)
    return tot

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

# ---------- UI ----------
STATE = {'mapping': [], 'path': None, 'data': None, 'df_mons': pd.DataFrame(), 'df_runes': pd.DataFrame()}

with ui.header().classes('items-center gap-3'):
    ui.label('SWEX Monster Browser').classes('text-xl font-bold')

profile_select = ui.select(options=[], label='Profile').classes('m-4 min-w-[560px]')
ui.button('Load', on_click=lambda: ((lambda sel=profile_select.value: load_selected(sel))())).classes('m-4')

with ui.row().classes('m-4 gap-4'):
    f_star = ui.select(['(any)','6','5','4','3','2','1'], value='(any)', label='★').classes('w-28')
    f_lvl_min = ui.number(label='Min Lv', value=1).classes('w-28')
    f_lvl_max = ui.number(label='Max Lv', value=50).classes('w-28')
    f_runes_min = ui.number(label='Min Runes', value=0).classes('w-32')
    f_q = ui.input(label='Search name/sets').classes('w-96')

cols = [
    {'name':'unit_id','label':'Unit ID','field':'unit_id','sortable':True},
    {'name':'name','label':'Name','field':'name','sortable':True},
    {'name':'★','label':'★','field':'★','sortable':True},
    {'name':'level','label':'Lv','field':'level','sortable':True},
    {'name':'HP','label':'HP','field':'HP','sortable':True},
    {'name':'ATK','label':'ATK','field':'ATK','sortable':True},
    {'name':'DEF','label':'DEF','field':'DEF','sortable':True},
    {'name':'SPD','label':'SPD','field':'SPD','sortable':True},
    {'name':'CR%','label':'CR%','field':'CR%','sortable':True},
    {'name':'CD%','label':'CD%','field':'CD%','sortable':True},
    {'name':'RES%','label':'RES%','field':'RES%','sortable':True},
    {'name':'ACC%','label':'ACC%','field':'ACC%','sortable':True},
    {'name':'HP_with','label':'HP (with)','field':'HP_with','sortable':True},
    {'name':'ATK_with','label':'ATK (with)','field':'ATK_with','sortable':True},
    {'name':'DEF_with','label':'DEF (with)','field':'DEF_with','sortable':True},
    {'name':'SPD_with','label':'SPD (with)','field':'SPD_with','sortable':True},
    {'name':'CR%_with','label':'CR% (with)','field':'CR%_with','sortable':True},
    {'name':'CD%_with','label':'CD% (with)','field':'CD%_with','sortable':True},
    {'name':'RES%_with','label':'RES% (with)','field':'RES%_with','sortable':True},
    {'name':'ACC%_with','label':'ACC% (with)','field':'ACC%_with','sortable':True},
    {'name':'runes','label':'Runes','field':'runes','sortable':True},
    {'name':'sets','label':'Sets','field':'sets_compact'},
    # TODO: this doesn't seem to work inside a table slot?
    # {'name':'sets_icons_col','label':'Sets(Icons)','field':'sets_icons','sortable':False},
]

# ---- RESIZABLE LAYOUT ----
split = ui.splitter(value=75).classes('h-[78vh]')

with split:
    with split.before:
        table = ui.table(
            columns=cols, rows=[], row_key='unit_id',
            pagination={'rowsPerPage': 20},
            selection='single',
            on_select=lambda e: (open_monster_panel(int(e.selection[0]['unit_id'])) if e.selection else None),
        ).classes('m-4')

    with split.after:
        detail_card = ui.card().classes('m-3 w-full h-full overflow-auto')
        with detail_card:
            d_title = ui.label('Select a monster…').classes('text-lg font-semibold m-4')
            d_stats = ui.column().classes('m-4')
            ui.label('Equipped Runes').classes('text-md font-semibold m-2')
            d_runes = ui.table(columns=[
                {'name':'slot','label':'Slot','field':'slot','sortable':True},
                {'name':'set','label':'Set','field':'set','sortable':True},
                {'name':'main','label':'Main','field':'main'},
                {'name':'innate','label':'Innate','field':'innate'},
                {'name':'subs','label':'Subs','field':'subs'},
                {'name':'score','label':'Score','field':'score','sortable':True},
            ], rows=[], row_key='rune_id', pagination={'rowsPerPage': 10}).classes('m-2')

# custom cell: sets icons
with table.add_slot('body-cell-sets_icons_col'):
    def _(row):
        icons = row['row'].get('sets_icons') or []
        with ui.row().classes('items-center gap-1'):
            if not icons:
                ui.label('—').classes('opacity-50 text-xs')
            else:
                for it in icons:
                    cnt = int(it.get('count', 1))
                    path = it.get('path') or ''
                    name = it.get('name') or ''
                    shown = min(cnt, 3)
                    for _ in range(shown):
                        if path:
                            ui.image(path).classes('h-5 w-5 rounded')
                        else:
                            ui.label(name).classes('text-[10px]')
                    if cnt > 3:
                        ui.label(f'×{cnt}').classes('text-[10px] opacity-70')


# ---------- logic ----------
def refresh_profiles():
    STATE['mapping'] = find_profiles(EXPORT_DIR)
    profile_select.options = [label for label, _ in STATE['mapping']]
    profile_select.value = profile_select.options[0] if profile_select.options else None


def load_selected(selected_label):
    if not selected_label:
        ui.notify('No profile selected', color='negative'); return
    path_map = {label: p for (label, p) in STATE['mapping']}
    p = path_map.get(selected_label)
    if not p or not Path(p).exists():
        ui.notify('Selected file missing', color='negative'); return
    STATE['path'] = Path(p)
    STATE['data'] = load_profile(STATE['path'])

    df_runes = load_runes_df(STATE['data'])
    df_mons  = load_monsters_df(STATE['data'])

    if not df_mons.empty:
        extras = []
        for _, row in df_mons.iterrows():
            tot = unit_rune_totals(df_runes, int(row['unit_id']))
            extras.append(apply_runes_to_base(row, tot))
        df_mons = pd.concat([df_mons, pd.DataFrame(extras, index=df_mons.index)], axis=1)

    STATE['df_runes'] = df_runes
    STATE['df_mons']  = join_equipped(df_mons, df_runes)
    refresh_table()


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    out = df
    if f_star.value != '(any)':
        out = out[out['★'] == int(f_star.value)]
    try:
        lvmin = int(f_lvl_min.value or 1); lvmax = int(f_lvl_max.value or 50)
        out = out[(out['level'] >= lvmin) & (out['level'] <= lvmax)]
    except: pass
    try:
        rmin = int(f_runes_min.value or 0)
        out = out[out['runes'] >= rmin]
    except: pass
    q = (f_q.value or '').strip().lower()
    q = (f_q.value or '').strip().lower()
    if q:
        name_mask = df['name'].str.lower().str.contains(q, na=False)
        set_mask = df['sets_compact'].str.lower().str.contains(q, na=False)
        out = out[name_mask | set_mask]
    return out


def refresh_table():
    filt = apply_filters(STATE['df_mons'])
    table.rows = filt.to_dict(orient='records')
    table.update()


def open_monster_panel(unit_id: int):
    if split.value >= 99:
        split.value = 70  # reopen to 70/30

    dfm = STATE['df_mons']; dfr = STATE['df_runes']
    if dfm.empty: return
    row = dfm[dfm['unit_id'] == unit_id]
    if row.empty: return
    r = row.iloc[0]

    d_title.text = f"{r['name']} • {int(r['★'])}★ Lv{int(r['level'])}"

    d_stats.clear()
    with d_stats:
        cid = int(r.get('com2us_id') or 0)
        pair = resolve_unawakened_and_awakened(cid) if cid else {'base': None, 'awakened': None}

        # Portraits + names row
        with ui.row().classes('items-center gap-6 mb-2'):
            # Un-awakened (base)
            with ui.column().classes('items-center'):
                ui.label('Un-Awakened').classes('text-xs opacity-70')
                if pair['base'] and pair['base'].get('img'):
                    ui.image(pair['base']['img']).classes('h-20 w-20 rounded-xl')
                if pair['base'] and pair['base'].get('name'):
                    ui.label(pair['base']['name']).classes('text-xs mt-1')

            # Awakened
            with ui.column().classes('items-center'):
                ui.label('Awakened').classes('text-xs opacity-70')
                if pair['awakened'] and pair['awakened'].get('img'):
                    ui.image(pair['awakened']['img']).classes('h-20 w-20 rounded-xl')
                if pair['awakened'] and pair['awakened'].get('name'):
                    ui.label(pair['awakened']['name']).classes('text-xs mt-1')

        # build 2-column stat comparison
        with ui.row().classes('gap-8'):
            # --- base stats ---
            with ui.column().classes('w-48'):
                ui.label('Base Stats').classes('font-semibold underline mb-1')
                ui.label(f"HP:  {int(r['HP'])}")
                ui.label(f"ATK: {int(r['ATK'])}")
                ui.label(f"DEF: {int(r['DEF'])}")
                ui.label(f"SPD: {int(r['SPD'])}")
                ui.label(f"CR:  {int(r['CR%'])}%")
                ui.label(f"CD:  {int(r['CD%'])}%")
                ui.label(f"RES: {int(r['RES%'])}%")
                ui.label(f"ACC: {int(r['ACC%'])}%")

            # --- after-runes stats ---
            with ui.column().classes('w-48'):
                ui.label('With Runes').classes('font-semibold underline mb-1')
                ui.label(f"HP:  {int(r['HP_with'])}")
                ui.label(f"ATK: {int(r['ATK_with'])}")
                ui.label(f"DEF: {int(r['DEF_with'])}")
                ui.label(f"SPD: {int(r['SPD_with'])}")
                ui.label(f"CR:  {int(r['CR%_with'])}%")
                ui.label(f"CD:  {int(r['CD%_with'])}%")
                ui.label(f"RES: {int(r['RES%_with'])}%")
                ui.label(f"ACC: {int(r['ACC%_with'])}%")

        # sets section
        ui.label('Sets:').classes('mt-3 font-semibold')
        with ui.row().classes('items-center gap-2 ml-2'):
            icons = r['sets_icons'] if isinstance(r['sets_icons'], list) else []
            if not icons:
                ui.label('(none)')
            else:
                for it in icons:
                    path = it.get('path') or ''
                    name = it.get('name') or ''
                    cnt = int(it.get('count', 1))
                    shown = min(cnt, 3)
                    for _ in range(shown):
                        if path:
                            ui.image(path).classes('h-6 w-6 rounded')
                        else:
                            ui.label(name).classes('text-xs')
                    if cnt > 3:
                        ui.label(f"×{cnt}").classes('text-xs opacity-70')

    equip = dfr[dfr['unit_id'] == unit_id]
    if not equip.empty:
        equip = equip.sort_values(['slot','score'], ascending=[True, False])
    d_runes.rows = equip[['slot','set','main','innate','subs','score']].to_dict(orient='records')
    d_runes.update()

# filter hooks
f_star.on('update:model-value', lambda *_: refresh_table())
f_lvl_min.on('update:model-value', lambda *_: refresh_table())
f_lvl_max.on('update:model-value', lambda *_: refresh_table())
f_runes_min.on('update:model-value', lambda *_: refresh_table())
f_q.on('update:model-value', lambda *_: refresh_table())

# boot
if __name__ == '__main__':
    refresh_profiles()
    ui.run(host=HOST, port=PORT, reload=False)
