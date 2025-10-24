# app/logic/formatters.py
from app.model.runes import STAT

def fmt_eff(e):
    if not e or e[0] == 0:
        return ""
    t, v = e[0], e[1]
    return f"{STAT.get(t, f'Type{t}')} +{v}"
