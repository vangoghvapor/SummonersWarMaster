# app/main.py

from pathlib import Path
from nicegui import ui, app as nicegui_app

# if you already have these in app.config, this will reuse them
try:
    from app.config import EXPORT_DIR, HOST, PORT, ICONS_DIR
except Exception:
    # sensible fallbacks if config isn't ready yet
    REPO = Path(__file__).resolve().parents[1]
    EXPORT_DIR = REPO / 'data' / 'swex' / 'exports' / 'profile saves'
    ICONS_DIR = REPO / 'tools' / 'sw-exporter' / 'assets' / 'runes'
    HOST, PORT = '127.0.0.1', 8080

# import your page functions
# NOTE: adjust the function names if yours differ (e.g. `page`, `rune_page`, `monster_page`)
from app.ui.pages.rune_inventory import rune_page
from app.ui.pages.monster_browser import monster_page

# static mount for icons (matches what your scripts were doing)
nicegui_app.add_static_files('/swex_icons', str(ICONS_DIR.resolve()))

@ui.page('/')
def index():
    with ui.column().classes('items-start gap-2 p-4'):
        ui.label('SWEX Tools').style('font-weight:600; font-size: 1.2rem;')
        ui.link('Rune Inventory', '/runes')
        ui.link('Monster Browser', '/monsters')

@ui.page('/runes')
def runes():
    # your rune page expects an export_dir: Path
    rune_page(EXPORT_DIR)

@ui.page('/monsters')
def monsters():
    # your monster page likely also needs export_dir; if not, remove the arg
    monster_page(EXPORT_DIR)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(host=HOST, port=PORT)
