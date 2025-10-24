# scripts/rune_viewer.py
# Run:  .\.venv_wd\Scripts\python scripts\rune_viewer.py
# Open: http://127.0.0.1:8089

from nicegui import ui
from pathlib import Path
from app.ui.pages.rune_inventory import rune_page

HOST, PORT = '127.0.0.1', 8089
EXPORT_DIR = Path(__file__).resolve().parents[1] / 'data' / 'swex' / 'exports' / 'profile saves'

if __name__ == '__main__':
    rune_page(EXPORT_DIR)
    ui.run(host=HOST, port=PORT, reload=False)
