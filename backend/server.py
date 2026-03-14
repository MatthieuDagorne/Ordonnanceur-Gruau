from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import pandas as pd
import io
import uuid

from services.scheduler_engine import SchedulerEngine
from services.material_checker import MaterialChecker
from services.material_manager import MaterialManager, MaterialChecker as NewMaterialChecker
from services.rules_engine import RulesEngine
from services.machine_assigner import MachineAssigner
from services.demo_data import load_demo_data
from models.business_rule import BusinessRule as BusinessRuleModel

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic Models - Terminologie française, codes métier
class Machine(BaseModel):
    """Machine rattachée à un centre de charge"""
    model_config = ConfigDict(extra="ignore")
    id: str  # Code métier (ex: PLIEUSE_01), pas UUID
    nom: str
    centre_de_charge_id: str  # Référence au code du centre de charge
    description: Optional[str] = None

class Calendar(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    working_days: List[int] = Field(default=[1, 2, 3, 4, 5])
    start_hour: int = Field(default=8)
    end_hour: int = Field(default=17)

class MachineUnavailability(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    machine_id: str
    start_date: str
    end_date: str
    reason: str

class BusinessRule(BaseModel):
    """
    Règle métier pour le POC.
    Utilise des codes métier (pas UUID).
    """
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    
    # Critères de ciblage (codes métier) - règles simples
    tache_id: Optional[str] = None
    centre_de_charge_id: Optional[str] = None
    article_id: Optional[str] = None
    
    # Critères sur attributs article - règles avancées
    attribute_name: Optional[str] = None      # width, thickness, material_type, color, length
    attribute_operator: Optional[str] = None  # GT, GE, LT, LE, EQ, NE, IN, NOT_IN
    attribute_value: Optional[Any] = None     # Valeur de comparaison
    
    # Type: ALLOW, FORBID, PREFER
    rule_type: str
    
    # Machine cible (code métier)
    machine_id: str
    
    # État
    active: bool = Field(default=True)

class ManufacturingOrder(BaseModel):
    """
    Ordre de fabrication.
    
    Format due_date: ISO 8601 (YYYY-MM-DDTHH:MM:SS ou YYYY-MM-DD)
    Exemples: "2026-03-18T14:30:00", "2026-03-18 14:30:00", "2026-03-18"
    """
    model_config = ConfigDict(extra="ignore")
    id: str  # Code OF (ex: OF001, LV1100007)
    article_id: str  # Code article (ex: ART001, 100235570)
    quantity: float
    due_date: str  # Format: YYYY-MM-DDTHH:MM:SS ou YYYY-MM-DD
    status: str
    priority: Optional[int] = 0  # 0=normal, 1=prioritaire, 2=urgent

class Operation(BaseModel):
    """
    Opération de fabrication.
    
    Clé de jointure: order_id -> ManufacturingOrder.id
    L'article_id est récupéré depuis l'ordre via cette jointure.
    """
    model_config = ConfigDict(extra="ignore")
    id: str  # Code opération (ex: OF001_10, LV1100007_10)
    order_id: str  # Clé de jointure vers ManufacturingOrder.id
    operation_id: int  # Numéro dans la gamme (10, 20, 30...)
    tache_id: str  # Type de tâche (ex: PLIAGE, LVT001)
    centre_de_charge_id: str  # Centre de charge requis (ex: PLI01, LVC001)
    status: Optional[str] = "pending"
    production_time_minutes: int
    setup_time_minutes: int
    
    # Note: article_id n'est PAS dans l'opération, il vient de l'ordre via order_id
    
    # Assignation (déterminée par le moteur)
    machine_id: Optional[str] = None
    scheduled_start: Optional[str] = None  # Format: ISO 8601
    scheduled_end: Optional[str] = None    # Format: ISO 8601

class Article(BaseModel):
    """
    Article avec caractéristiques pour règles métier avancées.
    """
    model_config = ConfigDict(extra="ignore")
    id: str  # article_id
    description: str
    # Nouveaux champs pour règles sur attributs
    material_type: Optional[str] = None  # Type de matière (ex: ACIER, INOX, ALU)
    thickness: Optional[float] = None    # Épaisseur en mm
    color: Optional[str] = None          # Couleur
    width: Optional[float] = None        # Largeur en mm
    length: Optional[float] = None       # Longueur en mm

class CentreDeCharge(BaseModel):
    """Centre de charge avec calendrier associé."""
    model_config = ConfigDict(extra="ignore")
    id: str  # Code centre (ex: PLI01, LVC001)
    nom: str
    description: Optional[str] = None
    calendar_id: Optional[str] = None  # Référence au calendrier

class Stock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    article_id: str  # Cohérent avec ManufacturingOrder et Operation
    quantity: float

# Nouveaux modèles pour la gestion des matières
class OperationMaterial(BaseModel):
    """Besoin matière pour une opération."""
    model_config = ConfigDict(extra="ignore")
    id: str  # operation_id (ex: LV1100001_10)
    order_id: str
    operation_id: int
    article_composant_id: str
    quantity: float

class PlannedSupplierReceipt(BaseModel):
    """Réception fournisseur planifiée."""
    model_config = ConfigDict(extra="ignore")
    article_id: str
    quantity: float
    planned_date: str  # Format: YYYY-MM-DDTHH:MM:SS

class Scenario(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    schedule_data: Optional[Dict[str, Any]] = None
    status: str = "draft"

class ScheduleRequestWithOptions(BaseModel):
    scenario_id: Optional[str] = None
    ignore_rules: bool = False
    ignore_material: bool = False
    debug_mode: bool = True
    auto_assign_machines: bool = True
    max_solver_time_seconds: int = 60  # Nouveau: temps maximum de calcul

class ImportResult(BaseModel):
    success: bool
    message: str
    records_imported: int = 0
    previous_records: int = 0
    duplicates_found: int = 0

class DataStats(BaseModel):
    manufacturing_orders: int
    operations: int
    articles: int
    stocks: int
    machines: int
    work_centers: int
    calendars: int
    rules: int
    scenarios: int
    last_import: Optional[str] = None

# Centres de Charge endpoints
@api_router.post("/centres-de-charge")
async def create_centre_de_charge(centre: CentreDeCharge):
    """Créer un centre de charge avec un code métier."""
    doc = centre.model_dump()
    # Vérifier que l'ID n'existe pas déjà
    existing = await db.centres_de_charge.find_one({"id": centre.id})
    if existing:
        raise HTTPException(status_code=400, detail=f"Le centre de charge '{centre.id}' existe déjà")
    await db.centres_de_charge.insert_one(doc)
    return centre

@api_router.get("/centres-de-charge")
async def get_centres_de_charge():
    """Liste tous les centres de charge."""
    centres = await db.centres_de_charge.find({}, {"_id": 0}).to_list(1000)
    return centres

@api_router.delete("/centres-de-charge/{centre_id}")
async def delete_centre_de_charge(centre_id: str):
    result = await db.centres_de_charge.delete_one({"id": centre_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Centre de charge non trouvé")
    return {"message": "Supprimé avec succès"}

@api_router.put("/centres-de-charge/{centre_id}")
async def update_centre_de_charge(centre_id: str, updates: Dict[str, Any]):
    """Met à jour un centre de charge (notamment le calendrier associé)."""
    # Filtrer les champs modifiables
    allowed_fields = {'nom', 'description', 'calendar_id'}
    update_data = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    
    result = await db.centres_de_charge.update_one(
        {"id": centre_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Centre de charge non trouvé")
    
    return {"message": "Mis à jour avec succès", "updated": update_data}

# Machines endpoints
@api_router.post("/machines")
async def create_machine(machine: Machine):
    """Créer une machine avec un code métier."""
    doc = machine.model_dump()
    # Vérifier que l'ID n'existe pas déjà
    existing = await db.machines.find_one({"id": machine.id})
    if existing:
        raise HTTPException(status_code=400, detail=f"La machine '{machine.id}' existe déjà")
    await db.machines.insert_one(doc)
    return machine

@api_router.get("/machines")
async def get_machines():
    """Liste toutes les machines."""
    machines = await db.machines.find({}, {"_id": 0}).to_list(1000)
    return machines

@api_router.delete("/machines/{machine_id}")
async def delete_machine(machine_id: str):
    result = await db.machines.delete_one({"id": machine_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Machine non trouvée")
    return {"message": "Supprimé avec succès"}

# Calendars endpoints
@api_router.post("/calendars", response_model=Calendar)
async def create_calendar(calendar: Calendar):
    doc = calendar.model_dump()
    await db.calendars.insert_one(doc)
    return calendar

@api_router.get("/calendars", response_model=List[Calendar])
async def get_calendars():
    calendars = await db.calendars.find({}, {"_id": 0}).to_list(1000)
    return calendars

@api_router.delete("/calendars/{calendar_id}")
async def delete_calendar(calendar_id: str):
    result = await db.calendars.delete_one({"id": calendar_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Calendar not found")
    return {"message": "Deleted successfully"}

# Unavailability endpoints
@api_router.post("/unavailability", response_model=MachineUnavailability)
async def create_unavailability(unavailability: MachineUnavailability):
    doc = unavailability.model_dump()
    await db.unavailability.insert_one(doc)
    return unavailability

@api_router.get("/unavailability", response_model=List[MachineUnavailability])
async def get_unavailability():
    unavailability = await db.unavailability.find({}, {"_id": 0}).to_list(1000)
    return unavailability

@api_router.delete("/unavailability/{unavailability_id}")
async def delete_unavailability(unavailability_id: str):
    result = await db.unavailability.delete_one({"id": unavailability_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Unavailability not found")
    return {"message": "Deleted successfully"}

# Business Rules endpoints
@api_router.post("/rules")
async def create_rule(rule: BusinessRule):
    """Créer une règle métier."""
    doc = rule.model_dump()
    if 'rule_type' in doc and doc['rule_type']:
        doc['rule_type'] = doc['rule_type'].upper()
    await db.business_rules.insert_one(doc)
    return {
        'id': doc.get('id'),
        'name': doc.get('name'),
        'tache_id': doc.get('tache_id'),
        'centre_de_charge_id': doc.get('centre_de_charge_id'),
        'article_id': doc.get('article_id'),
        'rule_type': doc.get('rule_type', 'ALLOW').upper(),
        'machine_id': doc.get('machine_id'),
        'active': doc.get('active', True)
    }

@api_router.get("/rules")
async def get_rules():
    """Liste toutes les règles métier."""
    rules = await db.business_rules.find({}, {"_id": 0}).to_list(1000)
    valid_rules = []
    for rule in rules:
        if rule.get('name') and rule.get('machine_id') and rule.get('rule_type'):
            rule_type = rule.get('rule_type', '').upper()
            if rule_type not in ['ALLOW', 'FORBID', 'PREFER']:
                rule_type = 'ALLOW'
            
            valid_rules.append({
                'id': rule.get('id'),
                'name': rule.get('name'),
                'tache_id': rule.get('tache_id') or rule.get('task_id'),  # Compatibilité
                'centre_de_charge_id': rule.get('centre_de_charge_id') or rule.get('work_center_id'),
                'article_id': rule.get('article_id'),
                'rule_type': rule_type,
                'machine_id': rule.get('machine_id'),
                'active': rule.get('active', True)
            })
    return valid_rules

@api_router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    result = await db.business_rules.delete_one({"id": rule_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Deleted successfully"}

@api_router.delete("/rules")
async def delete_all_rules():
    """Supprime toutes les règles métier (utile pour nettoyer les anciennes données)."""
    result = await db.business_rules.delete_many({})
    return {"message": f"{result.deleted_count} règle(s) supprimée(s)"}

# Manufacturing Orders endpoints
@api_router.get("/manufacturing-orders")
async def get_manufacturing_orders():
    """Retourne tous les ordres de fabrication."""
    orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(1000)
    return orders

@api_router.get("/operations")
async def get_operations():
    """Retourne toutes les opérations avec terminologie française."""
    operations = await db.operations.find({}, {"_id": 0}).to_list(1000)
    result = []
    for op in operations:
        result.append({
            'id': op.get('id'),
            'order_id': op.get('order_id'),
            'article_id': op.get('article_id'),
            'operation_id': op.get('operation_id'),
            'tache_id': op.get('tache_id') or op.get('task_id'),
            'centre_de_charge_id': op.get('centre_de_charge_id') or op.get('work_center_id'),
            'status': op.get('status'),
            'production_time_minutes': op.get('production_time_minutes'),
            'setup_time_minutes': op.get('setup_time_minutes'),
            'machine_id': op.get('machine_id')
        })
    return result

@api_router.get("/operations-enrichies")
async def get_operations_enrichies():
    """
    Retourne les opérations enrichies avec jointure sur les ordres de fabrication.
    Clé de jointure: order_id
    
    Chaque opération contient:
    - Données de l'opération (tache_id, centre_de_charge_id, etc.)
    - Données de l'ordre (article_id, date_besoin, priority)
    """
    orders_raw = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(1000)
    operations_raw = await db.operations.find({}, {"_id": 0}).to_list(1000)
    
    # Index des ordres par order_id pour jointure rapide
    orders_by_id = {}
    for order in orders_raw:
        order_id = order.get('id')
        orders_by_id[order_id] = {
            'article_id': order.get('article_id') or order.get('article'),
            'quantity': order.get('quantity'),
            'date_besoin': order.get('due_date') or order.get('date_besoin'),
            'priority': order.get('priority', 0),
            'status': order.get('status')
        }
    
    # Enrichir chaque opération avec les données de l'ordre
    result = []
    for op in operations_raw:
        order_id = op.get('order_id')
        order_data = orders_by_id.get(order_id, {})
        
        enriched_op = {
            # Données de l'opération
            'id': op.get('id'),
            'order_id': order_id,
            'operation_id': op.get('operation_id'),
            'tache_id': op.get('tache_id') or op.get('task_id'),
            'centre_de_charge_id': op.get('centre_de_charge_id') or op.get('work_center_id'),
            'production_time_minutes': op.get('production_time_minutes', 0),
            'setup_time_minutes': op.get('setup_time_minutes', 0),
            'status': op.get('status'),
            'machine_id': op.get('machine_id'),
            
            # Données de l'ordre (jointure sur order_id)
            'article_id': order_data.get('article_id'),
            'date_besoin': order_data.get('date_besoin'),
            'priority': order_data.get('priority', 0),
            'quantity': order_data.get('quantity'),
            
            # Indicateur de jointure réussie
            'ordre_trouve': order_id in orders_by_id
        }
        result.append(enriched_op)
    
    # Trier par date_besoin puis par order_id
    result.sort(key=lambda x: (x.get('date_besoin') or '9999-99-99', x.get('order_id') or '', x.get('operation_id') or 0))
    
    return result

# ==========================================
# STOCK PROJETE - Vue du stock dans le temps
# ==========================================
@api_router.get("/projected-stock")
async def get_projected_stock():
    """
    Calcule et retourne le stock projeté avec :
    - Stock initial par article
    - Consommations planifiées (besoins matière des opérations)
    - Réceptions fournisseurs planifiées
    - Dates de rupture et de disponibilité basées sur l'ordonnancement
    
    Les dates sont déterminées par :
    1. scheduled_start des opérations si elles ont été ordonnancées
    2. due_date des ordres si non ordonnancées
    """
    try:
        stocks = await db.stocks.find({}, {"_id": 0}).to_list(1000)
        operation_materials = await db.operation_materials.find({}, {"_id": 0}).to_list(10000)
        planned_receipts = await db.planned_supplier_receipts.find({}, {"_id": 0}).to_list(1000)
        orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(1000)
        operations = await db.operations.find({}, {"_id": 0}).to_list(1000)
        
        # Index des ordres par ID
        orders_by_id = {o.get('id'): o for o in orders}
        
        # Index des opérations par ID
        operations_by_id = {op.get('id'): op for op in operations}
        
        # Stock initial par article
        stock_by_article = {s.get('article_id'): s.get('quantity', 0) for s in stocks}
        
        # Consommations par article (depuis operation_materials)
        # Avec timestamp de l'ordonnanceur ou date de besoin
        consumption_by_article = {}
        consumption_details = []
        
        for mat in operation_materials:
            article_id = mat.get('article_composant_id')
            qty = mat.get('quantity', 0)
            op_id = mat.get('id')
            order_id = mat.get('order_id')
            
            # Récupérer l'opération pour obtenir scheduled_start
            operation = operations_by_id.get(op_id, {})
            scheduled_start = operation.get('scheduled_start')
            
            # Récupérer la date de besoin depuis l'ordre si pas de scheduled_start
            order = orders_by_id.get(order_id, {})
            due_date = order.get('due_date')
            
            # Timestamp de consommation : scheduled_start prioritaire, sinon due_date
            consumption_datetime = scheduled_start or due_date
            
            if article_id not in consumption_by_article:
                consumption_by_article[article_id] = []
            
            consumption_by_article[article_id].append({
                'quantity': qty,
                'datetime': consumption_datetime,
                'operation_id': op_id,
                'order_id': order_id,
                'is_scheduled': scheduled_start is not None
            })
            
            consumption_details.append({
                'article_id': article_id,
                'quantity': qty,
                'operation_id': op_id,
                'order_id': order_id,
                'scheduled_datetime': scheduled_start,
                'due_date': due_date,
                'consumption_datetime': consumption_datetime,
                'is_scheduled': scheduled_start is not None
            })
        
        # Trier les consommations par datetime
        for article_id in consumption_by_article:
            consumption_by_article[article_id].sort(
                key=lambda x: x.get('datetime') or '9999-99-99'
            )
        
        # Réceptions planifiées par article
        receipts_by_article = {}
        for receipt in planned_receipts:
            article_id = receipt.get('article_id')
            if article_id not in receipts_by_article:
                receipts_by_article[article_id] = []
            receipts_by_article[article_id].append({
                'quantity': receipt.get('quantity', 0),
                'planned_date': receipt.get('planned_date')
            })
        
        # Trier les réceptions par date
        for article_id in receipts_by_article:
            receipts_by_article[article_id].sort(key=lambda x: x.get('planned_date') or '9999-99-99')
        
        # Calculer le stock projeté par article avec projection temporelle
        projected_stock = []
        
        # Collecter tous les articles concernés
        all_articles = set(stock_by_article.keys()) | set(consumption_by_article.keys()) | set(receipts_by_article.keys())
        
        for article_id in sorted(all_articles):
            initial_stock = stock_by_article.get(article_id, 0)
            consumptions = consumption_by_article.get(article_id, [])
            receipts = receipts_by_article.get(article_id, [])
            
            total_consumption = sum(c.get('quantity', 0) for c in consumptions)
            total_receipts = sum(r.get('quantity', 0) for r in receipts)
            
            # Stock projeté final
            final_stock = initial_stock + total_receipts - total_consumption
            
            # Calculer la projection temporelle
            # Construire la timeline : événements triés par date
            events = []
            for cons in consumptions:
                events.append({
                    'datetime': cons.get('datetime'),
                    'type': 'consumption',
                    'quantity': -cons.get('quantity', 0),
                    'operation_id': cons.get('operation_id')
                })
            for rec in receipts:
                events.append({
                    'datetime': rec.get('planned_date'),
                    'type': 'receipt',
                    'quantity': rec.get('quantity', 0)
                })
            
            # Trier par datetime
            events.sort(key=lambda x: x.get('datetime') or '9999-99-99')
            
            # Calculer le stock à chaque instant et détecter les ruptures
            current_stock = initial_stock
            has_shortage = False
            shortage_quantity = 0
            first_shortage_datetime = None
            availability_date = None
            timeline = []
            
            for event in events:
                current_stock += event['quantity']
                
                timeline.append({
                    'datetime': event.get('datetime'),
                    'type': event['type'],
                    'quantity_change': event['quantity'],
                    'stock_after': current_stock,
                    'operation_id': event.get('operation_id')
                })
                
                if current_stock < 0 and not has_shortage:
                    has_shortage = True
                    first_shortage_datetime = event.get('datetime')
                    shortage_quantity = abs(current_stock)
                
                # Date de disponibilité : quand le stock redevient >= 0
                if has_shortage and current_stock >= 0 and availability_date is None:
                    availability_date = event.get('datetime')
            
            projected_stock.append({
                'article_id': article_id,
                'initial_stock': initial_stock,
                'total_consumption': total_consumption,
                'total_receipts': total_receipts,
                'final_stock': final_stock,
                'has_shortage': has_shortage,
                'shortage_quantity': shortage_quantity,
                'first_shortage_datetime': first_shortage_datetime,
                'availability_date': availability_date,
                'receipts': receipts,
                'timeline': timeline[:20]  # Limiter pour l'affichage
            })
        
        # Trier par rupture (en premier) puis par datetime de rupture puis par article_id
        projected_stock.sort(key=lambda x: (
            0 if x['has_shortage'] else 1, 
            x.get('first_shortage_datetime') or '9999-99-99',
            x['article_id']
        ))
        
        # Compter les opérations ordonnancées vs non ordonnancées
        scheduled_consumptions = len([c for c in consumption_details if c.get('is_scheduled')])
        unscheduled_consumptions = len([c for c in consumption_details if not c.get('is_scheduled')])
        
        return {
            'projected_stock': projected_stock,
            'consumption_details': consumption_details,
            'summary': {
                'total_articles': len(projected_stock),
                'articles_with_shortage': len([p for p in projected_stock if p['has_shortage']]),
                'articles_ok': len([p for p in projected_stock if not p['has_shortage']]),
                'scheduled_consumptions': scheduled_consumptions,
                'unscheduled_consumptions': unscheduled_consumptions
            }
        }
        
    except Exception as e:
        logger.error(f"Projected stock error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# OPERATION MATERIALS - Besoins matière par opération
# ==========================================
@api_router.get("/operation-materials")
async def get_operation_materials():
    """Récupère tous les besoins matière des opérations."""
    materials = await db.operation_materials.find({}, {"_id": 0}).to_list(10000)
    return materials

@api_router.post("/operation-materials")
async def create_operation_material(material: OperationMaterial):
    """Crée un besoin matière pour une opération."""
    doc = material.model_dump()
    await db.operation_materials.insert_one(doc)
    return doc

@api_router.delete("/operation-materials")
async def delete_all_operation_materials():
    """Supprime tous les besoins matière."""
    result = await db.operation_materials.delete_many({})
    return {"deleted": result.deleted_count}

# ==========================================
# PLANNED SUPPLIER RECEIPTS - Réceptions fournisseurs planifiées
# ==========================================
@api_router.get("/planned-supplier-receipts")
async def get_planned_supplier_receipts():
    """Récupère toutes les réceptions fournisseurs planifiées."""
    receipts = await db.planned_supplier_receipts.find({}, {"_id": 0}).to_list(10000)
    return receipts

@api_router.post("/planned-supplier-receipts")
async def create_planned_supplier_receipt(receipt: PlannedSupplierReceipt):
    """Crée une réception fournisseur planifiée."""
    doc = receipt.model_dump()
    await db.planned_supplier_receipts.insert_one(doc)
    return doc

@api_router.delete("/planned-supplier-receipts")
async def delete_all_planned_supplier_receipts():
    """Supprime toutes les réceptions planifiées."""
    result = await db.planned_supplier_receipts.delete_many({})
    return {"deleted": result.deleted_count}

# Scenarios endpoints
@api_router.post("/scenarios", response_model=Scenario)
async def create_scenario(scenario: Scenario):
    doc = scenario.model_dump()
    await db.scenarios.insert_one(doc)
    return scenario

@api_router.get("/scenarios", response_model=List[Scenario])
async def get_scenarios():
    scenarios = await db.scenarios.find({}, {"_id": 0}).to_list(1000)
    return scenarios

@api_router.get("/scenarios/{scenario_id}", response_model=Scenario)
async def get_scenario(scenario_id: str):
    scenario = await db.scenarios.find_one({"id": scenario_id}, {"_id": 0})
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario

# DATA MANAGEMENT
@api_router.post("/data/reset")
async def reset_operational_data():
    try:
        orders_count = await db.manufacturing_orders.count_documents({})
        operations_count = await db.operations.count_documents({})
        articles_count = await db.articles.count_documents({})
        stocks_count = await db.stocks.count_documents({})
        scenarios_count = await db.scenarios.count_documents({})
        
        await db.manufacturing_orders.delete_many({})
        await db.operations.delete_many({})
        await db.articles.delete_many({})
        await db.stocks.delete_many({})
        await db.components.delete_many({})
        await db.transactions.delete_many({})
        await db.scenarios.delete_many({})
        
        logger.info("🗑️  Données opérationnelles supprimées")
        logger.info(f"   - {orders_count} ordres de fabrication")
        logger.info(f"   - {operations_count} opérations")
        logger.info(f"   - {articles_count} articles")
        logger.info(f"   - {stocks_count} stocks")
        logger.info(f"   - {scenarios_count} scénarios")
        
        return {
            "success": True,
            "message": "Données opérationnelles supprimées",
            "deleted": {
                "orders": orders_count,
                "operations": operations_count,
                "articles": articles_count,
                "stocks": stocks_count,
                "scenarios": scenarios_count
            }
        }
    except Exception as e:
        logger.error(f"Reset error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/reset-all")
async def reset_all_data():
    """
    Réinitialise TOUTES les collections de la base de données.
    Utile pour nettoyer les données incohérentes et repartir sur une base propre.
    """
    try:
        counts = {
            "manufacturing_orders": await db.manufacturing_orders.count_documents({}),
            "operations": await db.operations.count_documents({}),
            "machines": await db.machines.count_documents({}),
            "centres_de_charge": await db.centres_de_charge.count_documents({}),
            "work_centers": await db.work_centers.count_documents({}),
            "business_rules": await db.business_rules.count_documents({}),
            "articles": await db.articles.count_documents({}),
            "stocks": await db.stocks.count_documents({}),
            "calendars": await db.calendars.count_documents({}),
            "scenarios": await db.scenarios.count_documents({}),
            "unavailability": await db.unavailability.count_documents({}),
            "operation_materials": await db.operation_materials.count_documents({}),
            "planned_supplier_receipts": await db.planned_supplier_receipts.count_documents({})
        }
        
        # Supprimer TOUTES les collections
        await db.manufacturing_orders.delete_many({})
        await db.operations.delete_many({})
        await db.machines.delete_many({})
        await db.centres_de_charge.delete_many({})
        await db.work_centers.delete_many({})
        await db.business_rules.delete_many({})
        await db.articles.delete_many({})
        await db.stocks.delete_many({})
        await db.calendars.delete_many({})
        await db.scenarios.delete_many({})
        await db.unavailability.delete_many({})
        await db.components.delete_many({})
        await db.transactions.delete_many({})
        await db.operation_materials.delete_many({})
        await db.planned_supplier_receipts.delete_many({})
        
        total_deleted = sum(counts.values())
        
        logger.info("🗑️  RESET COMPLET - Toutes les collections vidées")
        for collection, count in counts.items():
            if count > 0:
                logger.info(f"   - {collection}: {count}")
        
        return {
            "success": True,
            "message": f"Reset complet: {total_deleted} documents supprimés",
            "deleted": counts
        }
    except Exception as e:
        logger.error(f"Reset all error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/data/stats", response_model=DataStats)
async def get_data_stats():
    stats = DataStats(
        manufacturing_orders=await db.manufacturing_orders.count_documents({}),
        operations=await db.operations.count_documents({}),
        articles=await db.articles.count_documents({}),
        stocks=await db.stocks.count_documents({}),
        machines=await db.machines.count_documents({}),
        work_centers=await db.work_centers.count_documents({}),
        calendars=await db.calendars.count_documents({}),
        rules=await db.business_rules.count_documents({}),
        scenarios=await db.scenarios.count_documents({})
    )
    
    last_order = await db.manufacturing_orders.find_one({}, {"_id": 0}, sort=[("id", -1)])
    if last_order:
        stats.last_import = datetime.now(timezone.utc).isoformat()
    
    return stats

# Import CSV with new structure
@api_router.post("/import/manufacturing-orders", response_model=ImportResult)
async def import_manufacturing_orders(file: UploadFile = File(...)):
    try:
        previous_count = await db.manufacturing_orders.count_documents({})
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        # Check for duplicate IDs
        if 'id' in df.columns:
            duplicate_ids = df['id'].duplicated().sum()
            if duplicate_ids > 0:
                return ImportResult(
                    success=False,
                    message=f"Erreur: {duplicate_ids} ID(s) en double dans le fichier CSV",
                    duplicates_found=duplicate_ids
                )
        
        await db.manufacturing_orders.delete_many({})
        logger.info(f"🗑️  {previous_count} anciens ordres supprimés")
        
        records = df.to_dict('records')
        for record in records:
            if 'id' not in record or pd.isna(record['id']):
                record['id'] = str(uuid.uuid4())
            else:
                record['id'] = str(record['id'])
            # Ensure article_id field
            if 'article' in record and 'article_id' not in record:
                record['article_id'] = record['article']
            await db.manufacturing_orders.insert_one(record)
        
        logger.info(f"✅ {len(records)} nouveaux ordres importés")
        
        return ImportResult(
            success=True,
            message=f"Import réussi: {len(records)} ordres (remplace {previous_count} anciens)",
            records_imported=len(records),
            previous_records=previous_count
        )
    except Exception as e:
        logger.error(f"Import error: {str(e)}", exc_info=True)
        return ImportResult(success=False, message=str(e))

@api_router.post("/import/operations", response_model=ImportResult)
async def import_operations(file: UploadFile = File(...)):
    try:
        previous_count = await db.operations.count_documents({})
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        # Check for duplicate IDs
        if 'id' in df.columns:
            duplicate_ids = df['id'].duplicated().sum()
            if duplicate_ids > 0:
                return ImportResult(
                    success=False,
                    message=f"Erreur: {duplicate_ids} ID(s) en double dans le fichier CSV",
                    duplicates_found=duplicate_ids
                )
        
        await db.operations.delete_many({})
        logger.info(f"🗑️  {previous_count} anciennes opérations supprimées")
        
        records = df.to_dict('records')
        for record in records:
            if 'id' not in record or pd.isna(record['id']):
                record['id'] = str(uuid.uuid4())
            else:
                record['id'] = str(record['id'])
            await db.operations.insert_one(record)
        
        logger.info(f"✅ {len(records)} nouvelles opérations importées")
        
        return ImportResult(
            success=True,
            message=f"Import réussi: {len(records)} opérations (remplace {previous_count} anciennes)",
            records_imported=len(records),
            previous_records=previous_count
        )
    except Exception as e:
        logger.error(f"Import error: {str(e)}", exc_info=True)
        return ImportResult(success=False, message=str(e))

@api_router.post("/import/articles", response_model=ImportResult)
async def import_articles(file: UploadFile = File(...)):
    """
    Import CSV des articles avec attributs pour règles métier.
    
    Format CSV attendu:
    id,description,type_matiere,epaisseur,couleur,largeur,longueur
    100235560,PORTE DROITE,Acier,10,blanc,500,1000
    
    Mapping CSV -> MongoDB:
    - type_matiere -> material_type
    - epaisseur -> thickness
    - couleur -> color
    - largeur -> width
    - longueur -> length
    """
    try:
        previous_count = await db.articles.count_documents({})
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        if 'id' in df.columns:
            duplicate_ids = df['id'].duplicated().sum()
            if duplicate_ids > 0:
                return ImportResult(
                    success=False,
                    message=f"Erreur: {duplicate_ids} ID(s) en double",
                    duplicates_found=duplicate_ids
                )
        
        await db.articles.delete_many({})
        logger.info(f"🗑️  {previous_count} anciens articles supprimés")
        
        # Mapping des colonnes CSV françaises vers les champs MongoDB anglais
        column_mapping = {
            'type_matiere': 'material_type',
            'epaisseur': 'thickness',
            'couleur': 'color',
            'largeur': 'width',
            'longueur': 'length'
        }
        
        records = df.to_dict('records')
        for record in records:
            # Assurer l'ID
            if 'id' not in record or pd.isna(record['id']):
                record['id'] = str(uuid.uuid4())
            else:
                record['id'] = str(record['id'])
            
            # Mapper les colonnes françaises vers anglaises
            for fr_col, en_col in column_mapping.items():
                if fr_col in record:
                    value = record.pop(fr_col)
                    # Convertir les valeurs numériques
                    if en_col in ['thickness', 'width', 'length'] and not pd.isna(value):
                        try:
                            record[en_col] = float(value)
                        except (ValueError, TypeError):
                            record[en_col] = value
                    elif not pd.isna(value):
                        record[en_col] = str(value)
            
            await db.articles.insert_one(record)
        
        logger.info(f"✅ {len(records)} nouveaux articles importés (avec attributs)")
        
        return ImportResult(
            success=True,
            message=f"Import réussi: {len(records)} articles avec attributs (remplace {previous_count} anciens)",
            records_imported=len(records),
            previous_records=previous_count
        )
    except Exception as e:
        logger.error(f"Import error: {str(e)}", exc_info=True)
        return ImportResult(success=False, message=str(e))

@api_router.post("/import/stocks", response_model=ImportResult)
async def import_stocks(file: UploadFile = File(...)):
    try:
        previous_count = await db.stocks.count_documents({})
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        await db.stocks.delete_many({})
        logger.info(f"🗑️  {previous_count} anciens stocks supprimés")
        
        records = df.to_dict('records')
        for record in records:
            if 'id' not in record or pd.isna(record.get('id')):
                record['id'] = str(uuid.uuid4())
            # Ensure article_id field
            if 'article' in record and 'article_id' not in record:
                record['article_id'] = record['article']
            await db.stocks.insert_one(record)
        
        logger.info(f"✅ {len(records)} nouveaux stocks importés")
        
        return ImportResult(
            success=True,
            message=f"Import réussi: {len(records)} stocks (remplace {previous_count} anciens)",
            records_imported=len(records),
            previous_records=previous_count
        )
    except Exception as e:
        logger.error(f"Import error: {str(e)}", exc_info=True)
        return ImportResult(success=False, message=str(e))

# Import des besoins matière par opération
@api_router.post("/import/operation-materials", response_model=ImportResult)
async def import_operation_materials(file: UploadFile = File(...)):
    """
    Import CSV des besoins matière par opération.
    Colonnes: id, order_id, operation_id, article_composant_id, quantity
    """
    try:
        previous_count = await db.operation_materials.count_documents({})
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        await db.operation_materials.delete_many({})
        logger.info(f"🗑️  {previous_count} anciens besoins matière supprimés")
        
        records = df.to_dict('records')
        for record in records:
            # Assurer le format des champs
            if 'quantity' in record:
                record['quantity'] = float(record['quantity'])
            if 'operation_id' in record:
                record['operation_id'] = int(record['operation_id'])
            await db.operation_materials.insert_one(record)
        
        logger.info(f"✅ {len(records)} besoins matière importés")
        
        return ImportResult(
            success=True,
            message=f"Import réussi: {len(records)} besoins matière (remplace {previous_count} anciens)",
            records_imported=len(records),
            previous_records=previous_count
        )
    except Exception as e:
        logger.error(f"Import error: {str(e)}", exc_info=True)
        return ImportResult(success=False, message=str(e))

# Import des réceptions fournisseurs planifiées
@api_router.post("/import/planned-supplier-receipts", response_model=ImportResult)
async def import_planned_supplier_receipts(file: UploadFile = File(...)):
    """
    Import CSV des réceptions fournisseurs planifiées.
    Colonnes: article_id, quantity, planned_date
    """
    try:
        previous_count = await db.planned_supplier_receipts.count_documents({})
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        await db.planned_supplier_receipts.delete_many({})
        logger.info(f"🗑️  {previous_count} anciennes réceptions planifiées supprimées")
        
        records = df.to_dict('records')
        for record in records:
            # Assurer le format des champs
            if 'quantity' in record:
                record['quantity'] = float(record['quantity'])
            await db.planned_supplier_receipts.insert_one(record)
        
        logger.info(f"✅ {len(records)} réceptions planifiées importées")
        
        return ImportResult(
            success=True,
            message=f"Import réussi: {len(records)} réceptions planifiées (remplace {previous_count} anciennes)",
            records_imported=len(records),
            previous_records=previous_count
        )
    except Exception as e:
        logger.error(f"Import error: {str(e)}", exc_info=True)
        return ImportResult(success=False, message=str(e))

# Scheduling with new model
@api_router.post("/scheduling/calculate")
async def calculate_schedule(request: ScheduleRequestWithOptions):
    try:
        scenario_id = request.scenario_id or str(uuid.uuid4())
        
        await db.scenarios.update_one(
            {"id": scenario_id},
            {"$set": {"status": "calculating"}},
            upsert=True
        )
        
        orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(1000)
        operations = await db.operations.find({}, {"_id": 0}).to_list(1000)
        machines = await db.machines.find({}, {"_id": 0}).to_list(1000)
        rules = await db.business_rules.find({}, {"_id": 0}).to_list(1000)
        stocks = await db.stocks.find({}, {"_id": 0}).to_list(1000)
        
        engine = SchedulerEngine(db)
        material_checker = MaterialChecker(stocks)
        rules_engine = RulesEngine(rules)
        
        options = {
            'ignore_rules': request.ignore_rules,
            'ignore_material': request.ignore_material,
            'debug_mode': request.debug_mode,
            'auto_assign_machines': request.auto_assign_machines,
            'max_solver_time_seconds': request.max_solver_time_seconds
        }
        
        schedule_result = await engine.schedule(
            orders, operations, machines, rules_engine, material_checker, options
        )
        
        await db.scenarios.update_one(
            {"id": scenario_id},
            {
                "$set": {
                    "status": "completed",
                    "schedule_data": schedule_result
                }
            },
            upsert=True
        )
        
        return {"scenario_id": scenario_id, "status": "completed", "result": schedule_result}
    except Exception as e:
        logger.error(f"Scheduling error: {str(e)}", exc_info=True)
        if request.scenario_id:
            await db.scenarios.update_one(
                {"id": request.scenario_id},
                {"$set": {"status": "error"}}
            )
        raise HTTPException(status_code=500, detail=str(e))

# Export endpoint
@api_router.get("/export/schedule/{scenario_id}")
async def export_schedule(scenario_id: str):
    scenario = await db.scenarios.find_one({"id": scenario_id}, {"_id": 0})
    if not scenario or not scenario.get('schedule_data'):
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    schedule_data = scenario['schedule_data']
    operations = schedule_data.get('operations', [])
    
    df = pd.DataFrame(operations)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    temp_file = f"/tmp/schedule_export_{scenario_id}.csv"
    with open(temp_file, 'w') as f:
        f.write(csv_buffer.getvalue())
    
    return FileResponse(
        temp_file,
        media_type='text/csv',
        filename=f'schedule_{scenario_id}.csv'
    )

# Diagnostic endpoint - Tableau complet d'assignation
@api_router.get("/diagnostic/assignment")
async def get_assignment_diagnostic():
    """
    Diagnostic complet de l'assignation des machines.
    
    Jointure opérations + ordres via order_id.
    L'article_id est récupéré depuis l'ordre pour le matching des règles.
    Les données article complètes sont utilisées pour les règles sur attributs.
    
    Format due_date: ISO 8601 (YYYY-MM-DDTHH:MM:SS ou YYYY-MM-DD)
    """
    try:
        orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(1000)
        operations_raw = await db.operations.find({}, {"_id": 0}).to_list(1000)
        machines_raw = await db.machines.find({}, {"_id": 0}).to_list(1000)
        rules = await db.business_rules.find({}, {"_id": 0}).to_list(1000)
        articles = await db.articles.find({}, {"_id": 0}).to_list(1000)
        
        # Charger les données matière pour le diagnostic
        operation_materials = await db.operation_materials.find({}, {"_id": 0}).to_list(10000)
        stocks = await db.stocks.find({}, {"_id": 0}).to_list(1000)
        planned_receipts = await db.planned_supplier_receipts.find({}, {"_id": 0}).to_list(1000)
        
        logger.info(f"\n{'='*80}")
        logger.info("DIAGNOSTIC D'ASSIGNATION")
        logger.info(f"{'='*80}")
        logger.info(f"Ordres: {len(orders)}")
        logger.info(f"Opérations: {len(operations_raw)}")
        logger.info(f"Machines: {len(machines_raw)}")
        logger.info(f"Règles: {len(rules)}")
        logger.info(f"Articles: {len(articles)}")
        logger.info(f"Besoins matière: {len(operation_materials)}")
        logger.info(f"Stocks: {len(stocks)}")
        logger.info(f"Réceptions planifiées: {len(planned_receipts)}")
        
        # Adapter la terminologie des opérations
        operations = []
        for op in operations_raw:
            operations.append({
                **op,
                'tache_id': op.get('tache_id') or op.get('task_id'),
                'centre_de_charge_id': op.get('centre_de_charge_id') or op.get('work_center_id')
            })
        
        # Adapter la terminologie des machines
        machines = []
        for m in machines_raw:
            machines.append({
                **m,
                'centre_de_charge_id': m.get('centre_de_charge_id') or m.get('work_center_id')
            })
        
        # Adapter la terminologie des règles
        adapted_rules = []
        for r in rules:
            adapted_rules.append({
                **r,
                'tache_id': r.get('tache_id') or r.get('task_id'),
                'centre_de_charge_id': r.get('centre_de_charge_id') or r.get('work_center_id')
            })
        
        # Log des règles pour debug
        logger.info("\nRègles chargées:")
        for r in adapted_rules:
            logger.info(f"  [{r.get('rule_type', 'UNKNOWN')}] {r.get('name')}")
            logger.info(f"    tache={r.get('tache_id')}, centre={r.get('centre_de_charge_id')}, article={r.get('article_id')}")
            if r.get('attribute_name'):
                logger.info(f"    attribut: {r.get('attribute_name')} {r.get('attribute_operator')} {r.get('attribute_value')}")
            logger.info(f"    -> machine={r.get('machine_id')}")
        
        # Passer les articles au moteur de règles pour les règles sur attributs
        rules_engine = RulesEngine(adapted_rules, articles)
        assigner = MachineAssigner(machines, rules_engine, articles)
        
        result = assigner.assign_machines_to_operations(operations, orders)
        
        # Enrichir le diagnostic avec les informations matière
        material_manager = MaterialManager(stocks, operation_materials, planned_receipts)
        
        # Index des ordres pour enrichissement
        orders_by_id = {o.get('id'): o for o in orders}
        
        # Ajouter le diagnostic matière à chaque opération
        for diag in result['diagnostics_table']:
            op_id = diag['operation_id']
            op_materials = material_manager.get_operation_materials(op_id)
            
            diag['material_status'] = {
                'components': [],
                'all_available': True,
                'blocking_components': []
            }
            
            if op_materials:
                for mat in op_materials:
                    stock_qty = material_manager.initial_stocks.get(mat.article_composant_id, 0)
                    is_available = stock_qty >= mat.quantity
                    
                    diag['material_status']['components'].append({
                        'article_id': mat.article_composant_id,
                        'required': mat.quantity,
                        'available': stock_qty,
                        'is_available': is_available
                    })
                    
                    if not is_available:
                        diag['material_status']['all_available'] = False
                        diag['material_status']['blocking_components'].append(mat.article_composant_id)
        
        return {
            'summary': {
                'total_operations': result['total_operations'],
                'assigned': result['assigned_count'],
                'unassigned': result['unassigned_count'],
                'preferred': result['preferred_count'],
                'late': result.get('late_count', 0),
                'urgent': result.get('urgent_count', 0),
                'failure_causes': result['failure_causes']
            },
            'machines_par_centre': {
                centre: [{'id': m.get('id')} for m in ms]
                for centre, ms in assigner.machines_by_centre.items()
            },
            'regles_chargees': [
                {
                    'name': r['name'],
                    'type': r['type'],
                    'tache_id': r.get('tache_id'),
                    'centre_de_charge_id': r.get('centre_de_charge_id'),
                    'article_id': r.get('article_id'),
                    'machine_id': r['machine_id']
                }
                for r in result['rules_diagnostics']['rules_detail']
            ],
            'diagnostics_table': result['diagnostics_table'],
            'material_info': {
                'stocks_count': len(stocks),
                'operation_materials_count': len(operation_materials),
                'planned_receipts_count': len(planned_receipts)
            }
        }
    except Exception as e:
        logger.error(f"Diagnostic error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Demo data
@api_router.post("/demo/load")
async def load_demo():
    try:
        result = await load_demo_data(db)
        return result
    except Exception as e:
        logger.error(f"Demo data error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard stats
@api_router.get("/dashboard/stats")
async def get_dashboard_stats():
    total_orders = await db.manufacturing_orders.count_documents({})
    pending_orders = await db.manufacturing_orders.count_documents({"status": "pending"})
    
    late_orders = 0
    orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(1000)
    today = datetime.now(timezone.utc)
    for order in orders:
        try:
            due_date = datetime.fromisoformat(order.get('due_date', '9999-12-31'))
            if due_date < today and order.get('status') != 'completed':
                late_orders += 1
        except:
            pass
    
    total_machines = await db.machines.count_documents({})
    
    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "late_orders": late_orders,
        "total_machines": total_machines
    }

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()