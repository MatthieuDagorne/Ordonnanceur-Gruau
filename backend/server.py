from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, status, BackgroundTasks
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
import asyncio
from concurrent.futures import ThreadPoolExecutor

from services.scheduler_engine import SchedulerEngine
from services.material_checker import MaterialChecker
from services.material_manager import MaterialManager, MaterialChecker as NewMaterialChecker
from services.rules_engine import RulesEngine
from services.machine_assigner import MachineAssigner
from services.demo_data import load_demo_data
from services.aps_engine import APSEngine, BOMExploder, CapacityPlanner
from services.erp_transformer import (
    transform_manufacturing_orders,
    transform_operations,
    transform_operation_materials,
    transform_stocks,
    transform_planned_supplier_receipts,
    transform_articles
)
from models.business_rule import BusinessRule as BusinessRuleModel

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Storage pour les jobs de calcul asynchrones
scheduling_jobs: Dict[str, Dict[str, Any]] = {}

# Thread pool pour exécuter les calculs lourds
executor = ThreadPoolExecutor(max_workers=2)


def detect_csv_separator(contents: bytes) -> str:
    """
    Détecte automatiquement le séparateur CSV.
    
    Bonnes pratiques :
    - Point-virgule (;) : Standard européen, évite les conflits avec les décimales "5,2"
    - Virgule (,) : Standard US/international, nécessite des décimales avec point "5.2"
    
    Cette fonction analyse les premières lignes pour déterminer le séparateur.
    """
    try:
        # Décoder le contenu
        text = contents.decode('utf-8')
    except UnicodeDecodeError:
        try:
            text = contents.decode('latin-1')
        except:
            text = contents.decode('utf-8', errors='ignore')
    
    # Prendre les premières lignes (header + quelques données)
    first_lines = text.split('\n')[:5]
    
    # Analyser uniquement la première ligne (header) pour éviter les faux positifs avec les décimales
    header_line = first_lines[0] if first_lines else ''
    
    # Compter les occurrences de chaque séparateur dans le header
    semicolon_count = header_line.count(';')
    comma_count = header_line.count(',')
    
    # Le séparateur avec le plus d'occurrences dans le header gagne
    # En cas d'égalité, préférer le point-virgule (standard européen)
    if semicolon_count >= comma_count and semicolon_count > 0:
        return ';'
    elif comma_count > 0:
        return ','
    
    # Fallback : point-virgule par défaut
    return ';'


def read_csv_auto(contents: bytes) -> pd.DataFrame:
    """
    Lit un CSV avec détection automatique du séparateur et de l'encodage.
    
    Gère les décimales européennes (virgule) si le séparateur est point-virgule.
    Gère le BOM UTF-8.
    """
    separator = detect_csv_separator(contents)
    
    # Si séparateur point-virgule, les décimales peuvent utiliser la virgule
    decimal_char = ',' if separator == ';' else '.'
    
    # Essayer différents encodages (utf-8-sig en premier pour gérer le BOM)
    for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv(
                io.BytesIO(contents), 
                sep=separator, 
                encoding=encoding,
                decimal=decimal_char
            )
            logger.info(f"📄 CSV lu avec séparateur '{separator}', décimales '{decimal_char}', encodage '{encoding}'")
            return df
        except Exception:
            continue
    
    # Fallback sans conversion décimale
    logger.warning(f"⚠️ CSV fallback: lecture basique avec séparateur '{separator}'")
    return pd.read_csv(io.BytesIO(contents), sep=separator)

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
    start_hour: int = Field(default=8)  # Kept for backward compatibility
    end_hour: int = Field(default=17)   # Kept for backward compatibility
    start_time: str = Field(default="08:00")  # New: HH:MM format
    end_time: str = Field(default="17:00")    # New: HH:MM format

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
    
    TEMPS DE DÉPLACEMENT:
    - transfer_time_minutes: temps nécessaire pour déplacer la pièce vers le poste suivant
    - Ce temps est ajouté APRÈS la fin de l'opération, avant le début de l'opération suivante
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
    transfer_time_minutes: int = 0  # Temps de déplacement vers le poste suivant
    
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
    """
    Options avancées pour l'ordonnancement APS.
    """
    scenario_id: Optional[str] = None
    scenario_name: Optional[str] = None
    
    # Stratégie de planification
    scheduling_strategy: str = "ASAP"  # "ASAP" (au plus tôt) ou "JIT" (au plus tard)
    
    # Horizon de planification
    horizon_days: int = 14  # Horizon en jours (0 = tous les ordres)
    
    # Contraintes à ignorer (debug)
    ignore_rules: bool = False
    ignore_material: bool = False
    ignore_calendars: bool = False
    ignore_priorities: bool = False   # Ignorer les priorités des OF
    
    # Propagations à ignorer (debug)
    ignore_priority_propagation: bool = False  # Ignorer la propagation de priorité vers fournisseurs
    ignore_material_propagation: bool = False  # Ignorer la propagation matière (dépendances)
    
    # Paramètres solveur
    max_solver_time_seconds: int = 60
    optimization_gap: float = 0.05    # Gap d'optimalité acceptable (5% par défaut)
    
    # Options avancées
    debug_mode: bool = True
    auto_assign_machines: bool = True
    allow_splitting: bool = True      # Permettre le fractionnement des opérations longues
    respect_sequence: bool = True     # Respecter l'ordre des opérations dans l'OF

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
    machines: int = 0
    work_centers: int = 0
    calendars: int = 0
    rules: int = 0
    scenarios: int = 0
    operation_materials: int = 0     # Matières par opération
    planned_receipts: int = 0        # Réceptions fournisseurs planifiées
    bom_lines: int = 0               # Lignes de nomenclature
    unavailabilities: int = 0        # Indisponibilités machines
    last_import: Optional[str] = None

# ==================================================
# MODÈLES APS - Advanced Planning & Scheduling
# ==================================================

class BOMLine(BaseModel):
    """Ligne de nomenclature (Bill of Materials)."""
    model_config = ConfigDict(extra="ignore")
    parent_article_id: str      # Article parent (produit fini ou semi-fini)
    child_article_id: str       # Article composant
    quantity: float             # Quantité nécessaire par unité du parent
    level: int = 1              # Niveau de nomenclature (1=composant direct)
    unit: str = "pièce"         # Unité de mesure
    scrap_rate: float = 0.0     # Taux de rebut (ex: 0.02 = 2%)

class MRPResult(BaseModel):
    """Résultat du calcul MRP."""
    article_id: str
    gross_requirement: float     # Besoin brut
    on_hand: float               # Stock disponible
    scheduled_receipts: float    # Réceptions planifiées
    net_requirement: float       # Besoin net
    planned_orders: List[Dict]   # Ordres planifiés
    shortage_date: Optional[str] # Date de première rupture
    level: int                   # Niveau BOM

class CapacitySlot(BaseModel):
    """Créneau de capacité machine."""
    machine_id: str
    date: str
    start_time: str
    end_time: str
    capacity_minutes: int        # Capacité disponible
    loaded_minutes: int          # Charge planifiée
    utilization_rate: float      # Taux d'utilisation
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

@api_router.put("/machines/{machine_id}")
async def update_machine(machine_id: str, updates: Dict[str, Any]):
    """Met à jour une machine existante."""
    allowed_fields = {'nom', 'name', 'centre_de_charge_id', 'work_center_id', 'description'}
    update_data = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    
    result = await db.machines.update_one(
        {"id": machine_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Machine non trouvée")
    
    # Retourner la machine mise à jour
    updated_machine = await db.machines.find_one({"id": machine_id}, {"_id": 0})
    return updated_machine

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

@api_router.get("/calendars/{calendar_id}", response_model=Calendar)
async def get_calendar(calendar_id: str):
    calendar = await db.calendars.find_one({"id": calendar_id}, {"_id": 0})
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")
    return calendar

@api_router.put("/calendars/{calendar_id}", response_model=Calendar)
async def update_calendar(calendar_id: str, calendar: Calendar):
    # Vérifier que le calendrier existe
    existing = await db.calendars.find_one({"id": calendar_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Calendar not found")
    
    # Mettre à jour
    update_data = calendar.model_dump()
    update_data["id"] = calendar_id  # Garder l'ID original
    await db.calendars.replace_one({"id": calendar_id}, update_data)
    return Calendar(**update_data)

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

@api_router.put("/unavailability/{unavailability_id}")
async def update_unavailability(unavailability_id: str, updates: Dict[str, Any]):
    """Met à jour une indisponibilité existante."""
    allowed_fields = {'machine_id', 'start_date', 'end_date', 'reason'}
    update_data = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    
    result = await db.unavailability.update_one(
        {"id": unavailability_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Indisponibilité non trouvée")
    
    # Retourner l'indisponibilité mise à jour
    updated = await db.unavailability.find_one({"id": unavailability_id}, {"_id": 0})
    return updated

# Business Rules endpoints
@api_router.post("/rules")
async def create_rule(rule: Dict[str, Any]):
    """Créer une règle métier avec support des conditions multiples ET/OU."""
    import uuid
    
    doc = dict(rule)
    if not doc.get('id'):
        doc['id'] = str(uuid.uuid4())
    
    if 'rule_type' in doc and doc['rule_type']:
        doc['rule_type'] = doc['rule_type'].upper()
    
    await db.business_rules.insert_one(doc)
    
    # Retourner tous les champs
    return {
        'id': doc.get('id'),
        'name': doc.get('name'),
        'tache_id': doc.get('tache_id'),
        'centre_de_charge_id': doc.get('centre_de_charge_id'),
        'article_id': doc.get('article_id'),
        'attribute_name': doc.get('attribute_name'),
        'attribute_operator': doc.get('attribute_operator'),
        'attribute_value': doc.get('attribute_value'),
        'attribute_conditions': doc.get('attribute_conditions'),
        'conditions_logic': doc.get('conditions_logic', 'AND'),
        'rule_type': doc.get('rule_type', 'ALLOW').upper(),
        'machine_id': doc.get('machine_id'),
        'active': doc.get('active', True)
    }

@api_router.get("/rules")
async def get_rules():
    """Liste toutes les règles métier avec tous les attributs."""
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
                'tache_id': rule.get('tache_id') or rule.get('task_id'),
                'centre_de_charge_id': rule.get('centre_de_charge_id') or rule.get('work_center_id'),
                'article_id': rule.get('article_id'),
                # Attribut unique (rétro-compatibilité)
                'attribute_name': rule.get('attribute_name'),
                'attribute_operator': rule.get('attribute_operator'),
                'attribute_value': rule.get('attribute_value'),
                # Attributs multiples avec ET/OU
                'attribute_conditions': rule.get('attribute_conditions'),
                'conditions_logic': rule.get('conditions_logic', 'AND'),
                'rule_type': rule_type,
                'machine_id': rule.get('machine_id'),
                'active': rule.get('active', True)
            })
    return valid_rules

@api_router.get("/rules/{rule_id}")
async def get_rule(rule_id: str):
    """Récupère une règle métier par son ID."""
    rule = await db.business_rules.find_one({"id": rule_id}, {"_id": 0})
    if not rule:
        raise HTTPException(status_code=404, detail="Règle non trouvée")
    return rule

@api_router.put("/rules/{rule_id}")
async def update_rule(rule_id: str, updates: Dict[str, Any]):
    """
    Met à jour une règle métier existante.
    
    Champs modifiables:
    - name, tache_id, centre_de_charge_id, article_id
    - attribute_name, attribute_operator, attribute_value (rétro-compatibilité)
    - attribute_conditions, conditions_logic (nouveau: ET/OU)
    - rule_type, machine_id, active
    """
    allowed_fields = {
        'name', 'tache_id', 'centre_de_charge_id', 'article_id',
        'attribute_name', 'attribute_operator', 'attribute_value',
        'attribute_conditions', 'conditions_logic',
        'rule_type', 'machine_id', 'active'
    }
    update_data = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour")
    
    # Normaliser rule_type en majuscules
    if 'rule_type' in update_data and update_data['rule_type']:
        update_data['rule_type'] = update_data['rule_type'].upper()
    
    result = await db.business_rules.update_one(
        {"id": rule_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Règle non trouvée")
    
    # Retourner la règle mise à jour
    updated_rule = await db.business_rules.find_one({"id": rule_id}, {"_id": 0})
    return updated_rule

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
    orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(10000)
    return orders


@api_router.put("/manufacturing-orders/{order_id}")
async def update_manufacturing_order(order_id: str, order: ManufacturingOrder):
    """Met à jour un ordre de fabrication."""
    existing = await db.manufacturing_orders.find_one({"id": order_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Ordre de fabrication non trouvé")
    
    order_dict = order.model_dump()
    order_dict['id'] = order_id  # S'assurer que l'ID reste le même
    
    await db.manufacturing_orders.update_one(
        {"id": order_id},
        {"$set": order_dict}
    )
    
    return order_dict


@api_router.get("/operations")
async def get_operations():
    """Retourne toutes les opérations avec terminologie française."""
    operations = await db.operations.find({}, {"_id": 0}).to_list(10000)
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
            'transfer_time_minutes': op.get('transfer_time_minutes', 0),  # Temps de déplacement
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
    orders_raw = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(10000)
    operations_raw = await db.operations.find({}, {"_id": 0}).to_list(10000)
    
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
        orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(10000)
        operations = await db.operations.find({}, {"_id": 0}).to_list(10000)
        
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
            # Le champ est 'due_quantity' (ou 'quantity' pour compatibilité)
            qty = mat.get('due_quantity') or mat.get('quantity', 0)
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
        
        # Collecter tous les articles concernés (filtrer les None)
        all_articles = set(stock_by_article.keys()) | set(consumption_by_article.keys()) | set(receipts_by_article.keys())
        all_articles = {a for a in all_articles if a is not None}
        
        for article_id in sorted(all_articles, key=lambda x: str(x)):
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
# STOCK PROJETE PAR SCENARIO - Timeline détaillée
# ==========================================
@api_router.get("/projected-stock/{scenario_id}")
async def get_projected_stock_by_scenario(scenario_id: str, article_id: Optional[str] = None):
    """
    Calcule le stock projeté dans le contexte d'un scénario d'ordonnancement spécifique.
    
    LOGIQUE MATIÈRE TEMPORELLE:
    - Utilise les opérations planifiées du scénario pour déterminer les dates de consommation exactes
    - Affiche une timeline d'événements (réceptions et consommations) pour chaque article
    - Permet de diagnostiquer pourquoi le moteur a reporté certaines opérations
    
    Paramètres:
    - scenario_id: ID du scénario d'ordonnancement
    - article_id: (optionnel) Filtrer par article spécifique
    
    Returns:
    - projected_stock: Liste des articles avec leur projection
    - timeline: Événements triés chronologiquement
    - scenario_info: Informations sur le scénario
    """
    try:
        # Récupérer le scénario
        scenario = await db.scenarios.find_one({"id": scenario_id}, {"_id": 0})
        if not scenario:
            raise HTTPException(status_code=404, detail="Scénario non trouvé")
        
        # Récupérer les données de base
        stocks = await db.stocks.find({}, {"_id": 0}).to_list(1000)
        operation_materials = await db.operation_materials.find({}, {"_id": 0}).to_list(10000)
        planned_receipts = await db.planned_supplier_receipts.find({}, {"_id": 0}).to_list(1000)
        
        # Extraire les opérations planifiées du scénario
        schedule_data = scenario.get('schedule_data', {})
        scheduled_operations = schedule_data.get('operations', [])
        scheduling_start = schedule_data.get('scheduling_start')
        
        # Index des opérations planifiées par ID
        scheduled_ops_by_id = {op.get('operation_id'): op for op in scheduled_operations}
        
        # Stock initial par article
        stock_by_article = {s.get('article_id'): s.get('quantity', 0) for s in stocks}
        
        # Construire la timeline d'événements
        all_events = []
        articles_set = set()
        
        # 1. Ajouter les réceptions fournisseurs comme événements
        for receipt in planned_receipts:
            art_id = receipt.get('article_id')
            if article_id and art_id != article_id:
                continue
            articles_set.add(art_id)
            all_events.append({
                'type': 'RECEIPT',
                'article_id': art_id,
                'quantity': receipt.get('quantity', 0),
                'datetime': receipt.get('planned_date'),
                'reference': "Réception fournisseur",
                'details': {
                    'source': 'planned_supplier_receipts'
                }
            })
        
        # 2. Ajouter les productions (entrées en stock des articles fabriqués)
        # Ces productions sont générées par le moteur d'ordonnancement
        productions = schedule_data.get('productions', [])
        for prod in productions:
            art_id = prod.get('article_id')
            if article_id and art_id != article_id:
                continue
            articles_set.add(art_id)
            all_events.append({
                'type': 'PRODUCTION_RECEIPT',
                'article_id': art_id,
                'quantity': prod.get('quantity', 0),  # Positif car entrée en stock
                'datetime': prod.get('end_datetime'),  # Fin de dernière op + transfert
                'reference': f"Fabrication OF {prod.get('order_id')}",
                'details': {
                    'source': 'production',
                    'order_id': prod.get('order_id'),
                    'operation_end_datetime': prod.get('operation_end_datetime'),
                    'transfer_time_minutes': prod.get('transfer_time_minutes', 0)
                }
            })
        
        # 4. Ajouter les consommations des opérations planifiées
        for mat in operation_materials:
            art_id = mat.get('article_composant_id')
            if article_id and art_id != article_id:
                continue
            articles_set.add(art_id)
            
            op_id = mat.get('id')
            order_id = mat.get('order_id')
            qty = mat.get('due_quantity') or mat.get('quantity', 0)
            
            # Récupérer la date de l'opération depuis le scénario
            scheduled_op = scheduled_ops_by_id.get(op_id, {})
            consumption_datetime = scheduled_op.get('start_datetime')
            
            if not consumption_datetime:
                # Opération non planifiée dans ce scénario - marquer comme "à planifier"
                consumption_datetime = None
            
            all_events.append({
                'type': 'CONSUMPTION',
                'article_id': art_id,
                'quantity': -qty,  # Négatif car sortie de stock
                'datetime': consumption_datetime,
                'reference': f"Op {op_id} (OF {order_id})",
                'details': {
                    'operation_id': op_id,
                    'order_id': order_id,
                    'is_scheduled': consumption_datetime is not None,
                    'machine_id': scheduled_op.get('machine_id')
                }
            })
        
        # Trier les événements par datetime (les None à la fin)
        def sort_key(e):
            dt = e.get('datetime')
            if dt is None:
                return ('9999-99-99', e.get('article_id', ''))
            return (dt, e.get('article_id', ''))
        
        all_events.sort(key=sort_key)
        
        # Calculer le stock projeté par article
        projected_stock = []
        
        for art_id in sorted(articles_set):
            initial_stock = stock_by_article.get(art_id, 0)
            
            # Filtrer les événements pour cet article
            article_events = [e for e in all_events if e.get('article_id') == art_id]
            
            # Simuler l'évolution du stock
            current_stock = initial_stock
            timeline = []
            has_shortage = False
            first_shortage_datetime = None
            min_stock = initial_stock
            
            for event in article_events:
                prev_stock = current_stock
                current_stock += event.get('quantity', 0)
                
                timeline.append({
                    'datetime': event.get('datetime'),
                    'type': event.get('type'),
                    'quantity_change': event.get('quantity'),
                    'stock_before': prev_stock,
                    'stock_after': current_stock,
                    'reference': event.get('reference'),
                    'is_scheduled': event.get('details', {}).get('is_scheduled', True)
                })
                
                if current_stock < 0 and not has_shortage:
                    has_shortage = True
                    first_shortage_datetime = event.get('datetime')
                
                min_stock = min(min_stock, current_stock)
            
            # Calculer les totaux
            total_receipts_supplier = sum(e.get('quantity', 0) for e in article_events if e.get('type') == 'RECEIPT')
            total_receipts_production = sum(e.get('quantity', 0) for e in article_events if e.get('type') == 'PRODUCTION_RECEIPT')
            total_receipts = total_receipts_supplier + total_receipts_production
            total_consumptions = abs(sum(e.get('quantity', 0) for e in article_events if e.get('type') == 'CONSUMPTION'))
            
            projected_stock.append({
                'article_id': art_id,
                'initial_stock': initial_stock,
                'total_receipts': total_receipts,
                'total_receipts_supplier': total_receipts_supplier,
                'total_receipts_production': total_receipts_production,
                'total_consumptions': total_consumptions,
                'final_stock': current_stock,
                'min_stock': min_stock,
                'has_shortage': has_shortage,
                'first_shortage_datetime': first_shortage_datetime,
                'timeline': timeline,
                'events_count': len(article_events)
            })
        
        # Trier par rupture puis par article
        projected_stock.sort(key=lambda x: (0 if x['has_shortage'] else 1, x['article_id']))
        
        return {
            'scenario_id': scenario_id,
            'scenario_name': scenario.get('name'),
            'scenario_status': schedule_data.get('status'),
            'scheduling_start': scheduling_start,
            'operations_count': len(scheduled_operations),
            'projected_stock': projected_stock,
            'summary': {
                'total_articles': len(projected_stock),
                'articles_with_shortage': len([p for p in projected_stock if p['has_shortage']]),
                'articles_ok': len([p for p in projected_stock if not p['has_shortage']]),
                'total_events': len(all_events)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Projected stock by scenario error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# APS - Advanced Planning & Scheduling
# ==========================================

@api_router.get("/aps/mrp")
async def get_mrp():
    """
    Calcul MRP (Material Requirements Planning).
    
    Explose les nomenclatures et calcule les besoins nets en composants
    en tenant compte du stock et des réceptions planifiées.
    """
    try:
        aps_engine = APSEngine(db)
        
        # Récupérer les opérations ordonnancées pour les dates de consommation
        operations = await db.operations.find({}, {"_id": 0}).to_list(10000)
        scheduled_ops = [op for op in operations if op.get('scheduled_start')]
        
        result = await aps_engine.run_mrp(scheduled_operations=scheduled_ops)
        return result
    except Exception as e:
        logger.error(f"MRP calculation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/aps/capacity")
async def get_capacity(horizon_days: int = 7):
    """
    Calcul de capacité finie.
    
    Retourne la charge vs capacité par machine en tenant compte:
    - Calendriers des centres de charge
    - production_time_minutes et setup_time_minutes des opérations
    """
    try:
        aps_engine = APSEngine(db)
        
        # Récupérer les opérations avec temps
        operations = await db.operations.find({}, {"_id": 0}).to_list(10000)
        
        result = await aps_engine.calculate_capacity(
            operations=operations,
            horizon_days=horizon_days
        )
        return result
    except Exception as e:
        logger.error(f"Capacity calculation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/aps/kpis")
async def get_aps_kpis():
    """
    KPIs APS - Indicateurs de performance.
    
    Retourne:
    - OTD (On-Time Delivery): % des ordres livrés à temps
    - Utilisation machines: % de capacité utilisée
    - WIP (Work In Progress): ordres en cours
    - Retards: ordres en retard avec détail
    """
    try:
        orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(10000)
        operations = await db.operations.find({}, {"_id": 0}).to_list(10000)
        machines = await db.machines.find({}, {"_id": 0}).to_list(100)
        
        now = datetime.now()
        now_iso = now.isoformat()
        
        # Calcul OTD
        total_orders = len(orders)
        on_time_orders = 0
        late_orders = []
        
        for order in orders:
            due_date = order.get('due_date')
            status = order.get('status', 'pending')
            
            if status == 'completed':
                on_time_orders += 1
            elif due_date:
                try:
                    due_dt = datetime.fromisoformat(due_date.replace('Z', '+00:00').replace('+00:00', ''))
                    if due_dt < now:
                        late_orders.append({
                            'order_id': order.get('id'),
                            'article_id': order.get('article_id'),
                            'due_date': due_date,
                            'delay_hours': round((now - due_dt).total_seconds() / 3600, 1)
                        })
                except (ValueError, AttributeError):
                    pass
        
        otd_rate = (on_time_orders / total_orders * 100) if total_orders > 0 else 0
        
        # Calcul utilisation machines (sur horizon 7 jours)
        aps_engine = APSEngine(db)
        capacity_result = await aps_engine.calculate_capacity(operations=operations, horizon_days=7)
        
        total_capacity = sum(s['capacity_minutes'] for s in capacity_result.get('capacity_slots', []))
        total_loaded = sum(s['loaded_minutes'] for s in capacity_result.get('capacity_slots', []))
        overall_utilization = (total_loaded / total_capacity * 100) if total_capacity > 0 else 0
        
        # WIP
        wip_orders = [o for o in orders if o.get('status') in ['pending', 'in_progress']]
        scheduled_ops = [op for op in operations if op.get('scheduled_start')]
        
        return {
            'otd': {
                'rate': round(otd_rate, 1),
                'on_time': on_time_orders,
                'total': total_orders
            },
            'late_orders': {
                'count': len(late_orders),
                'orders': sorted(late_orders, key=lambda x: x.get('delay_hours', 0), reverse=True)[:10]
            },
            'utilization': {
                'overall_rate': round(overall_utilization, 1),
                'capacity_hours': round(total_capacity / 60, 1),
                'loaded_hours': round(total_loaded / 60, 1),
                'by_machine': capacity_result.get('summary_by_machine', {})
            },
            'wip': {
                'orders_count': len(wip_orders),
                'operations_scheduled': len(scheduled_ops),
                'operations_total': len(operations)
            },
            'timestamp': now_iso
        }
    except Exception as e:
        logger.error(f"KPIs calculation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/aps/bom")
async def get_bom():
    """Liste toutes les lignes de nomenclature."""
    bom = await db.bom.find({}, {"_id": 0}).to_list(10000)
    return bom

@api_router.post("/aps/bom")
async def create_bom_line(line: BOMLine):
    """Crée une ligne de nomenclature."""
    doc = line.model_dump()
    await db.bom.insert_one(doc)
    return doc

@api_router.delete("/aps/bom")
async def delete_all_bom():
    """Supprime toutes les lignes de nomenclature."""
    result = await db.bom.delete_many({})
    return {"deleted": result.deleted_count}

@api_router.post("/aps/bom/explode")
async def explode_bom(article_id: str, quantity: float = 1.0):
    """
    Explose la nomenclature pour un article donné.
    
    Retourne la liste complète des composants nécessaires
    à travers tous les niveaux de la nomenclature.
    """
    try:
        bom_lines = await db.bom.find({}, {"_id": 0}).to_list(10000)
        exploder = BOMExploder(bom_lines)
        
        explosion = exploder.explode(article_id, quantity)
        totals = exploder.get_all_components(article_id, quantity)
        
        return {
            'article_id': article_id,
            'quantity': quantity,
            'explosion_detail': explosion,
            'components_total': totals,
            'total_components': len(totals)
        }
    except Exception as e:
        logger.error(f"BOM explosion error: {str(e)}", exc_info=True)
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
    try:
        scenarios = await db.scenarios.find({}, {"_id": 0}).to_list(1000)
        return scenarios
    except Exception as e:
        logger.error(f"Erreur lors du chargement des scénarios: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur de base de données: {str(e)}")

# IMPORTANT: Cette route doit être AVANT /scenarios/{scenario_id}
@api_router.get("/scenarios/compare")
async def compare_scenarios_inline(ids: str):
    """Compare plusieurs scénarios par leurs IDs (séparés par des virgules)."""
    try:
        scenario_ids = [s.strip() for s in ids.split(',') if s.strip()]
        
        if len(scenario_ids) < 2:
            raise HTTPException(status_code=400, detail="Au moins 2 scénarios requis")
        
        scenarios = []
        for sid in scenario_ids:
            scenario = await db.scenarios.find_one({"id": sid}, {"_id": 0})
            if scenario:
                scenarios.append(scenario)
        
        if len(scenarios) < 2:
            raise HTTPException(status_code=404, detail="Scénarios introuvables")
        
        comparison = []
        for scenario in scenarios:
            schedule_data = scenario.get('schedule_data', {})
            operations = schedule_data.get('operations', [])
            conflicts = schedule_data.get('conflicts', [])
            
            total_ops = len(operations)
            total_conflicts = len(conflicts)
            
            if operations:
                min_start = min(op.get('start_minutes', 0) for op in operations)
                max_end = max(op.get('end_minutes', 0) for op in operations)
                makespan = max_end - min_start
            else:
                makespan = 0
            
            machine_usage = {}
            for op in operations:
                machine_id = op.get('machine_id')
                duration = op.get('duration_minutes', 0)
                if machine_id:
                    machine_usage[machine_id] = machine_usage.get(machine_id, 0) + duration
            
            late_count = 0
            for op in operations:
                end_dt = op.get('end_datetime')
                due_date = op.get('date_besoin')
                if end_dt and due_date:
                    try:
                        end = datetime.fromisoformat(end_dt.replace('Z', '+00:00'))
                        due = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                        if end > due:
                            late_count += 1
                    except:
                        pass
            
            comparison.append({
                'scenario_id': scenario.get('id'),
                'scenario_name': scenario.get('name'),
                'status': schedule_data.get('status'),
                'created_at': scenario.get('created_at'),
                'metrics': {
                    'operations_scheduled': total_ops,
                    'conflicts': total_conflicts,
                    'makespan_minutes': makespan,
                    'makespan_hours': round(makespan / 60, 2),
                    'late_operations': late_count,
                    'machines_used': len(machine_usage),
                    'solver_time': schedule_data.get('solver_time', 0)
                }
            })
        
        best = {
            'least_conflicts': min(comparison, key=lambda x: x['metrics']['conflicts'])['scenario_id'],
            'shortest_makespan': min(comparison, key=lambda x: x['metrics']['makespan_minutes'])['scenario_id'],
            'least_late': min(comparison, key=lambda x: x['metrics']['late_operations'])['scenario_id'],
            'fastest_solve': min(comparison, key=lambda x: x['metrics']['solver_time'])['scenario_id']
        }
        
        return {
            'scenarios': comparison,
            'best': best,
            'comparison_count': len(comparison)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing scenarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/scenarios/{scenario_id}")
async def delete_scenario_inline(scenario_id: str):
    """Supprime un scénario par son ID."""
    result = await db.scenarios.delete_one({"id": scenario_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Scénario non trouvé")
    return {"status": "deleted", "id": scenario_id}


@api_router.delete("/scenarios")
async def delete_all_scenarios():
    """Supprime TOUS les scénarios."""
    count = await db.scenarios.count_documents({})
    result = await db.scenarios.delete_many({})
    return {
        "status": "deleted",
        "deleted_count": result.deleted_count,
        "message": f"{result.deleted_count} scénario(s) supprimé(s)"
    }


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
        work_centers=await db.centres_de_charge.count_documents({}),
        calendars=await db.calendars.count_documents({}),
        rules=await db.business_rules.count_documents({}),
        scenarios=await db.scenarios.count_documents({}),
        operation_materials=await db.operation_materials.count_documents({}),
        planned_receipts=await db.planned_supplier_receipts.count_documents({}),
        bom_lines=await db.bom_lines.count_documents({}),
        unavailabilities=await db.machine_unavailabilities.count_documents({})
    )
    
    last_order = await db.manufacturing_orders.find_one({}, {"_id": 0}, sort=[("id", -1)])
    if last_order:
        stats.last_import = datetime.now(timezone.utc).isoformat()
    
    return stats

# Import CSV with new structure
@api_router.post("/import/manufacturing-orders", response_model=ImportResult)
async def import_manufacturing_orders(file: UploadFile = File(...)):
    """
    Import CSV des ordres de fabrication (format ERP).
    
    Colonnes ERP supportées:
    - OrdreFabrication, Article, QuantiteOrdre, QuantiteLivree
    - StatutOrdre, DateLivraisonRequise, CodePlanificateur, Priorite
    """
    try:
        previous_count = await db.manufacturing_orders.count_documents({})
        contents = await file.read()
        df = read_csv_auto(contents)
        
        logger.info(f"📥 Import OF: colonnes détectées = {df.columns.tolist()}")
        
        # Détecter le format (ERP ou interne)
        is_erp_format = 'OrdreFabrication' in df.columns
        
        if is_erp_format:
            logger.info("📄 Format ERP détecté - transformation en cours...")
            records = transform_manufacturing_orders(df)
        else:
            # Format interne (ancien format)
            logger.info("📄 Format interne détecté")
            records = df.to_dict('records')
            for record in records:
                if 'id' not in record or pd.isna(record.get('id')):
                    record['id'] = str(uuid.uuid4())
                else:
                    record['id'] = str(record['id'])
                if 'article' in record and 'article_id' not in record:
                    record['article_id'] = record['article']
        
        # Vérifier les doublons
        ids = [r['id'] for r in records]
        if len(ids) != len(set(ids)):
            duplicates = len(ids) - len(set(ids))
            return ImportResult(
                success=False,
                message=f"Erreur: {duplicates} ID(s) en double après transformation",
                duplicates_found=duplicates
            )
        
        await db.manufacturing_orders.delete_many({})
        logger.info(f"🗑️  {previous_count} anciens ordres supprimés")
        
        if records:
            await db.manufacturing_orders.insert_many(records)
        
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


async def _create_missing_centres_de_charge(df: pd.DataFrame, db) -> int:
    """
    Crée automatiquement les centres de charge manquants à partir des données d'opérations ERP.
    
    Args:
        df: DataFrame des opérations avec colonnes 'CentreDeCharge' et 'DescriptionCentreDeCharge'
        db: Base de données
    
    Returns:
        Nombre de centres de charge créés
    
    Notes:
        - Ne modifie pas les centres de charge existants
        - Crée seulement si le centre n'existe pas
        - Utilise DescriptionCentreDeCharge si disponible
    """
    if 'CentreDeCharge' not in df.columns:
        return 0
    
    # Obtenir les centres de charge uniques du CSV
    unique_centres = df[['CentreDeCharge']].drop_duplicates()
    
    # Ajouter la description si disponible
    if 'DescriptionCentreDeCharge' in df.columns:
        # Prendre la première description non vide pour chaque centre
        centre_descriptions = df.dropna(subset=['DescriptionCentreDeCharge'])[['CentreDeCharge', 'DescriptionCentreDeCharge']].drop_duplicates('CentreDeCharge')
        unique_centres = unique_centres.merge(centre_descriptions, on='CentreDeCharge', how='left')
    
    centres_created = 0
    
    for _, row in unique_centres.iterrows():
        centre_id = str(row['CentreDeCharge']) if pd.notna(row['CentreDeCharge']) else None
        if not centre_id:
            continue
        
        # Vérifier si le centre existe déjà
        existing = await db.centres_de_charge.find_one({"id": centre_id})
        if existing:
            continue  # Ne pas écraser un centre existant
        
        # Créer le nouveau centre de charge
        description = ''
        if 'DescriptionCentreDeCharge' in row and pd.notna(row.get('DescriptionCentreDeCharge')):
            description = str(row['DescriptionCentreDeCharge'])
        
        new_centre = {
            "id": centre_id,
            "nom": description or centre_id,  # Utiliser la description comme nom si disponible
            "description": description,
            "calendar_id": None,  # À compléter manuellement
            "capacite_horaire": 1.0,
            "auto_created": True  # Marqueur pour savoir que c'est une création automatique
        }
        
        await db.centres_de_charge.insert_one(new_centre)
        logger.info(f"   🏭 Centre de charge créé: {centre_id} ({description or 'sans description'})")
        centres_created += 1
    
    return centres_created


async def _create_missing_centres_from_internal_format(df: pd.DataFrame, db) -> int:
    """
    Crée automatiquement les centres de charge manquants à partir du format interne.
    
    Args:
        df: DataFrame des opérations avec colonne 'centre_de_charge_id'
        db: Base de données
    
    Returns:
        Nombre de centres de charge créés
    """
    if 'centre_de_charge_id' not in df.columns:
        return 0
    
    unique_centres = df['centre_de_charge_id'].dropna().unique()
    centres_created = 0
    
    for centre_id in unique_centres:
        centre_id = str(centre_id)
        
        # Vérifier si le centre existe déjà
        existing = await db.centres_de_charge.find_one({"id": centre_id})
        if existing:
            continue
        
        new_centre = {
            "id": centre_id,
            "nom": centre_id,
            "description": "",
            "calendar_id": None,
            "capacite_horaire": 1.0,
            "auto_created": True
        }
        
        await db.centres_de_charge.insert_one(new_centre)
        logger.info(f"   🏭 Centre de charge créé: {centre_id}")
        centres_created += 1
    
    return centres_created


@api_router.post("/import/operations", response_model=ImportResult)
async def import_operations(file: UploadFile = File(...)):
    """
    Import CSV des opérations (format ERP).
    
    Colonnes ERP supportées:
    - OrdreFabrication, Operation, OperationSuivante, Tache, DescriptionTache
    - CentreDeCharge, DescriptionCentreDeCharge, TempsPreparation, TempsCycle
    - TempsDeplacement, UniteTemps, QuantitePlanifiee, QuantiteAchevee, StatutOperation
    
    Calcul automatique:
    - id = order_id + "_" + operation_seq
    - production_time_minutes = run_time_unit × remaining_quantity
    - transfer_time_minutes converti selon l'unité (Jours×1440, Heures×60)
    
    NOUVEAU: Création automatique des centres de charge manquants
    """
    try:
        previous_count = await db.operations.count_documents({})
        contents = await file.read()
        df = read_csv_auto(contents)
        
        logger.info(f"📥 Import opérations: colonnes détectées = {df.columns.tolist()}")
        
        # Détecter le format (ERP ou interne)
        is_erp_format = 'OrdreFabrication' in df.columns and 'Operation' in df.columns
        
        if is_erp_format:
            logger.info("📄 Format ERP détecté - transformation en cours...")
            records = transform_operations(df)
            
            # NOUVEAU: Créer automatiquement les centres de charge manquants
            centres_created = await _create_missing_centres_de_charge(df, db)
            if centres_created > 0:
                logger.info(f"🏭 {centres_created} centres de charge créés automatiquement")
        else:
            # Format interne (ancien format)
            logger.info("📄 Format interne détecté")
            records = df.to_dict('records')
            for record in records:
                if 'id' not in record or pd.isna(record.get('id')):
                    record['id'] = str(uuid.uuid4())
                else:
                    record['id'] = str(record['id'])
                if 'transfer_time_minutes' not in record or pd.isna(record.get('transfer_time_minutes')):
                    record['transfer_time_minutes'] = 0
                else:
                    record['transfer_time_minutes'] = int(record['transfer_time_minutes'])
            
            # Créer les centres de charge à partir du champ centre_de_charge_id si présent
            if 'centre_de_charge_id' in df.columns:
                centres_created = await _create_missing_centres_from_internal_format(df, db)
                if centres_created > 0:
                    logger.info(f"🏭 {centres_created} centres de charge créés automatiquement")
        
        # Vérifier les doublons
        ids = [r['id'] for r in records]
        if len(ids) != len(set(ids)):
            duplicates = len(ids) - len(set(ids))
            return ImportResult(
                success=False,
                message=f"Erreur: {duplicates} ID(s) en double après transformation",
                duplicates_found=duplicates
            )
        
        await db.operations.delete_many({})
        logger.info(f"🗑️  {previous_count} anciennes opérations supprimées")
        
        if records:
            await db.operations.insert_many(records)
        
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


@api_router.get("/articles")
async def get_articles():
    """Retourne tous les articles avec leurs attributs."""
    articles = await db.articles.find({}, {"_id": 0}).to_list(1000)
    return articles


@api_router.post("/import/articles", response_model=ImportResult)
async def import_articles(file: UploadFile = File(...)):
    """
    Import CSV des articles avec attributs (format ERP ou interne).
    
    Format ERP:
    - Article, DescriptionArticle, Matiere, Epaisseur, Longueur, Largeur, Couleur
    
    Format interne:
    - id, description, type_matiere, epaisseur, couleur, largeur, longueur
    """
    try:
        previous_count = await db.articles.count_documents({})
        contents = await file.read()
        df = read_csv_auto(contents)
        
        logger.info(f"📥 Import articles: colonnes détectées = {df.columns.tolist()}")
        
        # Détecter le format (ERP ou interne)
        is_erp_format = 'Article' in df.columns and 'DescriptionArticle' in df.columns
        
        if is_erp_format:
            logger.info("📄 Format ERP détecté - transformation en cours...")
            records = transform_articles(df)
        else:
            # Format interne (ancien format)
            logger.info("📄 Format interne détecté")
            
            if 'id' in df.columns:
                duplicate_ids = df['id'].duplicated().sum()
                if duplicate_ids > 0:
                    return ImportResult(
                        success=False,
                        message=f"Erreur: {duplicate_ids} ID(s) en double",
                        duplicates_found=duplicate_ids
                    )
            
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
                if 'id' not in record or pd.isna(record.get('id')):
                    record['id'] = str(uuid.uuid4())
                else:
                    record['id'] = str(record['id'])
                
                for fr_col, en_col in column_mapping.items():
                    if fr_col in record:
                        value = record.pop(fr_col)
                        if en_col in ['thickness', 'width', 'length'] and not pd.isna(value):
                            try:
                                record[en_col] = float(value)
                            except (ValueError, TypeError):
                                record[en_col] = value
                        elif not pd.isna(value):
                            record[en_col] = str(value)
        
        await db.articles.delete_many({})
        logger.info(f"🗑️  {previous_count} anciens articles supprimés")
        
        if records:
            await db.articles.insert_many(records)
        
        logger.info(f"✅ {len(records)} nouveaux articles importés")
        
        return ImportResult(
            success=True,
            message=f"Import réussi: {len(records)} articles (remplace {previous_count} anciens)",
            records_imported=len(records),
            previous_records=previous_count
        )
    except Exception as e:
        logger.error(f"Import error: {str(e)}", exc_info=True)
        return ImportResult(success=False, message=str(e))


@api_router.get("/stocks")
async def get_stocks():
    """Retourne tous les stocks."""
    stocks = await db.stocks.find({}, {"_id": 0}).to_list(10000)
    return stocks

@api_router.post("/import/stocks", response_model=ImportResult)
async def import_stocks(file: UploadFile = File(...)):
    """
    Import CSV des stocks (format ERP).
    
    Colonnes ERP supportées:
    - Magasin, Article, StockPhysique
    
    Agrégation automatique par article_id.
    """
    try:
        previous_count = await db.stocks.count_documents({})
        contents = await file.read()
        df = read_csv_auto(contents)
        
        logger.info(f"📥 Import stocks: colonnes détectées = {df.columns.tolist()}")
        
        # Détecter le format (ERP ou interne)
        is_erp_format = 'Magasin' in df.columns and 'StockPhysique' in df.columns
        
        if is_erp_format:
            logger.info("📄 Format ERP détecté - transformation en cours...")
            records = transform_stocks(df)
        else:
            # Format interne (ancien format)
            logger.info("📄 Format interne détecté")
            records = df.to_dict('records')
            for record in records:
                if 'id' not in record or pd.isna(record.get('id')):
                    record['id'] = str(uuid.uuid4())
                if 'article' in record and 'article_id' not in record:
                    record['article_id'] = record['article']
        
        await db.stocks.delete_many({})
        logger.info(f"🗑️  {previous_count} anciens stocks supprimés")
        
        if records:
            await db.stocks.insert_many(records)
        
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
    Import CSV des besoins matière par opération (format ERP).
    
    Colonnes ERP supportées:
    - OrdreFabrication, Operation, Position, Article, Magasin, QuantiteASortir
    
    Génération automatique:
    - operation_id = order_id + "_" + operation_seq
    """
    try:
        previous_count = await db.operation_materials.count_documents({})
        contents = await file.read()
        df = read_csv_auto(contents)
        
        logger.info(f"📥 Import matières: colonnes détectées = {df.columns.tolist()}")
        
        # Détecter le format (ERP ou interne)
        is_erp_format = 'OrdreFabrication' in df.columns and 'QuantiteASortir' in df.columns
        
        if is_erp_format:
            logger.info("📄 Format ERP détecté - transformation en cours...")
            records = transform_operation_materials(df)
        else:
            # Format interne (ancien format)
            logger.info("📄 Format interne détecté")
            records = df.to_dict('records')
            for record in records:
                if 'quantity' in record:
                    record['quantity'] = float(record['quantity']) if not pd.isna(record['quantity']) else 0
                if 'operation_id' in record and not isinstance(record['operation_id'], str):
                    record['operation_id'] = str(record['operation_id'])
        
        await db.operation_materials.delete_many({})
        logger.info(f"🗑️  {previous_count} anciens besoins matière supprimés")
        
        if records:
            await db.operation_materials.insert_many(records)
        
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
    Import CSV des réceptions fournisseurs planifiées (format ERP).
    
    Colonnes ERP supportées:
    - Magasin, TypeTransaction, TypeOrdre, Ordre, Article
    - DescriptionArticle, QuantitePlanifiee, DateTransaction
    """
    try:
        previous_count = await db.planned_supplier_receipts.count_documents({})
        contents = await file.read()
        df = read_csv_auto(contents)
        
        logger.info(f"📥 Import réceptions: colonnes détectées = {df.columns.tolist()}")
        
        # Détecter le format (ERP ou interne)
        is_erp_format = 'Magasin' in df.columns and 'DateTransaction' in df.columns
        
        if is_erp_format:
            logger.info("📄 Format ERP détecté - transformation en cours...")
            records = transform_planned_supplier_receipts(df)
        else:
            # Format interne (ancien format)
            logger.info("📄 Format interne détecté")
            records = df.to_dict('records')
            for record in records:
                if 'quantity' in record:
                    record['quantity'] = float(record['quantity']) if not pd.isna(record['quantity']) else 0
        
        await db.planned_supplier_receipts.delete_many({})
        logger.info(f"🗑️  {previous_count} anciennes réceptions planifiées supprimées")
        
        if records:
            await db.planned_supplier_receipts.insert_many(records)
        
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

# Import des nomenclatures (BOM)
@api_router.post("/import/bom", response_model=ImportResult)
async def import_bom(file: UploadFile = File(...)):
    """
    Import CSV des nomenclatures (Bill of Materials).
    
    Colonnes: parent_article_id, child_article_id, quantity, level, unit, scrap_rate
    
    Exemple:
    parent_article_id,child_article_id,quantity,level,unit,scrap_rate
    100235560,COMP_A,2,1,pièce,0.02
    100235560,COMP_B,4,1,pièce,0
    COMP_A,MATIERE_X,0.5,2,kg,0.05
    """
    try:
        previous_count = await db.bom.count_documents({})
        contents = await file.read()
        df = read_csv_auto(contents)
        
        await db.bom.delete_many({})
        logger.info(f"🗑️  {previous_count} anciennes lignes BOM supprimées")
        
        records = df.to_dict('records')
        for record in records:
            # Convertir les types
            if 'quantity' in record:
                record['quantity'] = float(record['quantity'])
            if 'level' in record:
                record['level'] = int(record.get('level', 1))
            if 'scrap_rate' in record:
                record['scrap_rate'] = float(record.get('scrap_rate', 0))
            if 'unit' not in record or pd.isna(record.get('unit')):
                record['unit'] = 'pièce'
            await db.bom.insert_one(record)
        
        logger.info(f"✅ {len(records)} lignes BOM importées")
        
        return ImportResult(
            success=True,
            message=f"Import réussi: {len(records)} lignes BOM (remplace {previous_count} anciennes)",
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
        
        # Créer le scénario avec la date de création actuelle
        await db.scenarios.update_one(
            {"id": scenario_id},
            {
                "$set": {"status": "calculating"},
                "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}
            },
            upsert=True
        )
        
        orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(10000)
        operations = await db.operations.find({}, {"_id": 0}).to_list(10000)
        machines = await db.machines.find({}, {"_id": 0}).to_list(1000)
        rules = await db.business_rules.find({}, {"_id": 0}).to_list(1000)
        stocks = await db.stocks.find({}, {"_id": 0}).to_list(1000)
        articles = await db.articles.find({}, {"_id": 0}).to_list(1000)  # Pour les règles sur attributs
        unavailabilities = await db.unavailability.find({}, {"_id": 0}).to_list(1000)  # Indisponibilités machines
        
        engine = SchedulerEngine(db)
        material_checker = MaterialChecker(stocks)
        rules_engine = RulesEngine(rules, articles)  # Passer les articles pour règles sur attributs
        
        options = {
            'ignore_rules': request.ignore_rules,
            'ignore_material': request.ignore_material,
            'ignore_calendars': request.ignore_calendars,
            'ignore_priorities': request.ignore_priorities,
            'ignore_priority_propagation': request.ignore_priority_propagation,
            'ignore_material_propagation': request.ignore_material_propagation,
            'debug_mode': request.debug_mode,
            'auto_assign_machines': request.auto_assign_machines,
            'max_solver_time_seconds': request.max_solver_time_seconds,
            'scheduling_strategy': request.scheduling_strategy,  # ASAP ou JIT
            'optimization_gap': request.optimization_gap,
            'allow_splitting': request.allow_splitting,
            'respect_sequence': request.respect_sequence,
            'horizon_days': request.horizon_days,  # Horizon de planification
            'unavailabilities': unavailabilities  # Ajouter les indisponibilités
        }
        
        schedule_result = await engine.schedule(
            orders, operations, machines, rules_engine, material_checker, options
        )
        
        # Sauvegarder les options utilisées dans le scénario
        await db.scenarios.update_one(
            {"id": scenario_id},
            {
                "$set": {
                    "status": "completed",
                    "schedule_data": schedule_result,
                    "options": options,
                    "name": request.scenario_name or f"Scénario {scenario_id[:8]}"
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


# ==================== CALCUL ASYNCHRONE ====================
# Permet de lancer des calculs longs sans timeout du proxy

class AsyncJobStatus(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: Optional[int] = None
    message: Optional[str] = None
    scenario_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


async def run_scheduling_job(job_id: str, request_dict: dict):
    """Exécute le calcul d'ordonnancement en arrière-plan."""
    global scheduling_jobs
    
    try:
        scheduling_jobs[job_id]['status'] = 'running'
        scheduling_jobs[job_id]['message'] = 'Chargement des données...'
        
        scenario_id = request_dict.get('scenario_id') or str(uuid.uuid4())
        scenario_name = request_dict.get('scenario_name') or f"Scénario {datetime.now().strftime('%H:%M:%S')}"
        scheduling_jobs[job_id]['scenario_id'] = scenario_id
        
        # Créer le scénario avec status "calculating" ET le nom
        await db.scenarios.update_one(
            {"id": scenario_id},
            {
                "$set": {
                    "name": scenario_name,
                    "status": "calculating"
                },
                "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}
            },
            upsert=True
        )
        
        scheduling_jobs[job_id]['message'] = 'Chargement des ordres et opérations...'
        
        orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(10000)
        operations = await db.operations.find({}, {"_id": 0}).to_list(10000)
        machines = await db.machines.find({}, {"_id": 0}).to_list(1000)
        rules = await db.business_rules.find({}, {"_id": 0}).to_list(1000)
        stocks = await db.stocks.find({}, {"_id": 0}).to_list(1000)
        articles = await db.articles.find({}, {"_id": 0}).to_list(1000)
        unavailabilities = await db.unavailability.find({}, {"_id": 0}).to_list(1000)
        
        scheduling_jobs[job_id]['message'] = f'Données chargées: {len(operations)} opérations'
        scheduling_jobs[job_id]['progress'] = 10
        
        engine = SchedulerEngine(db)
        material_checker = MaterialChecker(stocks)
        rules_engine = RulesEngine(rules, articles)
        
        scheduling_jobs[job_id]['message'] = 'Calcul en cours...'
        scheduling_jobs[job_id]['progress'] = 20
        
        options = {
            'ignore_rules': request_dict.get('ignore_rules', False),
            'ignore_material': request_dict.get('ignore_material', False),
            'ignore_calendars': request_dict.get('ignore_calendars', False),
            'ignore_priorities': request_dict.get('ignore_priorities', False),
            'ignore_priority_propagation': request_dict.get('ignore_priority_propagation', False),
            'ignore_material_propagation': request_dict.get('ignore_material_propagation', False),
            'debug_mode': request_dict.get('debug_mode', True),
            'auto_assign_machines': request_dict.get('auto_assign_machines', True),
            'max_solver_time_seconds': request_dict.get('max_solver_time_seconds', 60),
            'scheduling_strategy': request_dict.get('scheduling_strategy', 'ASAP'),
            'optimization_gap': request_dict.get('optimization_gap', 0.05),
            'allow_splitting': request_dict.get('allow_splitting', True),
            'respect_sequence': request_dict.get('respect_sequence', True),
            'horizon_days': request_dict.get('horizon_days', 14),  # Horizon de planification
            'unavailabilities': unavailabilities
        }
        
        result = await engine.schedule(
            orders=orders,
            operations=operations,
            machines=machines,
            rules_engine=rules_engine,
            material_checker=material_checker,
            options=options
        )
        
        scheduling_jobs[job_id]['progress'] = 90
        scheduling_jobs[job_id]['message'] = 'Sauvegarde du scénario...'
        
        # Sauvegarder le scénario
        scenario_name = request_dict.get('scenario_name') or f"Scénario {datetime.now().strftime('%H:%M:%S')}"
        
        await db.scenarios.update_one(
            {"id": scenario_id},
            {"$set": {
                "name": scenario_name,
                "status": "completed",
                "schedule_data": result,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        scheduling_jobs[job_id]['status'] = 'completed'
        scheduling_jobs[job_id]['progress'] = 100
        scheduling_jobs[job_id]['message'] = f"Calcul terminé: {len(result.get('operations', []))} opérations planifiées"
        scheduling_jobs[job_id]['completed_at'] = datetime.now(timezone.utc).isoformat()
        scheduling_jobs[job_id]['result'] = {
            'scenario_id': scenario_id,
            'status': result.get('status'),
            'operations_count': len(result.get('operations', [])),
            'solver_time': result.get('scheduling_stats', {}).get('actual_solver_time'),
            'utilization': result.get('scheduling_stats', {}).get('global_utilization_percent')
        }
        
    except Exception as e:
        logger.error(f"Async scheduling error: {str(e)}", exc_info=True)
        scheduling_jobs[job_id]['status'] = 'failed'
        scheduling_jobs[job_id]['error'] = str(e)
        scheduling_jobs[job_id]['completed_at'] = datetime.now(timezone.utc).isoformat()


@api_router.post("/scheduling/calculate/async")
async def calculate_schedule_async(request: ScheduleRequestWithOptions, background_tasks: BackgroundTasks):
    """
    Lance un calcul d'ordonnancement en arrière-plan.
    
    Retourne immédiatement un job_id que le client peut utiliser pour
    suivre la progression et récupérer le résultat via /scheduling/status/{job_id}
    
    Avantage: Pas de timeout du proxy car la requête retourne immédiatement.
    """
    job_id = str(uuid.uuid4())
    
    scheduling_jobs[job_id] = {
        'job_id': job_id,
        'status': 'pending',
        'progress': 0,
        'message': 'En attente de démarrage...',
        'started_at': datetime.now(timezone.utc).isoformat(),
        'scenario_id': None,
        'result': None,
        'error': None,
        'completed_at': None
    }
    
    # Convertir le request en dict pour le passer au background task
    request_dict = {
        'scenario_id': request.scenario_id,
        'scenario_name': request.scenario_name,
        'scheduling_strategy': request.scheduling_strategy,
        'horizon_days': request.horizon_days,  # Horizon de planification
        'ignore_rules': request.ignore_rules,
        'ignore_material': request.ignore_material,
        'ignore_calendars': request.ignore_calendars,
        'ignore_priorities': request.ignore_priorities,
        'ignore_priority_propagation': request.ignore_priority_propagation,
        'ignore_material_propagation': request.ignore_material_propagation,
        'max_solver_time_seconds': request.max_solver_time_seconds,
        'optimization_gap': request.optimization_gap,
        'debug_mode': request.debug_mode,
        'auto_assign_machines': request.auto_assign_machines,
        'allow_splitting': request.allow_splitting,
        'respect_sequence': request.respect_sequence
    }
    
    # Lancer le calcul en arrière-plan
    background_tasks.add_task(run_scheduling_job, job_id, request_dict)
    
    return {
        'job_id': job_id,
        'status': 'pending',
        'message': 'Calcul démarré en arrière-plan. Utilisez /api/scheduling/status/{job_id} pour suivre la progression.'
    }


@api_router.get("/scheduling/status/{job_id}", response_model=AsyncJobStatus)
async def get_scheduling_status(job_id: str):
    """
    Récupère le statut d'un calcul d'ordonnancement asynchrone.
    
    Statuts possibles:
    - pending: En attente de démarrage
    - running: Calcul en cours
    - completed: Calcul terminé avec succès
    - failed: Échec du calcul
    """
    if job_id not in scheduling_jobs:
        raise HTTPException(status_code=404, detail="Job non trouvé")
    
    return scheduling_jobs[job_id]


@api_router.get("/scheduling/jobs")
async def list_scheduling_jobs():
    """Liste tous les jobs de calcul (pour le debug)."""
    return list(scheduling_jobs.values())



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
        orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(10000)
        operations_raw = await db.operations.find({}, {"_id": 0}).to_list(10000)
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
    orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(10000)
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

# ============================================
# NOUVEAUX ENDPOINTS P1/P2
# ============================================

# Vue matricielle des compatibilités Machine/Tâche
@api_router.get("/matrix/machine-task")
async def get_machine_task_matrix():
    """
    Génère une vue matricielle des compatibilités entre machines et tâches.
    Utilise les règles métier pour déterminer les autorisations/interdictions.
    """
    try:
        machines = await db.machines.find({}, {"_id": 0}).to_list(100)
        operations = await db.operations.find({}, {"_id": 0}).to_list(10000)
        rules = await db.business_rules.find({"active": True}, {"_id": 0}).to_list(1000)
        centres = await db.centres_de_charge.find({}, {"_id": 0}).to_list(100)
        
        # Extraire les tâches uniques
        taches_set = set()
        for op in operations:
            tache_id = op.get('tache_id')
            if tache_id:
                taches_set.add(tache_id)
        taches = sorted(list(taches_set))
        
        # Index des machines par centre
        machines_by_centre = {}
        for machine in machines:
            centre_id = machine.get('centre_de_charge_id')
            if centre_id:
                if centre_id not in machines_by_centre:
                    machines_by_centre[centre_id] = []
                machines_by_centre[centre_id].append(machine.get('id'))
        
        # Construire la matrice
        matrix = []
        for machine in machines:
            machine_id = machine.get('id')
            machine_centre = machine.get('centre_de_charge_id')
            
            row = {
                'machine_id': machine_id,
                'machine_name': machine.get('nom', machine_id),
                'centre_id': machine_centre,
                'compatibilities': {}
            }
            
            for tache_id in taches:
                # Déterminer le statut de compatibilité
                status = 'unknown'  # Par défaut
                rule_applied = None
                
                # Vérifier les règles
                for rule in rules:
                    rule_tache = rule.get('tache_id')
                    rule_machine = rule.get('machine_id')
                    rule_type = rule.get('rule_type')
                    
                    # Règle qui s'applique à cette tâche et cette machine
                    if rule_machine == machine_id:
                        if rule_tache == tache_id or rule_tache is None:
                            if rule_type == 'FORBID':
                                status = 'forbidden'
                                rule_applied = rule.get('name')
                            elif rule_type == 'ALLOW':
                                status = 'allowed'
                                rule_applied = rule.get('name')
                            elif rule_type == 'PREFER':
                                status = 'preferred'
                                rule_applied = rule.get('name')
                
                # Si pas de règle spécifique, vérifier si la machine est dans le bon centre
                if status == 'unknown':
                    # Chercher les opérations avec cette tâche pour connaître leur centre
                    for op in operations:
                        if op.get('tache_id') == tache_id:
                            op_centre = op.get('centre_de_charge_id')
                            if op_centre and op_centre == machine_centre:
                                status = 'compatible'
                            elif op_centre:
                                status = 'incompatible'
                            break
                
                row['compatibilities'][tache_id] = {
                    'status': status,
                    'rule': rule_applied
                }
            
            matrix.append(row)
        
        return {
            'machines': [m.get('id') for m in machines],
            'taches': taches,
            'matrix': matrix,
            'rules_count': len(rules)
        }
    except Exception as e:
        logger.error(f"Error generating matrix: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Données Gantt enrichies
@api_router.get("/gantt/data/{scenario_id}")
async def get_gantt_data(scenario_id: str):
    """
    Retourne les données formatées pour l'affichage Gantt interactif.
    Inclut les informations sur les machines, les plages horaires, matières et calendriers.
    """
    try:
        scenario = await db.scenarios.find_one({"id": scenario_id}, {"_id": 0})
        if not scenario:
            raise HTTPException(status_code=404, detail="Scénario non trouvé")
        
        schedule_data = scenario.get('schedule_data', {})
        operations = schedule_data.get('operations', [])
        
        # Charger les machines pour les couleurs et noms
        machines = await db.machines.find({}, {"_id": 0}).to_list(100)
        machines_dict = {m.get('id'): m for m in machines}
        
        # Charger les centres de charge
        centres = await db.centres_de_charge.find({}, {"_id": 0}).to_list(100)
        centres_dict = {c.get('id'): c for c in centres}
        
        # Charger les calendriers
        calendars = await db.calendars.find({}, {"_id": 0}).to_list(100)
        calendars_dict = {c.get('id'): c for c in calendars}
        
        # Charger les ordres pour les infos supplémentaires
        orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(10000)
        orders_dict = {o.get('id'): o for o in orders}
        
        # Charger les besoins en matières pour chaque opération
        operation_materials = await db.operation_materials.find({}, {"_id": 0}).to_list(10000)
        materials_by_op = {}
        for mat in operation_materials:
            # L'operation_id dans operation_materials est au format "ORDER_ID_OPERATION_SEQ" (ex: LV1100001_10)
            # C'est le même format que operation_id dans les opérations ordonnancées
            op_id = mat.get('operation_id') or mat.get('id')
            if op_id:
                if op_id not in materials_by_op:
                    materials_by_op[op_id] = []
                materials_by_op[op_id].append(mat)
        
        # Charger les stocks et réceptions pour le stock projeté dynamique
        stocks = await db.stocks.find({}, {"_id": 0}).to_list(1000)
        stocks_dict = {s.get('article_id'): s.get('quantity', 0) for s in stocks}
        planned_receipts = await db.planned_supplier_receipts.find({}, {"_id": 0}).to_list(1000)
        
        # Initialiser le MaterialManager pour le calcul de stock projeté temporel
        from services.material_manager import MaterialManager
        material_manager = MaterialManager(stocks, operation_materials, planned_receipts)
        
        # IMPORTANT: Ajouter les productions planifiées des OFs au MaterialManager
        # Cela permet de calculer le stock projeté en tenant compte des articles fabriqués
        productions = schedule_data.get('productions', [])
        for prod in productions:
            order_id = prod.get('order_id')
            article_id = prod.get('article_id')
            quantity = prod.get('quantity', 0)
            end_datetime_str = prod.get('end_datetime')
            
            if article_id and end_datetime_str:
                try:
                    end_datetime = datetime.fromisoformat(end_datetime_str.replace('Z', '+00:00'))
                    material_manager.add_planned_production(
                        order_id=order_id,
                        article_id=article_id,
                        quantity=quantity,
                        end_date=end_datetime
                    )
                except Exception as e:
                    logger.warning(f"Erreur ajout production {order_id}: {e}")
        
        # Trier les opérations par date de début pour simuler les consommations dans l'ordre
        sorted_operations = sorted(operations, key=lambda x: x.get('start_datetime', ''))
        
        # Simuler les consommations pour calculer le stock projeté à chaque horodatage
        # On utilise un dictionnaire pour tracker les consommations cumulées
        cumulated_consumptions = {}  # {article_id: total_consumed}
        
        # Couleurs par machine
        colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316']
        machine_colors = {}
        for i, m in enumerate(machines):
            machine_colors[m.get('id')] = colors[i % len(colors)]
        
        # Formater les tâches pour le Gantt (dans l'ordre chronologique pour le calcul matière)
        gantt_tasks = []
        for op in sorted_operations:
            machine_id = op.get('machine_id')
            order_id = op.get('order_id')
            order = orders_dict.get(order_id, {})
            machine = machines_dict.get(machine_id, {})
            centre_id = machine.get('centre_de_charge_id') or machine.get('work_center_id')
            centre = centres_dict.get(centre_id, {})
            
            # Calculer si en retard - Utiliser la valeur stockée si disponible
            is_late = op.get('is_late', False)
            lateness_minutes = op.get('lateness_minutes', 0)
            
            # Récupérer la date de besoin
            due_date = op.get('date_besoin') or order.get('due_date')
            
            # Sinon, calculer is_late à partir des dates (fallback)
            if not is_late and due_date:
                end_dt = op.get('end_datetime')
                if end_dt:
                    try:
                        due = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                        end = datetime.fromisoformat(end_dt.replace('Z', '+00:00'))
                        is_late = end > due
                    except:
                        pass
            
            # Calculer le stock projeté à l'horodatage exact de l'opération
            op_id = op.get('operation_id')
            op_start_dt = op.get('start_datetime')
            materials = materials_by_op.get(op_id, [])
            materials_info = []
            materials_ok = True
            
            # Parser la date de début de l'opération
            op_start = None
            if op_start_dt:
                try:
                    op_start = datetime.fromisoformat(op_start_dt.replace('Z', '+00:00'))
                except:
                    pass
            
            for mat in materials:
                article_id = mat.get('article_composant_id') or mat.get('article_id')
                qty_needed = mat.get('due_quantity') or mat.get('quantity', 0)
                
                # Calculer le stock projeté à l'horodatage de l'opération
                # = stock initial + réceptions avant t - consommations des opérations précédentes
                if op_start:
                    # Stock projeté = MaterialManager.get_projected_stock(article, date) - consommations cumulées
                    base_projected = material_manager.get_projected_stock(article_id, op_start)
                    already_consumed = cumulated_consumptions.get(article_id, 0)
                    qty_stock = base_projected - already_consumed
                else:
                    qty_stock = stocks_dict.get(article_id, 0)
                
                available = qty_stock >= qty_needed
                if not available:
                    materials_ok = False
                materials_info.append({
                    'article_id': article_id,
                    'needed': qty_needed,
                    'in_stock': round(qty_stock, 2),  # Stock projeté à t
                    'available': available
                })
            
            # Après avoir traité cette opération, enregistrer ses consommations
            for mat in materials:
                article_id = mat.get('article_composant_id') or mat.get('article_id')
                qty_needed = mat.get('due_quantity') or mat.get('quantity', 0)
                if article_id not in cumulated_consumptions:
                    cumulated_consumptions[article_id] = 0
                cumulated_consumptions[article_id] += qty_needed
            
            gantt_tasks.append({
                'id': op.get('operation_id'),
                'operation_id': op.get('operation_id'),
                'order_id': order_id,
                'article_id': op.get('article_id') or order.get('article_id'),
                'machine_id': machine_id,
                'machine_name': machine.get('nom', machine_id),
                'centre_de_charge_id': centre_id,
                'centre_de_charge_nom': centre.get('nom', centre_id),
                'start': op.get('start_datetime'),
                'end': op.get('end_datetime'),
                'start_minutes': op.get('start_minutes', 0),
                'end_minutes': op.get('end_minutes', 0),
                'duration_minutes': op.get('duration_minutes', 0),
                'due_date': due_date if due_date else order.get('due_date'),
                'is_late': is_late,
                'lateness_minutes': lateness_minutes,
                'color': machine_colors.get(machine_id, '#6B7280'),
                'materials': materials_info,
                'materials_ok': materials_ok,
                'materials_count': len(materials_info),
                # Nouvelles propriétés pour urgence et production
                'is_urgent': op.get('is_urgent', False),
                'priority': op.get('priority', 0),
                'order_quantity': op.get('order_quantity', order.get('quantity', 0)),
                'transfer_time_minutes': op.get('transfer_time_minutes', 0)
            })
        
        # Grouper par machine
        by_machine = {}
        for task in gantt_tasks:
            mid = task['machine_id']
            if mid not in by_machine:
                machine = machines_dict.get(mid, {})
                centre_id = machine.get('centre_de_charge_id') or machine.get('work_center_id')
                centre = centres_dict.get(centre_id, {})
                
                # Récupérer le calendrier spécifique de cette machine
                calendar_id = centre.get('calendar_id')
                machine_calendar = calendars_dict.get(calendar_id, {
                    'start_hour': 0,
                    'end_hour': 24,
                    'working_days': [0, 1, 2, 3, 4, 5, 6]
                })
                
                by_machine[mid] = {
                    'machine_id': mid,
                    'machine_name': task['machine_name'],
                    'color': task['color'],
                    'centre_de_charge_id': centre_id,
                    'centre_de_charge_nom': task.get('centre_de_charge_nom', centre_id),
                    'calendar': {
                        'start_hour': machine_calendar.get('start_hour', 0),
                        'end_hour': machine_calendar.get('end_hour', 24),
                        'start_time': machine_calendar.get('start_time', '00:00'),
                        'end_time': machine_calendar.get('end_time', '24:00'),
                        'working_days': machine_calendar.get('working_days', [0, 1, 2, 3, 4, 5, 6])
                    },
                    'tasks': []
                }
            by_machine[mid]['tasks'].append(task)
        
        # Trier les tâches par heure de début
        for mid in by_machine:
            by_machine[mid]['tasks'].sort(key=lambda x: x['start_minutes'])
        
        # Calculer l'échelle de temps
        if gantt_tasks:
            min_start = min(t['start_minutes'] for t in gantt_tasks)
            max_end = max(t['end_minutes'] for t in gantt_tasks)
            scheduling_start = schedule_data.get('scheduling_start')
        else:
            min_start = 0
            max_end = 0
            scheduling_start = datetime.now().isoformat()
        
        # Liste unique des centres de charge pour le filtre
        unique_centres = list(set(
            m.get('centre_de_charge_id') for m in by_machine.values() 
            if m.get('centre_de_charge_id')
        ))
        centres_for_filter = [
            {'id': cid, 'nom': centres_dict.get(cid, {}).get('nom', cid)} 
            for cid in unique_centres
        ]
        
        # Informations sur les calendriers pour les zones de fermeture
        calendar_info = []
        for cal in calendars:
            calendar_info.append({
                'id': cal.get('id'),
                'name': cal.get('name'),
                'working_days': cal.get('working_days', [1,2,3,4,5]),
                'start_time': cal.get('start_time', '08:00'),
                'end_time': cal.get('end_time', '17:00')
            })
        
        return {
            'scenario_id': scenario_id,
            'scenario_name': scenario.get('name'),
            'status': schedule_data.get('status'),
            'scheduling_start': scheduling_start,
            'time_range': {
                'min_minutes': min_start,
                'max_minutes': max_end,
                'total_minutes': max_end - min_start
            },
            'machines': list(by_machine.values()),
            'total_tasks': len(gantt_tasks),
            'machine_colors': machine_colors,
            'centres_de_charge': centres_for_filter,
            'calendars': calendar_info
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting gantt data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Stock projeté amélioré avec dates ordonnancées
@api_router.get("/projected-stock/advanced")
async def get_projected_stock_advanced():
    """
    Calcul avancé du stock projeté utilisant les dates de début d'opération
    issues du dernier ordonnancement plutôt que les dates besoin.
    """
    try:
        # Charger toutes les données nécessaires
        stocks = await db.stocks.find({}, {"_id": 0}).to_list(1000)
        operation_materials = await db.operation_materials.find({}, {"_id": 0}).to_list(10000)
        planned_receipts = await db.planned_supplier_receipts.find({}, {"_id": 0}).to_list(1000)
        operations = await db.operations.find({}, {"_id": 0}).to_list(10000)
        orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(10000)
        
        # Récupérer le dernier scénario d'ordonnancement
        last_scenario = await db.scenarios.find_one(
            {"status": "completed"},
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        scheduled_ops = {}
        if last_scenario and last_scenario.get('schedule_data', {}).get('operations'):
            for op in last_scenario['schedule_data']['operations']:
                op_id = op.get('operation_id')
                if op_id:
                    scheduled_ops[op_id] = {
                        'start_datetime': op.get('start_datetime'),
                        'end_datetime': op.get('end_datetime'),
                        'machine_id': op.get('machine_id')
                    }
        
        # Index des ordres et opérations
        orders_dict = {o.get('id'): o for o in orders}
        ops_by_id = {o.get('id'): o for o in operations}
        
        # Calculer les consommations avec dates ordonnancées
        consumptions_by_article = {}
        
        for mat in operation_materials:
            op_id = mat.get('operation_id')
            article_id = mat.get('article_composant_id') or mat.get('article_id')
            quantity = mat.get('due_quantity') or mat.get('quantity', 0)
            
            if not article_id or not quantity:
                continue
            
            # Déterminer la date de consommation
            consumption_date = None
            is_scheduled = False
            
            # Priorité 1: Date de l'opération ordonnancée
            if op_id in scheduled_ops:
                consumption_date = scheduled_ops[op_id].get('start_datetime')
                is_scheduled = True
            
            # Priorité 2: Date besoin de l'ordre
            if not consumption_date:
                op = ops_by_id.get(op_id, {})
                order_id = op.get('order_id')
                if order_id:
                    order = orders_dict.get(order_id, {})
                    consumption_date = order.get('due_date')
            
            if not consumption_date:
                consumption_date = datetime.now().isoformat()
            
            if article_id not in consumptions_by_article:
                consumptions_by_article[article_id] = []
            
            consumptions_by_article[article_id].append({
                'operation_id': op_id,
                'quantity': quantity,
                'consumption_datetime': consumption_date,
                'is_scheduled': is_scheduled
            })
        
        # Index des réceptions
        receipts_by_article = {}
        for rec in planned_receipts:
            article_id = rec.get('article_id')
            if article_id:
                if article_id not in receipts_by_article:
                    receipts_by_article[article_id] = []
                receipts_by_article[article_id].append({
                    'quantity': rec.get('quantity', 0),
                    'planned_date': rec.get('planned_date')
                })
        
        # Index des stocks
        stock_by_article = {s.get('article_id'): s.get('quantity', 0) for s in stocks}
        
        # Calculer le stock projeté
        all_articles = set(stock_by_article.keys()) | set(consumptions_by_article.keys()) | set(receipts_by_article.keys())
        all_articles = {a for a in all_articles if a is not None}
        
        projected_stock = []
        consumption_details = []
        
        for article_id in sorted(all_articles, key=lambda x: str(x)):
            initial_stock = stock_by_article.get(article_id, 0)
            consumptions = consumptions_by_article.get(article_id, [])
            receipts = receipts_by_article.get(article_id, [])
            
            total_consumption = sum(c['quantity'] for c in consumptions)
            total_receipts = sum(r['quantity'] for r in receipts)
            final_stock = initial_stock + total_receipts - total_consumption
            
            # Calculer la timeline et détecter les ruptures
            events = []
            for cons in consumptions:
                events.append({
                    'datetime': cons.get('consumption_datetime'),
                    'type': 'consumption',
                    'quantity': -cons.get('quantity', 0),
                    'operation_id': cons.get('operation_id'),
                    'is_scheduled': cons.get('is_scheduled', False)
                })
                consumption_details.append({
                    'article_id': article_id,
                    'operation_id': cons.get('operation_id'),
                    'quantity': cons.get('quantity', 0),
                    'consumption_datetime': cons.get('consumption_datetime'),
                    'is_scheduled': cons.get('is_scheduled', False)
                })
            
            for rec in receipts:
                events.append({
                    'datetime': rec.get('planned_date'),
                    'type': 'receipt',
                    'quantity': rec.get('quantity', 0)
                })
            
            events.sort(key=lambda x: x.get('datetime') or '9999-99-99')
            
            current_stock = initial_stock
            has_shortage = False
            shortage_quantity = 0
            first_shortage_datetime = None
            availability_date = None
            
            for event in events:
                prev_stock = current_stock
                current_stock += event['quantity']
                
                if current_stock < 0 and not has_shortage:
                    has_shortage = True
                    shortage_quantity = abs(current_stock)
                    first_shortage_datetime = event.get('datetime')
                
                if has_shortage and current_stock >= 0 and not availability_date:
                    availability_date = event.get('datetime')
            
            scheduled_count = sum(1 for c in consumptions if c.get('is_scheduled'))
            
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
                'consumptions_count': len(consumptions),
                'scheduled_consumptions': scheduled_count,
                'unscheduled_consumptions': len(consumptions) - scheduled_count
            })
        
        # Trier par criticité
        projected_stock.sort(key=lambda x: (0 if x['has_shortage'] else 1, x.get('first_shortage_datetime') or '9999'))
        consumption_details.sort(key=lambda x: x.get('consumption_datetime') or '9999')
        
        return {
            'projected_stock': projected_stock,
            'consumption_details': consumption_details[:100],
            'summary': {
                'total_articles': len(projected_stock),
                'articles_with_shortage': sum(1 for p in projected_stock if p['has_shortage']),
                'articles_ok': sum(1 for p in projected_stock if not p['has_shortage']),
                'scheduled_consumptions': sum(p['scheduled_consumptions'] for p in projected_stock),
                'unscheduled_consumptions': sum(p['unscheduled_consumptions'] for p in projected_stock),
                'has_scheduling_data': bool(scheduled_ops)
            }
        }
    except Exception as e:
        logger.error(f"Error in advanced projected stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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