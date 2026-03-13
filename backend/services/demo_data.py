import logging

logger = logging.getLogger(__name__)

def create_demo_data():
    """
    Crée un jeu de données de démonstration minimal.
    2 machines, 2 OF, 3 opérations.
    """
    demo_data = {
        'work_centers': [
            {'id': 'wc_demo_1', 'name': 'Atelier Demo', 'description': 'Poste de démonstration'}
        ],
        'machines': [
            {'id': 'machine_demo_1', 'name': 'Machine A', 'work_center_id': 'wc_demo_1'},
            {'id': 'machine_demo_2', 'name': 'Machine B', 'work_center_id': 'wc_demo_1'}
        ],
        'articles': [
            {'id': 'art_demo_1', 'description': 'Article Demo 1'},
            {'id': 'art_demo_2', 'description': 'Article Demo 2'}
        ],
        'stocks': [
            {'article': 'art_demo_1', 'quantity': 100},
            {'article': 'art_demo_2', 'quantity': 100}
        ],
        'manufacturing_orders': [
            {
                'id': 'of_demo_1',
                'article': 'art_demo_1',
                'quantity': 10,
                'due_date': '2026-04-01',
                'status': 'pending'
            },
            {
                'id': 'of_demo_2',
                'article': 'art_demo_2',
                'quantity': 5,
                'due_date': '2026-04-02',
                'status': 'pending'
            }
        ],
        'operations': [
            {
                'id': 'op_demo_1',
                'order_id': 'of_demo_1',
                'operation_number': 10,
                'sequence': 1,
                'production_time_minutes': 60,
                'setup_time_minutes': 15,
                'machine_id': 'machine_demo_1'
            },
            {
                'id': 'op_demo_2',
                'order_id': 'of_demo_1',
                'operation_number': 20,
                'sequence': 2,
                'production_time_minutes': 45,
                'setup_time_minutes': 10,
                'machine_id': 'machine_demo_2'
            },
            {
                'id': 'op_demo_3',
                'order_id': 'of_demo_2',
                'operation_number': 10,
                'sequence': 1,
                'production_time_minutes': 90,
                'setup_time_minutes': 20,
                'machine_id': 'machine_demo_1'
            }
        ],
        'calendars': [
            {
                'id': 'cal_demo_1',
                'name': 'Calendrier 24/7',
                'working_days': [1, 2, 3, 4, 5, 6, 7],
                'start_hour': 0,
                'end_hour': 24
            }
        ]
    }
    
    logger.info("📦 Jeu de données de démonstration créé:")
    logger.info(f"   - {len(demo_data['machines'])} machines")
    logger.info(f"   - {len(demo_data['manufacturing_orders'])} ordres de fabrication")
    logger.info(f"   - {len(demo_data['operations'])} opérations")
    
    return demo_data

async def load_demo_data(db):
    """
    Charge les données de démonstration dans la base.
    """
    demo = create_demo_data()
    
    # Clear existing demo data
    await db.work_centers.delete_many({'id': {'$regex': '^wc_demo_'}})
    await db.machines.delete_many({'id': {'$regex': '^machine_demo_'}})
    await db.articles.delete_many({'id': {'$regex': '^art_demo_'}})
    await db.stocks.delete_many({'article': {'$regex': '^art_demo_'}})
    await db.manufacturing_orders.delete_many({'id': {'$regex': '^of_demo_'}})
    await db.operations.delete_many({'id': {'$regex': '^op_demo_'}})
    await db.calendars.delete_many({'id': {'$regex': '^cal_demo_'}})
    
    # Insert demo data
    if demo['work_centers']:
        await db.work_centers.insert_many(demo['work_centers'])
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
    
    logger.info("✓ Données de démonstration chargées dans la base")
    
    return {
        'success': True,
        'message': 'Données de démonstration chargées',
        'counts': {
            'work_centers': len(demo['work_centers']),
            'machines': len(demo['machines']),
            'manufacturing_orders': len(demo['manufacturing_orders']),
            'operations': len(demo['operations']),
            'articles': len(demo['articles']),
            'stocks': len(demo['stocks']),
            'calendars': len(demo['calendars'])
        }
    }