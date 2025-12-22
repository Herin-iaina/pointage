#!/usr/bin/env python3
"""
Récupère les utilisateurs enrichis depuis MongoDB et exporte en CSV.
À utiliser après sync_mongodb_attendance.py.
"""

import csv
import json
from pathlib import Path
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

# Configuration
MONGODB_URI = "mongodb://172.17.17.72:27017"
DB_NAME = "pointage"
USERS_COLLECTION = "users"
ATTENDANCE_COLLECTION = "attendance"


def connect_to_mongodb():
    """Se connecte à MongoDB"""
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ismaster')
        db = client[DB_NAME]
        print(f"✅ Connecté à MongoDB: {MONGODB_URI}/{DB_NAME}")
        return db
    except (ServerSelectionTimeoutError, ConnectionFailure) as e:
        print(f"❌ Erreur de connexion MongoDB: {e}")
        return None


def export_users_from_mongodb(db, output_file=None):
    """Exporte les utilisateurs depuis MongoDB en CSV"""
    if db is None:
        return None
    
    if output_file is None:
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'output/utilisateurs_mongodb_{now}.csv'
    
    try:
        users_collection = db[USERS_COLLECTION]
        users = list(users_collection.find({}))
        
        if not users:
            print("❌ Aucun utilisateur trouvé dans MongoDB")
            return None
        
        # Préparation des données
        output_data = []
        for user in users:
            output_data.append({
                'user_id': user.get('user_id', ''),
                'pseudo': user.get('pseudo', ''),
                'name': user.get('name', ''),
                'number': user.get('number', ''),
                'matricule': user.get('matricule', ''),
                'email': user.get('email', ''),
                'pole': user.get('pole', ''),
                'bench': user.get('bench', ''),
                'title': user.get('title', ''),
                'privilege': user.get('privilege', ''),
                'group_id': user.get('group_id', ''),
                'card_number': user.get('card_number', ''),
                'device_ip': user.get('device_ip', ''),
            })
        
        # Sauvegarde CSV
        Path('output').mkdir(parents=True, exist_ok=True)
        fieldnames = [k for k in output_data[0].keys() if k]
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_data)
        
        print(f"✅ {len(users)} utilisateurs exportés")
        print(f"📄 Fichier: {output_file}")
        
        # Statistiques
        with_number = sum(1 for u in output_data if u.get('number'))
        without_number = len(output_data) - with_number
        print(f"   - Avec numéro: {with_number}")
        print(f"   - Sans numéro: {without_number}")
        
        return output_file
    
    except Exception as e:
        print(f"❌ Erreur lors de l'export: {e}")
        return None


def export_attendance_from_mongodb(db, output_file=None):
    """Exporte l'attendance depuis MongoDB en CSV"""
    if db is None:
        return None
    
    if output_file is None:
        now = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'output/attendance_mongodb_{now}.csv'
    
    try:
        attendance_collection = db[ATTENDANCE_COLLECTION]
        records = list(attendance_collection.find({}).sort('timestamp', 1))
        
        if not records:
            print("⚠️  Aucun enregistrement d'attendance trouvé")
            return None
        
        Path('output').mkdir(parents=True, exist_ok=True)
        fieldnames = ['user_id', 'timestamp', 'type', 'raw_data']
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow({
                    'user_id': record.get('user_id', ''),
                    'timestamp': record.get('timestamp', ''),
                    'type': record.get('type', ''),
                    'raw_data': record.get('raw_data', ''),
                })
        
        print(f"✅ {len(records)} enregistrements d'attendance exportés")
        print(f"📄 Fichier: {output_file}")
        
        return output_file
    
    except Exception as e:
        print(f"❌ Erreur lors de l'export: {e}")
        return None


def get_mongodb_statistics(db):
    """Affiche les statistiques MongoDB"""
    if db is None:
        return
    
    try:
        users_coll = db[USERS_COLLECTION]
        attendance_coll = db[ATTENDANCE_COLLECTION]
        
        total_users = users_coll.count_documents({})
        users_with_number = users_coll.count_documents({'number': {'$exists': True, '$ne': ''}})
        users_without_number = total_users - users_with_number
        total_attendance = attendance_coll.count_documents({})
        
        print("\n📊 Statistiques MongoDB:")
        print(f"   Utilisateurs totaux: {total_users}")
        print(f"   - Avec numéro: {users_with_number}")
        print(f"   - Sans numéro: {users_without_number}")
        print(f"   Enregistrements attendance: {total_attendance}")
        
    except Exception as e:
        print(f"❌ Erreur lors des statistiques: {e}")


def main():
    print("=" * 70)
    print("EXPORT MONGODB - UTILISATEURS ET ATTENDANCE")
    print("=" * 70)
    print()
    
    # Connexion MongoDB
    db = connect_to_mongodb()
    if db is None:
        return
    print()
    
    # Statistiques
    get_mongodb_statistics(db)
    print()
    
    # Export utilisateurs
    print("\n📋 Export des utilisateurs...")
    users_file = export_users_from_mongodb(db)
    
    # Export attendance
    print("\n📋 Export de l'attendance...")
    attendance_file = export_attendance_from_mongodb(db)
    
    print("\n" + "=" * 70)
    print("✨ Export terminé!")
    print("=" * 70)


if __name__ == "__main__":
    main()
