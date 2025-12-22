#!/bin/bash
# Script d'aide pour le pipeline ZK Attendance

set -e

HELP_MESSAGE="
Usage: ./run.sh [COMMAND]

Commands:
  start         Démarrer les services (MongoDB + Extraction)
  stop          Arrêter les services
  restart       Redémarrer les services
  extract       Exécuter le pipeline d'extraction
  test          Tester l'extraction (mode dry-run)
  logs          Afficher les logs du dernier pipeline
  mongo         Ouvrir MongoDB Shell
  clean         Arrêter et nettoyer les services
  help          Afficher cette aide

Examples:
  ./run.sh start       # Démarrer les services
  ./run.sh extract     # Exécuter l'extraction
  ./run.sh mongo       # Accéder à MongoDB
  ./run.sh stop        # Arrêter les services

Configuration:
  - MongoDB : http://localhost:27017 (admin:password)
  - IPs pointeuses : src/main.py → MACHINE_IPS
  - Corrections : config/user_corrections.json
"

case "${1:-help}" in
  start)
    echo "🚀 Démarrage des services..."
    docker-compose up -d
    echo "✅ Services démarrés"
    echo "   MongoDB : mongodb://admin:password@localhost:27017"
    echo "   Attendre ~10 secondes pour la disponibilité..."
    sleep 15
    ;;
  
  stop)
    echo "⏹️  Arrêt des services..."
    docker-compose stop
    echo "✅ Services arrêtés"
    ;;
  
  restart)
    echo "🔄 Redémarrage des services..."
    docker-compose restart
    echo "✅ Services redémarrés"
    ;;
  
  extract)
    echo "📥 Extraction ZK → MongoDB..."
    docker-compose run --rm extraction
    echo "✅ Extraction terminée"
    ;;
  
  test)
    echo "🧪 Test d'extraction (mode dry-run)..."
    docker-compose run --rm extraction python3 -m src.main --dry-run
    echo "✅ Test terminé"
    ;;
  
  logs)
    echo "📋 Logs du pipeline..."
    docker-compose logs extraction | tail -50
    ;;
  
  mongo)
    echo "🗄️  Ouverture de MongoDB Shell..."
    docker-compose exec mongodb mongosh -u admin -p password --authenticationDatabase admin pointage
    ;;
  
  clean)
    echo "🧹 Nettoyage complet..."
    docker-compose down -v
    echo "✅ Nettoyage terminé"
    ;;
  
  help|*)
    echo "$HELP_MESSAGE"
    ;;
esac
