#!/usr/bin/env python3
"""
Script pour enrichir la base MongoDB avec les user_id depuis le fichier utilisateurs.
Lance manuellement: python3 enrich_mongodb_user_id.py
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
COLLECTION_NAME = "users"
USERS_CSV_FILE = "output/utilisateurs_20251219_073025.csv"

def load_users_from_csv(csv_file):
    """Charge les utilisateurs depuis le fichier CSV et retourne deux dicts"""
    users_by_number = {}  # matricule -> user_id
    users_by_name = {}    # pseudo -> user_id
    
    if not Path(csv_file).exists():
        print(f"❌ Erreur: Le fichier {csv_file} n'existe pas")
        return users_by_number, users_by_name
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_id = row.get('user_id', '').strip()
                if not user_id:
                    continue
                
                # Par matricule (number)
                number = row.get('number', '').strip()
                if number:
                    users_by_number[number] = int(user_id)
                
                # Par nom (name)
                name = row.get('name', '').strip()
                if name:
                    users_by_name[name] = int(user_id)
        
        total = len(users_by_number) + len(users_by_name)
        print(f"✅ {len(users_by_number)} matricules et {len(users_by_name)} noms chargés depuis le CSV")
        return users_by_number, users_by_name
    
    except Exception as e:
        print(f"❌ Erreur lors de la lecture du CSV: {e}")
        return users_by_number, users_by_name


def connect_to_mongodb():
    """Se connecte à MongoDB et retourne la collection"""
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Tester la connexion
        client.admin.command('ismaster')
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        print(f"✅ Connecté à MongoDB: {DB_NAME}.{COLLECTION_NAME}")
        return collection
    
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        print(f"❌ Erreur de connexion MongoDB: {e}")
        print(f"   Vérifiez que MongoDB est en cours d'exécution sur {MONGODB_URI}")
        return None


def enrich_users_with_id(collection, users_by_number, users_by_name):
    """Enrichit les utilisateurs MongoDB avec les user_id ZK"""
    if collection is None:
        return 0, 0, 0, []
    
    updated_count = 0
    not_found_count = 0
    error_count = 0
    not_found_users = []
    
    try:
        total_count = collection.count_documents({})
        print(f"\n📊 Traitement de {total_count} utilisateurs dans MongoDB...")
        
        users = collection.find()
        for user in users:
            try:
                matricule = user.get('matricule', '').strip()
                pseudo = user.get('pseudo', '').strip()
                
                user_id = None
                matched_by = None
                
                # Chercher d'abord par matricule
                if matricule in users_by_number:
                    user_id = users_by_number[matricule]
                    matched_by = "matricule"
                # Puis par pseudo (nom)
                elif pseudo in users_by_name:
                    user_id = users_by_name[pseudo]
                    matched_by = "pseudo"
                
                if user_id is not None:
                    # Vérifier si le user_id est déjà un int ZK (pas un ObjectId)
                    current_user_id = user.get('user_id')
                    if isinstance(current_user_id, int):
                        print(f"   ℹ️  {pseudo}: user_id déjà numérique ({current_user_id})")
                    else:
                        # Remplacer le user_id par l'ID numérique
                        collection.update_one(
                            {'_id': user['_id']},
                            {'$set': {'user_id': user_id}}
                        )
                        updated_count += 1
                        print(f"   ✅ {pseudo}: user_id mis à jour à {user_id} (trouvé par {matched_by})")
                else:
                    not_found_count += 1
                    not_found_users.append(pseudo if pseudo else matricule)
                    print(f"   ❌ {pseudo if pseudo else matricule}: non trouvé dans le CSV")
            
            except Exception as e:
                error_count += 1
                print(f"   ⚠️  Erreur lors de la mise à jour de {user.get('pseudo', 'inconnu')}: {e}")
        
        return updated_count, not_found_count, error_count, not_found_users
    
    except Exception as e:
        print(f"❌ Erreur lors du traitement: {e}")
        return 0, 0, 0, []


def generate_report(updated_count, not_found_count, error_count, not_found_users):
    """Génère un rapport d'exécution"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "statistics": {
            "updated": updated_count,
            "not_found": not_found_count,
            "errors": error_count
        },
        "not_found_users": not_found_users
    }
    
    report_file = f"output/enrich_mongodb_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n📄 Rapport généré: {report_file}")
    except Exception as e:
        print(f"⚠️  Impossible de générer le rapport: {e}")
    
    return report


def main():
    print("=" * 70)
    print("ENRICHISSEMENT MONGODB - AJOUT USER_ID ZK")
    print("=" * 70)
    print()
    
    # Charger les utilisateurs depuis le CSV
    users_by_number, users_by_name = load_users_from_csv(USERS_CSV_FILE)
    if not users_by_number and not users_by_name:
        print("❌ Aucun utilisateur à charger, arrêt du script")
        return
    
    # Se connecter à MongoDB
    collection = connect_to_mongodb()
    if collection is None:
        return
    
    # Enrichir les utilisateurs
    print()
    updated, not_found, errors, not_found_users = enrich_users_with_id(collection, users_by_number, users_by_name)
    
    # Afficher les résultats
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"✅ Utilisateurs mis à jour: {updated}")
    print(f"⚠️  Utilisateurs non trouvés: {not_found}")
    print(f"❌ Erreurs: {errors}")
    
    if not_found_users and not_found <= 10:
        print(f"\n📋 Utilisateurs non trouvés:")
        for user in not_found_users:
            print(f"   - {user}")
    
    # Générer le rapport
    report = generate_report(updated, not_found, errors, not_found_users)
    
    print("\n✨ Enrichissement terminé!")


if __name__ == "__main__":
    main()
