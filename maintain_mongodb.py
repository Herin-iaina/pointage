#!/usr/bin/env python3
"""
Script de maintenance MongoDB - Gère les index et nettoie les erreurs.
"""

import json
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure

# Configuration
MONGODB_URI = "mongodb://172.17.17.72:27017"
DB_NAME = "pointage"
USERS_COLLECTION = "users"


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


def list_indexes(db):
    """Liste tous les index de la collection"""
    collection = db[USERS_COLLECTION]
    indexes = collection.list_indexes()
    
    print("\n📋 Index existants:")
    for idx in indexes:
        print(f"   • {idx['name']}: {idx['key']}")
        if idx.get('unique'):
            print(f"     ↳ Unique: Oui")
        if idx.get('sparse'):
            print(f"     ↳ Sparse: Oui")


def remove_problematic_indexes(db):
    """Supprime les index qui causent des erreurs"""
    collection = db[USERS_COLLECTION]
    
    print("\n🔧 Suppression des index problématiques...")
    
    try:
        # Lister les index
        indexes = collection.list_indexes()
        indexes_to_remove = []
        
        for idx in indexes:
            if idx['name'] == '_id_':
                continue  # Ne pas supprimer l'index _id
            
            # Index unique sur matricule sans sparse
            if idx.get('unique') and 'matricule' in dict(idx['key']):
                if not idx.get('sparse'):
                    indexes_to_remove.append(idx['name'])
                    print(f"   ❌ {idx['name']}: Index unique non-sparse sur matricule")
        
        # Supprimer les index
        for idx_name in indexes_to_remove:
            collection.drop_index(idx_name)
            print(f"   ✅ Supprimé: {idx_name}")
        
        if not indexes_to_remove:
            print("   ✓ Aucun index problématique trouvé")
        
        return len(indexes_to_remove) > 0
    
    except Exception as e:
        print(f"   ⚠️  Erreur: {e}")
        return False


def create_sparse_indexes(db):
    """Crée des index sparse (ignore les null)"""
    collection = db[USERS_COLLECTION]
    
    print("\n🔨 Création d'index sparse...")
    
    try:
        # Index sparse sur matricule (permet plusieurs null)
        collection.create_index(
            [('matricule', 1)],
            unique=True,
            sparse=True,
            name='matricule_sparse'
        )
        print("   ✅ Index sparse créé sur matricule")
        
        # Index sur user_id
        collection.create_index([('user_id', 1)], name='user_id_idx')
        print("   ✅ Index créé sur user_id")
        
        # Index sur pseudo
        collection.create_index([('pseudo', 1)], name='pseudo_idx')
        print("   ✅ Index créé sur pseudo")
        
    except Exception as e:
        print(f"   ⚠️  Erreur: {e}")


def cleanup_duplicates(db):
    """Nettoie les doublons avec matricule null"""
    collection = db[USERS_COLLECTION]
    
    print("\n🧹 Nettoyage des doublons avec matricule=null...")
    
    try:
        # Trouver les doublons avec matricule null
        duplicates = list(collection.find({'matricule': None}))
        
        if len(duplicates) > 1:
            print(f"   ⚠️  {len(duplicates)} documents avec matricule=null")
            print("   Options:")
            print("   1. Supprimer les doublons (garder le premier)")
            print("   2. Faire un merge manuel")
            
            # Garder le premier, supprimer les autres
            first_id = duplicates[0]['_id']
            to_remove = [d['_id'] for d in duplicates[1:]]
            
            result = collection.delete_many({'_id': {'$in': to_remove}})
            print(f"   ✅ {result.deleted_count} documents supprimés")
        else:
            print("   ✓ Aucun doublon trouvé")
    
    except Exception as e:
        print(f"   ⚠️  Erreur: {e}")


def get_statistics(db):
    """Affiche les statistiques de la collection"""
    collection = db[USERS_COLLECTION]
    
    print("\n📊 Statistiques:")
    total = collection.count_documents({})
    with_matricule = collection.count_documents({'matricule': {'$exists': True, '$ne': None, '$ne': ''}})
    without_matricule = total - with_matricule
    
    print(f"   Total utilisateurs: {total}")
    print(f"   Avec matricule: {with_matricule}")
    print(f"   Sans matricule: {without_matricule}")


def main():
    print("=" * 70)
    print("MAINTENANCE MONGODB")
    print("=" * 70)
    print()
    
    db = connect_to_mongodb()
    if db is None:
        return
    print()
    
    # Afficher les index actuels
    list_indexes(db)
    
    # Supprimer les index problématiques
    removed = remove_problematic_indexes(db)
    
    # Nettoyer les doublons si des index ont été supprimés
    if removed:
        cleanup_duplicates(db)
    
    # Créer les nouveaux index sparse
    create_sparse_indexes(db)
    print()
    
    # Afficher les index après modification
    list_indexes(db)
    print()
    
    # Statistiques
    get_statistics(db)
    
    print("\n" + "=" * 70)
    print("✨ Maintenance terminée!")
    print("=" * 70)
    print("\n💡 Conseil:")
    print("   Relancer maintenant: python3 run_all_pipeline.py")


if __name__ == "__main__":
    main()
