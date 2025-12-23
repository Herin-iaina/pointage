# 🚀 Déploiement sur Serveur Linux avec Docker Compose + Ofelia

Guide complet pour déployer le pipeline `pointage` sur un serveur Linux avec planification automatique.

## 📋 Prérequis

- ✅ Docker installé (v20.10+)
- ✅ **Docker Compose v2+** (v1.x cause une erreur KeyError: 'id')
- ✅ Accès SSH au serveur
- ✅ MongoDB accessible sur `172.17.17.72:27017`
- ✅ Machines ZK Teco accessibles (`172.17.17.26-28`)

### Vérifier/Upgrader Docker Compose

```bash
# Vérifier la version
docker compose --version

# Si vous avez docker-compose v1.x, upgrader :
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 🔧 Installation sur le serveur

### 1️⃣ Cloner le projet

```bash
# Créer le répertoire de déploiement
sudo mkdir -p /opt/pointage
cd /opt/pointage

# Cloner depuis Git
git clone https://github.com/Herin-iaina/pointage.git .

# Ou copier directement
scp -r ~/pointage/* user@server:/opt/pointage/
```

### 2️⃣ Créer les répertoires nécessaires

```bash
# Créer les dossiers pour les volumes
sudo mkdir -p /opt/pointage/{output,config,logs}

# Définir les permissions
sudo chown -R $USER:$USER /opt/pointage
chmod -R 755 /opt/pointage
```

### 3️⃣ Configurer le fichier `.env`

```bash
# Créer le fichier .env
cat > /opt/pointage/.env << 'EOF'
# Configuration MongoDB
MONGODB_URI=mongodb://172.17.17.72:27017/pointage

# Configuration ZK Teco
ZK_MACHINE_IPS=172.17.17.26,172.17.17.27,172.17.17.28
EOF
```

### 4️⃣ Vérifier la structure

```bash
ls -la /opt/pointage/
# output/
# config/
# logs/
# .env
# docker/
# src/
# Dockerfile
# docker-compose.yml
# requirements.txt
# ...
```

## 🚀 Lancer le scheduler

### ⚠️ IMPORTANT : Adaptez les chemins pour Linux

Sur Linux, les chemins doivent être **absolus** (`/opt/pointage/...`). Le fichier `docker-compose-scheduler.yml` les utilise déjà. Vérifiez simplement:

```bash
cd /opt/pointage/docker
cat docker-compose-scheduler.yml | grep -A 5 "volumes:"
# Doit montrer: /opt/pointage/output, /opt/pointage/config, /opt/pointage/logs
```

Ensuite, lancez avec **Docker Compose v2** (sans tiret) :

```bash
cd /opt/pointage/docker

# Démarrer les services (extraction + scheduler)
docker compose -f docker-compose-scheduler.yml up -d

# Vérifier l'état
docker compose -f docker-compose-scheduler.yml ps

# Voir les logs du scheduler
docker compose -f docker-compose-scheduler.yml logs -f scheduler
```

⚠️ **Important** : Utilisez `docker compose` (v2) et non `docker-compose` (v1)

## 📅 Configuration du scheduler Ofelia

**Le scheduler utilise les labels Docker (déjà configuré) :**

```yaml
extraction:
  labels:
    ofelia.enabled: "true"
    ofelia.job-exec.extraction-hourly.schedule: "@hourly"
    ofelia.job-exec.extraction-hourly.command: "python3 -m src.main"
```

**Pour changer la fréquence :**

```bash
cd /opt/pointage/docker
nano docker-compose-scheduler.yml
```

Modifiez le label :

```yaml
labels:
  ofelia.job-exec.extraction-hourly.schedule: "@hourly"  # Toutes les heures
  # Autres options :
  # "@every 30m"      → Toutes les 30 minutes
  # "0 7 * * *"       → 7h du matin
  # "0 7,14 * * *"    → 7h et 14h
  # "@daily"          → Minuit
```

Puis redémarrez :

```bash
docker compose restart scheduler
```

## 🔍 Monitoring et Maintenance

### Vérifier que le scheduler fonctionne

```bash
cd /opt/pointage/docker

# Voir tous les conteneurs
docker compose -f docker-compose-scheduler.yml ps

# Voir les logs du scheduler
docker compose -f docker-compose-scheduler.yml logs scheduler

# Voir les logs en temps réel
docker compose -f docker-compose-scheduler.yml logs -f scheduler

# Voir les logs de la dernière exécution
docker compose -f docker-compose-scheduler.yml logs extraction
```

### Exécuter manuellement le pipeline

```bash
cd /opt/pointage/docker

# Test (dry-run)
docker compose -f docker-compose-scheduler.yml exec extraction python3 -m src.main --dry-run

# Exécution réelle
docker compose -f docker-compose-scheduler.yml exec extraction python3 -m src.main
```

### Vérifier les fichiers générés

```bash
# Voir les résultats
ls -lah /opt/pointage/output/
ls -lah /opt/pointage/logs/

# Voir les doublons détectés
cat /opt/pointage/output/utilisateurs_doublons.csv
```

## 🛑 Arrêter/Redémarrer

```bash
cd /opt/pointage/docker

# Arrêter tous les services
docker compose -f docker-compose-scheduler.yml down

# Redémarrer
docker compose -f docker-compose-scheduler.yml up -d

# Redémarrer après une mise à jour du code
docker compose -f docker-compose-scheduler.yml up -d --build

# Redémarrer uniquement le scheduler
docker compose -f docker-compose-scheduler.yml restart scheduler

# Voir l'état
docker compose -f docker-compose-scheduler.yml ps
```

## 🐛 Troubleshooting

### Erreur : "can't reach device"
```
Cause : Les machines ZK ne sont pas accessibles
Solution : Vérifier la connectivité réseau
ping 172.17.17.26
```

### Erreur : "Impossible de se connecter à MongoDB"
```
Cause : MongoDB n'est pas accessible ou l'URI est incorrecte
Solution : Vérifier dans .env et tester la connexion
mongosh mongodb://172.17.17.72:27017/pointage
```

### Les fichiers n'apparaissent pas dans `/opt/pointage/output`
```
Cause : Les volumes ne sont pas correctement mappés
Solution : Vérifier les chemins dans docker-compose-scheduler.yml
Doit être : /opt/pointage/output:/app/output
```

### Le scheduler ne s'exécute pas

```bash
cd /opt/pointage/docker

# Vérifier que le service scheduler tourne
docker ps | grep scheduler

# Vérifier les logs
docker compose -f docker-compose-scheduler.yml logs scheduler

# Redémarrer le scheduler
docker compose -f docker-compose-scheduler.yml restart scheduler

# ⚠️ Si erreur "KeyError: 'id'" → Upgrader Docker Compose v2
# Voir la section Prérequis pour les instructions d'upgrade
```

## 📊 Structure attendue après déploiement

```
/opt/pointage/
├── output/
│   ├── utilisateurs_doublons.csv
│   ├── pointage_final_*.csv          (généré)
│   └── utilisateurs_*.json           (généré)
├── config/
│   └── user_corrections.json
├── logs/
│   └── extraction_*.log              (généré)
├── src/
│   ├── main.py
│   ├── mongodb_client.py
│   ├── zk_client.py
│   ├── processor.py
│   └── utils.py
├── docker/
│   ├── docker-compose-scheduler.yml
│   └── Dockerfile
├── .env                              (créé)
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 🔐 Sécurité

Pour la production :

1. **Changer le mot de passe MongoDB** dans `MONGODB_URI`
2. **Utiliser des variables d'environnement sensibles** (credentials)
3. **Configurer les permissions** sur les fichiers générés
4. **Mettre en place une sauvegarde** des données dans `output/` et `logs/`

```bash
# Exemple : Sauvegarder les logs
0 2 * * * tar -czf /backup/pointage-$(date +\%Y\%m\%d).tar.gz /opt/pointage/logs/
```

## ✅ Vérification finale

```bash
cd /opt/pointage/docker

# 1. Vérifier que les conteneurs tournent
docker compose -f docker-compose-scheduler.yml ps

# 2. Exécuter une extraction manuelle
docker compose -f docker-compose-scheduler.yml exec extraction python3 -m src.main --dry-run

# 3. Vérifier les logs
docker compose -f docker-compose-scheduler.yml logs extraction | tail -20

# 4. Vérifier que MongoDB reçoit les données
mongosh mongodb://172.17.17.72:27017/pointage
> db.zkteco.countDocuments()
```

---

**Version:** 1.0  
**Date:** Décembre 2025  
**Support:** Voir README.md
