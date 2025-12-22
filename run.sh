#!/bin/bash
#
# Script utilitaire pour ZK Attendance Pipeline
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_help() {
    cat << 'EOF'
🕐 ZK Attendance Pipeline

Usage: ./run.sh [commande]

DOCKER
  start               Démarre les services
  stop                Arrête les services  
  restart             Redémarre les services
  clean               Nettoie tout

EXÉCUTION
  extract             Lance l'extraction
  test                Mode test (dry-run)

MONITORING
  logs                Logs en temps réel
  mongo               MongoDB Shell
  status              Statut

SCHEDULER
  install-scheduler   Installe scheduler (cron/systemd/docker)
  timer-status        Statut du systemd timer
  timer-logs          Logs du systemd timer

AIDE
  help                Cette aide

EOF
}

case "${1:-help}" in
  start)
    echo -e "${BLUE}🚀 Démarrage...${NC}"
    docker-compose up -d
    sleep 3
    docker-compose ps
    echo -e "${GREEN}✅ Démarré${NC}"
    ;;
  
  stop)
    echo -e "${YELLOW}⏹️  Arrêt...${NC}"
    docker-compose down
    echo -e "${GREEN}✅ Arrêté${NC}"
    ;;
  
  restart)
    echo -e "${BLUE}🔄 Redémarrage...${NC}"
    docker-compose restart
    echo -e "${GREEN}✅ Redémarré${NC}"
    ;;
  
  extract)
    echo -e "${BLUE}📥 Extraction...${NC}"
    docker-compose run extraction python3 -m src.main
    echo -e "${GREEN}✅ Terminé${NC}"
    ;;
  
  test)
    echo -e "${BLUE}🧪 Mode test...${NC}"
    docker-compose run extraction python3 -m src.main --dry-run
    echo -e "${GREEN}✅ Terminé${NC}"
    ;;
  
  extract-local)
    echo -e "${BLUE}📥 Extraction locale...${NC}"
    python3 -m src.main
    echo -e "${GREEN}✅ Terminé${NC}"
    ;;
  
  logs)
    echo -e "${BLUE}📋 Logs...${NC}"
    docker-compose logs -f extraction
    ;;
  
  mongo)
    echo -e "${BLUE}🗄️  MongoDB...${NC}"
    docker-compose exec mongodb mongosh -u admin -p password --authenticationDatabase admin
    ;;
  
  status)
    echo -e "${BLUE}📊 Statut :${NC}"
    docker-compose ps
    ;;
  
  clean)
    echo -e "${RED}🧹 Nettoyage...${NC}"
    read -p "Sûr ? (y/n) : " confirm
    if [ "$confirm" = "y" ]; then
        docker-compose down -v
        echo -e "${GREEN}✅ Nettoyé${NC}"
    fi
    ;;
  
  install-scheduler)
    bash "$SCRIPT_DIR/install-scheduler.sh"
    ;;
  
  timer-status)
    sudo systemctl status pointage-extraction.timer
    ;;
  
  timer-logs)
    sudo journalctl -u pointage-extraction -f
    ;;
  
  help|*)
    show_help
    ;;
esac

