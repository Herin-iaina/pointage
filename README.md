# ZK Attendance Extraction

Outil d'extraction et de traitement des données de pointage ZKTeco.

## Structure

- `src/`: Code source
  - `main.py`: Point d'entrée
  - `zk_client.py`: Communication avec les appareils
  - `processor.py`: Traitement des données
  - `utils.py`: Utilitaires
- `config/`: Fichiers de configuration
  - `user_corrections.json`: Corrections manuelles des utilisateurs
- `output/`: Fichiers CSV générés

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python3 -m src.main
```

Options :
- `--keep-all`: Conserver tous les fichiers CSV intermédiaires dans `output/`.
- `--sheet-id ID`: (Optionnel) ID ou Nom du Google Sheet. Ignoré si hardcodé dans `src/enricher.py`.
- `--sheet-name NAME`: (Optionnel) Nom de l'onglet à utiliser (par défaut: premier onglet).
- `--credentials PATH`: Chemin vers le fichier JSON de service account (défaut: `config/service_account.json`).

## Fonctionnalités

1. Récupération des utilisateurs depuis les pointeuses (IPs configurées dans `src/main.py`).
2. Application des corrections définies dans `config/user_corrections.json`.
3. Récupération des pointages.
4. Détection des doublons (même nom, ID différents).
5. Génération d'un fichier propre `pointage_final_YYYYMMDD_HHMMSS.csv`.
