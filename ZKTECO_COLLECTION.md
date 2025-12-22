# 📊 Collection ZKTECO - Documentation

## Vue d'ensemble

La collection `zkteco` stocke les **enregistrements bruts d'extraction ZK Teco**, avec détection automatique des doublons basée sur les timestamps.

```
ZK Machines → collect_all_attendance() → zkteco_records
                                              ↓
                                    mongodb_client.insert_zkteco_records()
                                              ↓
                                    Collection zkteco (MongoDB)
```

## Schéma du document

```json
{
  "_id": ObjectId("..."),
  "name": "John Doe",
  "user_id": 1,
  "timestamp": "2025-12-22 09:30:00",
  "punch_type": "Check In",
  "created_at": "2025-12-22T15:45:30.123456"
}
```

### Champs

| Champ | Type | Description |
|-------|------|-------------|
| `_id` | ObjectId | Identifiant MongoDB (auto-généré) |
| `name` | String | Nom de l'employé |
| `user_id` | Integer | ID ZK de l'employé |
| `timestamp` | String | Date/heure du pointage (ISO format) |
| `punch_type` | String | Type de pointage (Check In, Check Out, etc.) |
| `created_at` | String | Date d'insertion dans MongoDB (ISO format) |

## Indexes

Deux indexes sont créés automatiquement :

### 1. Index sur timestamp
```
{timestamp: 1}
```
Permet le tri et filtrage efficace par date.

### 2. Index unique composé (user_id + timestamp)
```
{user_id: 1, timestamp: 1} UNIQUE
```
Garantit qu'on ne peut pas avoir deux enregistrements identiques pour le même utilisateur à la même heure.

## Détection des doublons

### Mécanisme

Avant d'insérer, le système :

1. **Lit le dernier timestamp** dans la collection
   ```python
   last_timestamp = mongo_client.get_last_timestamp_zkteco()
   ```

2. **Filtre les enregistrements** : ignore tous les enregistrements avec `timestamp <= last_timestamp`
   ```python
   if timestamp <= last_timestamp:
       skip()  # Ignore l'ancien enregistrement
   ```

3. **Insère seulement les nouveaux** enregistrements (plus récents)

### Résultats de l'insertion

La méthode retourne un dictionnaire avec statistiques :

```python
{
    'inserted': 150,   # Nouveaux enregistrements ajoutés
    'skipped': 45,     # Anciens enregistrements ignorés
    'errors': 2        # Erreurs d'insertion
}
```

## Utilisation

### Lire le dernier timestamp

```python
mongo = MongoDBClient('mongodb://...')
mongo.connect()

last_ts = mongo.get_last_timestamp_zkteco()
if last_ts:
    print(f"Dernier timestamp : {last_ts}")
```

### Insérer des enregistrements

```python
records = [
    {
        'name': 'Alice',
        'user_id': 1,
        'timestamp': '2025-12-22 09:30:00',
        'punch_type': 'Check In'
    },
    ...
]

result = mongo.insert_zkteco_records(records)
print(f"Inséré : {result['inserted']}, Ignoré : {result['skipped']}")
```

### Requêtes MongoDB utiles

```javascript
// Compter les enregistrements
db.zkteco.countDocuments()

// Voir les derniers enregistrements
db.zkteco.find().sort({timestamp: -1}).limit(10)

// Enregistrements d'un utilisateur
db.zkteco.find({user_id: 1}).sort({timestamp: -1})

// Enregistrements entre deux dates
db.zkteco.find({
  timestamp: {
    $gte: "2025-12-01",
    $lte: "2025-12-31"
  }
})

// Statistiques par type de pointage
db.zkteco.aggregate([
  {$group: {_id: "$punch_type", count: {$sum: 1}}}
])

// Utilisateurs les plus actifs
db.zkteco.aggregate([
  {$group: {_id: "$user_id", count: {$sum: 1}}},
  {$sort: {count: -1}},
  {$limit: 10}
])
```

## Processus d'exécution dans main.py

```
[1/2] Extraction ZK
     ├─ Lecture utilisateurs (all_users)
     ├─ Lecture attendance (all_attendance)
     └─ Format zkteco (format_attendance_for_zkteco)
         └─ {name, user_id, timestamp, punch_type}

[2/2] Insertion MongoDB
     ├─ Connexion à MongoDB
     ├─ Lecture dernier timestamp
     ├─ Insertion utilisateurs (collection users)
     └─ Insertion zkteco (collection zkteco)
         ├─ Filtre : timestamp > last_timestamp
         ├─ Unique index : user_id + timestamp
         └─ Résultats : inserted, skipped, errors
```

## Performance

- **Filtrage par timestamp** : O(1) - lecture simple
- **Unique index check** : Effectué par MongoDB
- **Insertion batch** : Optimisée par PyMongo

Pour 1000 enregistrements :
- Temps typique : 0.5-1 sec (réseau)
- Pas de doublons garantis

## Exemple complet

```python
from src.mongodb_client import MongoDBClient
from src.zk_client import ZKClient

# Extraction
zk = ZKClient(['172.17.17.26', '172.17.17.27', '172.17.17.28'])
users = zk.collect_all_users()
attendance = zk.collect_all_attendance()

# Format zkteco
zkteco_records = [
    {
        'name': u['name'],
        'user_id': int(u['user_id']),
        'timestamp': str(a['timestamp']),
        'punch_type': parse_punch_type(a['raw'])
    }
    for u in users
    for a in attendance
    if a['user_id'] == u['user_id']
]

# Insertion
mongo = MongoDBClient('mongodb://172.17.17.72:27017')
mongo.connect()

# Lire dernier timestamp
last_ts = mongo.get_last_timestamp_zkteco()
print(f"Dernier : {last_ts}")

# Insérer (filtre automatique)
result = mongo.insert_zkteco_records(zkteco_records)
print(f"Inséré : {result['inserted']}, Ignoré : {result['skipped']}")

# Statistiques
stats = mongo.get_statistics()
print(f"Total zkteco : {stats['total_zkteco_records']}")

mongo.disconnect()
```

---

**Version:** 1.0  
**Dernière mise à jour:** Décembre 2025
