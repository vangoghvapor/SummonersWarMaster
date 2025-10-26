import os, subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SWEX_CMD = REPO / 'scripts' / 'run_swex.cmd'   # <-- adjust if it lives elsewhere

def launch_swex_detached():
    if os.name != 'nt':
        print('[SWEX] Skipping: .cmd is Windows-only')
        return
    if not SWEX_CMD.exists():
        print(f'[SWEX] Not found: {SWEX_CMD}')
        return
    try:
        # Run in its own shell, don’t block, don’t spam our console
        subprocess.Popen(
            str(SWEX_CMD),
            shell=True,
            cwd=str(SWEX_CMD.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            creationflags=getattr(subprocess, 'CREATE_NEW_CONSOLE', 0),
        )
        print(f'[SWEX] Launched: {SWEX_CMD}')
    except Exception as e:
        print(f'[SWEX] Failed to launch: {e}')