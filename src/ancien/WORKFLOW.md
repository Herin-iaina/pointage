# 📋 WORKFLOW OPTIMISÉ - POINTAGE + MONGODB

## ✅ Ordre d'exécution recommandé

### **Phase 1: Extraction ZK (sans MongoDB)**
```bash
python3 -m src.main
```
**Génère:**
- ✅ `utilisateurs_YYYYMMDD_HHMMSS.csv` (utilisateurs ZK)
- ✅ `pointage_final_YYYYMMDD_HHMMSS.csv` (attendance ZK)
- ✅ `utilisateurs_doublons_YYYYMMDD_HHMMSS.csv` (doublons)

---

### **Phase 2: Enrichissement MongoDB**

#### Étape 2.1 - Ajouter user_id à MongoDB
```bash
python3 enrich_mongodb_user_id.py --fill-empty
```
- ✅ Ajoute `user_id` aux documents sans ID
- ✅ Récupère user_id depuis `utilisateurs_*.csv`
- 📊 Génère rapport: `enrich_mongodb_report_*.json`

#### Étape 2.2 - Synchroniser l'attendance à MongoDB
```bash
python3 sync_mongodb_attendance.py
```
- ✅ Récupère utilisateurs depuis `utilisateurs_*.csv`
- ✅ Gère les doublons (prend l'ID le plus élevé)
- ✅ Insère/Met à jour dans MongoDB
- ✅ Ajoute les numéros manquants
- 📊 Génère rapport: `sync_mongodb_report_*.json`

#### Étape 2.3 - Exporter les utilisateurs enrichis
```bash
python3 export_mongodb.py
```
- ✅ Récupère tous les utilisateurs de MongoDB
- ✅ Inclut les numéros et toutes les données enrichies
- ✅ Génère: `utilisateurs_mongodb_*.csv`

---

### **Phase 3: Génération des fichiers finaux**

#### Option A - Faire manuellement (flexible)
```bash
# 1. Charger les utilisateurs MongoDB enrichis
# 2. Générer pointage_final avec les numéros

# Utiliser utilisateurs_mongodb_*.csv et pointage_final_*.csv existant
```

#### Option B - Générer les fichiers finals (recommandé)
```bash
python3 -c "
import csv
from pathlib import Path

# Charger utilisateurs de MongoDB
users_mongo = {}
with open('output/utilisateurs_mongodb_*.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        users_mongo[str(row['user_id'])] = row

# Enrichir le pointage
# À faire
"
```

---

## 📊 Comparaison: Avant vs Après

### ❌ Ancien workflow (Google Sheets):
```
ZK Extract
  ↓ (8 étapes)
Utilisateurs CSV (sans numéros)
Pointage CSV (sans numéros)
```

### ✅ Nouveau workflow (MongoDB):
```
ZK Extract (Phase 1)
  ↓
Utilisateurs CSV (ZK)
Pointage CSV (ZK)
  ↓
MongoDB Enrich (Phase 2)
  ↓ (3 sous-étapes)
Utilisateurs Enrichis (avec numéros)
Attendance MongoDB
  ↓
Export MongoDB
  ↓
Utilisateurs Final (avec numéros)
Pointage Final (avec numéros)
```

---

## 🔄 Utilisation recommandée

### **Première exécution:**
```bash
# 1. Extraction
python3 -m src.main

# 2. Enrichissement MongoDB (complet)
python3 enrich_mongodb_user_id.py --full-update
python3 sync_mongodb_attendance.py
python3 export_mongodb.py

# 3. Vérification des doublons
cat output/utilisateurs_doublons_*.csv
```

### **Exécutions suivantes:**
```bash
# 1. Extraction
python3 -m src.main

# 2. Enrichissement MongoDB (seulement les vides)
python3 enrich_mongodb_user_id.py --fill-empty
python3 sync_mongodb_attendance.py
python3 export_mongodb.py
```

---

## 📁 Fichiers générés

| Fichier | Source | Contient |
|---------|--------|----------|
| `utilisateurs_*.csv` | ZK | user_id, name, number, device_ip |
| `pointage_final_*.csv` | ZK | nom, numero, date_heure, type |
| `utilisateurs_mongodb_*.csv` | MongoDB | user_id, number, pseudo, email, pole, bench |
| `utilisateurs_doublons_*.csv` | ZK | Doublons détectés |
| `utilisateurs_sans_numero_*.csv` | ZK | Utilisateurs sans numéro |

---

## ⚠️ Points importants

1. **Les numéros** viennent de MongoDB (après enrichissement)
2. **Les doublons** doivent être manuellement validés
3. **Le fichier final** doit être généré APRÈS l'export MongoDB
4. **Vérifier** que `utilisateurs_mongodb_*.csv` a des numéros avant de l'utiliser

---

## 🔧 Scripts disponibles

| Script | Rôle |
|--------|------|
| `python3 -m src.main` | Extraction complète ZK |
| `enrich_mongodb_user_id.py` | Ajoute user_id à MongoDB |
| `sync_mongodb_attendance.py` | Synchronise ZK → MongoDB |
| `export_mongodb.py` | Exporte MongoDB → CSV |

---

## 💡 Prochaines améliorations

- [ ] Automatiser la génération des fichiers finals
- [ ] Créer un script `merge_mongodb_with_zk.py`
- [ ] Ajouter validation des numéros
- [ ] Dashboard MongoDB avec statistiques

