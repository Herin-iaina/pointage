#!/usr/bin/env python3
"""
Script maître pour l'extraction complète des données ZK Attendance.
Travaille directement avec MongoDB (pas de Google Sheets).
"""

import sys
import argparse
import csv
from datetime import datetime
from pathlib import Path
from .zk_client import ZKClient
from .processor import (
    load_corrections,
    apply_corrections_to_users,
    find_duplicate_name_users,
    save_duplicates_to_csv,
    prepare_clean_attendance,
    list_users_without_number,
    save_users_without_number_to_csv,
    save_final_attendance,
    print_statistics,
    cleanup_intermediate_files
)

# Configuration
MACHINE_IPS = ['172.17.17.26', '172.17.17.27', '172.17.17.28']

def main():
    parser = argparse.ArgumentParser(description="Extraction complète ZK Attendance → MongoDB")
    parser.add_argument('--keep-all', action='store_true', 
                        help="Garder tous les fichiers CSV intermédiaires")
    args = parser.parse_args()
    
    print("="*70)
    print("EXTRACTION COMPLÈTE ZK ATTENDANCE → MONGODB")
    print("="*70)
    
    # ÉTAPE 1 : Chargement corrections
    print("\n[1/6] Chargement des corrections...")
    corrections = load_corrections()
    print(f"  ✓ {len(corrections)} corrections chargées")
    
    # ÉTAPE 2 : Récupération utilisateurs
    print("\n[2/6] Récupération des utilisateurs...")
    try:
        client = ZKClient(MACHINE_IPS)
        all_users = client.collect_all_users()
    except Exception as e:
        print(f"  ✗ Erreur lors de l'initialisation du client ZK: {e}")
        sys.exit(1)
        
    print(f"  ✓ {len(all_users)} utilisateurs récupérés")
    
    # ÉTAPE 3 : Application corrections
    print("\n[3/5] Application des corrections...")
    count_applied = apply_corrections_to_users(all_users, corrections)
    print(f"  ✓ {count_applied} corrections appliquées")
    
    # ÉTAPE 4 : Récupération attendance
    print("\n[4/5] Récupération des enregistrements d'attendance...")
    all_attendance = client.collect_all_attendance()
    print(f"  ✓ {len(all_attendance)} enregistrements récupérés")
    
    # ÉTAPE 5 : Détection doublons
    print("\n[5/5] Détection des doublons...")
    duplicates = find_duplicate_name_users(all_users)
    dup_file = None
    if duplicates:
        dup_file = save_duplicates_to_csv(duplicates)
        print(f"  ✓ {len(duplicates)} groupes de doublons détectés")
        print(f"    → Fichier : {dup_file}")
    else:
        print(f"  ✓ Aucun doublon détecté")
    
    # ÉTAPE 6 : Génération fichier final
    print("\n[6/5] Génération du fichier final...")
    users_dict = {str(u.get('user_id')): {
        'name': u.get('name', ''),
        'number': u.get('number', ''),
    } for u in all_users}
    
    clean_records = prepare_clean_attendance(users_dict, all_attendance)
    
    final_file = save_final_attendance(clean_records)
    print(f"  ✓ Fichier généré : {final_file}")
    print("\n  Statistiques :")
    print_statistics(clean_records)
    
    # ÉTAPE 7 : Sauvegarde utilisateurs finaux (avec corrections appliquées)
    print("\n[7/5] Sauvegarde des utilisateurs finaux...")
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    users_final_file = Path('output') / f'utilisateurs_{now}.csv'
    fieldnames = ['device_ip', 'user_id', 'name', 'title', 'number', 'privilege', 'group_id', 'card_number']
    
    Path('output').mkdir(parents=True, exist_ok=True)
    with open(users_final_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for u in all_users:
            row = {k: u.get(k, '') for k in fieldnames}
            writer.writerow(row)
    print(f"  ✓ Fichier généré : {users_final_file}")

    # Liste des utilisateurs sans numéro
    users_without = list_users_without_number(all_users)
    if users_without:
        without_csv = save_users_without_number_to_csv(all_users)
        print(f"  ✓ {len(users_without)} utilisateurs sans numéro détectés")
        print(f"    → CSV : {without_csv}")
    else:
        print(f"  ✓ Aucun utilisateur sans numéro")
    
    # ÉTAPE 8 : Nettoyage fichiers intermédiaires
    print("\n[8/5] Nettoyage des fichiers intermédiaires...")
    keep_files = {Path(final_file).name, users_final_file.name}
    if dup_file:
        keep_files.add(Path(dup_file).name)
    
    if not args.keep_all:
        if clean_records:
            removed = cleanup_intermediate_files(keep_files)
            print(f"  ✓ {removed} fichiers CSV intermédiaires supprimés")
            print(f"  ✓ Fichiers conservés : {len(keep_files)}")
            for f in sorted(keep_files):
                print(f"    - {f}")
        else:
            print(f"  ⚠ Aucun enregistrement trouvé, conservation des anciens fichiers CSV.")
    else:
        print(f"  ℹ Tous les fichiers conservés (--keep-all utilisé)")
    
    print("\n" + "="*70)
    print(f"✓ EXTRACTION TERMINÉE")
    print("="*70)
    print(f"\nFichiers finaux :")
    for f in sorted(keep_files):
        print(f"  - {f}")
    print(f"\n📋 Prochaines étapes:")
    print(f"   1. python3 sync_mongodb_attendance.py --fill-empty")
    print(f"   2. Vérifier les doublons dans {dup_file if dup_file else 'aucun'}")
    print(f"   3. Requêtes MongoDB pour valider les données")

if __name__ == '__main__':
    main()
