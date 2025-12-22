# 📂 Structure du Projet - Simplifiée & Dockerisée

## Arborescence actuelle

```
pointage/
├── src/                          # Code source principal
│   ├── __init__.py
│   ├── main.py                  # ⭐ Script principal (extraction → MongoDB)
│   ├── zk_client.py             # Client ZK Teco
│   ├── mongodb_client.py        # Client MongoDB
│   ├── processor.py             # Traitement données
│   ├── utils.py                 # Utilitaires
│   └── ancien/                  # Scripts archivés
│       ├── main_old.py
│       ├── sync_mongodb_attendance.py
│       ├── enrich_mongodb_user_id.py
│       ├── export_mongodb.py
│       ├── complete_numbers_from_mongodb.py
│       ├── merge_mongodb_with_zk.py
│       ├── run_all_pipeline.py
│       └── sort_csv.py
│
├── config/                       # Configuration
│   └── user_corrections.json    # Corrections manuelles
│
├── output/                       # Fichiers générés
│   └── (fichiers CSV/JSON générés)
│
├── Dockerfile                   # 🐳 Image Docker Python
├── docker-compose.yml           # 🐳 Orchestration (MongoDB + Python)
├── run.sh                       # 🚀 Script d'aide
├── requirements.txt             # Dépendances Python
└── README.md                    # Documentation
```

## Fichiers clés

### Core (Production)
- **src/main.py** : Point d'entrée unique
  - Extraction ZK → Insertion MongoDB
  - Gestion corrections & doublons
  - Output : Fichiers CSV + données MongoDB

- **src/zk_client.py** : Communication ZK
  - Récupération utilisateurs
  - Récupération attendance

- **src/mongodb_client.py** : Opérations MongoDB
  - Insert/update users
  - Insert/update attendance
  - Statistiques

- **src/processor.py** : Traitement
  - Corrections
  - Détection doublons
  - Nettoyage données

### Docker
- **Dockerfile** : Image Python 3.11 slim
  - Dépendances système (gcc)
  - Pip install requirements
  - CMD : python3 -m src.main

- **docker-compose.yml** : Services
  - MongoDB 7.0 avec persistence
  - Service Python qui exécute main.py
  - Volumes partagés (output/, config/)
  - Network Docker

### Scripts & Docs
- **run.sh** : Alias pratiques
  ```bash
  ./run.sh start      # Démarrer les services
  ./run.sh extract    # Exécuter l'extraction
  ./run.sh stop       # Arrêter
  ./run.sh mongo      # Accéder à MongoDB
  ```

- **README.md** : Documentation complète
  - Installation
  - Usage
  - Configuration
  - Troubleshooting

### Archivés (src/ancien/)
- Anciens scripts multi-étape
- Preserved for reference
- Plus jamais utilisés

## Flux simplifié

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Compose                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────┐          ┌──────────────┐               │
│  │  MongoDB   │ ◄────────┤  Extraction  │               │
│  │     7.0    │          │   (Python)   │               │
│  └────────────┘          └──────────────┘               │
│       │                         │                        │
│       │                         │                        │
│       └─────────┬───────────────┘                        │
│               DONE                                       │
│                                                           │
└─────────────────────────────────────────────────────────┘

                  ZK Machines
                      │
                      ▼
            ┌──────────────────┐
            │  src/main.py     │
            │  ─────────────   │
            │  • load_corrections()
            │  • collect_all_users()
            │  • collect_all_attendance()
            │  • apply_corrections()
            │  • detect_duplicates()
            │  • insert_mongodb()
            └──────────────────┘
```

## Changements principaux

### ✅ Avant (complexe)
- 8+ scripts Python
- Google Sheets integration
- Multi-étapes dans run_all_pipeline.py
- Fichiers intermédiaires nombreux
- Pas de containerization

### ✨ Après (simplifié)
- 1 script principal (main.py)
- Mongodb comme source unique
- Deux étapes : Extract → Insert
- Fichiers CSV générés uniquement pour doublons
- Docker pour déploiement
- run.sh pour faciliter l'usage

## Utilisation

### Option Docker (recommandé)
```bash
./run.sh start
./run.sh extract
./run.sh mongo
./run.sh stop
```

### Option Local
```bash
python3 -m src.main
python3 -m src.main --dry-run
```

## Variables d'environnement (Docker)

- `MONGODB_URI` = `mongodb://admin:password@mongodb:27017/pointage?authSource=admin`

En local, modifier dans `src/main.py`:
```python
MONGODB_URI = 'mongodb://localhost:27017'
```

---

**Dernière mise à jour:** Décembre 2025
