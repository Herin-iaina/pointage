#!/bin/bash

# 🚀 Script d'installation automatique - Déploiement Linux
# Usage: sudo bash deploy-linux.sh

set -e

echo "╔════════════════════════════════════════════════════╗"
echo "║   🚀 DÉPLOIEMENT POINTAGE - SERVEUR LINUX          ║"
echo "╚════════════════════════════════════════════════════╝"

# Couleurs
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOY_DIR="/opt/pointage"
MONGODB_HOST="172.17.17.72"
MONGODB_PORT="27017"

# ===== VÉRIFICATIONS PRÉALABLES =====
echo -e "\n${BLUE}[1/5] Vérification des prérequis...${NC}"

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez installer Docker d'abord."
    exit 1
fi
echo "✅ Docker trouvé: $(docker --version)"

# Vérifier Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé."
    exit 1
fi
echo "✅ Docker Compose trouvé: $(docker-compose --version)"

# ===== CRÉER RÉPERTOIRES =====
echo -e "\n${BLUE}[2/5] Création des répertoires...${NC}"

sudo mkdir -p "$DEPLOY_DIR"/{output,config,logs}
echo "✅ Répertoires créés: $DEPLOY_DIR"

# ===== CRÉER .env =====
echo -e "\n${BLUE}[3/5] Configuration du fichier .env...${NC}"

if [ -f "$DEPLOY_DIR/.env" ]; then
    echo "⚠️  Le fichier .env existe déjà. Conservation de la configuration existante."
else
    sudo tee "$DEPLOY_DIR/.env" > /dev/null <<EOF
# Configuration MongoDB
MONGODB_URI=mongodb://$MONGODB_HOST:$MONGODB_PORT/pointage

# Configuration ZK Teco
ZK_MACHINE_IPS=172.17.17.26,172.17.17.27,172.17.17.28
EOF
    echo "✅ Fichier .env créé"
fi

# ===== DÉMARRER DOCKER-COMPOSE =====
echo -e "\n${BLUE}[4/5] Démarrage des services Docker...${NC}"

cd "$DEPLOY_DIR/docker"

# Construire et démarrer
docker-compose -f docker-compose-scheduler.yml up -d

echo "✅ Services démarrés"

# ===== VÉRIFICATION FINALE =====
echo -e "\n${BLUE}[5/5] Vérification finale...${NC}"

echo ""
echo "📊 État des conteneurs :"
docker-compose -f docker-compose-scheduler.yml ps

echo ""
echo "📝 Logs du scheduler :"
docker-compose -f docker-compose-scheduler.yml logs scheduler | tail -5

# ===== RÉSUMÉ =====
echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║          ✅ DÉPLOIEMENT TERMINÉ                    ║"
echo "╚════════════════════════════════════════════════════╝"

echo ""
echo -e "${GREEN}Configuration complète :${NC}"
echo "  📁 Répertoire: $DEPLOY_DIR"
echo "  🐳 Docker: ✅ Actif"
echo "  📅 Scheduler: ✅ Ofelia (toutes les heures)"
echo "  📊 Logs: $DEPLOY_DIR/logs/"
echo "  📤 Output: $DEPLOY_DIR/output/"

echo ""
echo -e "${YELLOW}Commandes utiles :${NC}"
echo "  # Voir les logs du scheduler"
echo "  docker-compose -f $DEPLOY_DIR/docker/docker-compose-scheduler.yml logs -f scheduler"
echo ""
echo "  # Exécuter manuellement une extraction"
echo "  docker-compose -f $DEPLOY_DIR/docker/docker-compose-scheduler.yml exec extraction python3 -m src.main"
echo ""
echo "  # Arrêter les services"
echo "  docker-compose -f $DEPLOY_DIR/docker/docker-compose-scheduler.yml down"
echo ""

echo -e "${GREEN}✨ Le pipeline s'exécutera automatiquement selon l'horaire défini!${NC}"
