#!/usr/bin/env python3
"""
Script maître pour l'extraction complète des données ZK Attendance.
Refactorisé.
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
    enrich_users_from_google_sheet,
    check_users_not_in_attendance,
    save_users_not_in_attendance,
    write_user_ids_to_google_sheet,
    find_duplicate_name_users,
    save_duplicates_to_csv,
    prepare_clean_attendance,
    list_users_without_number,
    save_users_to_json,
    save_users_without_number_to_csv,
    save_final_attendance,
    print_statistics,
    cleanup_intermediate_files
)

# Configuration
MACHINE_IPS = ['172.17.17.26', '172.17.17.27', '172.17.17.28']

def main():
    parser = argparse.ArgumentParser(description="Extraction complète ZK Attendance")
    parser.add_argument('--keep-all', action='store_true', 
                        help="Garder tous les fichiers CSV intermédiaires")
    parser.add_argument('--sheet-id', type=str, 
                        help="ID ou Nom du Google Sheet pour enrichissement")
    parser.add_argument('--sheet-name', type=str, 
                        help="Nom de l'onglet (feuille) à utiliser")
    parser.add_argument('--credentials', type=str, default='credentials.json',
                        help="Chemin vers le fichier JSON de credentials (défaut: credentials.json)")
    args = parser.parse_args()
    
    print("="*70)
    print("EXTRACTION COMPLÈTE ZK ATTENDANCE (Refactored)")
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
    print("\n[3/6] Application des corrections...")
    count_applied = apply_corrections_to_users(all_users, corrections)
    print(f"  ✓ {count_applied} corrections appliquées")
    
    # ÉTAPE 3b : Enrichissement Google Sheets (numéros manquants)
    print("\n[3b/6] Enrichissement depuis Google Sheets...")
    if Path(args.credentials).exists():
        count_enriched = enrich_users_from_google_sheet(
            all_users, 
            credentials_file=args.credentials,
            sheet_id_or_url=args.sheet_id,
            sheet_name=args.sheet_name or 'ACTIF'
        )
        print(f"  ✓ {count_enriched} numéros complétés via Google Sheets")
        
        # ÉTAPE 3c : Écriture des user_id dans le Google Sheet (colonne 37)
        print("\n[3c/6] Écriture des user_id dans le Google Sheet...")
        count_written = write_user_ids_to_google_sheet(
            all_users,
            credentials_file=args.credentials,
            sheet_id_or_url=args.sheet_id,
            sheet_name=args.sheet_name or 'ENCODAGE',
            column_index=37
        )
        print(f"  ✓ {count_written} user_id écris dans le Google Sheet")
    else:
        print(f"  ⚠ Fichier credentials non trouvé, enrichissement Google Sheets ignoré")
    
    # ÉTAPE 4 : Récupération attendance
    print("\n[4/6] Récupération des enregistrements d'attendance...")
    all_attendance = client.collect_all_attendance()
    print(f"  ✓ {len(all_attendance)} enregistrements récupérés")
    
    # ÉTAPE 4b : Vérification des utilisateurs du Sheet sans pointage
    print("\n[4b/6] Vérification des utilisateurs sans pointage...")
    if Path(args.credentials).exists():
        users_without_att = check_users_not_in_attendance(
            all_attendance,
            credentials_file=args.credentials,
            sheet_id_or_url=args.sheet_id,
            sheet_name=args.sheet_name or 'ACTIF'
        )
        if users_without_att:
            csv_file, json_file = save_users_not_in_attendance(users_without_att)
            print(f"  ✓ {len(users_without_att)} utilisateurs du Sheet sans pointage")
            print(f"    → CSV : {csv_file}")
            print(f"    → JSON : {json_file}")
        else:
            print(f"  ✓ Tous les utilisateurs du Sheet ont des pointages")
    else:
        print(f"  ⚠ Vérification ignorée (credentials non trouvés)")
    
    # ÉTAPE 5 : Détection doublons
    print("\n[5/6] Détection des doublons...")
    duplicates = find_duplicate_name_users(all_users)
    dup_file = None
    if duplicates:
        dup_file = save_duplicates_to_csv(duplicates)
        print(f"  ✓ {len(duplicates)} groupes de doublons détectés")
        print(f"    → Fichier : {dup_file}")
    else:
        print(f"  ✓ Aucun doublon détecté")
    
    # ÉTAPE 6 : Génération fichier final
    print("\n[6/6] Génération du fichier final...")
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
    print("\n[7/7] Sauvegarde des utilisateurs finaux...")
    now = datetime.now().strftime('%Y%m%d_%H%M%S')
    users_final_file = Path('output') / f'utilisateurs_{now}.csv'
    fieldnames = ['device_ip', 'user_id', 'name', 'title', 'number', 'privilege', 'group_id', 'card_number']
    with open(users_final_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for u in all_users:
            row = {k: u.get(k, '') for k in fieldnames}
            writer.writerow(row)
    print(f"  ✓ Fichier généré : {users_final_file}")
    # Sauvegarde en JSON des utilisateurs
    users_json_file = save_users_to_json(all_users)
    print(f"  ✓ Fichier JSON généré : {users_json_file}")

    # Liste des utilisateurs sans numéro
    users_without = list_users_without_number(all_users)
    if users_without:
        without_csv = save_users_without_number_to_csv(all_users)
        without_json = save_users_to_json(users_without, filename=f"utilisateurs_sans_numero_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        print(f"  ✓ {len(users_without)} utilisateurs sans numéro détectés")
        print(f"    → CSV : {without_csv}")
        print(f"    → JSON : {without_json}")
    else:
        print(f"  ✓ Aucun utilisateur sans numéro")
    
    # ÉTAPE 8 : Nettoyage fichiers intermédiaires
    print("\n[8/8] Nettoyage des fichiers intermédiaires...")
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
    print(f"\nProchaine étape : enrichir avec Google Sheet pour compléter les numéros vides")

if __name__ == '__main__':
    main()
