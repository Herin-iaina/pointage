#!/usr/bin/env python3
"""
Module MongoDB pour l'insertion des données ZK Teco.

Collections :
  - users: Utilisateurs (gérés par main.py)
  - zkteco: Raw extraction ZK Teco (name, user_id, timestamp, punch_type)
           Détection des doublons basée sur timestamp
"""

import os
import json
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://172.17.17.72:27017/pointage')
DB_NAME = "pointage"
ZKTECO_COLLECTION = "zkteco"  # Collection dédiée pour raw ZK Teco data


class MongoDBClient:
    """Client pour interagir avec la base MongoDB"""
    
    def __init__(self, uri=MONGODB_URI, db_name=DB_NAME):
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self.connected = False
    
    def connect(self):
        """Établit la connexion à MongoDB"""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ismaster')
            self.db = self.client[self.db_name]
            self.connected = True
            print(f"✅ Connecté à MongoDB: {self.uri}/{self.db_name}")
            return True
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            print(f"❌ Erreur de connexion MongoDB: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Ferme la connexion"""
        if self.client:
            self.client.close()
            self.connected = False
    
    def ensure_zkteco_indexes(self):
        """Crée les indexes nécessaires pour la collection zkteco"""
        if not self.connected or self.db is None:
            return False
        
        try:
            zkteco_coll = self.db[ZKTECO_COLLECTION]
            # Index sur timestamp pour filtrage efficace
            zkteco_coll.create_index('timestamp')
            # Index composé user_id + timestamp pour éviter les doublons
            zkteco_coll.create_index([('user_id', 1), ('timestamp', 1)], unique=True)
            return True
        except Exception as e:
            print(f"⚠️  Erreur création indexes zkteco: {e}")
            return False
    
    def get_last_timestamp_zkteco(self):
        """Récupère le dernier timestamp inséré dans la collection zkteco"""
        if not self.connected or self.db is None:
            return None
        
        try:
            zkteco_coll = self.db[ZKTECO_COLLECTION]
            last_record = zkteco_coll.find_one(
                {},
                sort=[('timestamp', -1)]
            )
            if last_record:
                return last_record.get('timestamp')
        except Exception as e:
            print(f"⚠️  Erreur lecture dernier timestamp: {e}")
        
        return None
    
    def get_statistics(self):
        """Récupère les statistiques globales"""
        if not self.connected or self.db is None:
            return {}
        
        users_coll = self.db['users']
        zkteco_coll = self.db[ZKTECO_COLLECTION]
        
        total_users = users_coll.count_documents({})
        users_with_number = users_coll.count_documents({'number': {'$exists': True, '$ne': ''}})
        total_zkteco = zkteco_coll.count_documents({})
        
        return {
            'total_users': total_users,
            'users_with_number': users_with_number,
            'total_zkteco_records': total_zkteco,
            'timestamp': datetime.now().isoformat()
        }
    
    def insert_zkteco_records(self, records):
        """
        Insère les enregistrements ZK Teco dans la collection zkteco.
        Filtre automatiquement les enregistrements avec timestamp <= dernier timestamp existant.
        
        Args:
            records: Liste des enregistrements {'name': ..., 'user_id': ..., 'timestamp': ..., 'punch_type': ...}
        
        Returns:
            Dict avec {'inserted': count, 'skipped': count, 'errors': count}
        """
        if not self.connected or self.db is None:
            return {'inserted': 0, 'skipped': 0, 'errors': 0}
        
        # Créer les indexes si nécessaire
        self.ensure_zkteco_indexes()
        
        # Récupérer le dernier timestamp
        last_timestamp = self.get_last_timestamp_zkteco()
        
        zkteco_coll = self.db[ZKTECO_COLLECTION]
        stats = {'inserted': 0, 'skipped': 0, 'errors': 0}
        
        for record in records:
            try:
                timestamp = record.get('timestamp')
                user_id = record.get('user_id')
                
                # Filtrer les anciens enregistrements
                if last_timestamp and timestamp <= last_timestamp:
                    stats['skipped'] += 1
                    continue
                
                # Insérer le nouvel enregistrement
                doc = {
                    'name': record.get('name', ''),
                    'user_id': int(user_id) if user_id else None,
                    'timestamp': timestamp,
                    'punch_type': record.get('punch_type', ''),
                    'created_at': datetime.now().isoformat()
                }
                
                try:
                    zkteco_coll.insert_one(doc)
                    stats['inserted'] += 1
                except Exception as e:
                    # Doublon (unique index) ou autre erreur
                    if 'duplicate' in str(e).lower():
                        stats['skipped'] += 1
                    else:
                        stats['errors'] += 1
            
            except Exception as e:
                stats['errors'] += 1
        
        return stats


if __name__ == "__main__":
    # Test simple
    client = MongoDBClient()
    if client.connect():
        stats = client.get_statistics()
        print("\n📊 Statistiques MongoDB:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        client.disconnect()
