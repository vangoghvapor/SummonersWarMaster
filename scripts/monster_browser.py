# scripts/monster_browser.py
from nicegui import ui
from app.config import HOST, PORT, EXPORT_DIR
from app.ui.pages.monster_browser import monster_page

if __name__ == '__main__':
    monster_page(EXPORT_DIR)
    ui.run(host=HOST, port=PORT, reload=False)
