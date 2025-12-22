# 🚀 Quick Start

## 30 secondes pour démarrer

### Avec Docker (recommandé)

```bash
# 1. Démarrer les services
./run.sh start

# 2. Lancer l'extraction
./run.sh extract

# 3. Arrêter (optionnel)
./run.sh stop
```

### Sans Docker (local)

```bash
# Installation
pip install -r requirements.txt

# Exécution
python3 -m src.main
```

---

## Cheat Sheet

```bash
# Démarrage
./run.sh start          # Lance MongoDB + services

# Exécution
./run.sh extract        # Lance l'extraction
./run.sh test           # Mode test (dry-run)

# Monitoring
./run.sh logs           # Affiche les logs
./run.sh mongo          # Ouvre MongoDB Shell

# Arrêt
./run.sh stop           # Arrête les services
./run.sh clean          # Nettoie tout (docker-compose down -v)

# Aide
./run.sh help           # Affiche toutes les commandes
```

---

## Résultats

Après l'exécution, vérifiez :

**Fichiers générés :**
```bash
ls -la output/
# utilisateurs_doublons_*.csv (si doublons)
```

**MongoDB :**
```bash
./run.sh mongo
# > db.users.countDocuments()
# > db.attendance.countDocuments()
```

---

## Configuration (si nécessaire)

### IPs des pointeuses

Éditez `src/main.py` :
```python
MACHINE_IPS = ['172.17.17.26', '172.17.17.27', '172.17.17.28']
```

### Corrections manuelles

Éditez `config/user_corrections.json` :
```json
{
  "corrections": {
    "36": {"number": "0499/", "title": ""}
  }
}
```

---

## Troubleshooting rapide

| Problème | Solution |
|----------|----------|
| MongoDB ne démarre pas | `./run.sh clean && ./run.sh start` |
| Pas de données | Vérifier IPs ZK (ping) |
| Doublons | Voir `output/utilisateurs_doublons_*.csv` |
| Mode test | `./run.sh test` (dry-run) |

---

**C'est tout! 🎉**

Pour plus de détails → voir README.md
