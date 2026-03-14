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
from services.rules_engine import RulesEngine
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

# Pydantic Models - Structure révisée
class WorkCenter(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None

class Machine(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    work_center_id: str
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
    Règles métier basées sur task_id et work_center_id.
    """
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    rule_type: str
    is_hard: bool = Field(default=True)
    
    # Critères de ciblage
    task_id: Optional[str] = None
    work_center_id: Optional[str] = None
    machine_id: Optional[str] = None
    article_id: Optional[str] = None
    
    # Condition
    condition_operator: str = Field(default="equals")
    condition_value: Optional[str] = None
    
    # Action
    action_type: str
    action_value: Optional[str] = None
    
    # État
    active: bool = Field(default=True)
    description: Optional[str] = None

class ManufacturingOrder(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    article_id: str  # Renommé de 'article' vers 'article_id'
    quantity: float
    due_date: str
    status: str

class Operation(BaseModel):
    """
    Structure complète des opérations avec task_id et work_center_id.
    """
    model_config = ConfigDict(extra="ignore")
    id: str
    order_id: str
    article_id: str
    operation_id: int  # Numéro d'opération dans la gamme
    task_id: str  # Type de tâche (ex: USINAGE, ASSEMBLAGE)
    work_center_id: str  # Centre de charge requis
    status: Optional[str] = "pending"
    production_time_minutes: int
    setup_time_minutes: int
    
    # Assignation machine (optionnelle, déterminée par le moteur)
    machine_id: Optional[str] = None
    scheduled_start: Optional[str] = None
    scheduled_end: Optional[str] = None

class Article(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str  # article_id
    description: str

class Stock(BaseModel):
    model_config = ConfigDict(extra="ignore")
    article_id: str  # Cohérent avec ManufacturingOrder et Operation
    quantity: float

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

# Work Centers endpoints
@api_router.post("/work-centers", response_model=WorkCenter)
async def create_work_center(work_center: WorkCenter):
    doc = work_center.model_dump()
    await db.work_centers.insert_one(doc)
    return work_center

@api_router.get("/work-centers", response_model=List[WorkCenter])
async def get_work_centers():
    work_centers = await db.work_centers.find({}, {"_id": 0}).to_list(1000)
    return work_centers

@api_router.delete("/work-centers/{work_center_id}")
async def delete_work_center(work_center_id: str):
    result = await db.work_centers.delete_one({"id": work_center_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Work center not found")
    return {"message": "Deleted successfully"}

# Machines endpoints
@api_router.post("/machines", response_model=Machine)
async def create_machine(machine: Machine):
    doc = machine.model_dump()
    await db.machines.insert_one(doc)
    return machine

@api_router.get("/machines", response_model=List[Machine])
async def get_machines():
    machines = await db.machines.find({}, {"_id": 0}).to_list(1000)
    return machines

@api_router.delete("/machines/{machine_id}")
async def delete_machine(machine_id: str):
    result = await db.machines.delete_one({"id": machine_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Machine not found")
    return {"message": "Deleted successfully"}

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
@api_router.post("/rules", response_model=BusinessRule)
async def create_rule(rule: BusinessRule):
    doc = rule.model_dump()
    await db.business_rules.insert_one(doc)
    return rule

@api_router.get("/rules", response_model=List[BusinessRule])
async def get_rules():
    rules = await db.business_rules.find({}, {"_id": 0}).to_list(1000)
    return rules

@api_router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: str):
    result = await db.business_rules.delete_one({"id": rule_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Deleted successfully"}

# Manufacturing Orders endpoints
@api_router.get("/manufacturing-orders", response_model=List[ManufacturingOrder])
async def get_manufacturing_orders():
    orders = await db.manufacturing_orders.find({}, {"_id": 0}).to_list(1000)
    return orders

@api_router.get("/operations", response_model=List[Operation])
async def get_operations():
    operations = await db.operations.find({}, {"_id": 0}).to_list(1000)
    return operations

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
        
        records = df.to_dict('records')
        for record in records:
            if 'id' not in record or pd.isna(record['id']):
                record['id'] = str(uuid.uuid4())
            else:
                record['id'] = str(record['id'])
            await db.articles.insert_one(record)
        
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
            'auto_assign_machines': request.auto_assign_machines
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