#!/usr/bin/env python3
"""
Orchestrateur - Lance tout le pipeline dans le bon ordre.

Utilisation:
  python3 run_all_pipeline.py              # Complet (--fill-empty par défaut)
  python3 run_all_pipeline.py --full       # Mise à jour complète MongoDB
  python3 run_all_pipeline.py --no-merge   # Sans fusion finale
"""

import sys
import argparse
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Exécute une commande et affiche le résultat"""
    print(f"\n{'='*70}")
    print(f"▶️  {description}")
    print(f"{'='*70}")
    
    try:
        result = subprocess.run(cmd, shell=True, cwd=Path(__file__).parent)
        if result.returncode != 0:
            print(f"❌ Erreur lors de: {description}")
            return False
        return True
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Pipeline complet: ZK → MongoDB → Fichiers finals")
    parser.add_argument('--full', action='store_true',
                        help="Mise à jour complète MongoDB (--full-update)")
    parser.add_argument('--no-merge', action='store_true',
                        help="Ne pas fusionner les fichiers finals")
    parser.add_argument('--skip-extract', action='store_true',
                        help="Sauter l'extraction ZK (utiliser les fichiers existants)")
    args = parser.parse_args()
    
    print("╔" + "="*68 + "╗")
    print("║" + " "*68 + "║")
    print("║" + "  🚀 PIPELINE COMPLET: ZK → MONGODB → FICHIERS FINALS".center(68) + "║")
    print("║" + " "*68 + "║")
    print("╚" + "="*68 + "╝")
    
    steps = []
    
    # Étape 1: Extraction ZK
    if not args.skip_extract:
        steps.append(("python3 -m src.main", "1️⃣  Extraction ZK (utilisateurs + attendance)"))
    
    # Étape 2: Enrichissement MongoDB
    enrich_mode = "--full-update" if args.full else "--fill-empty"
    steps.append((f"python3 enrich_mongodb_user_id.py {enrich_mode}", 
                  "2️⃣  Enrichissement MongoDB (user_id)"))
    
    # Étape 3: Synchronisation MongoDB
    steps.append(("python3 sync_mongodb_attendance.py",
                  "3️⃣  Synchronisation ZK → MongoDB"))
    
    # Étape 4: Export MongoDB
    steps.append(("python3 export_mongodb.py",
                  "4️⃣  Export MongoDB → CSV"))
    
    # Étape 4b: Compléter les numéros depuis MongoDB
    steps.append(("python3 complete_numbers_from_mongodb.py",
                  "4b️⃣  Complétion des numéros depuis MongoDB"))
    
    # Étape 5: Fusion (optionnel)
    if not args.no_merge:
        steps.append(("python3 merge_mongodb_with_zk.py",
                      "5️⃣  Fusion ZK + MongoDB → Fichiers finals"))
    
    # Exécuter les étapes
    print(f"\n📋 Plan d'exécution ({len(steps)} étapes):\n")
    for i, (cmd, desc) in enumerate(steps, 1):
        print(f"   {i}. {desc}")
    
    print("\n" + "="*70)
    success_count = 0
    
    for cmd, desc in steps:
        if run_command(cmd, desc):
            success_count += 1
        else:
            print(f"\n⚠️  Pipeline interrompu à l'étape: {desc}")
            sys.exit(1)
    
    # Résumé final
    print(f"\n{'='*70}")
    print("✨ PIPELINE COMPLÉTÉ AVEC SUCCÈS ✨")
    print(f"{'='*70}")
    print(f"\n✅ {success_count}/{len(steps)} étapes exécutées\n")
    
    print("📁 Fichiers générés dans 'output/':")
    output_dir = Path("output")
    
    # Afficher les fichiers récents
    if output_dir.exists():
        csv_files = sorted(output_dir.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)[:10]
        for f in csv_files:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"   • {f.name:50} ({size_mb:.2f} MB)")
    
    print("\n🎯 Fichiers essentiels:")
    print("   • utilisateurs_merged_*.csv     ← Utilisateurs avec numéros")
    print("   • pointage_merged_*.csv         ← Pointage avec numéros")
    print("   • utilisateurs_doublons_*.csv   ← À valider manuellement")
    
    print("\n" + "="*70)
    print("✅ Prêt pour la prochaine étape!")
    print("="*70)


if __name__ == "__main__":
    main()
