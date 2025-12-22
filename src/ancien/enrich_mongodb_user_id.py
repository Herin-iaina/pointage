#!/usr/bin/env python3
"""
Script pour enrichir la base MongoDB avec les user_id depuis le fichier utilisateurs.
Lance manuellement: python3 enrich_mongodb_user_id.py

Modes d'exécution:
  --full-update    : Remplace tous les user_id existants (même s'ils existent)
  --fill-empty     : Ajoute user_id seulement aux documents sans user_id (défaut)
"""

import csv
import json
import argparse
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

# Configuration
MONGODB_URI = "mongodb://172.17.17.72:27017"
DB_NAME = "pointage"
COLLECTION_NAME = "users"
USERS_CSV_FILE = None  # Auto-détection du dernier fichier


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

def load_users_from_csv(csv_file):
    """Charge les utilisateurs depuis le fichier CSV et retourne deux dicts"""
    # Auto-détection si pas de fichier spécifié
    if csv_file is None:
        csv_file = find_latest_users_csv()
    
    users_by_number = {}  # matricule -> user_id
    users_by_name = {}    # pseudo -> user_id
    
    if not csv_file or not Path(csv_file).exists():
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


def enrich_users_with_id(collection, users_by_number, users_by_name, mode='fill-empty'):
    """
    Enrichit les utilisateurs MongoDB avec les user_id ZK
    
    Args:
        collection: Collection MongoDB
        users_by_number: Dict matricule -> user_id
        users_by_name: Dict pseudo -> user_id
        mode: 'fill-empty' (défaut) ou 'full-update'
              - fill-empty: Ajoute user_id seulement aux docs sans user_id
              - full-update: Remplace tous les user_id existants
    """
    if collection is None:
        return 0, 0, 0, []
    
    updated_count = 0
    skipped_count = 0
    not_found_count = 0
    error_count = 0
    not_found_users = []
    
    try:
        total_count = collection.count_documents({})
        mode_label = "MISE À JOUR COMPLÈTE" if mode == 'full-update' else "REMPLISSAGE VIDE"
        print(f"\n📊 Traitement de {total_count} utilisateurs en mode [{mode_label}]...")
        
        users = collection.find()
        for user in users:
            try:
                matricule = user.get('matricule', '').strip()
                pseudo = user.get('pseudo', '').strip()
                current_user_id = user.get('user_id')
                
                # En mode 'fill-empty', ignorer si user_id existe déjà
                if mode == 'fill-empty' and current_user_id is not None:
                    skipped_count += 1
                    continue
                
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
                    # Mettre à jour
                    collection.update_one(
                        {'_id': user['_id']},
                        {'$set': {'user_id': user_id}}
                    )
                    updated_count += 1
                    action = "✅ Mis à jour" if current_user_id else "✅ Ajouté"
                    print(f"   {action}: {pseudo} → user_id {user_id} (trouvé par {matched_by})")
                else:
                    not_found_count += 1
                    not_found_users.append(pseudo if pseudo else matricule)
                    print(f"   ❌ {pseudo if pseudo else matricule}: non trouvé dans le CSV")
            
            except Exception as e:
                error_count += 1
                print(f"   ⚠️  Erreur lors de la mise à jour de {user.get('pseudo', 'inconnu')}: {e}")
        
        return updated_count, skipped_count, not_found_count, error_count, not_found_users
    
    except Exception as e:
        print(f"❌ Erreur lors du traitement: {e}")
        return 0, 0, 0, 0, []


def generate_report(updated_count, skipped_count, not_found_count, error_count, not_found_users, mode):
    """Génère un rapport d'exécution"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "statistics": {
            "updated": updated_count,
            "skipped": skipped_count,
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
    parser = argparse.ArgumentParser(description="Enrichissement MongoDB avec user_id ZK")
    parser.add_argument('--full-update', action='store_true',
                        help="Remplacer TOUS les user_id (même s'ils existent)")
    parser.add_argument('--fill-empty', action='store_true',
                        help="Ajouter user_id seulement aux docs vides (défaut)")
    args = parser.parse_args()
    
    # Déterminer le mode
    mode = 'full-update' if args.full_update else 'fill-empty'
    
    print("=" * 70)
    print("ENRICHISSEMENT MONGODB - AJOUT USER_ID ZK")
    print(f"Mode: {mode.upper().replace('-', ' ')}")
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
    updated, skipped, not_found, errors, not_found_users = enrich_users_with_id(
        collection, users_by_number, users_by_name, mode=mode
    )
    
    # Afficher les résultats
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"✅ Utilisateurs mis à jour: {updated}")
    if skipped > 0:
        print(f"⏭️  Utilisateurs ignorés (déjà avec user_id): {skipped}")
    print(f"⚠️  Utilisateurs non trouvés: {not_found}")
    print(f"❌ Erreurs: {errors}")
    
    if not_found_users and not_found <= 10:
        print(f"\n📋 Utilisateurs non trouvés:")
        for user in not_found_users:
            print(f"   - {user}")
    
    # Générer le rapport
    report = generate_report(updated, skipped, not_found, errors, not_found_users, mode)
    
    print("\n✨ Enrichissement terminé!")


if __name__ == "__main__":
    main()
