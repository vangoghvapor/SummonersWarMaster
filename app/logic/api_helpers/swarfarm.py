# app/api_helpers/swarfarm.py
from __future__ import annotations
from pathlib import Path
from functools import lru_cache
import json, re, requests

_slugify_re = re.compile(r'[^a-z0-9]+')
_slug_like_path = re.compile(r'^\d{3,}-[a-z0-9-]+/?$', re.I)

def _read_cache(path: Path) -> dict[int, dict]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
        return {int(k): v for k, v in raw.items()}
    except Exception:
        return {}

def _write_cache(path: Path, cache: dict[int, dict]) -> None:
    try:
        path.write_text(json.dumps({str(k): v for k, v in cache.items()}, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception:
        pass

def swarfarm_bestiary_url(com2us_id: int, name: str | None = None) -> str:
    if name:
        slug = _slugify_re.sub('-', (name or '').lower()).strip('-')
        return f'https://swarfarm.com/bestiary/{int(com2us_id)}-{slug}/'
    return f'https://swarfarm.com/bestiary/{int(com2us_id)}/'

def _api_get_list(params: dict, timeout=12) -> dict:
    r = requests.get("https://swarfarm.com/api/v2/monsters/", params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()

def _api_get_detail(internal_id: int, timeout=12) -> dict:
    r = requests.get(f"https://swarfarm.com/api/v2/monsters/{int(internal_id)}/", timeout=timeout)
    r.raise_for_status()
    return r.json()

def fetch_swarfarm_monsters(com2us_ids: list[int], cache_path: Path) -> dict[int, dict]:
    """Return {com2us_id: {name, hp, atk, ...}} using a persistent cache."""
    out = _read_cache(cache_path)
    ids = sorted({int(x) for x in com2us_ids if x})
    missing = [i for i in ids if i not in out]
    if not missing:
        return out
    for cid in missing:
        try:
            data = _api_get_list({'com2us_id': cid})
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
    _write_cache(cache_path, out)
    return out

def _img_from_filename(filename: str) -> str:
    filename = (filename or "").strip()
    return f"https://swarfarm.com/static/herders/images/monsters/{filename}" if filename else ""

def resolve_unawakened_and_awakened(com2us_id: int, cache_path: Path) -> dict:
    """Return {'base': {...}, 'awakened': {...}} and cache the pair."""
    cache = _read_cache(cache_path)
    if com2us_id in cache and cache[com2us_id].get("pair_cached"):
        return cache[com2us_id]["pair_cached"]

    try:
        cur_list = _api_get_list({'com2us_id': com2us_id})
        cur = cur_list['results'][0] if cur_list.get('count', 0) >= 1 else None
    except Exception:
        cur = None

    if not cur:
        return {'base': None, 'awakened': None}

    cur_form = {
        'name': cur.get('name', f'ID:{cur.get("com2us_id", com2us_id)}'),
        'com2us_id': cur.get('com2us_id', com2us_id),
        'img': _img_from_filename(cur.get('image_filename') or cur.get('image_file_name') or ''),
    }

    base_form, awak_form = None, None
    try:
        if cur.get('awakens_from'):
            b = _api_get_detail(int(cur['awakens_from']))
            base_form = {
                'name': b.get('name', f'ID:{b.get("com2us_id","?")}'),
                'com2us_id': b.get('com2us_id', 0),
                'img': _img_from_filename(b.get('image_filename') or b.get('image_file_name') or ''),
            }
            awak_form = cur_form
        elif cur.get('awakens_to'):
            a = _api_get_detail(int(cur['awakens_to']))
            awak_form = {
                'name': a.get('name', f'ID:{a.get("com2us_id","?")}'),
                'com2us_id': a.get('com2us_id', 0),
                'img': _img_from_filename(a.get('image_filename') or a.get('image_file_name') or ''),
            }
            base_form = cur_form
        else:
            base_form = cur_form
    except Exception:
        base_form = base_form or cur_form

    pair = {'base': base_form, 'awakened': awak_form}
    cache.setdefault(com2us_id, {})["pair_cached"] = pair
    _write_cache(cache_path, cache)
    return pair
