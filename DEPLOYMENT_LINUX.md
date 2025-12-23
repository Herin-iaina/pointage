# 🚀 Déploiement sur Serveur Linux avec Docker Compose + Ofelia

Guide complet pour déployer le pipeline `pointage` sur un serveur Linux avec planification automatique.

## 📋 Prérequis

- ✅ Docker installé (v20.10+)
- ✅ Docker Compose installé (v2.0+)
- ✅ Accès SSH au serveur
- ✅ MongoDB accessible sur `172.17.17.72:27017`
- ✅ Machines ZK Teco accessibles (`172.17.17.26-28`)

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

### Option A : Depuis le répertoire `/opt/pointage/docker`

```bash
cd /opt/pointage/docker

# Démarrer les services
docker-compose -f docker-compose-scheduler.yml up -d

# Vérifier l'état
docker-compose -f docker-compose-scheduler.yml ps

# Voir les logs
docker-compose -f docker-compose-scheduler.yml logs -f scheduler
```

### Option B : Depuis la racine du projet

```bash
cd /opt/pointage

# Adapter les chemins dans docker-compose-scheduler.yml
# Les chemins relatifs `../output` doivent être changés en chemins absolus
```

## 📅 Configuration du scheduler Ofelia

**Éditer le fichier :**
```bash
nano /opt/pointage/docker/docker-compose-scheduler.yml
```

**Modifier la variable d'environnement pour changer la fréquence :**

```yaml
environment:
  # Format cron standard
  OFELIA_JOB_EXEC_EXTRACTION_SCHEDULE: "0 * * * *"  # Toutes les heures
  
  # Autres exemples :
  # "0 7 * * *"       → 7h du matin (chaque jour)
  # "0 9-17 * * *"    → Toutes les heures entre 9h et 17h
  # "0,30 * * * *"    → Toutes les 30 minutes
  # "@every 15m"      → Toutes les 15 minutes
  # "@hourly"         → Toutes les heures
  # "@daily"          → Chaque jour à minuit
```

## 🔍 Monitoring et Maintenance

### Vérifier que le scheduler fonctionne

```bash
# Voir tous les conteneurs
docker ps

# Voir les logs du scheduler
docker-compose -f /opt/pointage/docker/docker-compose-scheduler.yml logs scheduler

# Voir les logs de la dernière exécution extraction
docker-compose -f /opt/pointage/docker/docker-compose-scheduler.yml logs extraction
```

### Exécuter manuellement le pipeline

```bash
# Lancer une extraction manuelle
docker-compose -f /opt/pointage/docker/docker-compose-scheduler.yml exec extraction python3 -m src.main --dry-run

# Ou directement
docker-compose -f /opt/pointage/docker/docker-compose-scheduler.yml exec extraction python3 -m src.main
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
# Arrêter tous les services
cd /opt/pointage/docker
docker-compose -f docker-compose-scheduler.yml down

# Redémarrer
docker-compose -f docker-compose-scheduler.yml up -d

# Redémarrer en reconstruisant l'image
docker-compose -f docker-compose-scheduler.yml up -d --build
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
# Vérifier que le service scheduler tourne
docker ps | grep scheduler

# Vérifier les logs
docker logs pointage-scheduler

# Redémarrer le scheduler
docker-compose -f docker-compose-scheduler.yml restart scheduler
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
# 1. Vérifier que les conteneurs tournent
docker ps | grep pointage

# 2. Exécuter une extraction manuelle
docker-compose -f /opt/pointage/docker/docker-compose-scheduler.yml exec extraction python3 -m src.main --dry-run

# 3. Vérifier les logs
docker-compose -f /opt/pointage/docker/docker-compose-scheduler.yml logs extraction | tail -20

# 4. Vérifier que MongoDB reçoit les données
mongosh mongodb://172.17.17.72:27017/pointage
> db.zkteco.countDocuments()
```

---

**Version:** 1.0  
**Date:** Décembre 2025  
**Support:** Voir README.md
