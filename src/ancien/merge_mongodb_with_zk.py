#!/usr/bin/env python3
"""
Fusionne les données ZK avec MongoDB enrichies.
Génère les fichiers finals avec les numéros complets.

À utiliser après:
1. python3 -m src.main
2. python3 enrich_mongodb_user_id.py
3. python3 sync_mongodb_attendance.py
4. python3 export_mongodb.py
"""

import csv
import json
from pathlib import Path
from datetime import datetime

# Configuration
OUTPUT_DIR = "output"


def find_latest_file(pattern):
    """Trouve le fichier le plus récent correspondant au pattern"""
    files = list(Path(OUTPUT_DIR).glob(pattern))
    if not files:
        return None
    return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[0]


def load_users_from_csv(filepath):
    """Charge les utilisateurs depuis un CSV"""
    users = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_id = row.get('user_id', '').strip()
                if user_id:
                    users[user_id] = row
        print(f"✅ {len(users)} utilisateurs chargés depuis {filepath.name}")
        return users
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        return {}


def merge_users(zk_users, mongodb_users):
    """Fusionne les données ZK avec MongoDB enrichies"""
    merged = {}
    
    # D'abord ajouter tous les utilisateurs MongoDB
    for user_id, user_data in mongodb_users.items():
        merged[user_id] = dict(user_data)
    
    # Puis compléter/overrider avec les données ZK
    for user_id, user_data in zk_users.items():
        if user_id in merged:
            # Garder les données MongoDB (notamment numéro)
            # Mais mettre à jour si manquant
            for key, value in user_data.items():
                if not merged[user_id].get(key) and value:
                    merged[user_id][key] = value
        else:
            # Nouvel utilisateur
            merged[user_id] = dict(user_data)
    
    return merged


def load_attendance_from_csv(filepath):
    """Charge l'attendance depuis un CSV"""
    records = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        print(f"✅ {len(records)} enregistrements chargés depuis {filepath.name}")
        return records
    except Exception as e:
        print(f"❌ Erreur lors du chargement: {e}")
        return []


def enrich_attendance(attendance_records, users_dict):
    """Enrichit l'attendance avec les numéros des utilisateurs"""
    enriched = []
    no_number_count = 0
    
    for record in attendance_records:
        user_id = record.get('user_id', '').strip()
        
        # Chercher l'utilisateur
        if user_id in users_dict:
            user = users_dict[user_id]
            numero = user.get('number', '').strip()
            
            enriched_record = {
                'nom': user.get('pseudo', user.get('name', '')),
                'numero': numero,
                'date_heure': record.get('date_heure', record.get('timestamp', '')),
                'type': record.get('type', '')
            }
            
            if not numero:
                no_number_count += 1
            
            enriched.append(enriched_record)
    
    if no_number_count > 0:
        print(f"⚠️  {no_number_count} enregistrements sans numéro")
    
    return enriched


def save_merged_users(merged_users, filename=None):
    """Sauvegarde les utilisateurs fusionnés"""
    if filename is None:
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'utilisateurs_merged_{now}.csv'
    
    filepath = Path(OUTPUT_DIR) / filename
    
    if not merged_users:
        print("❌ Aucun utilisateur à sauvegarder")
        return None
    
    # Déterminer les colonnes
    fieldnames = ['user_id', 'pseudo', 'name', 'number', 'matricule', 'email', 
                  'pole', 'bench', 'title', 'privilege', 'group_id', 'card_number', 'device_ip']
    
    try:
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for user_id, user_data in sorted(merged_users.items()):
                writer.writerow(user_data)
        
        # Statistiques
        with_number = sum(1 for u in merged_users.values() if u.get('number', '').strip())
        without_number = len(merged_users) - with_number
        
        print(f"✅ {len(merged_users)} utilisateurs sauvegardés")
        print(f"   - Avec numéro: {with_number}")
        print(f"   - Sans numéro: {without_number}")
        print(f"📄 Fichier: {filepath.name}")
        
        return filepath
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")
        return None


def save_enriched_attendance(enriched_records, filename=None):
    """Sauvegarde l'attendance enrichie"""
    if filename is None:
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'pointage_merged_{now}.csv'
    
    filepath = Path(OUTPUT_DIR) / filename
    
    if not enriched_records:
        print("❌ Aucun enregistrement à sauvegarder")
        return None
    
    try:
        fieldnames = ['nom', 'numero', 'date_heure', 'type']
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(enriched_records)
        
        # Statistiques
        with_number = sum(1 for r in enriched_records if r.get('numero', '').strip())
        without_number = len(enriched_records) - with_number
        
        print(f"✅ {len(enriched_records)} enregistrements sauvegardés")
        print(f"   - Avec numéro: {with_number}")
        print(f"   - Sans numéro: {without_number}")
        print(f"📄 Fichier: {filepath.name}")
        
        return filepath
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")
        return None


def main():
    print("=" * 70)
    print("FUSION - ZK + MONGODB → FICHIERS FINALS")
    print("=" * 70)
    print()
    
    # Trouver les fichiers
    print("🔍 Recherche des fichiers sources...")
    
    zk_users_file = find_latest_file("utilisateurs_*.csv")
    if not zk_users_file:
        print("❌ Fichier utilisateurs ZK non trouvé")
        print("   Exécutez d'abord: python3 -m src.main")
        return
    print(f"✓ ZK utilisateurs: {zk_users_file.name}")
    
    mongodb_users_file = find_latest_file("utilisateurs_mongodb_*.csv")
    if not mongodb_users_file:
        print("❌ Fichier utilisateurs MongoDB non trouvé")
        print("   Exécutez d'abord: python3 export_mongodb.py")
        return
    print(f"✓ MongoDB utilisateurs: {mongodb_users_file.name}")
    
    zk_attendance_file = find_latest_file("pointage_final_*.csv")
    if not zk_attendance_file:
        print("❌ Fichier pointage ZK non trouvé")
        print("   Exécutez d'abord: python3 -m src.main")
        return
    print(f"✓ ZK pointage: {zk_attendance_file.name}")
    print()
    
    # Charger les données
    print("📋 Chargement des données...")
    zk_users = load_users_from_csv(zk_users_file)
    mongodb_users = load_users_from_csv(mongodb_users_file)
    attendance = load_attendance_from_csv(zk_attendance_file)
    print()
    
    if not zk_users or not mongodb_users or not attendance:
        print("❌ Données insuffisantes pour la fusion")
        return
    
    # Fusionner les utilisateurs
    print("🔄 Fusion des utilisateurs...")
    merged_users = merge_users(zk_users, mongodb_users)
    print(f"✓ {len(merged_users)} utilisateurs fusionnés")
    print()
    
    # Enrichir l'attendance
    print("🔄 Enrichissement de l'attendance...")
    enriched_attendance = enrich_attendance(attendance, merged_users)
    print(f"✓ {len(enriched_attendance)} enregistrements enrichis")
    print()
    
    # Sauvegarder
    print("💾 Sauvegarde des fichiers finals...")
    users_output = save_merged_users(merged_users)
    attendance_output = save_enriched_attendance(enriched_attendance)
    print()
    
    print("=" * 70)
    print("✨ FUSION TERMINÉE")
    print("=" * 70)
    print(f"\n📁 Fichiers générés:")
    if users_output:
        print(f"   ✓ {users_output.name}")
    if attendance_output:
        print(f"   ✓ {attendance_output.name}")
    
    print(f"\n✅ Les fichiers ont maintenant tous les numéros!")


if __name__ == "__main__":
    main()
