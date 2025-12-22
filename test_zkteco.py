#!/usr/bin/env python3
"""
Script de test pour valider la collection zkteco
"""

from src.mongodb_client import MongoDBClient
from datetime import datetime

def test_zkteco():
    """Test la collection zkteco"""
    
    print("🧪 Test Collection ZKTECO")
    print("=" * 70)
    
    # Connexion
    mongo = MongoDBClient('mongodb://172.17.17.72:27017')
    if not mongo.connect():
        print("❌ Impossible de connecter à MongoDB")
        return False
    
    print("✅ Connexion établie")
    
    # Créer les indexes
    print("\n1️⃣  Création des indexes...")
    mongo.ensure_zkteco_indexes()
    print("   ✓ Indexes créés")
    
    # Lire le dernier timestamp
    print("\n2️⃣  Lecture du dernier timestamp...")
    last_ts = mongo.get_last_timestamp_zkteco()
    print(f"   ℹ️  Dernier timestamp : {last_ts}")
    
    # Test d'insertion
    print("\n3️⃣  Test d'insertion...")
    test_records = [
        {
            'name': 'Alice',
            'user_id': 1,
            'timestamp': datetime.now().isoformat(),
            'punch_type': 'Check In'
        },
        {
            'name': 'Bob',
            'user_id': 2,
            'timestamp': datetime.now().isoformat(),
            'punch_type': 'Check Out'
        }
    ]
    
    result = mongo.insert_zkteco_records(test_records)
    print(f"   ✓ Inséré : {result['inserted']}")
    print(f"   ✓ Ignoré : {result['skipped']}")
    print(f"   ✓ Erreurs : {result['errors']}")
    
    # Vérifier les doublons
    print("\n4️⃣  Test de détection des doublons...")
    print("   (Insertion des mêmes enregistrements)")
    
    result2 = mongo.insert_zkteco_records(test_records)
    print(f"   ✓ Inséré : {result2['inserted']}")
    print(f"   ✓ Ignoré (doublons) : {result2['skipped']}")
    print(f"   ✓ Erreurs : {result2['errors']}")
    
    # Statistiques
    print("\n5️⃣  Statistiques...")
    stats = mongo.get_statistics()
    print(f"   - Total zkteco : {stats.get('total_zkteco_records', 0)}")
    print(f"   - Total utilisateurs : {stats.get('total_users', 0)}")
    
    # Lire les enregistrements
    print("\n6️⃣  Lecture des enregistrements...")
    zkteco_coll = mongo.db['zkteco']
    records = list(zkteco_coll.find().limit(5))
    print(f"   ✓ {len(records)} enregistrements trouvés")
    
    for rec in records[:3]:
        print(f"     - {rec.get('name')} ({rec.get('user_id')}): {rec.get('timestamp')}")
    
    mongo.disconnect()
    
    print("\n" + "=" * 70)
    print("✅ TESTS TERMINÉS")
    print("=" * 70)
    
    return True


if __name__ == '__main__':
    test_zkteco()
