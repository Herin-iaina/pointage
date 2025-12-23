#!/usr/bin/env python3
"""
Script simplifié : Extraction ZK → Insertion MongoDB
Deux étapes uniquement :
  1. Extraction des données depuis les pointeuses ZK
  2. Insertion/mise à jour dans MongoDB (collections users et zkteco)

Collections MongoDB :
  - users: Utilisateurs enrichis (métadonnées)
  - zkteco: Raw extraction ZK (name, user_id, timestamp, punch_type)
           Détection des doublons basée sur timestamp
"""

import sys
import os
import argparse
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from .zk_client import ZKClient
from .mongodb_client import MongoDBClient
from .processor import (
    load_corrections,
    apply_corrections_to_users,
    find_duplicate_name_users,
    save_duplicates_to_csv,
)
from .utils import parse_punch_type, PUNCH_TYPES

# Charger les variables d'environnement depuis .env
load_dotenv()

# Configuration depuis les variables d'environnement
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://172.17.17.72:27017/pointage')
ZK_IPS_STR = os.getenv('ZK_MACHINE_IPS', '172.17.17.26,172.17.17.27,172.17.17.28')
MACHINE_IPS = [ip.strip() for ip in ZK_IPS_STR.split(',')]


def format_attendance_for_zkteco(all_attendance, all_users):
    """
    Formate les enregistrements d'attendance pour insertion dans zkteco.
    
    Format : {name, user_id, timestamp, punch_type}
    """
    # Créer un dict user_id → name
    users_by_id = {str(u.get('user_id')): u.get('name', '') for u in all_users}
    
    zkteco_records = []
    for record in all_attendance:
        user_id = record.get('user_id')
        timestamp = record.get('timestamp')
        raw = record.get('raw', '')
        
        if not user_id or not timestamp:
            continue
        
        # Parse punch type
        punch_type_tuple = parse_punch_type(raw)
        punch_type = PUNCH_TYPES.get(punch_type_tuple, 'Inconnu')
        
        zkteco_records.append({
            'name': users_by_id.get(str(user_id), ''),
            'user_id': int(user_id) if user_id else None,
            'timestamp': timestamp,
            'punch_type': punch_type
        })
    
    return zkteco_records


def main():
    parser = argparse.ArgumentParser(
        description="Extraction ZK → Insertion MongoDB (users + zkteco)"
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help="Afficher les données sans les insérer dans MongoDB"
    )
    args = parser.parse_args()
    
    print("=" * 70)
    print("🕐 EXTRACTION ZK → MONGODB (zkteco)")
    print("DEBUG: ommit_ping=True enabled")
    print("=" * 70)
    
    # ÉTAPE 1 : Extraction ZK
    print("\n[1/2] 📥 Extraction des données ZK...")
    try:
        # Corrections locales
        corrections = load_corrections()
        print(f"  ✓ {len(corrections)} corrections chargées")
        
        # Client ZK
        zk_client = ZKClient(MACHINE_IPS)
        
        # Récupération utilisateurs
        print("  📍 Récupération des utilisateurs...")
        all_users = zk_client.collect_all_users()
        print(f"    ✓ {len(all_users)} utilisateurs")
        
        # Application corrections
        count_corrected = apply_corrections_to_users(all_users, corrections)
        print(f"    ✓ {count_corrected} corrections appliquées")
        
        # Détection doublons
        duplicates = find_duplicate_name_users(all_users)
        if duplicates:
            dup_file = save_duplicates_to_csv(duplicates)
            print(f"    ⚠️  {len(duplicates)} doublons détectés → {dup_file}")
        
        # Récupération attendance
        print("  📍 Récupération des enregistrements d'attendance...")
        all_attendance = zk_client.collect_all_attendance()
        print(f"    ✓ {len(all_attendance)} enregistrements")
        
        # Format pour zkteco
        zkteco_records = format_attendance_for_zkteco(all_attendance, all_users)
        print(f"    ✓ {len(zkteco_records)} enregistrements formatés pour zkteco")
        
    except Exception as e:
        print(f"\n  ✗ Erreur lors de l'extraction ZK: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # ÉTAPE 2 : Insertion MongoDB
    print("\n[2/2] 💾 Insertion dans MongoDB...")
    if args.dry_run:
        print("  ℹ️  Mode DRY-RUN (pas d'insertion)")
        print(f"\n  📊 Données prêtes pour insertion :")
        print(f"    - Utilisateurs : {len(all_users)}")
        print(f"    - Enregistrements zkteco : {len(zkteco_records)}")
        return
    
    try:
        mongo_client = MongoDBClient(MONGODB_URI)
        
        # Connexion
        if not mongo_client.connect():
            print("  ✗ Impossible de connecter à MongoDB")
            sys.exit(1)
        
        # Lecture du dernier timestamp
        print("  📍 Lecture du dernier timestamp dans zkteco...")
        last_timestamp = mongo_client.get_last_timestamp_zkteco()
        if last_timestamp:
            print(f"    ℹ️  Dernier timestamp : {last_timestamp}")
            print(f"    ℹ️  Insertion seulement des enregistrements plus récents")
        else:
            print(f"    ℹ️  Première insertion (collection vide)")
        
        # Insertion utilisateurs (toujours)
        print("  📍 Insertion/mise à jour des utilisateurs...")
        users_coll = mongo_client.db['users']
        users_updated = 0
        users_inserted = 0
        
        for user in all_users:
            try:
                result = users_coll.replace_one(
                    {'user_id': int(user.get('user_id'))},
                    user,
                    upsert=True
                )
                if result.upserted_id:
                    users_inserted += 1
                else:
                    users_updated += 1
            except Exception as e:
                print(f"    ⚠️  Erreur insertion user {user.get('user_id')}: {e}")
        
        print(f"    ✓ {users_inserted} inséré, {users_updated} mis à jour")
        
        # Insertion zkteco (avec filtre timestamp)
        print("  📍 Insertion des enregistrements zkteco...")
        zkteco_result = mongo_client.insert_zkteco_records(zkteco_records)
        print(f"    ✓ {zkteco_result.get('inserted')} inséré, "
              f"{zkteco_result.get('skipped')} ignoré (ancien), "
              f"{zkteco_result.get('errors')} erreur(s)")
        
        # Statistiques finales
        stats = mongo_client.get_statistics()
        print(f"\n  📈 Statistiques MongoDB :")
        print(f"    - Total utilisateurs : {stats.get('total_users', 0)}")
        print(f"    - Utilisateurs avec numéro : {stats.get('users_with_number', 0)}")
        print(f"    - Total enregistrements zkteco : {stats.get('total_zkteco_records', 0)}")
        
        mongo_client.disconnect()
        
    except Exception as e:
        print(f"\n  ✗ Erreur lors de l'insertion MongoDB: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("✅ EXTRACTION ET INSERTION TERMINÉES")
    print("=" * 70)


if __name__ == '__main__':
    main()
