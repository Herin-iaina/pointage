# 📦 Résumé - Déploiement sur Serveur Linux

## 🎯 Approche recommandée pour Linux

**Docker Compose + Ofelia Scheduler** ✅ (MEILLEURE OPTION)
- ✅ Simple à configurer
- ✅ Pas de dépendances système
- ✅ Logs centralisés
- ✅ Monitoring facile
- ✅ Redémarrage automatique

## 🚀 Déploiement rapide (3 étapes)

### 1️⃣ Sur ton Mac (préparation)

```bash
cd ~/pointage

# Vérifier que tout est prêt
git status
git add .
git commit -m "Préparation déploiement Linux"
git push
```

### 2️⃣ Sur le serveur Linux (installation)

```bash
# Se connecter au serveur
ssh user@server

# Créer le répertoire de déploiement
sudo mkdir -p /opt/pointage
cd /opt/pointage

# Cloner le projet
git clone https://github.com/Herin-iaina/pointage.git .

# Lancer le script d'installation automatisé
sudo bash deploy-linux.sh
```

**C'est tout !** ✨ Le pipeline s'exécutera automatiquement toutes les heures.

### 3️⃣ Vérification (sur le serveur)

```bash
# Voir les conteneurs actifs
docker ps | grep pointage

# Voir les logs
docker-compose -f /opt/pointage/docker/docker-compose-scheduler.yml logs -f scheduler
```

## 📁 Fichiers créés pour Linux

```
/opt/pointage/
├── .env                          ← Configuration (créé automatiquement)
├── docker/
│   └── docker-compose-scheduler.yml  ← Scheduler Ofelia
├── output/                           ← Résultats générés
├── logs/                             ← Logs d'exécution
└── ... (le reste du projet)
```

## 🔧 Configuration après déploiement

### Changer la fréquence d'exécution

Éditer `/opt/pointage/docker/docker-compose-scheduler.yml` :

```yaml
environment:
  OFELIA_JOB_EXEC_EXTRACTION_SCHEDULE: "0 * * * *"  # Toutes les heures
  # Autres options :
  # "0 7 * * *"     → 7h du matin
  # "0 9-17 * * *"  → Toutes les heures entre 9h et 17h
  # "@every 30m"    → Toutes les 30 minutes
```

Puis redémarrer :

```bash
cd /opt/pointage/docker
docker-compose -f docker-compose-scheduler.yml restart scheduler
```

### Changer la configuration MongoDB

Éditer `/opt/pointage/.env` :

```bash
MONGODB_URI=mongodb://username:password@172.17.17.72:27017/pointage
```

Puis redémarrer les conteneurs :

```bash
cd /opt/pointage/docker
docker-compose -f docker-compose-scheduler.yml restart extraction
```

## 📊 Monitoring

### Voir les logs en temps réel

```bash
docker-compose -f /opt/pointage/docker/docker-compose-scheduler.yml logs -f scheduler
```

### Exécuter manuellement une extraction

```bash
docker-compose -f /opt/pointage/docker/docker-compose-scheduler.yml exec extraction python3 -m src.main
```

### Voir les résultats

```bash
# Fichiers générés
ls -la /opt/pointage/output/

# Logs d'exécution
ls -la /opt/pointage/logs/
```

## 🛑 Arrêter/Redémarrer

```bash
# Arrêter complètement
cd /opt/pointage/docker
docker-compose -f docker-compose-scheduler.yml down

# Redémarrer
docker-compose -f docker-compose-scheduler.yml up -d

# Redémarrer après une mise à jour du code
docker-compose -f docker-compose-scheduler.yml up -d --build
```

## 🔐 Sécurité en production

✅ À faire :
1. Changer le mot de passe MongoDB dans `.env`
2. Restreindre les permissions des fichiers
3. Configurer les sauvegardes

```bash
# Exemple : Sauvegarder les logs tous les jours
0 2 * * * tar -czf /backup/pointage-$(date +\%Y\%m\%d).tar.gz /opt/pointage/logs/
```

## ❓ FAQ

**Q: Le pipeline ne s'exécute pas à l'heure prévue**
```
R: Vérifier que le scheduler est actif
   docker ps | grep scheduler
   
   Voir les logs :
   docker logs pointage-scheduler
```

**Q: Les fichiers n'apparaissent pas dans output/**
```
R: Vérifier les chemins dans docker-compose-scheduler.yml
   Doit être : /opt/pointage/output:/app/output
   
   Vérifier les permissions :
   ls -la /opt/pointage/output/
```

**Q: Comment voir si le pipeline a bien fonctionné ?**
```
R: Vérifier MongoDB :
   mongosh mongodb://172.17.17.72:27017/pointage
   > db.zkteco.countDocuments()
   
   Ou voir les fichiers générés :
   ls -la /opt/pointage/output/
```

## 📚 Documentation complète

Voir [DEPLOYMENT_LINUX.md](DEPLOYMENT_LINUX.md) pour le guide détaillé.

---

**Prêt à déployer ?** 🚀

```bash
# Sur le serveur Linux
sudo bash /opt/pointage/deploy-linux.sh
```
