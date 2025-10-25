# app/pages/monster_browser_page.py

from __future__ import annotations
from pathlib import Path
import pandas as pd
from nicegui import ui, app

from app.config import ICONS_DIR, SWARFARM_CACHE
from app.logic.data_loading.profiles import find_profiles, load_profile
from app.logic.data_loading.monsters_io import load_monsters_df
from app.logic.data_loading.rune_io import load_runes_df
from app.logic.formatting.mapping import get_set_icon_map
from app.logic.formatting.filters import filter_monsters
from app.logic.formatting.summaries import join_equipped
from app.logic.api_helpers.swarfarm import resolve_unawakened_and_awakened
from app.logic.calc.monster_stats import apply_runes_to_base
from app.logic.calc.rune_calc import unit_rune_totals


def monster_page(export_dir: Path) -> None:
    """Build the Monster Browser UI into the current NiceGUI app."""
    # static files for set icons (idempotent)
    try:
        app.add_static_files('/swex_icons', str(ICONS_DIR.resolve()))
    except Exception:
        pass

    SET_ICON_PATH = get_set_icon_map(ICONS_DIR)

    # ---------- UI scaffolding ----------
    STATE = {
        'mapping': [],
        'path': None,
        'data': None,
        'df_mons': pd.DataFrame(),
        'df_runes': pd.DataFrame(),
    }

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
    ]

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


    # ---------- logic (closures over STATE/widgets) ----------
    def refresh_profiles():
        STATE['mapping'] = find_profiles(export_dir)
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

        # compat: ensure 'unit_id' exists for downstream code
        if 'unit_id' not in df_runes.columns and 'equipped_unit_id' in df_runes.columns:
            df_runes = df_runes.rename(columns={'equipped_unit_id': 'unit_id'})
        if 'unit_id' in df_runes.columns:
            df_runes['unit_id'] = pd.to_numeric(df_runes['unit_id'], errors='coerce').fillna(0).astype(int)

        df_mons = load_monsters_df(STATE['data'])

        if not df_mons.empty:
            extras = []
            for _, row in df_mons.iterrows():
                tot = unit_rune_totals(df_runes, int(row['unit_id']))
                extras.append(apply_runes_to_base(row, tot))
            df_mons = pd.concat([df_mons, pd.DataFrame(extras, index=df_mons.index)], axis=1)

        STATE['df_runes'] = df_runes
        STATE['df_mons']  = join_equipped(df_mons, df_runes, SET_ICON_PATH)
        refresh_table()

    def refresh_table():
        filt = filter_monsters(
            STATE['df_mons'],
            stars=f_star.value,
            lv_min=f_lvl_min.value,
            lv_max=f_lvl_max.value,
            min_runes=f_runes_min.value,
            query=f_q.value,
        )
        table.rows = filt.to_dict(orient='records')
        table.update()

    def open_monster_panel(unit_id: int):
        if split.value >= 99:
            split.value = 70  # reopen to 70/30

        dfm = STATE['df_mons']; dfr = STATE['df_runes']
        if dfm.empty:
            return
        row = dfm[dfm['unit_id'] == unit_id]
        if row.empty:
            return
        r = row.iloc[0]

        d_title.text = f"{r['name']} • {int(r['★'])}★ Lv{int(r['level'])}"

        d_stats.clear()
        with d_stats:
            cid = int(r.get('com2us_id') or 0)
            pair = resolve_unawakened_and_awakened(cid, SWARFARM_CACHE) if cid else {'base': None, 'awakened': None}

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

    # filter hooks & initial boot
    f_star.on('update:model-value', lambda *_: refresh_table())
    f_lvl_min.on('update:model-value', lambda *_: refresh_table())
    f_lvl_max.on('update:model-value', lambda *_: refresh_table())
    f_runes_min.on('update:model-value', lambda *_: refresh_table())
    f_q.on('update:model-value', lambda *_: refresh_table())

    refresh_profiles()
    print('[monster_page] icons mapped:', sorted(SET_ICON_PATH.keys()))
