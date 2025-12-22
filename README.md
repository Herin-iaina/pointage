# 🕐 ZK Attendance - Pipeline Simplifié

Extraction et enrichissement des données de pointage ZKTeco avec MongoDB et Docker.

## 📋 Vue d'ensemble

```
ZK Machines
    ↓
Extraction (utilisateurs + attendance)
    ↓
Corrections locales
    ↓
MongoDB
    ↓
DONE ✅
```

## 📁 Structure du projet

```
├── src/
│   ├── __init__.py
│   ├── main.py                 # Script principal : extraction → MongoDB
│   ├── zk_client.py            # Client ZK
│   ├── mongodb_client.py       # Client MongoDB
│   ├── processor.py            # Traitement des données
│   ├── utils.py                # Utilitaires
│   └── ancien/                 # Scripts anciens (archivés)
│       └── ...
├── config/
│   └── user_corrections.json   # Corrections manuelles
├── output/                      # Fichiers générés
├── Dockerfile                   # Image Docker
├── docker-compose.yml          # Orchestration Docker
├── requirements.txt            # Dépendances Python
└── README.md                   # Cette documentation
```

## 🚀 Installation rapide

### Prérequis
- **Docker** & **Docker Compose**
- Ou en local : Python 3.11+, MongoDB 7.0

### Option 1 : Avec Docker (recommandé)

```bash
# Démarrer les services
docker-compose up -d

# Attendre que MongoDB soit prêt (~ 10 secondes)
sleep 15

# Exécuter le pipeline
docker-compose run extraction

# Vérifier les résultats
docker-compose logs extraction

# Arrêter les services
docker-compose down
```

### Option 2 : En local

```bash
# Installation des dépendances
pip install -r requirements.txt

# Assurer que MongoDB tourne sur 172.17.17.72:27017
# (ou modifier MONGODB_URI dans src/main.py)

# Exécuter le script
python3 -m src.main

# Mode test (pas d'insertion dans MongoDB)
python3 -m src.main --dry-run
```

## 📊 Usage

### Exécution complète

```bash
docker-compose up extraction
```

Le script exécute automatiquement :
1. ✅ Extraction des utilisateurs et attendance depuis ZK
2. ✅ Application des corrections locales
3. ✅ Détection des doublons
4. ✅ Insertion dans MongoDB

### Mode test (dry-run)

```bash
docker-compose run extraction python3 -m src.main --dry-run
```

Affiche les données sans les insérer.

### Accéder à MongoDB

```bash
# Ouvrir MongoDB Shell
docker-compose exec mongodb mongosh -u admin -p password --authenticationDatabase admin

# Ou depuis l'extérieur
mongosh mongodb://admin:password@localhost:27017/pointage?authSource=admin
```

**Commandes MongoDB utiles :**

```javascript
// Voir les collections
show collections

// Compter les utilisateurs
db.users.countDocuments()

// Voir les premiers utilisateurs
db.users.find().limit(5).pretty()

// Voir les enregistrements d'attendance
db.attendance.countDocuments()
```

## 🔧 Configuration

### Corrections manuelles

Éditez `config/user_corrections.json` :

```json
{
  "corrections": {
    "36": {
      "number": "0499/SMART",
      "title": "Manager"
    }
  }
}
```

Appliquez à la prochaine exécution.

### IPs des pointeuses ZK

Dans `src/main.py` :

```python
MACHINE_IPS = ['172.17.17.26', '172.17.17.27', '172.17.17.28']
```

### Connexion MongoDB

**En Docker :** Utilise `mongodb://admin:password@mongodb:27017/pointage`

**En local :** Modifiez dans `src/main.py` :

```python
MONGODB_URI = 'mongodb://localhost:27017'
```

## 📊 Données dans MongoDB

### Collection `users`

```json
{
  "_id": ObjectId("..."),
  "device_ip": "172.17.17.26",
  "user_id": 1,
  "name": "John Doe",
  "number": "0001/RES",
  "title": "Employee",
  "privilege": 0,
  "group_id": 0,
  "card_number": "12345678"
}
```

### Collection `attendance`

```json
{
  "_id": ObjectId("..."),
  "user_id": 1,
  "nom": "John Doe",
  "numero": "0001/RES",
  "date_heure": "2025-12-22 09:30:00",
  "type": "Check In"
}
```

## 🐛 Troubleshooting

### MongoDB ne démarre pas

```bash
# Vérifier les logs
docker-compose logs mongodb

# Redémarrer
docker-compose down
docker-compose up -d mongodb
sleep 15
```

### Erreur de connexion ZK

```bash
# Vérifier que les IPs sont correctes
ping 172.17.17.26
ping 172.17.17.27
ping 172.17.17.28

# Vérifier les firewall rules
```

### Aucune donnée extraite

```bash
# Vérifier les corrections JSON
cat config/user_corrections.json

# Exécuter en mode dry-run
python3 -m src.main --dry-run
```

### Doublons détectés

Un fichier `utilisateurs_doublons_*.csv` est généré dans `output/`.

Résoudre manuellement ou via corrections JSON.

## 📈 Fichiers générés

- `utilisateurs_doublons_*.csv` - Doublons détectés
- Données finales dans MongoDB (`users`, `attendance`)

## 🔐 Sécurité

- **En production :** Changez les credentials MongoDB
- **En production :** Utilisez un réseau Docker sécurisé
- **En production :** Montez des volumes pour la persistence

## 📞 Support

Pour les problèmes :

1. Vérifier les logs
2. Consulter les rapports d'erreurs
3. Vérifier les connections réseau

---

**Version:** 3.0 (Simplifié + Docker)  
**Dernière mise à jour:** Décembre 2025
