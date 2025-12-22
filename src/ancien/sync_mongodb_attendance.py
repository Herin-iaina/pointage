#!/usr/bin/env python3
"""
Synchronisation des données d'attendance avec MongoDB.
Utilise directement la base MongoDB sans passer par Google Sheets.

Stratégie:
1. Chercher par user_id si disponible
2. Sinon chercher par pseudo
3. Si doublons, prendre l'ID le plus élevé
4. Insérer/Mettre à jour directement dans MongoDB
"""

import csv
import json
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

# Configuration
MONGODB_URI = "mongodb://172.17.17.72:27017"
DB_NAME = "pointage"
USERS_COLLECTION = "users"
ATTENDANCE_COLLECTION = "attendance"
USERS_CSV_FILE = None  # Auto-détection


def find_latest_users_csv():
    """Trouve le dernier fichier utilisateurs_*.csv"""
    output_dir = Path("output")
    files = list(output_dir.glob("utilisateurs_*.csv"))
    # Exclure les fichiers mongodb et merged
    files = [f for f in files if 'mongodb' not in f.name and 'merged' not in f.name and 'doublons' not in f.name and 'sans_numero' not in f.name]
    if files:
        latest = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        return str(latest)
    return None


def find_latest_duplicates_csv():
    """Trouve le dernier fichier doublons"""
    output_dir = Path("output")
    files = list(output_dir.glob("utilisateurs_doublons_*.csv"))
    if files:
        latest = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
        return str(latest)
    return None


def connect_to_mongodb():
    """Se connecte à MongoDB et retourne la base de données"""
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ismaster')
        db = client[DB_NAME]
        print(f"✅ Connecté à MongoDB: {MONGODB_URI}/{DB_NAME}")
        return db
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        print(f"❌ Erreur de connexion MongoDB: {e}")
        return None


def load_duplicates():
    """Charge la liste des doublons et retourne un dict {name: [user_ids]}"""
    duplicates = {}
    
    dup_file = find_latest_duplicates_csv()
    if not dup_file:
        print(f"⚠️  Fichier des doublons non trouvé")
        return duplicates
    
    try:
        current_group = None
        current_ids = []
        
        with open(dup_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                group_name = row.get('group_name', '').strip()
                user_id = row.get('user_id', '').strip()
                
                # Nouveau groupe
                if group_name and group_name != current_group:
                    if current_group and current_ids:
                        duplicates[current_group] = sorted(current_ids, reverse=True)
                    current_group = group_name
                    current_ids = []
                
                if user_id and user_id.isdigit():
                    current_ids.append(int(user_id))
        
        # Dernier groupe
        if current_group and current_ids:
            duplicates[current_group] = sorted(current_ids, reverse=True)
        
        print(f"✅ {len(duplicates)} groupes de doublons chargés")
        return duplicates
    
    except Exception as e:
        print(f"❌ Erreur lors de la lecture des doublons: {e}")
        return duplicates


def load_zk_users():
    """Charge les utilisateurs ZK depuis le CSV"""
    csv_file = USERS_CSV_FILE if USERS_CSV_FILE else find_latest_users_csv()
    
    if not csv_file:
        print(f"❌ Aucun fichier utilisateurs trouvé")
        return []
    
    users = []
    
    if not Path(csv_file).exists():
        print(f"❌ Le fichier {csv_file} n'existe pas")
        return users
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                users.append({
                    'user_id': int(row['user_id']) if row.get('user_id') else None,
                    'name': row.get('name', '').strip(),
                    'number': row.get('number', '').strip(),
                    'device_ip': row.get('device_ip', '').strip(),
                    'title': row.get('title', '').strip(),
                    'privilege': row.get('privilege', '').strip(),
                    'group_id': row.get('group_id', '').strip(),
                    'card_number': row.get('card_number', '').strip(),
                })
        
        print(f"✅ {len(users)} utilisateurs ZK chargés depuis {Path(csv_file).name}")
        return users
    
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du CSV: {e}")
        return users


def find_user_in_mongodb(db, user_zk, duplicates):
    """
    Cherche l'utilisateur dans MongoDB.
    
    Stratégie:
    1. Chercher par user_id si disponible
    2. Sinon chercher par pseudo
    3. Si doublons détectés, retourner le plus élevé
    """
    users_collection = db[USERS_COLLECTION]
    
    # Si l'utilisateur ZK a un user_id
    if user_zk.get('user_id'):
        user = users_collection.find_one({'user_id': user_zk['user_id']})
        if user:
            return user, 'user_id'
    
    # Sinon chercher par pseudo (name)
    pseudo = user_zk.get('name')
    if pseudo:
        # Vérifier si c'est un doublon
        if pseudo in duplicates:
            # Chercher tous les users avec ce pseudo et retourner le plus élevé
            user_ids = duplicates[pseudo]
            for uid in user_ids:  # Déjà trié en ordre descendant
                user = users_collection.find_one({'user_id': uid})
                if user:
                    return user, f'doublon (user_id={uid})'
        else:
            # Recherche simple par pseudo
            user = users_collection.find_one({'pseudo': pseudo})
            if user:
                return user, 'pseudo'
    
    return None, None


def sync_attendance(db, users_zk, duplicates):
    """Synchronise les données d'attendance avec MongoDB"""
    users_collection = db[USERS_COLLECTION]
    
    matched = 0
    not_found = 0
    inserted = 0
    updated = 0
    not_found_users = []
    
    print(f"\n📊 Synchronisation de {len(users_zk)} utilisateurs ZK...\n")
    
    for user_zk in users_zk:
        user_name = user_zk.get('name', '').strip()
        user_id_zk = user_zk.get('user_id')
        
        try:
            # Chercher l'utilisateur dans MongoDB
            user_mongo, found_by = find_user_in_mongodb(db, user_zk, duplicates)
            
            if user_mongo:
                matched += 1
                
                # Préparer les données à mettre à jour
                update_data = {
                    'name': user_zk['name'],
                    'number': user_zk['number'],
                    'title': user_zk['title'],
                    'device_ip': user_zk['device_ip'],
                    'privilege': user_zk['privilege'],
                    'group_id': user_zk['group_id'],
                    'card_number': user_zk['card_number'],
                    'zk_user_id': user_id_zk,
                    'last_synced': datetime.now().isoformat()
                }
                
                # Ajouter user_id si pas déjà présent
                if not user_mongo.get('user_id') and user_id_zk:
                    update_data['user_id'] = user_id_zk
                
                # Mettre à jour
                users_collection.update_one(
                    {'_id': user_mongo['_id']},
                    {'$set': update_data}
                )
                updated += 1
                print(f"   ✅ {user_name}: Mis à jour (trouvé par {found_by})")
            
            else:
                not_found += 1
                not_found_users.append(user_name)
                
                # Insérer le nouvel utilisateur
                new_user = {
                    'pseudo': user_name,
                    'name': user_zk['name'],
                    'number': user_zk['number'],
                    'title': user_zk['title'],
                    'device_ip': user_zk['device_ip'],
                    'privilege': user_zk['privilege'],
                    'group_id': user_zk['group_id'],
                    'card_number': user_zk['card_number'],
                    'user_id': user_id_zk,
                    'zk_user_id': user_id_zk,
                    'created_at': datetime.now().isoformat(),
                    'last_synced': datetime.now().isoformat()
                }
                
                result = users_collection.insert_one(new_user)
                inserted += 1
                print(f"   ➕ {user_name}: Inséré (user_id={user_id_zk})")
        
        except Exception as e:
            print(f"   ❌ Erreur pour {user_name}: {e}")
    
    return matched, not_found, inserted, updated, not_found_users


def generate_report(matched, not_found, inserted, updated, not_found_users):
    """Génère un rapport d'exécution"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "statistics": {
            "matched": matched,
            "not_found": not_found,
            "inserted": inserted,
            "updated": updated,
            "total_processed": matched + not_found
        },
        "not_found_users": not_found_users[:50]  # Limiter à 50 pour le rapport
    }
    
    report_file = f"output/sync_mongodb_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n📄 Rapport généré: {report_file}")
    except Exception as e:
        print(f"⚠️  Impossible de générer le rapport: {e}")
    
    return report


def main():
    print("=" * 70)
    print("SYNCHRONISATION MONGODB - ATTENDANCE")
    print("=" * 70)
    print()
    
    # Charger les doublons
    print("📋 Chargement des doublons...")
    duplicates = load_duplicates()
    print()
    
    # Charger les utilisateurs ZK
    print("📋 Chargement des utilisateurs ZK...")
    users_zk = load_zk_users()
    if not users_zk:
        print("❌ Aucun utilisateur à synchroniser")
        return
    print()
    
    # Se connecter à MongoDB
    db = connect_to_mongodb()
    if db is None:
        return
    print()
    
    # Synchroniser les données
    matched, not_found, inserted, updated, not_found_users = sync_attendance(
        db, users_zk, duplicates
    )
    
    # Afficher les résultats
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"✅ Utilisateurs trouvés: {matched}")
    print(f"❌ Utilisateurs non trouvés: {not_found}")
    print(f"➕ Utilisateurs insérés: {inserted}")
    print(f"🔄 Utilisateurs mis à jour: {updated}")
    
    if not_found_users and len(not_found_users) <= 20:
        print(f"\n📋 Utilisateurs non trouvés:")
        for user in not_found_users[:20]:
            print(f"   - {user}")
    
    # Générer le rapport
    report = generate_report(matched, not_found, inserted, updated, not_found_users)
    
    print("\n✨ Synchronisation terminée!")


if __name__ == "__main__":
    main()
