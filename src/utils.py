import re

# Mapping des types de pointage
PUNCH_TYPES = {
    (1, 0): "Entrée",
    (1, 1): "Sortie" ,
    (1, 4): "Entrée Pause",
    (1, 5): "Sortie Pause",
}

def parse_user_raw(raw_str: str):
    """Parser basique du champ `raw` pour extraire title/number/card si présents."""
    if not raw_str:
        return {}
    res = {}
    patterns = {
        'title': r"(?:title|title_name)\.?\s*(?:[:=]|\s)\s*([^,\)\]\r\n]+)",
        'number': r"(?:number|no|user_no)\.?\s*(?:[:=]|\s)\s*([0-9A-Za-z_\-]+)",
        'card_number': r"(?:card|card_number|cardno)\.?\s*(?:[:=]|\s)\s*([0-9A-Za-z_\-]+)"
    }
    for k, p in patterns.items():
        m = re.search(p, raw_str, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            val = val.strip('"\'')
            res[k] = val
    return res

def parse_punch_type(raw_str):
    """Extrait le type de pointage (1, X) depuis raw."""
    if not raw_str:
        return None
    match = re.search(r'\(1,\s*([0-5])\)', raw_str)
    if match:
        status = int(match.group(1))
        return (1, status)
    return None
