import logging

logger = logging.getLogger(__name__)

def create_demo_data():
    """
    Crée un jeu de données de démonstration avec la nouvelle structure.
    Utilise task_id et work_center_id.
    """
    demo_data = {
        'work_centers': [
            {'id': 'wc_demo_usinage', 'name': 'Atelier Usinage', 'description': 'Centre usinage'},
            {'id': 'wc_demo_assemblage', 'name': 'Atelier Assemblage', 'description': 'Centre assemblage'}
        ],
        'machines': [
            {'id': 'machine_demo_1', 'name': 'Tour CNC 01', 'work_center_id': 'wc_demo_usinage'},
            {'id': 'machine_demo_2', 'name': 'Tour CNC 02', 'work_center_id': 'wc_demo_usinage'},
            {'id': 'machine_demo_3', 'name': 'Poste Assemblage 01', 'work_center_id': 'wc_demo_assemblage'}
        ],
        'articles': [
            {'id': 'art_demo_1', 'description': 'Pièce Mécanique Type A'},
            {'id': 'art_demo_2', 'description': 'Pièce Mécanique Type B'}
        ],
        'stocks': [
            {'article_id': 'art_demo_1', 'quantity': 100},
            {'article_id': 'art_demo_2', 'quantity': 100}
        ],
        'manufacturing_orders': [
            {
                'id': 'of_demo_1',
                'article_id': 'art_demo_1',
                'quantity': 10,
                'due_date': '2026-04-01',
                'status': 'pending'
            },
            {
                'id': 'of_demo_2',
                'article_id': 'art_demo_2',
                'quantity': 5,
                'due_date': '2026-04-02',
                'status': 'pending'
            }
        ],
        'operations': [
            {
                'id': 'op_demo_1',
                'order_id': 'of_demo_1',
                'article_id': 'art_demo_1',
                'operation_id': 10,
                'task_id': 'USINAGE',
                'work_center_id': 'wc_demo_usinage',
                'status': 'pending',
                'production_time_minutes': 60,
                'setup_time_minutes': 15
                # Pas de machine_id - sera assigné automatiquement
            },
            {
                'id': 'op_demo_2',
                'order_id': 'of_demo_1',
                'article_id': 'art_demo_1',
                'operation_id': 20,
                'task_id': 'ASSEMBLAGE',
                'work_center_id': 'wc_demo_assemblage',
                'status': 'pending',
                'production_time_minutes': 45,
                'setup_time_minutes': 10
            },
            {
                'id': 'op_demo_3',
                'order_id': 'of_demo_2',
                'article_id': 'art_demo_2',
                'operation_id': 10,
                'task_id': 'USINAGE',
                'work_center_id': 'wc_demo_usinage',
                'status': 'pending',
                'production_time_minutes': 90,
                'setup_time_minutes': 20
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
        ],
        'business_rules': [
            # Règle: task USINAGE autorisée sur work_center usinage
            {
                'id': 'rule_demo_1',
                'rule_type': 'task_workcenter',
                'task_id': 'USINAGE',
                'work_center_id': 'wc_demo_usinage',
                'is_hard': True,
                'allowed': True,
                'description': 'Tâche usinage autorisée sur centre usinage'
            },
            # Règle: task ASSEMBLAGE autorisée sur work_center assemblage
            {
                'id': 'rule_demo_2',
                'rule_type': 'task_workcenter',
                'task_id': 'ASSEMBLAGE',
                'work_center_id': 'wc_demo_assemblage',
                'is_hard': True,
                'allowed': True,
                'description': 'Tâche assemblage autorisée sur centre assemblage'
            }
        ]
    }
    
    logger.info("📦 Jeu de données de démonstration créé (nouvelle structure):")
    logger.info(f"   - {len(demo_data['work_centers'])} work centers")
    logger.info(f"   - {len(demo_data['machines'])} machines")
    logger.info(f"   - {len(demo_data['manufacturing_orders'])} ordres de fabrication")
    logger.info(f"   - {len(demo_data['operations'])} opérations (avec task_id et work_center_id)")
    logger.info(f"   - {len(demo_data['business_rules'])} règles métier")
    
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
    await db.stocks.delete_many({'article_id': {'$regex': '^art_demo_'}})
    await db.manufacturing_orders.delete_many({'id': {'$regex': '^of_demo_'}})
    await db.operations.delete_many({'id': {'$regex': '^op_demo_'}})
    await db.calendars.delete_many({'id': {'$regex': '^cal_demo_'}})
    await db.business_rules.delete_many({'id': {'$regex': '^rule_demo_'}})
    
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
    if demo['business_rules']:
        await db.business_rules.insert_many(demo['business_rules'])
    
    logger.info("✓ Données de démonstration chargées dans la base")
    
    return {
        'success': True,
        'message': 'Données de démonstration chargées (nouvelle structure)',
        'counts': {
            'work_centers': len(demo['work_centers']),
            'machines': len(demo['machines']),
            'manufacturing_orders': len(demo['manufacturing_orders']),
            'operations': len(demo['operations']),
            'articles': len(demo['articles']),
            'stocks': len(demo['stocks']),
            'calendars': len(demo['calendars']),
            'rules': len(demo['business_rules'])
        }
    }
