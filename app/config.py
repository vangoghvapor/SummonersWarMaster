# ---------- config ----------
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EXPORT_DIR = REPO / 'data' / 'swex' / 'exports' / 'profile saves'
MONSTER_NAME_MAP = REPO / 'data' / 'swex' / 'monster_names.json'  # optional
CACHE_DIR = REPO / 'data' / 'swex' / 'cache'
CACHE_DIR.mkdir(parents=True, exist_ok=True)
SWARFARM_CACHE = CACHE_DIR / 'swarfarm_monsters.json'

# rune set icons (local assets)
ICONS_DIR = REPO / 'tools' / 'sw-exporter' / 'assets' / 'runes'

HOST, PORT = '127.0.0.1', 8081
