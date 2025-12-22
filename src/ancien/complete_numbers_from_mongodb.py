#!/usr/bin/env python3
"""
Enrichit les fichiers CSV générés par src.main avec les numéros de MongoDB.
À utiliser après que MongoDB soit enrichi avec les numéros.

Usage:
  python3 complete_numbers_from_mongodb.py
"""

import csv
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

# Configuration
MONGODB_URI = "mongodb://172.17.17.72:27017"
DB_NAME = "pointage"
USERS_COLLECTION = "users"


def find_latest_file(pattern):
    """Trouve le fichier le plus récent correspondant au pattern"""
    output_dir = Path("output")
    files = list(output_dir.glob(pattern))
    if not files:
        return None
    return sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[0]


def connect_to_mongodb():
    """Se connecte à MongoDB"""
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ismaster')
        db = client[DB_NAME]
        print(f"✅ Connecté à MongoDB")
        return db
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        print(f"❌ Erreur de connexion MongoDB: {e}")
        return None


def load_users_from_mongodb(db):
    """Charge tous les utilisateurs de MongoDB avec leurs numéros"""
    if db is None:
        return {}
    
    try:
        users_collection = db[USERS_COLLECTION]
        users = {}
        
        for user in users_collection.find({}):
            user_id = user.get('user_id')
            if user_id:
                users[int(user_id)] = {
                    'number': user.get('number', '').strip(),
                    'pseudo': user.get('pseudo', '').strip(),
                    'email': user.get('email', '').strip(),
                    'pole': user.get('pole', '').strip(),
                    'bench': user.get('bench', '').strip(),
                    'matricule': user.get('matricule', '').strip(),
                }
        
        print(f"✅ {len(users)} utilisateurs chargés de MongoDB")
        return users
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return {}


def enrich_users_csv(input_file, mongodb_users, output_file=None):
    """Enrichit le fichier utilisateurs avec les données de MongoDB"""
    if not Path(input_file).exists():
        print(f"❌ Fichier non trouvé: {input_file}")
        return None
    
    if output_file is None:
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'output/utilisateurs_enrichis_{now}.csv'
    
    try:
        rows = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            for row in reader:
                user_id = row.get('user_id')
                if user_id:
                    try:
                        uid = int(user_id)
                        if uid in mongodb_users:
                            mongo_data = mongodb_users[uid]
                            # Compléter les données vides avec celles de MongoDB
                            if not row.get('number'):
                                row['number'] = mongo_data['number']
                            if not row.get('email') and mongo_data['email']:
                                if 'email' in fieldnames:
                                    row['email'] = mongo_data['email']
                    except ValueError:
                        pass
                
                rows.append(row)
        
        # Sauvegarder
        Path('output').mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        # Statistiques
        with_number = sum(1 for r in rows if r.get('number', '').strip())
        without_number = len(rows) - with_number
        
        print(f"✅ Fichier enrichi: {Path(output_file).name}")
        print(f"   - Avec numéro: {with_number}/{len(rows)}")
        print(f"   - Sans numéro: {without_number}/{len(rows)}")
        
        return output_file
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None


def enrich_attendance_csv(input_file, mongodb_users, output_file=None):
    """Enrichit le fichier pointage avec les numéros de MongoDB"""
    if not Path(input_file).exists():
        print(f"❌ Fichier non trouvé: {input_file}")
        return None
    
    if output_file is None:
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'output/pointage_enrichi_{now}.csv'
    
    try:
        rows = []
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            
            for row in reader:
                # Essayer de trouver par user_id ou nom
                numero = row.get('numero', '').strip()
                
                if not numero:
                    # Chercher par nom dans les utilisateurs MongoDB
                    nom = row.get('nom', '').strip()
                    for uid, mongo_data in mongodb_users.items():
                        if mongo_data['pseudo'].lower() == nom.lower():
                            row['numero'] = mongo_data['number']
                            break
                
                rows.append(row)
        
        # Sauvegarder
        Path('output').mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        # Statistiques
        with_number = sum(1 for r in rows if r.get('numero', '').strip())
        without_number = len(rows) - with_number
        
        print(f"✅ Fichier enrichi: {Path(output_file).name}")
        print(f"   - Avec numéro: {with_number}/{len(rows)}")
        print(f"   - Sans numéro: {without_number}/{len(rows)}")
        
        return output_file
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None


def main():
    print("=" * 70)
    print("ENRICHISSEMENT DES FICHIERS CSV AVEC LES NUMÉROS DE MONGODB")
    print("=" * 70)
    print()
    
    # Connexion MongoDB
    db = connect_to_mongodb()
    if db is None:
        return
    print()
    
    # Charger les utilisateurs de MongoDB
    print("📋 Chargement des utilisateurs MongoDB...")
    mongodb_users = load_users_from_mongodb(db)
    if not mongodb_users:
        print("❌ Aucun utilisateur dans MongoDB")
        return
    print()
    
    # Trouver les fichiers source
    print("🔍 Recherche des fichiers source...")
    
    users_file = find_latest_file("utilisateurs_*.csv")
    if not users_file or 'mongodb' in users_file.name or 'merged' in users_file.name or 'enrichis' in users_file.name:
        users_file = find_latest_file("utilisateurs_[0-9]*.csv")
    
    attendance_file = find_latest_file("pointage_final_*.csv")
    
    if users_file:
        print(f"✓ Utilisateurs: {users_file.name}")
    else:
        print("❌ Fichier utilisateurs non trouvé")
    
    if attendance_file:
        print(f"✓ Pointage: {attendance_file.name}")
    else:
        print("❌ Fichier pointage non trouvé")
    print()
    
    # Enrichir les fichiers
    print("💾 Enrichissement des fichiers...")
    
    if users_file:
        print("\n📝 Enrichissement des utilisateurs...")
        enrich_users_csv(str(users_file), mongodb_users)
    
    if attendance_file:
        print("\n📝 Enrichissement du pointage...")
        enrich_attendance_csv(str(attendance_file), mongodb_users)
    
    print("\n" + "=" * 70)
    print("✨ Enrichissement terminé!")
    print("=" * 70)


if __name__ == "__main__":
    main()
