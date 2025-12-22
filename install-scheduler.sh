#!/bin/bash
#
# Script d'installation du scheduler pour le pipeline ZK → MongoDB
# Permet de choisir entre : cron, systemd timer, ou Docker
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_PATH="$SCRIPT_DIR"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  🕐 INSTALLATION DU SCHEDULER - ZK Attendance                  ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}Choisissez votre méthode de scheduling :${NC}\n"
echo "1) ${GREEN}Systemd Timer${NC}    ← Recommandé (meilleure pratique Linux)"
echo "2) ${GREEN}Cron${NC}              ← Simple, classique"
echo "3) ${GREEN}Docker Compose${NC}    ← Si vous utilisez Docker"
echo ""

read -p "Votre choix (1/2/3) : " choice

case $choice in
    1)
        echo -e "\n${BLUE}[1/3] Installation du Systemd Timer${NC}"
        install_systemd_timer
        ;;
    2)
        echo -e "\n${BLUE}[1/2] Installation du Cron${NC}"
        install_cron
        ;;
    3)
        echo -e "\n${BLUE}[1/3] Installation du Docker Compose Scheduler${NC}"
        install_docker_scheduler
        ;;
    *)
        echo -e "${RED}❌ Choix invalide${NC}"
        exit 1
        ;;
esac

echo -e "\n${GREEN}✅ Installation terminée !${NC}"
echo -e "\nConsultez la documentation : ${BLUE}docs/SCHEDULING.md${NC}"
}

# =============================================================================
# FONCTION 1 : SYSTEMD TIMER (RECOMMANDÉ)
# =============================================================================

install_systemd_timer() {
    echo "📝 Création des fichiers systemd..."
    
    # Créer le répertoire si nécessaire
    mkdir -p "$PROJECT_PATH/systemd"
    
    # Service
    cat > "$PROJECT_PATH/systemd/pointage-extraction.service" << 'EOF'
[Unit]
Description=ZK Attendance Extraction → MongoDB
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=pointage
WorkingDirectory=/home/pointage/pointage
ExecStart=/usr/bin/python3 -m src.main
StandardOutput=journal
StandardError=journal
SyslogIdentifier=pointage-extraction

# Options pour sécurité
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/home/pointage/pointage/output
EOF

    # Timer (toutes les heures)
    cat > "$PROJECT_PATH/systemd/pointage-extraction.timer" << 'EOF'
[Unit]
Description=Exécution du pipeline ZK toutes les heures
Requires=pointage-extraction.service

[Timer]
# Exécute le service toutes les heures
OnBootSec=5min
OnUnitActiveSec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF

    echo -e "${GREEN}✓${NC} Fichiers créés dans systemd/"
    
    echo -e "\n${YELLOW}Installation système (nécessite sudo)${NC}"
    sudo cp "$PROJECT_PATH/systemd/pointage-extraction.service" /etc/systemd/system/
    sudo cp "$PROJECT_PATH/systemd/pointage-extraction.timer" /etc/systemd/system/
    
    echo -e "${GREEN}✓${NC} Fichiers copiés dans /etc/systemd/system/"
    
    # Créer l'utilisateur systemd si nécessaire
    if ! id "pointage" &>/dev/null; then
        echo -e "\n${YELLOW}Création de l'utilisateur 'pointage'${NC}"
        sudo useradd --system --home /home/pointage --shell /usr/sbin/nologin pointage
        sudo chown -R pointage:pointage "$PROJECT_PATH"
    fi
    
    # Activer et démarrer
    echo -e "\n${YELLOW}Activation du timer${NC}"
    sudo systemctl daemon-reload
    sudo systemctl enable pointage-extraction.timer
    sudo systemctl start pointage-extraction.timer
    
    echo -e "\n${GREEN}✓${NC} Timer activé et démarré"
    
    echo -e "\n${BLUE}📋 Commandes utiles :${NC}"
    echo "  sudo systemctl status pointage-extraction.timer      # Statut du timer"
    echo "  sudo systemctl list-timers pointage-extraction       # Prochaines exécutions"
    echo "  sudo journalctl -u pointage-extraction -f            # Logs en temps réel"
    echo "  sudo systemctl start pointage-extraction.service     # Exécution manuelle"
}

# =============================================================================
# FONCTION 2 : CRON
# =============================================================================

install_cron() {
    echo "📝 Configuration du Cron..."
    
    # Créer le répertoire si nécessaire
    mkdir -p "$PROJECT_PATH/cron"
    
    cat > "$PROJECT_PATH/cron/crontab-schedule.txt" << EOF
# Crontab pour ZK Attendance Extraction
# À ajouter avec : crontab -e
#
# Format: minute heure jour mois jour_semaine commande
#

# Exécute le pipeline toutes les heures
0 * * * * cd $PROJECT_PATH && python3 -m src.main >> $PROJECT_PATH/logs/cron.log 2>&1

# Exécute le pipeline tous les jours à 7h du matin
0 7 * * * cd $PROJECT_PATH && python3 -m src.main >> $PROJECT_PATH/logs/cron.log 2>&1

# Exécute le pipeline 4 fois par jour (6h, 12h, 18h, 0h)
0 0,6,12,18 * * * cd $PROJECT_PATH && python3 -m src.main >> $PROJECT_PATH/logs/cron.log 2>&1

# Exécute le pipeline toutes les 30 minutes
*/30 * * * * cd $PROJECT_PATH && python3 -m src.main >> $PROJECT_PATH/logs/cron.log 2>&1
EOF

    echo -e "${GREEN}✓${NC} Fichier de configuration créé : cron/crontab-schedule.txt"
    
    # Créer le répertoire logs
    mkdir -p "$PROJECT_PATH/logs"
    
    echo -e "\n${YELLOW}Installation du Cron${NC}"
    echo -e "\nCopiez l'une de ces lignes dans votre crontab :"
    echo -e "${BLUE}"
    cat "$PROJECT_PATH/cron/crontab-schedule.txt" | grep "^0 \|^*"
    echo -e "${NC}"
    
    echo -e "\nExécutez : ${BLUE}crontab -e${NC}"
    echo "Puis collez la ligne désirée (sans le # commentaire)"
    
    echo -e "\n${BLUE}📋 Commandes utiles :${NC}"
    echo "  crontab -l                                           # Lister vos crons"
    echo "  crontab -e                                           # Éditer vos crons"
    echo "  tail -f $PROJECT_PATH/logs/cron.log                 # Logs du cron"
    echo "  grep CRON /var/log/syslog                           # Logs système"
}

# =============================================================================
# FONCTION 3 : DOCKER SCHEDULER
# =============================================================================

install_docker_scheduler() {
    echo "📝 Configuration pour Docker Compose..."
    
    mkdir -p "$PROJECT_PATH/docker"
    
    cat > "$PROJECT_PATH/docker/docker-compose-scheduler.yml" << 'EOF'
version: '3.8'

services:
  # Service Python - Extraction ZK → MongoDB
  extraction:
    build: .
    container_name: pointage-extraction
    environment:
      MONGODB_URI: mongodb://172.17.17.72:27017/pointage
    volumes:
      - ./output:/app/output
      - ./config:/app/config
    restart: "no"

  # Scheduler - Exécute le pipeline toutes les heures
  scheduler:
    image: mcuadros/ofelia:latest
    container_name: pointage-scheduler
    depends_on:
      - extraction
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    command: daemon --docker
    environment:
      OFELIA_JOB_EXEC_POINTAGE_EXTRACTION_SCHEDULE: "@hourly"
      OFELIA_JOB_EXEC_POINTAGE_EXTRACTION_CONTAINER: "pointage-extraction"
      OFELIA_JOB_EXEC_POINTAGE_EXTRACTION_COMMAND: "python3 -m src.main"
EOF

    echo -e "${GREEN}✓${NC} Fichier créé : docker/docker-compose-scheduler.yml"
    
    echo -e "\n${YELLOW}Utilisation :${NC}"
    echo "  docker-compose -f docker/docker-compose-scheduler.yml up -d"
    
    echo -e "\n${BLUE}📋 Commandes utiles :${NC}"
    echo "  docker-compose logs scheduler                        # Logs du scheduler"
    echo "  docker-compose logs extraction -f                    # Logs de l'extraction"
    echo "  docker ps                                            # Liste des conteneurs"
}

# Appel principal
main
