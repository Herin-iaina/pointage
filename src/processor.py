"""
Module de traitement des données d'attendance.
Travaille directement avec MongoDB (pas de Google Sheets).
"""

import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from .utils import PUNCH_TYPES, parse_punch_type


def load_corrections(corrections_file='config/user_corrections.json'):
    """Charge les corrections depuis JSON."""
    if not os.path.isfile(corrections_file):
        return {}
    
    try:
        with open(corrections_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        corrections = data.get('corrections', {})
        corrections = {k: v for k, v in corrections.items() if not k.startswith('_')}
        return corrections
    except Exception:
        return {}


def apply_corrections_to_users(users, corrections):
    """Applique les corrections aux utilisateurs."""
    count = 0
    for u in users:
        user_id = str(u.get('user_id', ''))
        if user_id in corrections:
            correction = corrections[user_id]
            if correction.get('number') and not u.get('number'):
                u['number'] = correction['number']
                count += 1
            if correction.get('title') and not u.get('title'):
                u['title'] = correction['title']
                count += 1
    return count


def find_duplicate_name_users(users):
    """Retourne les groupes d'utilisateurs avec le même nom mais user_id différents."""
    groups = {}
    for u in users:
        nm = (u.get('name') or '').strip()
        if not nm:
            continue
        key = nm.lower()
        groups.setdefault(key, []).append(u)

    duplicates = {}
    for key, members in groups.items():
        ids = set((m.get('user_id') for m in members))
        if len(members) > 1 and len(ids) > 1:
            duplicates[key] = members

    return duplicates


def save_duplicates_to_csv(duplicates, output_dir='output', filename=None):
    """Sauvegarde les doublons en CSV."""
    if filename is None:
        filename = 'utilisateurs_doublons.csv'
    
    filepath = os.path.join(output_dir, filename)

    fieldnames = ['group_name', 'device_ip', 'user_id', 'name', 'title', 'number', 'card_number']
    rows = []
    for group_name, members in duplicates.items():
        for m in members:
            row = {
                'group_name': group_name,
                'device_ip': m.get('device_ip', ''),
                'user_id': m.get('user_id', ''),
                'name': m.get('name', ''),
                'title': m.get('title', ''),
                'number': m.get('number', ''),
                'card_number': m.get('card_number', '')
            }
            rows.append(row)

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return filepath


def list_users_without_number(users):
    """Retourne la liste des utilisateurs n'ayant pas de numéro (champ 'number' vide)."""
    return [u for u in users if not (u.get('number') and str(u.get('number')).strip())]


def save_users_without_number_to_csv(users, output_dir='output', filename=None):
    """Sauvegarde les utilisateurs sans numéro dans un CSV dédié."""
    without = list_users_without_number(users)
    if filename is None:
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'utilisateurs_sans_numero_{now}.csv'

    filepath = os.path.join(output_dir, filename)
    fieldnames = ['device_ip', 'user_id', 'name', 'title', 'number', 'privilege', 'group_id', 'card_number']

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for u in without:
            row = {k: u.get(k, '') for k in fieldnames}
            writer.writerow(row)

    return filepath


def is_recent_date(date_obj):
    """Vérifie si la date est dans le mois en cours ou le mois précédent."""
    if not date_obj:
        return False
    
    now = datetime.now()
    # Mois en cours
    if date_obj.year == now.year and date_obj.month == now.month:
        return True
    
    # Mois précédent
    first_of_month = now.replace(day=1)
    last_month = first_of_month - timedelta(days=1)
    if date_obj.year == last_month.year and date_obj.month == last_month.month:
        return True
        
    return False


def prepare_clean_attendance(users_dict, attendance_records):
    """
    Fusionne utilisateurs et attendance pour génération finale.
    Filtre pour ne garder que le mois en cours et le mois précédent.
    
    Args:
        users_dict: Dict {str(user_id): {'name': ..., 'number': ...}}
        attendance_records: Liste des enregistrements d'attendance
    
    Returns:
        Liste des enregistrements nettoyés avec user_id
    """
    clean_records = []
    
    for record in attendance_records:
        user_id = record.get('user_id', '')
        timestamp = record.get('timestamp', '')
        raw = record.get('raw', '')
        
        if not user_id or not timestamp:
            continue
        
        try:
            from datetime import datetime as dt
            date_obj = dt.fromisoformat(str(timestamp).replace('Z', '+00:00'))
            
            if not is_recent_date(date_obj):
                continue
            
            user_info = users_dict.get(str(user_id), {})
            punch_type_tuple = parse_punch_type(raw)
            punch_type = PUNCH_TYPES.get(punch_type_tuple, 'Inconnu')
            
            clean_records.append({
                'user_id': int(user_id) if user_id else '',
                'nom': user_info.get('name', ''),
                'numero': user_info.get('number', ''),
                'date_heure': timestamp,
                'type': punch_type
            })
        except Exception as e:
            continue
    
    return clean_records


def save_final_attendance(records, output_dir='output', filename=None):
    """Sauvegarde le fichier final propre avec user_id."""
    if filename is None:
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'pointage_final_{now}.csv'
    
    filepath = os.path.join(output_dir, filename)
    
    fieldnames = ['user_id', 'nom', 'numero', 'date_heure', 'type']
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r)
    
    return filepath


def print_statistics(records):
    """Affiche les statistiques du fichier final."""
    empty_numbers = sum(1 for r in records if not r.get('numero'))
    type_counts = {}
    for r in records:
        punch_type = r.get('type', 'Inconnu')
        type_counts[punch_type] = type_counts.get(punch_type, 0) + 1
    
    print(f"  Total enregistrements : {len(records)}")
    print(f"  Numéros vides : {empty_numbers} ({100*empty_numbers/len(records):.1f}%)" if records else "  0 enregistrement")
    print(f"  Types : {type_counts}")


def cleanup_intermediate_files(keep_files, output_dir='output'):
    """Supprime tous les fichiers CSV sauf ceux spécifiés dans le dossier output."""
    csv_files = list(Path(output_dir).glob('*.csv'))
    removed = 0
    keep_names = {Path(f).name for f in keep_files}
    
    for f in csv_files:
        if f.name not in keep_names:
            try:
                f.unlink()
                removed += 1
            except:
                pass
    return removed
