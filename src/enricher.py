import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys

class SheetEnricher:
    def __init__(self, credentials_file, sheet_id_or_name, sheet_name=None):
        self.credentials_file = "credentials.json"
        self.sheet_id_or_name = "https://docs.google.com/spreadsheets/d/1XFwqibN4frSd65XQemBGEHe5RZ3BmAnKsnOhq6cndYw/edit?gid=1839329484#gid=1839329484"
        self.sheet_name = "ENCODAGE"
        self.client = None
        self.mapping = {} # Pseudo -> Matricule

    def connect(self):
        """Connecte à Google Sheets API."""
        if not os.path.exists(self.credentials_file):
            print(f"  ⚠ Fichier de credentials introuvable : {self.credentials_file}")
            return False
        
        try:
            scope = ['https://spreadsheets.google.com/feeds',
                     'https://www.googleapis.com/auth/spreadsheets',
                     'https://www.googleapis.com/auth/drive.file',
                     'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_file, scope)
            self.client = gspread.authorize(creds)
            return True
        except Exception as e:
            print(f"  ✗ Erreur connexion Google Sheets : {e}")
            return False

    def load_mapping(self):
        """Charge le mapping Pseudo -> Matricule depuis la feuille active."""
        if not self.client:
            return False
            
        try:
            # Ouvrir le sheet
            print(f"  [Debug] Tentative ouverture : {self.sheet_id_or_name}")
            try:
                if 'docs.google.com' in self.sheet_id_or_name:
                    sheet = self.client.open_by_url(self.sheet_id_or_name)
                else:
                    try:
                        sheet = self.client.open_by_key(self.sheet_id_or_name)
                    except gspread.SpreadsheetNotFound:
                        sheet = self.client.open(self.sheet_id_or_name)
            except gspread.SpreadsheetNotFound:
                print(f"  ✗ Spreadsheet introuvable : {self.sheet_id_or_name}")
                return False

            # Sélection de la feuille
            if self.sheet_name:
                try:
                    worksheet = sheet.worksheet(self.sheet_name)
                    print(f"  ✓ Feuille '{self.sheet_name}' sélectionnée")
                except gspread.WorksheetNotFound:
                    print(f"  ⚠ Feuille '{self.sheet_name}' introuvable, utilisation de la première feuille.")
                    worksheet = sheet.get_worksheet(0)
            else:
                worksheet = sheet.get_worksheet(0)
            
            records = worksheet.get_all_records()
            # Colonnes attendues : Matricule, Nom, Prénoms, Pseudo
            
            count = 0
            for row in records:
                pseudo = str(row.get('Pseudo', '')).strip()
                matricule = str(row.get('Matricule', '')).strip()
                
                if pseudo and matricule:
                    # On stocke en lowercase pour la recherche insensible à la casse
                    self.mapping[pseudo.lower()] = matricule
                    count += 1
            
            print(f"  ✓ Mapping chargé : {count} entrées (Pseudo -> Matricule)")
            return True
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  ✗ Erreur lecture feuille : {repr(e)}")
            return False

    def enrich_records(self, records):
        """Complète les numéros manquants dans les enregistrements."""
        count = 0
        for record in records:
            # Si le numéro est vide
            if not record.get('numero'):
                nom = (record.get('nom') or '').strip()
                if nom:
                    # Recherche dans le mapping
                    matricule = self.mapping.get(nom.lower())
                    if matricule:
                        record['numero'] = matricule
                        count += 1
        return count
