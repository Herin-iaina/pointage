#!/usr/bin/env python3
"""
Module MongoDB pour l'enrichissement des données d'attendance.
Remplace les interactions avec Google Sheets par des requêtes MongoDB.

Collections :
  - users: Utilisateurs enrichis
  - attendance: Attendance enrichi (ancien)
  - zkteco: Raw extraction ZK Teco (name, user_id, timestamp, punch_type)
"""

import json
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

# Configuration
MONGODB_URI = "mongodb://172.17.17.72:27017"
DB_NAME = "pointage"
USERS_COLLECTION = "users"
ATTENDANCE_COLLECTION = "attendance"
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
    
    def get_user_by_id(self, user_id):
        """Récupère un utilisateur par son ID"""
        if not self.connected or self.db is None:
            return None
        
        users_coll = self.db[USERS_COLLECTION]
        return users_coll.find_one({'user_id': int(user_id)})
    
    def get_user_by_pseudo(self, pseudo):
        """Récupère un utilisateur par son pseudo"""
        if not self.connected or self.db is None:
            return None
        
        users_coll = self.db[USERS_COLLECTION]
        return users_coll.find_one({'pseudo': pseudo})
    
    def get_users_with_number(self):
        """Récupère tous les utilisateurs avec un numéro (matricule)"""
        if not self.connected or self.db is None:
            return []
        
        users_coll = self.db[USERS_COLLECTION]
        return list(users_coll.find({'number': {'$exists': True, '$ne': ''}}))
    
    def get_all_users(self):
        """Récupère tous les utilisateurs"""
        if not self.connected or self.db is None:
            return []
        
        users_coll = self.db[USERS_COLLECTION]
        return list(users_coll.find({}))
    
    def update_user(self, user_id, data):
        """Mets à jour un utilisateur"""
        if not self.connected or self.db is None:
            return False
        
        users_coll = self.db[USERS_COLLECTION]
        result = users_coll.update_one(
            {'user_id': int(user_id)},
            {'$set': data}
        )
        return result.modified_count > 0
    
    def insert_attendance(self, user_id, timestamp, punch_type, raw_data):
        """Insère un enregistrement d'attendance"""
        if not self.connected or self.db is None:
            return False
        
        attendance_coll = self.db[ATTENDANCE_COLLECTION]
        record = {
            'user_id': int(user_id),
            'timestamp': timestamp,
            'type': punch_type,
            'raw_data': raw_data,
            'created_at': datetime.now().isoformat()
        }
        
        result = attendance_coll.insert_one(record)
        return result.inserted_id is not None
    
    def get_attendance_for_user(self, user_id, start_date=None, end_date=None):
        """Récupère les enregistrements d'attendance pour un utilisateur"""
        if not self.connected or self.db is None:
            return []
        
        attendance_coll = self.db[ATTENDANCE_COLLECTION]
        query = {'user_id': int(user_id)}
        
        if start_date or end_date:
            query['timestamp'] = {}
            if start_date:
                query['timestamp']['$gte'] = start_date
            if end_date:
                query['timestamp']['$lte'] = end_date
        
        return list(attendance_coll.find(query).sort('timestamp', 1))
    
    def search_users_by_name(self, name_pattern):
        """Cherche des utilisateurs par pattern de nom"""
        if not self.connected or self.db is None:
            return []
        
        users_coll = self.db[USERS_COLLECTION]
        return list(users_coll.find({
            'pseudo': {'$regex': name_pattern, '$options': 'i'}
        }))
    
    def get_duplicate_names(self):
        """Récupère les noms en doublon dans la base"""
        if not self.connected or self.db is None:
            return {}
        
        users_coll = self.db[USERS_COLLECTION]
        pipeline = [
            {
                '$group': {
                    '_id': '$pseudo',
                    'count': {'$sum': 1},
                    'users': {'$push': '$user_id'}
                }
            },
            {
                '$match': {'count': {'$gt': 1}}
            }
        ]
        
        duplicates = {}
        for item in users_coll.aggregate(pipeline):
            duplicates[item['_id']] = item['users']
        
        return duplicates
    
    def get_users_without_number(self):
        """Récupère les utilisateurs sans numéro (matricule)"""
        if not self.connected or self.db is None:
            return []
        
        users_coll = self.db[USERS_COLLECTION]
        return list(users_coll.find({
            '$or': [
                {'number': {'$exists': False}},
                {'number': ''},
                {'number': None}
            ]
        }))
    
    def get_statistics(self):
        """Récupère les statistiques globales"""
        if not self.connected or self.db is None:
            return {}
        
        users_coll = self.db[USERS_COLLECTION]
        attendance_coll = self.db[ATTENDANCE_COLLECTION]
        zkteco_coll = self.db[ZKTECO_COLLECTION]
        
        total_users = users_coll.count_documents({})
        users_with_number = users_coll.count_documents({'number': {'$exists': True, '$ne': ''}})
        users_without_number = total_users - users_with_number
        total_attendance = attendance_coll.count_documents({})
        total_zkteco = zkteco_coll.count_documents({})
        
        return {
            'total_users': total_users,
            'users_with_number': users_with_number,
            'users_without_number': users_without_number,
            'total_attendance_records': total_attendance,
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


def enrich_attendance_from_mongodb(attendance_records, mongo_client):
    """
    Enrichit les enregistrements d'attendance avec les informations des utilisateurs.
    
    Args:
        attendance_records: Liste des enregistrements d'attendance
        mongo_client: Instance de MongoDBClient
    
    Returns:
        Liste enrichie des enregistrements
    """
    enriched = []
    
    for record in attendance_records:
        user_id = record.get('user_id')
        user = mongo_client.get_user_by_id(user_id)
        
        if user:
            enriched_record = {
                **record,
                'user_name': user.get('pseudo', ''),
                'user_number': user.get('number', ''),
                'user_email': user.get('email', '')
            }
            enriched.append(enriched_record)
    
    return enriched


if __name__ == "__main__":
    # Test simple
    client = MongoDBClient()
    if client.connect():
        stats = client.get_statistics()
        print("\n📊 Statistiques MongoDB:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        client.disconnect()
