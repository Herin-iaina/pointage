# 📅 Guide de Schedulage - ZK Attendance Pipeline

Exécutez le pipeline automatiquement à intervalles réguliers pour maintenir MongoDB à jour.

## 🎯 Recommandation

**Pour une production Linux : Systemd Timer** ✅  
**Pour une simplicité classique : Cron** ✅  
**Pour Docker : Ofelia Scheduler** ✅

---

## 1️⃣ Systemd Timer (RECOMMANDÉ) 🏆

### Avantages
- ✅ Intégration native Linux
- ✅ Logs centralisés (journald)
- ✅ Gestion des dépendances
- ✅ Redémarrage automatique en cas d'erreur
- ✅ Meilleure pratique moderne

### Installation

```bash
# Lancer le script d'installation
bash install-scheduler.sh

# Choisir : 1 (Systemd Timer)
```

### Configuration manuelle

**1. Créer le service :**
```bash
sudo nano /etc/systemd/system/pointage-extraction.service
```

```ini
[Unit]
Description=ZK Attendance Extraction → MongoDB
After=network-online.target

[Service]
Type=oneshot
User=pointage
WorkingDirectory=/home/pointage/pointage
ExecStart=/usr/bin/python3 -m src.main
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pointage-extraction
```

**2. Créer le timer :**
```bash
sudo nano /etc/systemd/system/pointage-extraction.timer
```

```ini
[Unit]
Description=ZK Extraction Timer
Requires=pointage-extraction.service

[Timer]
OnBootSec=5min          # 5 minutes après le démarrage
OnUnitActiveSec=1h      # Puis toutes les heures
Persistent=true         # Rattrape si le système est arrêté

[Install]
WantedBy=timers.target
```

**3. Activer et démarrer :**
```bash
sudo systemctl daemon-reload
sudo systemctl enable pointage-extraction.timer
sudo systemctl start pointage-extraction.timer
```

### Commandes utiles

```bash
# Voir le statut
sudo systemctl status pointage-extraction.timer

# Voir les prochaines exécutions
sudo systemctl list-timers pointage-extraction

# Logs en temps réel
sudo journalctl -u pointage-extraction -f

# Exécution manuelle (pour tester)
sudo systemctl start pointage-extraction.service

# Voir les logs de la dernière exécution
sudo journalctl -u pointage-extraction -n 50

# Désactiver le timer
sudo systemctl disable pointage-extraction.timer
sudo systemctl stop pointage-extraction.timer
```

### Horaires courants

```ini
# Toutes les heures
OnUnitActiveSec=1h

# Toutes les 30 minutes
OnUnitActiveSec=30min

# Toutes les 6 heures
OnUnitActiveSec=6h

# Tous les jours à 7h du matin
OnCalendar=*-*-* 07:00:00

# Toutes les heures de 7h à 20h
OnCalendar=*-*-* 07-20:00:00
```

---

## 2️⃣ Cron (CLASSIQUE)

### Avantages
- ✅ Très simple et classique
- ✅ Compatible partout
- ✅ Peu de dépendances

### Inconvénients
- ❌ Pas de gestion des dépendances
- ❌ Logs dispersés (syslog)
- ❌ Moins flexible

### Installation

```bash
# Lancer le script d'installation
bash install-scheduler.sh

# Choisir : 2 (Cron)
```

### Configuration manuelle

```bash
crontab -e
```

Ajoutez l'une de ces lignes :

```bash
# Toutes les heures
0 * * * * cd /home/pointage/pointage && python3 -m src.main >> logs/cron.log 2>&1

# Tous les jours à 7h du matin
0 7 * * * cd /home/pointage/pointage && python3 -m src.main >> logs/cron.log 2>&1

# 4 fois par jour (6h, 12h, 18h, 0h)
0 0,6,12,18 * * * cd /home/pointage/pointage && python3 -m src.main >> logs/cron.log 2>&1

# Toutes les 30 minutes
*/30 * * * * cd /home/pointage/pointage && python3 -m src.main >> logs/cron.log 2>&1
```

### Commandes utiles

```bash
# Voir vos crons
crontab -l

# Éditer vos crons
crontab -e

# Voir les logs du cron
tail -f logs/cron.log

# Voir les logs système
grep CRON /var/log/syslog | tail -20

# Supprimer tous les crons
crontab -r
```

### Format Cron

```
minute (0-59) | heure (0-23) | jour (1-31) | mois (1-12) | jour_semaine (0-6)
```

Exemples :
```bash
0 * * * *           # Toutes les heures
*/30 * * * *        # Toutes les 30 minutes
0 7 * * *           # 7h du matin
0 */6 * * *         # Toutes les 6 heures
0 9-17 * * 1-5      # 9h à 17h en semaine
```

---

## 3️⃣ Docker Compose (CONTENEURS)

### Avantages
- ✅ Isolation complète
- ✅ Facile à déployer
- ✅ Portable

### Inconvénients
- ❌ Dépend de Docker
- ❌ Plus complexe

### Installation avec Ofelia

```bash
# Lancer le script d'installation
bash install-scheduler.sh

# Choisir : 3 (Docker Compose)
```

### Configuration manuelle

**Fichier `docker-compose-scheduler.yml` :**

```yaml
version: '3.8'

services:
  extraction:
    build: .
    environment:
      MONGODB_URI: mongodb://172.17.17.72:27017/pointage
    volumes:
      - ./output:/app/output
      - ./config:/app/config

  scheduler:
    image: mcuadros/ofelia:latest
    depends_on:
      - extraction
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: daemon --docker
```

**Lancer :**
```bash
docker-compose -f docker-compose-scheduler.yml up -d
```

### Commandes Docker

```bash
# Logs du scheduler
docker-compose logs scheduler -f

# Logs de l'extraction
docker-compose logs extraction -f

# Exécution manuelle
docker-compose run extraction python3 -m src.main

# Arrêter
docker-compose down
```

---

## 📊 Comparaison des trois méthodes

| Critère | Systemd | Cron | Docker |
|---------|---------|------|--------|
| **Facilité** | Moyen | Facile | Moyen |
| **Fiabilité** | Excellente | Bonne | Excellente |
| **Logs** | Centralisés (journald) | Dispersés (syslog) | Docker logs |
| **Recommandé pour** | Production Linux | Simplicité | Environnement conteneurisé |
| **Récupération erreurs** | Automatique | Manuel | Automatique |
| **Dépendances** | Systemd natif | aucune | Docker |

---

## 🔍 Monitoring et Logs

### Systemd Timer

```bash
# Logs centralisés
sudo journalctl -u pointage-extraction

# Logs récents
sudo journalctl -u pointage-extraction -n 100

# Logs avec timestamps
sudo journalctl -u pointage-extraction -o short-iso

# Logs en temps réel
sudo journalctl -u pointage-extraction -f
```

### Cron

```bash
# Logs du cron (dans les fichiers logs/)
tail -f logs/cron.log

# Logs système
grep pointage /var/log/syslog | tail -20
```

### Docker

```bash
docker-compose logs scheduler -f
docker-compose logs extraction -f
```

---

## 🆘 Dépannage

### Le pipeline ne s'exécute pas

**Systemd :**
```bash
sudo systemctl status pointage-extraction.timer
sudo journalctl -u pointage-extraction -n 50
```

**Cron :**
```bash
crontab -l
tail -f logs/cron.log
```

**Docker :**
```bash
docker-compose logs scheduler
docker ps
```

### Erreur de connexion MongoDB

Vérifiez que MongoDB est accessible :
```bash
# Test de connexion
python3 -c "from pymongo import MongoClient; print(MongoClient('mongodb://172.17.17.72:27017').server_info())"
```

### Les logs ne s'affichent pas

Créez le répertoire logs :
```bash
mkdir -p logs
chmod 755 logs
```

---

## 🎯 Recommandation finale

Pour **une installation de production sur Linux** :
1. ✅ **Utilisez Systemd Timer**
2. ✅ C'est la meilleure pratique moderne
3. ✅ Logs centralisés et gestion robuste

Pour **une installation simple** :
1. ✅ **Utilisez Cron**
2. ✅ Minimal, fiable, classique

Pour **une installation Docker** :
1. ✅ **Utilisez Ofelia**
2. ✅ Intégration Docker native

---

**Version:** 1.0  
**Dernière mise à jour:** Décembre 2025
