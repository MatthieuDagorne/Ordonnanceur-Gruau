import logging

logger = logging.getLogger(__name__)

def create_demo_data():
    """
    Crée un jeu de données de démonstration avec la terminologie française.
    Utilise tache_id et centre_de_charge_id (codes métier).
    Clé de jointure: order_id
    """
    demo_data = {
        'centres_de_charge': [
            {'id': 'PLI01', 'nom': 'Centre de Pliage', 'description': 'Atelier pliage tôles'},
            {'id': 'USI01', 'nom': 'Centre Usinage', 'description': 'Atelier usinage CNC'},
            {'id': 'ASS01', 'nom': 'Centre Assemblage', 'description': 'Atelier assemblage final'}
        ],
        'machines': [
            # Centre Pliage (PLI01)
            {'id': 'PLIEUSE_01', 'nom': 'Plieuse hydraulique 01', 'centre_de_charge_id': 'PLI01'},
            {'id': 'PLIEUSE_02', 'nom': 'Plieuse hydraulique 02', 'centre_de_charge_id': 'PLI01'},
            # Centre Usinage (USI01)
            {'id': 'TOUR_CNC_01', 'nom': 'Tour CNC 01', 'centre_de_charge_id': 'USI01'},
            {'id': 'TOUR_CNC_02', 'nom': 'Tour CNC 02', 'centre_de_charge_id': 'USI01'},
            {'id': 'FRAISEUSE_01', 'nom': 'Fraiseuse 5 axes', 'centre_de_charge_id': 'USI01'},
            # Centre Assemblage (ASS01)
            {'id': 'POSTE_ASS_01', 'nom': 'Poste assemblage 01', 'centre_de_charge_id': 'ASS01'},
            {'id': 'POSTE_ASS_02', 'nom': 'Poste assemblage 02', 'centre_de_charge_id': 'ASS01'}
        ],
        'articles': [
            {'id': 'ART001', 'description': 'Châssis métallique Type A'},
            {'id': 'ART002', 'description': 'Support de fixation Type B'},
            {'id': 'ART003', 'description': 'Boîtier électronique Type C'}
        ],
        'stocks': [
            {'article_id': 'ART001', 'quantity': 100},
            {'article_id': 'ART002', 'quantity': 150},
            {'article_id': 'ART003', 'quantity': 80}
        ],
        'manufacturing_orders': [
            # Ordre 1 - Urgent (date proche avec heure)
            {
                'id': 'OF001',
                'article_id': 'ART001',
                'quantity': 10,
                'due_date': '2026-03-18T14:00:00',  # Format datetime complet
                'status': 'pending',
                'priority': 1
            },
            # Ordre 2 - Normal
            {
                'id': 'OF002',
                'article_id': 'ART002',
                'quantity': 25,
                'due_date': '2026-03-25T09:00:00',
                'status': 'pending',
                'priority': 0
            },
            # Ordre 3 - En retard (pour tester les alertes)
            {
                'id': 'OF003',
                'article_id': 'ART003',
                'quantity': 5,
                'due_date': '2026-03-10T08:00:00',
                'status': 'pending',
                'priority': 2
            }
        ],
        'operations': [
            # OF001 - Opérations (order_id = clé de jointure)
            {
                'id': 'OF001_10',
                'order_id': 'OF001',
                'article_id': 'ART001',
                'operation_id': 10,
                'tache_id': 'PLIAGE',
                'centre_de_charge_id': 'PLI01',
                'status': 'pending',
                'production_time_minutes': 45,
                'setup_time_minutes': 15
            },
            {
                'id': 'OF001_20',
                'order_id': 'OF001',
                'article_id': 'ART001',
                'operation_id': 20,
                'tache_id': 'USINAGE',
                'centre_de_charge_id': 'USI01',
                'status': 'pending',
                'production_time_minutes': 90,
                'setup_time_minutes': 30
            },
            {
                'id': 'OF001_30',
                'order_id': 'OF001',
                'article_id': 'ART001',
                'operation_id': 30,
                'tache_id': 'ASSEMBLAGE',
                'centre_de_charge_id': 'ASS01',
                'status': 'pending',
                'production_time_minutes': 60,
                'setup_time_minutes': 10
            },
            # OF002 - Opérations
            {
                'id': 'OF002_10',
                'order_id': 'OF002',
                'article_id': 'ART002',
                'operation_id': 10,
                'tache_id': 'USINAGE',
                'centre_de_charge_id': 'USI01',
                'status': 'pending',
                'production_time_minutes': 120,
                'setup_time_minutes': 20
            },
            {
                'id': 'OF002_20',
                'order_id': 'OF002',
                'article_id': 'ART002',
                'operation_id': 20,
                'tache_id': 'ASSEMBLAGE',
                'centre_de_charge_id': 'ASS01',
                'status': 'pending',
                'production_time_minutes': 45,
                'setup_time_minutes': 10
            },
            # OF003 - Opérations (en retard)
            {
                'id': 'OF003_10',
                'order_id': 'OF003',
                'article_id': 'ART003',
                'operation_id': 10,
                'tache_id': 'PLIAGE',
                'centre_de_charge_id': 'PLI01',
                'status': 'pending',
                'production_time_minutes': 30,
                'setup_time_minutes': 10
            },
            {
                'id': 'OF003_20',
                'order_id': 'OF003',
                'article_id': 'ART003',
                'operation_id': 20,
                'tache_id': 'ASSEMBLAGE',
                'centre_de_charge_id': 'ASS01',
                'status': 'pending',
                'production_time_minutes': 40,
                'setup_time_minutes': 5
            }
        ],
        'calendars': [
            {
                'id': 'CAL_STD',
                'name': 'Calendrier Standard',
                'working_days': [1, 2, 3, 4, 5],
                'start_hour': 8,
                'end_hour': 17
            }
        ],
        'business_rules': [
            # Règle 1: Interdire PLIEUSE_01 pour l'article ART003
            {
                'id': 'RULE_001',
                'name': 'Interdire PLIEUSE_01 pour ART003',
                'tache_id': 'PLIAGE',
                'centre_de_charge_id': 'PLI01',
                'article_id': 'ART003',
                'rule_type': 'FORBID',
                'machine_id': 'PLIEUSE_01',
                'active': True
            },
            # Règle 2: Préférer TOUR_CNC_01 pour l'usinage
            {
                'id': 'RULE_002',
                'name': 'Préférer TOUR_CNC_01 pour usinage',
                'tache_id': 'USINAGE',
                'centre_de_charge_id': 'USI01',
                'article_id': None,
                'rule_type': 'PREFER',
                'machine_id': 'TOUR_CNC_01',
                'active': True
            },
            # Règle 3: Préférer POSTE_ASS_01 pour assemblage ART001
            {
                'id': 'RULE_003',
                'name': 'Préférer POSTE_ASS_01 pour ART001',
                'tache_id': 'ASSEMBLAGE',
                'centre_de_charge_id': 'ASS01',
                'article_id': 'ART001',
                'rule_type': 'PREFER',
                'machine_id': 'POSTE_ASS_01',
                'active': True
            }
        ]
    }
    
    logger.info("📦 Jeu de données de démonstration créé (terminologie française):")
    logger.info(f"   - {len(demo_data['centres_de_charge'])} centres de charge")
    logger.info(f"   - {len(demo_data['machines'])} machines")
    logger.info(f"   - {len(demo_data['manufacturing_orders'])} ordres de fabrication")
    logger.info(f"   - {len(demo_data['operations'])} opérations (avec tache_id, centre_de_charge_id, order_id)")
    logger.info(f"   - {len(demo_data['business_rules'])} règles métier")
    
    return demo_data

async def load_demo_data(db):
    """
    Charge les données de démonstration dans la base.
    Supprime d'abord les anciennes données puis insère les nouvelles.
    """
    demo = create_demo_data()
    
    # RESET COMPLET avant insertion
    await db.centres_de_charge.delete_many({})
    await db.work_centers.delete_many({})  # Ancienne collection
    await db.machines.delete_many({})
    await db.articles.delete_many({})
    await db.stocks.delete_many({})
    await db.manufacturing_orders.delete_many({})
    await db.operations.delete_many({})
    await db.calendars.delete_many({})
    await db.business_rules.delete_many({})
    
    logger.info("🗑️  Collections vidées avant insertion demo")
    
    # Insert demo data
    if demo['centres_de_charge']:
        await db.centres_de_charge.insert_many(demo['centres_de_charge'])
    if demo['machines']:
        await db.machines.insert_many(demo['machines'])
    if demo['articles']:
        await db.articles.insert_many(demo['articles'])
    if demo['stocks']:
        await db.stocks.insert_many(demo['stocks'])
    if demo['manufacturing_orders']:
        await db.manufacturing_orders.insert_many(demo['manufacturing_orders'])
    if demo['operations']:
        await db.operations.insert_many(demo['operations'])
    if demo['calendars']:
        await db.calendars.insert_many(demo['calendars'])
    if demo['business_rules']:
        await db.business_rules.insert_many(demo['business_rules'])
    
    logger.info("✅ Données de démonstration chargées (terminologie française)")
    
    return {
        'success': True,
        'message': 'Données de démonstration chargées (terminologie française)',
        'counts': {
            'centres_de_charge': len(demo['centres_de_charge']),
            'machines': len(demo['machines']),
            'manufacturing_orders': len(demo['manufacturing_orders']),
            'operations': len(demo['operations']),
            'articles': len(demo['articles']),
            'stocks': len(demo['stocks']),
            'calendars': len(demo['calendars']),
            'rules': len(demo['business_rules'])
        }
    }
