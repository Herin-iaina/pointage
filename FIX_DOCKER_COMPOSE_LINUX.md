# 🔧 Correction : Erreur "KeyError: 'id'" sur Linux

## ❌ Problème

```
Exception in thread Thread-2 (watch_events):
KeyError: 'id'
pointage-scheduler exited with code 1
```

## 🔍 Cause

Cette erreur vient d'une **incompatibilité entre Docker Compose v1 et Docker v20+**. 

Docker Compose v1 est **deprecated** et ne fonctionne plus correctement avec les versions récentes de Docker.

## ✅ Solution

### 1️⃣ Vérifier votre version de Docker Compose

```bash
docker-compose --version
```

### 2️⃣ Si vous avez v1.x (ex: 1.29.2), upgrader vers v2

```bash
# Supprimer l'ancienne version
sudo rm /usr/bin/docker-compose

# Installer Docker Compose v2
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Rendre exécutable
sudo chmod +x /usr/local/bin/docker-compose

# Vérifier l'installation
docker-compose --version  # Ou docker compose --version
```

### 3️⃣ Utiliser les bonnes commandes

Après upgrader, utilisez :

```bash
# ✅ CORRECT (Docker Compose v2)
docker compose up -d
docker compose ps
docker compose logs

# ❌ ANCIEN (Docker Compose v1 - deprecated)
docker-compose up -d
docker-compose ps
docker-compose logs
```

### 4️⃣ Adapter les chemins pour Linux

Avant de lancer, éditez `docker-compose-scheduler.yml` :

```bash
cd /opt/pointage/docker
nano docker-compose-scheduler.yml
```

Remplacez les chemins relatifs `../` par des chemins absolus `/opt/pointage/` :

```yaml
volumes:
  - /opt/pointage/output:/app/output    # Avant: ../output:/app/output
  - /opt/pointage/config:/app/config    # Avant: ../config:/app/config
  - /opt/pointage/logs:/app/logs        # Avant: ../logs:/app/logs
```

### 5️⃣ Relancer

```bash
cd /opt/pointage/docker
docker compose down
docker compose up -d
docker compose logs -f scheduler
```

## 📊 Vérifier que ça marche

```bash
# Voir les logs du scheduler
docker compose logs scheduler

# Vous devriez voir :
# "New job registered "extraction-hourly" - "python3 -m src.main" - "@hourly""
# "Starting scheduler with 1 jobs"
```

## 💡 Pourquoi Docker Compose v2?

| Aspect | v1 | v2 |
|--------|----|----|
| **Commande** | `docker-compose` | `docker compose` |
| **Maintenu** | ❌ Deprecated | ✅ Actif |
| **Bugs** | KeyError: 'id' | ✅ Fixés |
| **Performances** | Lente | ⚡ Rapide |
| **Compat. Docker** | Vieille | ✅ Récente |

## 🚨 En cas de problème

```bash
# Si docker compose command not found
sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
sudo ln -s /usr/local/bin/docker-compose /usr/local/bin/docker-compose

# Vérifier
which docker-compose
which docker

# Redémarrer Docker
sudo systemctl restart docker
```

---

**Après l'upgrade, tout devrait fonctionner ! ✨**
