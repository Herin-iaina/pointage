import csv
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from .utils import PUNCH_TYPES, parse_punch_type

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

def _col_index_to_letter(col_index):
    """Convertit un index de colonne (1-indexed) en lettre(s) Excel (A, B, ..., Z, AA, AB, ..., AK)."""
    result = ""
    while col_index > 0:
        col_index -= 1
        result = chr(65 + col_index % 26) + result
        col_index //= 26
    return result

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

def enrich_users_from_google_sheet(users, credentials_file='credentials.json', 
                                    sheet_id_or_url=None, sheet_name='ENCODAGE'):
    """Enrichit les utilisateurs avec les numéros depuis un Google Sheet.
    
    Charge le mapping Pseudo -> Matricule depuis Google Sheets et complète
    les utilisateurs sans numéro.
    
    Args:
        users: Liste des utilisateurs à enrichir
        credentials_file: Chemin vers le fichier JSON de credentials
        sheet_id_or_url: ID ou URL du Google Sheet (défaut: hardcodé dans enricher.py)
        sheet_name: Nom de l'onglet à utiliser (défaut: 'ACTIF')
    
    Returns:
        Nombre d'utilisateurs enrichis
    """
    if not HAS_GSPREAD:
        print("  ⚠ gspread/oauth2client non disponible, enrichissement Google Sheets impossible")
        return 0
    
    if not os.path.exists(credentials_file):
        print(f"  ⚠ Fichier de credentials introuvable : {credentials_file}")
        return 0
    
    # URL Google Sheet par défaut (depuis enricher.py)
    if not sheet_id_or_url:
        sheet_id_or_url = "https://docs.google.com/spreadsheets/d/1XFwqibN4frSd65XQemBGEHe5RZ3BmAnKsnOhq6cndYw/edit?gid=1839329484#gid=1839329484"
    
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/spreadsheets',
                 'https://www.googleapis.com/auth/drive.file',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        
        # Ouvrir le sheet
        try:
            if 'docs.google.com' in sheet_id_or_url:
                sheet = client.open_by_url(sheet_id_or_url)
            else:
                try:
                    sheet = client.open_by_key(sheet_id_or_url)
                except gspread.SpreadsheetNotFound:
                    sheet = client.open(sheet_id_or_url)
        except gspread.SpreadsheetNotFound:
            print(f"  ⚠ Spreadsheet introuvable : {sheet_id_or_url}")
            return 0
        
        # Sélectionner la feuille
        try:
            worksheet = sheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            print(f"  ⚠ Feuille '{sheet_name}' introuvable, utilisation de la première feuille.")
            worksheet = sheet.get_worksheet(0)
        
        # Charger le mapping Pseudo -> Matricule
        records = worksheet.get_all_records()
        mapping = {}
        for row in records:
            pseudo = str(row.get('Pseudo', '')).strip()
            matricule = str(row.get('Matricule', '')).strip()
            if pseudo and matricule:
                mapping[pseudo.lower()] = matricule
        
        print(f"  ✓ Mapping Google Sheets chargé : {len(mapping)} entrées")
        
        # Enrichir les utilisateurs
        count = 0
        for u in users:
            # Si le numéro est vide
            if not (u.get('number') and str(u.get('number')).strip()):
                nom = (u.get('name') or '').strip()
                if nom:
                    matricule = mapping.get(nom.lower())
                    if matricule:
                        u['number'] = matricule
                        count += 1
        
        return count
        
    except Exception as e:
        print(f"  ⚠ Erreur lors de l'enrichissement Google Sheets : {e}")
        return 0

def check_users_not_in_attendance(attendance_records, credentials_file='credentials.json',
                                   sheet_id_or_url=None, sheet_name='ACTIF'):
    """Vérifie quels utilisateurs du Google Sheet n'ont pas d'enregistrements d'attendance.
    
    Retourne une liste des utilisateurs du Sheet sans pointage.
    """
    if not HAS_GSPREAD:
        print("  ⚠ gspread/oauth2client non disponible")
        return []
    
    if not os.path.exists(credentials_file):
        print(f"  ⚠ Fichier de credentials introuvable : {credentials_file}")
        return []
    
    # URL Google Sheet par défaut
    if not sheet_id_or_url:
        sheet_id_or_url = "https://docs.google.com/spreadsheets/d/1XFwqibN4frSd65XQemBGEHe5RZ3BmAnKsnOhq6cndYw/edit?gid=1839329484#gid=1839329484"
    
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/spreadsheets',
                 'https://www.googleapis.com/auth/drive.file',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        
        # Ouvrir le sheet
        try:
            if 'docs.google.com' in sheet_id_or_url:
                sheet = client.open_by_url(sheet_id_or_url)
            else:
                try:
                    sheet = client.open_by_key(sheet_id_or_url)
                except gspread.SpreadsheetNotFound:
                    sheet = client.open(sheet_id_or_url)
        except gspread.SpreadsheetNotFound:
            print(f"  ⚠ Spreadsheet introuvable : {sheet_id_or_url}")
            return []
        
        # Sélectionner la feuille
        try:
            worksheet = sheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            print(f"  ⚠ Feuille '{sheet_name}' introuvable")
            worksheet = sheet.get_worksheet(0)
        
        # Charger les utilisateurs du sheet
        records = worksheet.get_all_records()
        sheet_users = {}
        for row in records:
            pseudo = str(row.get('Pseudo', '')).strip()
            if pseudo:
                sheet_users[pseudo.lower()] = row
        
        print(f"  ✓ {len(sheet_users)} utilisateurs chargés du Google Sheet")
        
        # Extraire les noms d'utilisateurs avec pointage (attendance)
        attendance_names = set()
        for record in attendance_records:
            user_id = record.get('user_id', '')
            if user_id:
                attendance_names.add(user_id)
        
        print(f"  ✓ {len(attendance_names)} utilisateurs uniques avec pointage")
        
        # Trouver les utilisateurs du sheet sans pointage
        # On regarde les Pseudo du sheet vs les user_id du pointage
        # Problème: on compare Pseudo vs user_id (pas directement comparables)
        # Solution: on retourne tous les utilisateurs du sheet avec peu/pas de pointage
        users_without_attendance = []
        for pseudo_lower, row in sheet_users.items():
            pseudo = str(row.get('Pseudo', '')).strip()
            # Compter combien de fois ce nom apparaît dans l'attendance
            count_in_attendance = sum(1 for r in attendance_records 
                                     if (r.get('user_id') or '').lower() == pseudo_lower)
            if count_in_attendance == 0:
                users_without_attendance.append({
                    'pseudo': pseudo,
                    'nom': row.get('Nom', ''),
                    'prenoms': row.get('Prénoms', ''),
                    'matricule': row.get('Matricule', ''),
                    'nombre_pointages': 0,
                })
        
        print(f"  ✓ {len(users_without_attendance)} utilisateurs du Sheet sans pointage")
        
        return users_without_attendance
        
    except Exception as e:
        print(f"  ⚠ Erreur lors de la vérification : {e}")
        return []

def save_users_not_in_attendance(users_without_attendance, output_dir='output', filename=None):
    """Sauvegarde les utilisateurs du Sheet sans pointage en CSV et JSON."""
    if not users_without_attendance:
        return None, None
    
    # Fichier CSV
    if filename is None:
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f'utilisateurs_sans_pointage_{now}.csv'
        json_filename = f'utilisateurs_sans_pointage_{now}.json'
    else:
        csv_filename = filename.replace('.json', '.csv')
        json_filename = filename
    
    csv_filepath = os.path.join(output_dir, csv_filename)
    json_filepath = os.path.join(output_dir, json_filename)
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Écrire CSV
    fieldnames = ['pseudo', 'nom', 'prenoms', 'matricule', 'nombre_pointages']
    with open(csv_filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(users_without_attendance)
    
    # Écrire JSON
    with open(json_filepath, 'w', encoding='utf-8') as f:
        json.dump(users_without_attendance, f, ensure_ascii=False, indent=2)
    
    return csv_filepath, json_filepath

def write_user_ids_to_google_sheet(users, credentials_file='credentials.json',
                                    sheet_id_or_url=None, sheet_name='ENCODAGE',
                                    column_index=37):
    """Écrit les user_id des utilisateurs ZK dans la colonne 37 du Google Sheet.
    
    Matcher les utilisateurs par Pseudo et écrit l'user_id dans la colonne spécifiée.
    
    Args:
        users: Liste des utilisateurs ZK avec user_id et name
        credentials_file: Chemin vers le fichier JSON de credentials
        sheet_id_or_url: ID ou URL du Google Sheet
        sheet_name: Nom de l'onglet à utiliser (défaut: 'ENCODAGE')
        column_index: Numéro de colonne (défaut: 37, colonne AK en A1 notation)
    
    Returns:
        Nombre d'user_id écris
    """
    if not HAS_GSPREAD:
        print("  ⚠ gspread/oauth2client non disponible")
        return 0
    
    if not os.path.exists(credentials_file):
        print(f"  ⚠ Fichier de credentials introuvable : {credentials_file}")
        return 0
    
    # URL Google Sheet par défaut
    if not sheet_id_or_url:
        sheet_id_or_url = "https://docs.google.com/spreadsheets/d/1XFwqibN4frSd65XQemBGEHe5RZ3BmAnKsnOhq6cndYw/edit?gid=1839329484#gid=1839329484"
    
    try:
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/spreadsheets',
                 'https://www.googleapis.com/auth/drive.file',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        
        # Ouvrir le sheet
        try:
            if 'docs.google.com' in sheet_id_or_url:
                sheet = client.open_by_url(sheet_id_or_url)
            else:
                try:
                    sheet = client.open_by_key(sheet_id_or_url)
                except gspread.SpreadsheetNotFound:
                    sheet = client.open(sheet_id_or_url)
        except gspread.SpreadsheetNotFound:
            print(f"  ⚠ Spreadsheet introuvable : {sheet_id_or_url}")
            return 0
        
        # Sélectionner la feuille
        try:
            worksheet = sheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            print(f"  ⚠ Feuille '{sheet_name}' introuvable")
            worksheet = sheet.get_worksheet(0)
        
        # Charger les utilisateurs du sheet avec leurs numéros de ligne
        records = worksheet.get_all_records()
        
        # Créer un mapping Pseudo -> user_id depuis les utilisateurs ZK
        zk_users_map = {}
        for u in users:
            name = (u.get('name') or '').strip()
            user_id = u.get('user_id', '')
            if name and user_id:
                zk_users_map[name.lower()] = str(user_id)
        
        print(f"  ✓ {len(zk_users_map)} utilisateurs ZK chargés")
        
        # Préparer les mises à jour
        updates = []
        count = 0
        
        # Les records sont 0-indexed, mais les lignes du sheet commencent à 2 (ligne 1 = header)
        for idx, row in enumerate(records, start=2):  # start=2 car ligne 1 est le header
            pseudo = str(row.get('Pseudo', '')).strip()
            if pseudo:
                user_id = zk_users_map.get(pseudo.lower())
                if user_id:
                    # Convertir l'index de colonne en lettre(s) (1=A, 2=B, ..., 37=AK)
                    col_letter = _col_index_to_letter(column_index)
                    cell_ref = f"{col_letter}{idx}"
                    updates.append({'range': cell_ref, 'values': [[user_id]]})
                    count += 1
        
        # Appliquer les mises à jour par batch
        if updates:
            print(f"  Mise à jour de {count} cellules...")
            for update in updates:
                worksheet.update(update['range'], update['values'])
            print(f"  ✓ {count} user_id écris dans la colonne {column_index}")
        else:
            print(f"  ⚠ Aucun user_id à écrire")
        
        return count
        
    except Exception as e:
        print(f"  ⚠ Erreur lors de l'écriture des user_id : {e}")
        import traceback
        traceback.print_exc()
        return 0

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
            readable_name = members[0].get('name') or key
            duplicates[readable_name] = members

    return duplicates

def save_duplicates_to_csv(duplicates, output_dir='output', filename=None):
    """Sauvegarde les doublons en CSV."""
    if filename is None:
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'utilisateurs_doublons_{now}.csv'
    
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
                'card_number': m.get('card_number', ''),
            }
            rows.append(row)

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return filepath

def list_users_without_number(users):
    """Retourne la liste des utilisateurs n'ayant pas de numéro (champ 'number' vide)."""
    return [u for u in users if not (u.get('number') and str(u.get('number')).strip())]


def save_users_to_json(users, output_dir='output', filename=None):
    """Sauvegarde la liste d'utilisateurs en JSON dans le dossier `output`.

    Retourne le chemin du fichier écrit.
    """
    if filename is None:
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'utilisateurs_{now}.json'

    filepath = os.path.join(output_dir, filename)

    # S'assurer que le dossier existe
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

    return filepath


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
    """Fusionne utilisateurs et attendance pour génération finale.
    Filtre pour ne garder que le mois en cours et le mois précédent.
    """
    clean_records = []
    
    for record in attendance_records:
        user_id = record.get('user_id', '')
        timestamp = record.get('timestamp', '')
        raw = record.get('raw', '')
        
        if not user_id or not timestamp:
            continue
            
        # Conversion timestamp pour filtrage
        try:
            if isinstance(timestamp, str):
                # Essayer plusieurs formats si nécessaire, mais standard ZK est souvent YYYY-MM-DD HH:MM:SS
                ts_obj = datetime.strptime(str(timestamp), '%Y-%m-%d %H:%M:%S')
            else:
                ts_obj = timestamp
                
            if not is_recent_date(ts_obj):
                continue
        except Exception:
            # Si erreur de parsing, on garde par sécurité ou on log ?
            # Pour l'instant on ignore si on ne peut pas parser la date
            continue
        
        user_info = users_dict.get(user_id, {})
        name = user_info.get('name', '')
        number = user_info.get('number', '')
        
        punch_tuple = parse_punch_type(raw)
        punch_type = PUNCH_TYPES.get(punch_tuple, 'Inconnu')
        
        clean_records.append({
            'nom': name,
            'numero': number,
            'date_heure': str(timestamp),
            'type': punch_type,
        })
    
    return clean_records

def save_final_attendance(records, output_dir='output', filename=None):
    """Sauvegarde le fichier final propre."""
    if filename is None:
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'pointage_final_{now}.csv'
    
    filepath = os.path.join(output_dir, filename)
    
    fieldnames = ['nom', 'numero', 'date_heure', 'type']
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    
    return filepath

def print_statistics(records):
    """Affiche les statistiques du fichier final."""
    empty_numbers = sum(1 for r in records if not r.get('numero'))
    type_counts = {}
    for r in records:
        t = r.get('type', 'Inconnu')
        type_counts[t] = type_counts.get(t, 0) + 1
    
    print(f"  Total enregistrements : {len(records)}")
    print(f"  Numéros vides : {empty_numbers} ({100*empty_numbers/len(records):.1f}%)")
    print(f"  Types : {type_counts}")

def cleanup_intermediate_files(keep_files, output_dir='output'):
    """Supprime tous les fichiers CSV sauf ceux spécifiés dans le dossier output."""
    # Note: This logic might need adjustment if we only want to clean output dir
    # Original script cleaned current dir. Let's clean output dir.
    csv_files = list(Path(output_dir).glob('*.csv'))
    removed = 0
    keep_names = {Path(f).name for f in keep_files}
    
    for f in csv_files:
        if f.name not in keep_names:
            f.unlink()
            removed += 1
    return removed
