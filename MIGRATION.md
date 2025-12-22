# 🎯 Guide de Migration - Avant → Après

## Résumé des changements

### ✅ Ce qui a changé

**src/ (nettoyé)**
- ❌ Suppression : enrich_mongodb_user_id.py
- ❌ Suppression : sync_mongodb_attendance.py
- ❌ Suppression : export_mongodb.py
- ❌ Suppression : complete_numbers_from_mongodb.py
- ❌ Suppression : merge_mongodb_with_zk.py
- ✅ Gardé : main.py (**SIMPLIFIÉ**)
- ✅ Gardé : zk_client.py
- ✅ Gardé : mongodb_client.py
- ✅ Gardé : processor.py
- ✅ Gardé : utils.py

**À la racine**
- ✅ Nouveau : Dockerfile
- ✅ Nouveau : docker-compose.yml
- ✅ Nouveau : run.sh
- ✅ Nouveau : PROJECT_STRUCTURE.md
- ❌ Supprimé : run_all_pipeline.py
- ❌ Supprimé : run_all.py

**src/ancien/** (archivage)
- 📦 Tous les anciens scripts sauvegardés
- 📦 Historique préservé
- 📦 Plus utilisés directement

---

## Ancien workflow

```
┌──────────────────────────────────────────────────────────────┐
│                    run_all_pipeline.py                        │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  1. main.py → utilisateurs_*.csv, pointage_final_*.csv       │
│  2. enrich_mongodb_user_id.py → user_id dans MongoDB         │
│  3. sync_mongodb_attendance.py → sync ZK → MongoDB           │
│  4. export_mongodb.py → utilisateurs_mongodb_*.csv           │
│  5. complete_numbers_from_mongodb.py → numeros completés     │
│  6. merge_mongodb_with_zk.py → fichiers finaux merged        │
│                                                                │
│  Problèmes : 6 étapes, 8+ scripts, complexe, lent            │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

## Nouveau workflow (simplifié)

```
┌──────────────────────────────────────────────────────────────┐
│                    src/main.py                                │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  1. Extraction ZK                                            │
│     → utilisateurs_*.csv                                      │
│     → pointage_final_*.csv                                    │
│     → utilisateurs_doublons_*.csv (si nécessaire)            │
│                                                                │
│  2. Insertion MongoDB                                        │
│     → collections users et attendance                         │
│                                                                │
│  DONE ✅                                                      │
│                                                                │
│  Avantages : simple, rapide, maintenable, Dockerisé          │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

---

## Commandes d'utilisation

### Avant

```bash
# Compliqué
python3 run_all_pipeline.py
python3 run_all_pipeline.py --full
python3 run_all_pipeline.py --no-merge
```

### Après

```bash
# Simple et clair
./run.sh start      # Démarrer MongoDB
./run.sh extract    # Lancer l'extraction
./run.sh mongo      # Vérifier MongoDB
./run.sh stop       # Arrêter les services
```

---

## Différences dans le code

### main.py - Avant

```python
def main():
    # ÉTAPE 1 : Corrections
    # ÉTAPE 2 : Extraction utilisateurs
    # ÉTAPE 3 : Corrections appliquées
    # ÉTAPE 4 : Extraction attendance
    # ÉTAPE 5 : Doublons
    # ÉTAPE 6 : Fichier final
    # ÉTAPE 7 : Utilisateurs finaux
    # ÉTAPE 8 : Utilisateurs sans numéro
    # ...
```

Complexité : 8 étapes, ~145 lignes

### main.py - Après

```python
def main():
    # [1/2] Extraction ZK
    # - load_corrections()
    # - collect_all_users()
    # - apply_corrections()
    # - collect_all_attendance()
    # - detect_duplicates()
    
    # [2/2] Insertion MongoDB
    # - insert_or_update_users()
    # - insert_or_update_attendance()
    # DONE
```

Simplicité : 2 étapes, ~100 lignes

---

## Migration checklist

- [x] ✅ Archivage des anciens scripts (src/ancien/)
- [x] ✅ Création du nouveau main.py simplifié
- [x] ✅ Création du Dockerfile
- [x] ✅ Création du docker-compose.yml
- [x] ✅ Création du run.sh
- [x] ✅ Documentation README.md mise à jour
- [x] ✅ Documentation PROJECT_STRUCTURE.md
- [x] ✅ Nettoyage à la racine

## Prochaines étapes

1. **Test local**
   ```bash
   ./run.sh start
   ./run.sh test
   ./run.sh stop
   ```

2. **Test en production**
   ```bash
   docker-compose up -d
   docker-compose run extraction
   docker-compose down
   ```

3. **Monitoring**
   ```bash
   ./run.sh logs
   ./run.sh mongo
   ```

---

## Rollback (si nécessaire)

Tous les anciens scripts sont dans `src/ancien/`:

```bash
# Pour utiliser un ancien script
python3 src/ancien/enrich_mongodb_user_id.py --full-update
python3 src/ancien/sync_mongodb_attendance.py
```

Mais vous ne devriez pas en avoir besoin! 🎉

---

**Dernière mise à jour:** Décembre 2025
