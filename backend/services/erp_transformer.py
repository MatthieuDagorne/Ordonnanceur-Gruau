"""
Transformateur de données ERP vers format interne.

Contrat de données V1 - Ordonnancement Industriel
"""

import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
import re

logger = logging.getLogger(__name__)

PARIS_TZ = ZoneInfo('Europe/Paris')


def parse_erp_date(date_str: str) -> str:
    """
    Convertit une date ERP (dd/MM/yyyy HH:mm) en format ISO (yyyy-MM-ddTHH:mm:ss).
    Applique la timezone Europe/Paris.
    """
    if pd.isna(date_str) or not date_str:
        return None
    
    try:
        # Format ERP: dd/MM/yyyy HH:mm
        dt = datetime.strptime(str(date_str).strip(), "%d/%m/%Y %H:%M")
        dt = dt.replace(tzinfo=PARIS_TZ)
        return dt.isoformat()
    except ValueError:
        try:
            # Fallback: dd/MM/yyyy sans heure
            dt = datetime.strptime(str(date_str).strip(), "%d/%m/%Y")
            dt = dt.replace(hour=23, minute=59, tzinfo=PARIS_TZ)
            return dt.isoformat()
        except ValueError:
            logger.warning(f"Date non parsable: {date_str}")
            return None


def convert_transport_time(value, unit: str) -> float:
    """
    Convertit le temps de transport en minutes selon l'unité.
    - Jours → ×1440
    - Heures → ×60
    - sinon → minutes
    """
    if pd.isna(value) or value is None:
        return 0
    
    try:
        val = float(value)
    except (ValueError, TypeError):
        return 0
    
    unit_lower = str(unit).lower().strip() if unit else 'minutes'
    
    if 'jour' in unit_lower or unit_lower == 'j':
        return val * 1440  # Jours en minutes
    elif 'heure' in unit_lower or unit_lower == 'h':
        return val * 60  # Heures en minutes
    else:
        return val  # Déjà en minutes


def safe_float(value, default=0.0) -> float:
    """Convertit une valeur en float de manière sécurisée."""
    if pd.isna(value) or value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0) -> int:
    """Convertit une valeur en int de manière sécurisée."""
    if pd.isna(value) or value is None:
        return default
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_str(value, default='') -> str:
    """Convertit une valeur en string de manière sécurisée."""
    if pd.isna(value) or value is None:
        return default
    return str(value).strip()


# =============================================================================
# TRANSFORMATEURS PAR FICHIER
# =============================================================================

def transform_manufacturing_orders(df: pd.DataFrame) -> list:
    """
    Transforme manufacturing_orders.csv du format ERP vers le format interne.
    
    Mapping:
    - OrdreFabrication → order_id (= id pour clé primaire)
    - Article → article_id
    - QuantiteOrdre → order_quantity
    - QuantiteLivree → delivered_quantity
    - StatutOrdre → order_status
    - DateLivraisonRequise → due_date
    - CodePlanificateur → planner_code
    - Priorite → priority
    
    Champ calculé:
    - remaining_quantity = order_quantity - delivered_quantity
    """
    records = []
    
    for _, row in df.iterrows():
        order_qty = safe_float(row.get('QuantiteOrdre', 0))
        delivered_qty = safe_float(row.get('QuantiteLivree', 0))
        
        record = {
            'id': safe_str(row.get('OrdreFabrication')),
            'order_id': safe_str(row.get('OrdreFabrication')),
            'article_id': safe_str(row.get('Article')),
            'order_quantity': order_qty,
            'delivered_quantity': delivered_qty,
            'remaining_quantity': order_qty - delivered_qty,
            'quantity': order_qty - delivered_qty,  # Alias pour compatibilité
            'order_status': safe_str(row.get('StatutOrdre')),
            'status': 'pending',  # Statut interne
            'due_date': parse_erp_date(row.get('DateLivraisonRequise')),
            'planner_code': safe_str(row.get('CodePlanificateur')),
            'priority': safe_int(row.get('Priorite', 999), 999),
        }
        
        # Ne garder que les OF avec quantité restante > 0
        if record['remaining_quantity'] > 0:
            records.append(record)
        else:
            logger.debug(f"OF {record['id']} ignoré (quantité restante = 0)")
    
    logger.info(f"✅ {len(records)} ordres transformés (sur {len(df)} lignes)")
    return records


def transform_operations(df: pd.DataFrame) -> list:
    """
    Transforme operations.csv du format ERP vers le format interne.
    
    Mapping:
    - OrdreFabrication → order_id
    - Operation → operation_seq (numéro séquence)
    - id généré = order_id + "_" + operation_seq
    - OperationSuivante → next_operation_seq
    - Tache → task_id (= tache_id)
    - DescriptionTache → task_label
    - CentreDeCharge → centre_de_charge_id
    - DescriptionCentreDeCharge → centre_label
    - TempsPreparation → setup_time_minutes
    - TempsCycle → run_time_unit_minutes
    - TempsDeplacement → transfer_time_minutes (converti selon UniteTemps)
    - QuantitePlanifiee → planned_quantity
    - QuantiteAchevee → completed_quantity
    - StatutOperation → operation_status
    
    Champs calculés:
    - remaining_quantity = planned_quantity - completed_quantity
    - production_time_minutes = run_time_unit_minutes × remaining_quantity
    """
    records = []
    
    for _, row in df.iterrows():
        order_id = safe_str(row.get('OrdreFabrication'))
        op_seq = safe_int(row.get('Operation', 0))
        
        planned_qty = safe_float(row.get('QuantitePlanifiee', 0))
        completed_qty = safe_float(row.get('QuantiteAchevee', 0))
        remaining_qty = planned_qty - completed_qty
        
        setup_time = safe_float(row.get('TempsPreparation', 0))
        run_time_unit = safe_float(row.get('TempsCycle', 0))
        time_unit = safe_str(row.get('UniteTemps', 'Minutes'))
        
        # Conversion du temps de transport selon l'unité
        transport_raw = row.get('TempsDeplacement', 0)
        transfer_time = convert_transport_time(transport_raw, time_unit)
        
        # Durée de production = temps unitaire × quantité restante
        production_time = run_time_unit * remaining_qty
        
        record = {
            'id': f"{order_id}_{op_seq}",
            'order_id': order_id,
            'operation_seq': op_seq,
            'sequence_number': op_seq,  # Alias
            'next_operation_seq': safe_int(row.get('OperationSuivante', 0)),
            'task_id': safe_str(row.get('Tache')),
            'tache_id': safe_str(row.get('Tache')),  # Alias pour règles métier
            'task_label': safe_str(row.get('DescriptionTache')),
            'centre_de_charge_id': safe_str(row.get('CentreDeCharge')),
            'centre_label': safe_str(row.get('DescriptionCentreDeCharge')),
            'setup_time_minutes': setup_time,
            'run_time_unit_minutes': run_time_unit,
            'production_time_minutes': production_time,
            'transfer_time_minutes': transfer_time,
            'time_unit': time_unit,
            'planned_quantity': planned_qty,
            'completed_quantity': completed_qty,
            'remaining_quantity': remaining_qty,
            'operation_status': safe_str(row.get('StatutOperation')),
            'status': 'pending',  # Statut interne
            # machine_id sera assigné par le MachineAssigner via les règles métier
            'machine_id': None,
        }
        
        # Ne garder que les opérations avec quantité restante > 0
        if remaining_qty > 0:
            records.append(record)
        else:
            logger.debug(f"Opération {record['id']} ignorée (quantité restante = 0)")
    
    logger.info(f"✅ {len(records)} opérations transformées (sur {len(df)} lignes)")
    return records


def transform_operation_materials(df: pd.DataFrame) -> list:
    """
    Transforme operation_material.csv du format ERP vers le format interne.
    
    Mapping:
    - OrdreFabrication → order_id
    - Operation → operation_seq
    - operation_id généré = order_id + "_" + operation_seq
    - Position → bom_position
    - Article → article_composant_id (= article_id)
    - Magasin → warehouse_id
    - QuantiteASortir → quantity (= required_quantity)
    """
    records = []
    
    for _, row in df.iterrows():
        order_id = safe_str(row.get('OrdreFabrication'))
        op_seq = safe_int(row.get('Operation', 0))
        
        record = {
            'order_id': order_id,
            'operation_seq': op_seq,
            'operation_id': f"{order_id}_{op_seq}",
            'bom_position': safe_int(row.get('Position', 0)),
            'article_composant_id': safe_str(row.get('Article')),
            'article_id': safe_str(row.get('Article')),  # Alias
            'warehouse_id': safe_str(row.get('Magasin', 'LV4800')),
            'quantity': safe_float(row.get('QuantiteASortir', 0)),
            'required_quantity': safe_float(row.get('QuantiteASortir', 0)),  # Alias
        }
        
        if record['quantity'] > 0:
            records.append(record)
    
    logger.info(f"✅ {len(records)} consommations matière transformées (sur {len(df)} lignes)")
    return records


def transform_stocks(df: pd.DataFrame) -> list:
    """
    Transforme stock.csv du format ERP vers le format interne.
    
    Mapping:
    - Magasin → warehouse_id
    - Article → article_id
    - StockPhysique → quantity
    
    Agrégation par article_id (tous magasins confondus pour V1).
    """
    # Agréger par article_id
    stock_by_article = {}
    
    for _, row in df.iterrows():
        article_id = safe_str(row.get('Article'))
        qty = safe_float(row.get('StockPhysique', 0))
        warehouse = safe_str(row.get('Magasin', 'LV4800'))
        
        if article_id:
            if article_id not in stock_by_article:
                stock_by_article[article_id] = {
                    'article_id': article_id,
                    'quantity': 0,
                    'warehouse_id': warehouse,
                }
            stock_by_article[article_id]['quantity'] += qty
    
    records = list(stock_by_article.values())
    logger.info(f"✅ {len(records)} stocks transformés (sur {len(df)} lignes, agrégés par article)")
    return records


def transform_planned_supplier_receipts(df: pd.DataFrame) -> list:
    """
    Transforme planned_supplier_receipts.csv du format ERP vers le format interne.
    
    Mapping:
    - Magasin → warehouse_id
    - TypeTransaction → transaction_type
    - TypeOrdre → order_type
    - Ordre → order_ref
    - Article → article_id
    - DescriptionArticle → article_label
    - QuantitePlanifiee → quantity (= planned_quantity)
    - DateTransaction → planned_date
    """
    records = []
    
    for idx, row in df.iterrows():
        record = {
            'id': f"RECEIPT_{idx}",  # Clé technique générée
            'warehouse_id': safe_str(row.get('Magasin', 'LV4800')),
            'transaction_type': safe_str(row.get('TypeTransaction')),
            'order_type': safe_str(row.get('TypeOrdre')),
            'order_ref': safe_str(row.get('Ordre')),
            'article_id': safe_str(row.get('Article')),
            'article_label': safe_str(row.get('DescriptionArticle')),
            'quantity': safe_float(row.get('QuantitePlanifiee', 0)),
            'planned_quantity': safe_float(row.get('QuantitePlanifiee', 0)),  # Alias
            'planned_date': parse_erp_date(row.get('DateTransaction')),
        }
        
        if record['quantity'] > 0 and record['planned_date']:
            records.append(record)
    
    logger.info(f"✅ {len(records)} réceptions planifiées transformées (sur {len(df)} lignes)")
    return records


def transform_articles(df: pd.DataFrame) -> list:
    """
    Transforme articles.csv du format ERP vers le format interne.
    
    Mapping:
    - Article → article_id (= id)
    - DescriptionArticle → article_label (= name)
    - Matiere → material
    - Epaisseur → thickness
    - Longueur → length
    - Largeur → width
    - Couleur → color
    """
    records = []
    
    for _, row in df.iterrows():
        article_id = safe_str(row.get('Article'))
        
        record = {
            'id': article_id,
            'article_id': article_id,
            'name': safe_str(row.get('DescriptionArticle', '')),
            'article_label': safe_str(row.get('DescriptionArticle', '')),
            'material': safe_str(row.get('Matiere', '')),
            'thickness': safe_float(row.get('Epaisseur')),
            'length': safe_float(row.get('Longueur')),
            'width': safe_float(row.get('Largeur')),
            'color': safe_str(row.get('Couleur', '')),
        }
        
        if article_id:
            records.append(record)
    
    logger.info(f"✅ {len(records)} articles transformés (sur {len(df)} lignes)")
    return records
