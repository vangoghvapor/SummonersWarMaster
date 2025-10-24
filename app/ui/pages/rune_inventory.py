from nicegui import ui
from pathlib import Path
import pandas as pd

from app.model.runes import SET
from app.logic.data_loading.profiles import find_profiles
from app.logic.data_loading.rune_io import load_runes_df
from app.logic.formatting.filters import filter_runes
from app.logic.formatting.summaries import summary_lines

def page(export_dir: Path):
    STATE = {'mapping': [], 'df': pd.DataFrame()}

    with ui.header().classes('items-center gap-3'):
        ui.label('SWMaster Rune Viewer').classes('text-xl font-bold')
        with ui.expansion('How “Score” is calculated', icon='info').classes('m-4'):
            ui.label('Innate + substats only (main stat ignored).')
            ui.code(
                'Score = 100 * [\n'
                '    (HP% + ATK% + DEF% + ACC% + RES%) / 40\n'
                '  + (SPD + CR) / 30\n'
                '  + (CD) / 35\n'
                '  + 0.35 * ( HP_flat / 1875 + (ATK_flat + DEF_flat) / 100 )\n'
                ']', language='text'
            )

    profile_select = ui.select(options=[], label='Profile').classes('m-4 min-w-[560px]')
    ui.button('Load', on_click=lambda: _load_selected(profile_select.value)).classes('m-4')

    with ui.card().classes('m-4'):
        ui.label('Summary (filtered)').classes('text-lg font-semibold mb-2')
        summary_line1 = ui.label('')
        summary_line2 = ui.label('')
        summary_line3 = ui.label('')
        summary_line4 = ui.label('')

    columns = [
        {'name':'rune_id','label':'ID','field':'rune_id','align':'left','sortable':True},
        {'name':'slot','label':'Slot','field':'slot','sortable':True},
        {'name':'set','label':'Set','field':'set','sortable':True},
        {'name':'grade★','label':'★','field':'grade★','sortable':True},
        {'name':'level','label':'+','field':'level','sortable':True},
        {'name':'main','label':'Main','field':'main','sortable':True},
        {'name':'innate','label':'Innate','field':'innate','sortable':True},
        {'name':'subs','label':'Subs','field':'subs'},
        {'name':'equipped','label':'Eq','field':'equipped','sortable':True},
        {'name':'equipped_unit_id','label':'Unit ID','field':'equipped_unit_id'},
        {'name':'score','label':'Score','field':'score','sortable':True},
    ]
    table = ui.table(columns=columns, rows=[], row_key='rune_id',
                     pagination={'rowsPerPage': 20}).classes('m-4')

    with ui.row().classes('m-4 gap-4'):
        set_filter = ui.select(['(any)'] + sorted(set(SET.values())), value='(any)', label='Set').classes('w-48')
        slot_filter = ui.select(['(any)'] + [str(i) for i in range(1,7)], value='(any)', label='Slot').classes('w-32')
        equipped_filter = ui.select(['(any)','equipped','unequipped'], value='(any)', label='Equipped').classes('w-40')
        search_text = ui.input(label='Search (main/innate/subs/set)').classes('w-96')

    def _refresh_profiles():
        STATE['mapping'] = find_profiles(export_dir)
        profile_select.options = [label for label, _ in STATE['mapping']]
        profile_select.value = profile_select.options[0] if profile_select.options else None

    def _load_selected(selected_label):
        if not selected_label:
            ui.notify('No profile selected', color='negative'); return
        path_map = {label: p for (label, p) in STATE['mapping']}
        p = path_map.get(selected_label)
        if not p or not Path(p).exists():
            ui.notify('Selected file missing', color='negative'); return
        STATE['df'] = load_runes_df(Path(p))
        _refresh_table()

    def _refresh_table():
        filtered = filter_runes(
            STATE['df'],
            set_filter.value,
            slot_filter.value,
            equipped_filter.value,
            search_text.value,
        )
        table.rows = filtered.to_dict(orient='records')
        table.update()
        l1, l2, l3, l4 = summary_lines(filtered)
        summary_line1.text = l1
        summary_line2.text = l2
        summary_line3.text = l3
        summary_line4.text = l4

    for ctrl in (set_filter, slot_filter, equipped_filter, search_text):
        ctrl.on('update:model-value', lambda *_: _refresh_table())

    _refresh_profiles()
