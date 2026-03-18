from ortools.sat.python import cp_model
import logging
import math
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from services.diagnostics import SchedulingDiagnostics
from services.machine_assigner import MachineAssigner
from services.material_manager import MaterialManager

logger = logging.getLogger(__name__)

# Fuseau horaire Europe/Paris
PARIS_TZ = ZoneInfo('Europe/Paris')


class CalendarManager:
    """
    Gestionnaire des calendriers pour les centres de charge.
    
    Permet de:
    - Déterminer les plages horaires de travail par machine
    - Calculer le temps effectif de travail
    - Créer des contraintes de calendrier pour le solveur
    """
    
    def __init__(self, calendars: List[Dict], centres_de_charge: List[Dict], machines: List[Dict]):
        self.calendars_by_id = {c.get('id'): c for c in calendars}
        self.centres_by_id = {c.get('id'): c for c in centres_de_charge}
        self.machines = machines
        
        # Construire l'index machine -> calendrier
        self.machine_calendar: Dict[str, Dict] = {}
        for machine in machines:
            machine_id = machine.get('id')
            centre_id = machine.get('centre_de_charge_id')
            
            # Récupérer le calendrier du centre de charge
            centre = self.centres_by_id.get(centre_id, {})
            calendar_id = centre.get('calendar_id')
            
            if calendar_id and calendar_id in self.calendars_by_id:
                self.machine_calendar[machine_id] = self.calendars_by_id[calendar_id]
            else:
                # Calendrier par défaut: 24/7
                self.machine_calendar[machine_id] = {
                    'id': 'default',
                    'name': 'Default 24/7',
                    'working_days': [0, 1, 2, 3, 4, 5, 6],  # Lundi-Dimanche
                    'start_hour': 0,
                    'end_hour': 24
                }
        
        logger.info("\n" + "="*60)
        logger.info("CALENDRIERS DES CENTRES DE CHARGE")
        logger.info("="*60)
        for machine_id, cal in self.machine_calendar.items():
            centre_id = next((m.get('centre_de_charge_id') for m in machines if m.get('id') == machine_id), None)
            logger.info(f"  Machine {machine_id} (centre {centre_id}): {cal.get('name', 'Default')}")
            logger.info(f"    Jours: {cal.get('working_days')}, Heures: {cal.get('start_hour')}-{cal.get('end_hour')}")
        logger.info("="*60 + "\n")
    
    def get_calendar_for_machine(self, machine_id: str) -> Dict:
        """Retourne le calendrier pour une machine."""
        return self.machine_calendar.get(machine_id, {
            'working_days': [0, 1, 2, 3, 4, 5, 6],
            'start_hour': 0,
            'end_hour': 24
        })
    
    def is_working_time(self, machine_id: str, dt: datetime) -> bool:
        """Vérifie si un moment donné est un temps de travail pour la machine."""
        calendar = self.get_calendar_for_machine(machine_id)
        working_days = calendar.get('working_days', [0, 1, 2, 3, 4, 5, 6])
        start_hour = calendar.get('start_hour', 0)
        end_hour = calendar.get('end_hour', 24)
        
        # weekday(): 0=Lundi, 6=Dimanche
        if dt.weekday() not in working_days:
            return False
        
        hour = dt.hour + dt.minute / 60
        if hour < start_hour or hour >= end_hour:
            return False
        
        return True
    
    def get_working_hours_per_day(self, machine_id: str) -> float:
        """Retourne le nombre d'heures de travail par jour pour une machine."""
        calendar = self.get_calendar_for_machine(machine_id)
        start_hour = calendar.get('start_hour', 0)
        end_hour = calendar.get('end_hour', 24)
        return max(0, end_hour - start_hour)
    
    def calculate_forbidden_time_slots(
        self, 
        machine_id: str, 
        scheduling_start: datetime, 
        horizon_days: int = 7
    ) -> List[Tuple[int, int]]:
        """
        Calcule les plages horaires interdites (hors calendrier) pour une machine.
        
        Retourne une liste de tuples (start_minute, end_minute) relatifs au scheduling_start.
        Ces plages représentent les périodes où la machine ne peut pas travailler.
        
        Utilise start_time/end_time (format HH:MM) pour une précision à la minute.
        """
        calendar = self.get_calendar_for_machine(machine_id)
        working_days = set(calendar.get('working_days', [0, 1, 2, 3, 4, 5, 6]))
        
        # Utiliser start_time/end_time si disponibles (précision minute), sinon fallback sur start_hour/end_hour
        start_time_str = calendar.get('start_time', '')
        end_time_str = calendar.get('end_time', '')
        
        if start_time_str and ':' in start_time_str:
            parts = start_time_str.split(':')
            start_hour = int(parts[0])
            start_minute = int(parts[1]) if len(parts) > 1 else 0
        else:
            start_hour = calendar.get('start_hour', 0)
            start_minute = 0
        
        if end_time_str and ':' in end_time_str:
            parts = end_time_str.split(':')
            end_hour = int(parts[0])
            end_minute = int(parts[1]) if len(parts) > 1 else 0
        else:
            end_hour = calendar.get('end_hour', 24)
            end_minute = 0
        
        # Convertir en minutes depuis minuit pour faciliter les calculs
        work_start_minutes = start_hour * 60 + start_minute  # Ex: 7*60+45 = 465 pour 07:45
        work_end_minutes = end_hour * 60 + end_minute  # Ex: 16*60+45 = 1005 pour 16:45
        
        # Si calendrier 24/7, pas de plages interdites
        if working_days == {0, 1, 2, 3, 4, 5, 6} and work_start_minutes == 0 and work_end_minutes == 24*60:
            return []
        
        forbidden_slots = []
        
        # Normaliser scheduling_start au début de la journée pour les calculs
        base_date = scheduling_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Heure actuelle en minutes depuis minuit
        current_minutes = scheduling_start.hour * 60 + scheduling_start.minute
        current_weekday = scheduling_start.weekday()
        
        if current_weekday not in working_days:
            # On démarre un jour non travaillé - géré par la boucle ci-dessous
            pass
        elif current_minutes >= work_end_minutes:
            # On est APRÈS l'heure de fermeture - zone interdite jusqu'au lendemain matin
            next_work_day = base_date + timedelta(days=1)
            for d in range(7):
                check_day = base_date + timedelta(days=1 + d)
                if check_day.weekday() in working_days:
                    next_work_day = check_day
                    break
            
            next_opening = next_work_day + timedelta(minutes=work_start_minutes)
            slot_end = math.ceil((next_opening - scheduling_start).total_seconds() / 60) + 1
            forbidden_slots.append((0, slot_end))
        elif current_minutes < work_start_minutes:
            # On est AVANT l'heure d'ouverture - zone interdite jusqu'à l'ouverture
            today_opening = base_date + timedelta(minutes=work_start_minutes)
            slot_end = math.ceil((today_opening - scheduling_start).total_seconds() / 60) + 1
            forbidden_slots.append((0, slot_end))
        
        # Calculer les zones interdites pour chaque jour de l'horizon
        for day_offset in range(horizon_days + 1):
            day_start = base_date + timedelta(days=day_offset)
            day_weekday = day_start.weekday()
            
            if day_weekday not in working_days:
                # Journée entière non travaillée
                slot_start_dt = day_start
                slot_end_dt = day_start + timedelta(days=1)
                
                slot_start = math.ceil((slot_start_dt - scheduling_start).total_seconds() / 60)
                slot_end = math.ceil((slot_end_dt - scheduling_start).total_seconds() / 60)
                
                if slot_end > 0:
                    forbidden_slots.append((max(0, slot_start), slot_end))
            else:
                # Jour travaillé - ajouter les plages hors heures de travail
                
                # MATIN: De minuit jusqu'à l'heure d'ouverture (ex: 00:00 - 07:45)
                if work_start_minutes > 0:
                    slot_start_dt = day_start  # 00:00
                    slot_end_dt = day_start + timedelta(minutes=work_start_minutes)  # Ex: 07:45
                    
                    slot_start = math.ceil((slot_start_dt - scheduling_start).total_seconds() / 60)
                    slot_end = math.ceil((slot_end_dt - scheduling_start).total_seconds() / 60) + 1
                    
                    if slot_end > 0:
                        forbidden_slots.append((max(0, slot_start), slot_end))
                
                # SOIR: De l'heure de fermeture jusqu'à minuit (ex: 16:45 - 24:00)
                if work_end_minutes < 24 * 60:
                    slot_start_dt = day_start + timedelta(minutes=work_end_minutes)  # Ex: 16:45
                    slot_end_dt = day_start + timedelta(days=1)  # Minuit du jour suivant
                    
                    slot_start = math.ceil((slot_start_dt - scheduling_start).total_seconds() / 60)
                    slot_end = math.ceil((slot_end_dt - scheduling_start).total_seconds() / 60)
                    
                    if slot_end > 0:
                        forbidden_slots.append((max(0, slot_start), slot_end))
        
        # Fusionner les plages qui se chevauchent pour optimiser
        if forbidden_slots:
            forbidden_slots.sort()
            merged = [forbidden_slots[0]]
            for current in forbidden_slots[1:]:
                if current[0] <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], current[1]))
                else:
                    merged.append(current)
            return merged
        
        return forbidden_slots


class UnavailabilityManager:
    """
    Gestionnaire des indisponibilités machines.
    
    Permet de:
    - Charger les périodes d'indisponibilité par machine
    - Créer des contraintes pour éviter la planification pendant ces périodes
    """
    
    def __init__(self, unavailabilities: List[Dict], scheduling_start: datetime):
        self.scheduling_start = scheduling_start
        
        # Index des indisponibilités par machine
        self.machine_unavailabilities: Dict[str, List[Dict]] = {}
        
        for unavail in unavailabilities:
            machine_id = unavail.get('machine_id')
            if not machine_id:
                continue
            
            if machine_id not in self.machine_unavailabilities:
                self.machine_unavailabilities[machine_id] = []
            
            # Parser les dates
            start_str = unavail.get('start_date')
            end_str = unavail.get('end_date')
            
            try:
                # Support différents formats de date
                if start_str:
                    if 'T' in start_str:
                        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    else:
                        start_dt = datetime.strptime(start_str, '%Y-%m-%d')
                        start_dt = start_dt.replace(hour=0, minute=0)
                else:
                    continue
                
                if end_str:
                    if 'T' in end_str:
                        end_dt = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    else:
                        end_dt = datetime.strptime(end_str, '%Y-%m-%d')
                        end_dt = end_dt.replace(hour=23, minute=59)
                else:
                    continue
                
                # Convertir en minutes depuis scheduling_start
                start_minutes = max(0, int((start_dt - scheduling_start).total_seconds() / 60))
                end_minutes = max(0, int((end_dt - scheduling_start).total_seconds() / 60))
                
                if end_minutes > start_minutes:
                    self.machine_unavailabilities[machine_id].append({
                        'start_minutes': start_minutes,
                        'end_minutes': end_minutes,
                        'start_datetime': start_dt,
                        'end_datetime': end_dt,
                        'reason': unavail.get('reason', 'Indisponibilité')
                    })
            except Exception as e:
                logger.warning(f"Erreur parsing indisponibilité: {e}")
        
        # Log des indisponibilités chargées
        if self.machine_unavailabilities:
            logger.info("\n" + "="*60)
            logger.info("INDISPONIBILITÉS MACHINES")
            logger.info("="*60)
            for machine_id, periods in self.machine_unavailabilities.items():
                for p in periods:
                    logger.info(f"  Machine {machine_id}: {p['start_datetime'].strftime('%d/%m %H:%M')} → {p['end_datetime'].strftime('%d/%m %H:%M')} ({p['reason']})")
            logger.info("="*60 + "\n")
    
    def get_unavailabilities_for_machine(self, machine_id: str) -> List[Dict]:
        """Retourne les périodes d'indisponibilité pour une machine."""
        return self.machine_unavailabilities.get(machine_id, [])
    
    def is_machine_available(self, machine_id: str, start_minute: int, end_minute: int) -> bool:
        """Vérifie si une machine est disponible pendant une plage horaire."""
        for unavail in self.get_unavailabilities_for_machine(machine_id):
            # Vérifier le chevauchement
            if start_minute < unavail['end_minutes'] and end_minute > unavail['start_minutes']:
                return False
        return True


class SchedulerEngine:
    """
    Moteur d'ordonnancement basé sur OR-Tools CP-SAT.
    
    Garanties:
    1. Non-chevauchement: une machine ne peut traiter qu'une opération à la fois
    2. Séquence: les opérations d'un même OF respectent l'ordre des gammes
    3. Priorité: les opérations urgentes (due_date proche) sont planifiées en premier
    
    Format datetime: ISO 8601 (YYYY-MM-DDTHH:MM:SS)
    """
    
    def __init__(self, db):
        self.db = db
        self.diagnostics = None
        self.scheduling_start = None
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """
        Parse une date/heure en datetime avec timezone Europe/Paris.
        Supporte: YYYY-MM-DDTHH:MM:SS, YYYY-MM-DD HH:MM:SS, YYYY-MM-DD
        """
        if not date_str:
            return None
        
        try:
            if 'T' in date_str:
                if '+' in date_str or 'Z' in date_str:
                    date_str = date_str.replace('Z', '+00:00')
                    dt = datetime.fromisoformat(date_str)
                    # Convertir en timezone Paris
                    return dt.astimezone(PARIS_TZ)
                dt = datetime.fromisoformat(date_str)
                # Ajouter timezone si absente
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=PARIS_TZ)
                return dt
            elif ' ' in date_str:
                dt = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                return dt.replace(tzinfo=PARIS_TZ)
            else:
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                return dt.replace(tzinfo=PARIS_TZ)
        except Exception as e:
            logger.warning(f"Impossible de parser la date '{date_str}': {e}")
            return None
    
    def _datetime_to_minutes(self, dt: datetime) -> int:
        """Convertit un datetime en minutes depuis le début de l'horizon."""
        if not self.scheduling_start:
            self.scheduling_start = datetime.now(PARIS_TZ)
        
        # S'assurer que les deux datetimes ont la même timezone
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=PARIS_TZ)
        if self.scheduling_start.tzinfo is None:
            self.scheduling_start = self.scheduling_start.replace(tzinfo=PARIS_TZ)
            
        delta = dt - self.scheduling_start
        return max(0, int(delta.total_seconds() / 60))
    
    def _minutes_to_datetime(self, minutes: int) -> datetime:
        """Convertit des minutes en datetime."""
        if not self.scheduling_start:
            self.scheduling_start = datetime.now(PARIS_TZ)
        return self.scheduling_start + timedelta(minutes=minutes)
    
    async def schedule(self, orders, operations, machines, rules_engine, material_checker, options=None):
        """
        Main scheduling function using OR-Tools CP-SAT with ITERATIVE MATERIAL REPLANIFICATION.
        
        Garantit:
        - Non-chevauchement sur chaque machine (contrainte NoOverlap)
        - Respect de l'ordre des opérations dans un OF
        - Priorité basée sur due_date avec heure
        - Disponibilité matière avec projection du stock DYNAMIQUE
        - Respect des calendriers des centres de charge
        - REPLANIFICATION AUTOMATIQUE en cas de rupture de stock
        
        Options:
        - ignore_rules: bool
        - ignore_material: bool
        - ignore_calendars: bool
        - debug_mode: bool
        - auto_assign_machines: bool (default True)
        - max_solver_time_seconds: int (default 60) - Budget temps GLOBAL pour toutes les itérations
        - _material_date_constraints: dict (internal - for iterative replanning)
        - _iteration: int (internal - current iteration number)
        - _start_time: float (internal - timestamp de début pour le budget temps)
        - _total_solver_time: float (internal - temps cumulé passé dans le solveur)
        
        Le moteur itère jusqu'à obtenir un ordonnancement SANS RUPTURE DE STOCK
        ou jusqu'à épuisement du budget temps défini par l'utilisateur.
        """
        options = options or {}
        debug_mode = options.get('debug_mode', True)
        ignore_rules = options.get('ignore_rules', False)
        ignore_material = options.get('ignore_material', False)
        ignore_calendars = options.get('ignore_calendars', False)
        ignore_priorities = options.get('ignore_priorities', False)
        ignore_priority_propagation = options.get('ignore_priority_propagation', False)
        ignore_material_propagation = options.get('ignore_material_propagation', False)
        auto_assign_machines = options.get('auto_assign_machines', True)
        max_solver_time_seconds = options.get('max_solver_time_seconds', 60)
        optimization_gap = options.get('optimization_gap', 0.05)  # Gap d'optimalité (5% par défaut)
        
        # Paramètres internes pour la replanification itérative
        material_date_constraints = options.get('_material_date_constraints', {})
        current_iteration = options.get('_iteration', 1)
        
        # Gestion du budget temps global
        # Si c'est la première itération, initialiser le timestamp de début
        if current_iteration == 1:
            start_time = time.time()
        else:
            start_time = options.get('_start_time', time.time())
        total_solver_time = options.get('_total_solver_time', 0.0)
        
        # Calculer le temps restant
        elapsed_time = time.time() - start_time
        remaining_time = max(1, max_solver_time_seconds - elapsed_time)  # Au moins 1 seconde
        
        # Temps alloué pour cette itération (répartition dynamique)
        # On garde une marge pour les itérations suivantes potentielles
        iteration_time = min(remaining_time * 0.8, remaining_time - 2) if remaining_time > 5 else remaining_time
        
        # Point de départ pour l'horizon de planification en timezone Europe/Paris
        # IMPORTANT: Garder la timezone pour compatibilité avec les dates de besoin
        now_paris = datetime.now(PARIS_TZ)
        self.scheduling_start = now_paris.replace(second=0, microsecond=0) + timedelta(minutes=1)
        
        logger.info("\n🕐 TIMEZONE: Europe/Paris")
        logger.info(f"   Heure de planification: {self.scheduling_start.strftime('%d/%m/%Y %H:%M')}")
        
        # Initialiser le diagnostic
        self.diagnostics = SchedulingDiagnostics(self.db)
        
        try:
            # PHASE 1: PRE-VALIDATION - Charger toutes les données
            stocks = await self.db.stocks.find({}, {"_id": 0}).to_list(1000)
            rules = await self.db.business_rules.find({}, {"_id": 0}).to_list(1000)
            operation_materials = await self.db.operation_materials.find({}, {"_id": 0}).to_list(10000)
            planned_receipts = await self.db.planned_supplier_receipts.find({}, {"_id": 0}).to_list(1000)
            calendars = await self.db.calendars.find({}, {"_id": 0}).to_list(100)
            centres_de_charge = await self.db.centres_de_charge.find({}, {"_id": 0}).to_list(100)
            
            logger.info(f"\n{'='*60}")
            logger.info("DONNÉES CHARGÉES POUR L'ORDONNANCEMENT")
            logger.info(f"{'='*60}")
            logger.info(f"  Ordres: {len(orders)}")
            logger.info(f"  Opérations: {len(operations)}")
            logger.info(f"  Machines: {len(machines)}")
            logger.info(f"  Règles: {len(rules)}")
            logger.info(f"  Besoins matière: {len(operation_materials)}")
            logger.info(f"  Stocks: {len(stocks)}")
            logger.info(f"  Réceptions planifiées: {len(planned_receipts)}")
            logger.info(f"  Calendriers: {len(calendars)}")
            logger.info(f"  Centres de charge: {len(centres_de_charge)}")
            logger.info(f"  Temps max solveur: {max_solver_time_seconds}s")
            logger.info(f"{'='*60}")
            logger.info("\n⚙️  OPTIONS AVANCÉES DU SOLVEUR:")
            logger.info(f"   Ignorer règles métier: {ignore_rules}")
            logger.info(f"   Ignorer matière: {ignore_material}")
            logger.info(f"   Ignorer calendriers: {ignore_calendars}")
            logger.info(f"   Ignorer priorités: {ignore_priorities}")
            logger.info(f"   Ignorer propagation priorité: {ignore_priority_propagation}")
            logger.info(f"   Ignorer propagation matière: {ignore_material_propagation}")
            logger.info(f"{'='*60}\n")
            
            # Initialiser le gestionnaire de calendriers
            self.calendar_manager = None
            if not ignore_calendars:
                self.calendar_manager = CalendarManager(calendars, centres_de_charge, machines)
            
            # Initialiser le gestionnaire d'indisponibilités machines
            unavailabilities = options.get('unavailabilities', [])
            self.unavailability_manager = UnavailabilityManager(unavailabilities, self.scheduling_start)
            
            await self.diagnostics.run_pre_validation(orders, operations, machines, rules, stocks)
            
            # Vérification bloquante
            if len(orders) == 0 or len(operations) == 0 or len(machines) == 0:
                logger.error("❌ Données insuffisantes pour l'ordonnancement")
                return self._error_result("Données insuffisantes")
            
            # Initialiser le gestionnaire de matières (attribut de classe pour le post-traitement)
            self.material_manager = MaterialManager(stocks, operation_materials, planned_receipts)
            
            logger.info("\n📦 LOGIQUE MATIÈRE TEMPORELLE ACTIVÉE")
            logger.info(f"   Stock initial: {len(stocks)} articles")
            logger.info(f"   Réceptions planifiées: {len(planned_receipts)}")
            logger.info(f"   Besoins opérations: {len(operation_materials)}")
            
            # PHASE 1.3: FILTRAGE PAR HORIZON DE PLANIFICATION
            # Objectif: Réduire le volume à optimiser tout en gardant une vue d'ensemble
            horizon_days = options.get('horizon_days', 14)
            allow_splitting = options.get('allow_splitting', True)
            
            # Statistiques de filtrage par horizon
            horizon_stats = {
                'horizon_days': horizon_days,
                'original_orders_count': len(orders),
                'original_operations_count': len(operations),
                'orders_in_horizon': 0,
                'orders_late': 0,
                'orders_dependency': 0,
                'orders_excluded': 0,
                'filtered_orders_count': 0,
                'filtered_operations_count': 0
            }
            
            if horizon_days > 0:
                logger.info(f"\n📅 FILTRAGE PAR HORIZON DE PLANIFICATION: {horizon_days} jours")
                
                # Date limite de l'horizon
                horizon_limit = self.scheduling_start + timedelta(days=horizon_days)
                logger.info(f"   Date limite horizon: {horizon_limit.strftime('%d/%m/%Y %H:%M')}")
                
                # Index des ordres par ID pour recherche rapide
                orders_by_id = {o.get('id'): o for o in orders}
                
                # Catégoriser les ordres
                orders_in_horizon = set()  # OFs dans l'horizon
                orders_late = set()         # OFs en retard
                orders_dependency = set()   # OFs inclus par dépendance
                
                # 1. Identifier les ordres dans l'horizon ET les ordres en retard
                for order in orders:
                    order_id = order.get('id')
                    due_date_str = order.get('due_date')
                    
                    if due_date_str:
                        try:
                            due_date = self._parse_datetime(due_date_str)
                            if due_date:
                                if due_date <= self.scheduling_start:
                                    # Ordre en retard - TOUJOURS inclus
                                    orders_late.add(order_id)
                                    logger.info(f"   🔴 {order_id}: EN RETARD (due: {due_date.strftime('%d/%m %H:%M')})")
                                elif due_date <= horizon_limit:
                                    # Ordre dans l'horizon
                                    orders_in_horizon.add(order_id)
                        except Exception:
                            # Si date invalide, inclure par défaut dans l'horizon
                            orders_in_horizon.add(order_id)
                    else:
                        # Pas de date de besoin - inclure dans l'horizon par défaut
                        orders_in_horizon.add(order_id)
                
                logger.info(f"   ✓ Ordres dans l'horizon: {len(orders_in_horizon)}")
                logger.info(f"   ✓ Ordres en retard: {len(orders_late)}")
                
                # 2. Identifier les dépendances nécessaires (OFs producteurs)
                # Pour chaque OF inclus, vérifier si ses besoins matière nécessitent des OFs hors horizon
                included_orders = orders_in_horizon | orders_late
                
                # Map article -> OF producteur
                article_producers_map = {}
                for o in orders:
                    article_id = o.get('article_id')
                    if article_id:
                        if article_id not in article_producers_map:
                            article_producers_map[article_id] = []
                        article_producers_map[article_id].append(o.get('id'))
                
                # Récupérer toutes les opérations des ordres inclus
                included_ops = [op for op in operations if op.get('order_id') in included_orders]
                
                # Pour chaque opération incluse, vérifier les besoins matière
                for op in included_ops:
                    op_id = op.get('id')
                    order_id = op.get('order_id')
                    
                    # Récupérer les besoins matière de cette opération
                    op_materials = self.material_manager.get_operation_materials(op_id)
                    
                    for mat in op_materials:
                        article_needed = mat.article_composant_id
                        qty_needed = mat.quantity
                        
                        # Vérifier si le stock initial est suffisant
                        initial_stock = self.material_manager.get_projected_stock(article_needed, self.scheduling_start)
                        
                        if initial_stock < qty_needed:
                            # Stock insuffisant - vérifier si un OF peut produire cet article
                            if article_needed in article_producers_map:
                                for producer_of_id in article_producers_map[article_needed]:
                                    if producer_of_id not in included_orders and producer_of_id not in orders_dependency:
                                        # Ajouter l'OF producteur par dépendance
                                        orders_dependency.add(producer_of_id)
                                        logger.info(f"   🔗 {producer_of_id}: Ajouté par dépendance matière ({article_needed} pour {order_id})")
                
                # Mise à jour des ordres inclus avec les dépendances
                all_included_orders = orders_in_horizon | orders_late | orders_dependency
                
                # 3. Filtrer les ordres et opérations
                filtered_orders = [o for o in orders if o.get('id') in all_included_orders]
                filtered_order_ids = set(o.get('id') for o in filtered_orders)
                filtered_operations = [op for op in operations if op.get('order_id') in filtered_order_ids]
                
                # Mettre à jour les statistiques
                horizon_stats['orders_in_horizon'] = len(orders_in_horizon)
                horizon_stats['orders_late'] = len(orders_late)
                horizon_stats['orders_dependency'] = len(orders_dependency)
                horizon_stats['orders_excluded'] = len(orders) - len(filtered_orders)
                horizon_stats['filtered_orders_count'] = len(filtered_orders)
                horizon_stats['filtered_operations_count'] = len(filtered_operations)
                
                logger.info(f"\n   📊 RÉSUMÉ DU FILTRAGE:")
                logger.info(f"      Ordres originaux: {len(orders)}")
                logger.info(f"      - Dans l'horizon: {len(orders_in_horizon)}")
                logger.info(f"      - En retard: {len(orders_late)}")
                logger.info(f"      - Par dépendance: {len(orders_dependency)}")
                logger.info(f"      - Exclus: {horizon_stats['orders_excluded']}")
                logger.info(f"      Ordres retenus: {len(filtered_orders)}")
                logger.info(f"      Opérations retenues: {len(filtered_operations)}/{len(operations)}")
                
                # Marquer les ordres avec leur raison d'inclusion
                for o in filtered_orders:
                    oid = o.get('id')
                    if oid in orders_late:
                        o['_horizon_inclusion_reason'] = 'late'
                    elif oid in orders_in_horizon:
                        o['_horizon_inclusion_reason'] = 'in_horizon'
                    elif oid in orders_dependency:
                        o['_horizon_inclusion_reason'] = 'dependency'
                
                # Remplacer les listes de travail
                orders = filtered_orders
                operations = filtered_operations
            else:
                logger.info(f"\n📅 HORIZON DE PLANIFICATION: Désactivé (tous les ordres)")
                for o in orders:
                    o['_horizon_inclusion_reason'] = 'no_filter'
            
            # PHASE 1.4: PROPAGATION DE PRIORITÉ
            # Identifier les OFs urgents et propager la priorité aux OFs fournisseurs
            priority_propagation_log = []
            orders_priority = {o.get('id'): o.get('priority', 0) for o in orders}
            propagated_priority = dict(orders_priority)  # Copie pour modification
            
            # Construire la map article -> OF qui le fabrique
            article_producers = {}
            for o in orders:
                article_id = o.get('article_id')
                if article_id:
                    if article_id not in article_producers:
                        article_producers[article_id] = []
                    article_producers[article_id].append(o.get('id'))
            
            # Si on ignore les priorités, tout le monde a priority=0
            if ignore_priorities:
                logger.info("\n🚫 PRIORITÉS IGNORÉES: Tous les OFs traités avec priorité=0")
                for o in orders:
                    o['_propagated_priority'] = 0
                    o['_is_urgent'] = False
            elif ignore_priority_propagation:
                # On garde les priorités originales mais sans propagation
                logger.info("\n🚫 PROPAGATION DE PRIORITÉ DÉSACTIVÉE: Seules les priorités originales sont conservées")
                for o in orders:
                    o['_propagated_priority'] = o.get('priority', 0)
                    o['_is_urgent'] = o.get('priority', 0) == 1
            else:
                # Propagation de priorité normale
                # Identifier les OFs urgents (priority=1)
                urgent_orders = [o for o in orders if o.get('priority', 0) == 1]
                
                if urgent_orders:
                    logger.info("\n🚨 PROPAGATION DE PRIORITÉ:")
                    logger.info(f"   OFs urgents initiaux: {[o.get('id') for o in urgent_orders]}")
                    
                    for urgent_order in urgent_orders:
                        urgent_id = urgent_order.get('id')
                        # Trouver les opérations de cet OF
                        urgent_ops = [op for op in operations if op.get('order_id') == urgent_id]
                        
                        for op in urgent_ops:
                            op_id = op.get('id')
                            # Récupérer les besoins matière
                            materials = self.material_manager.get_operation_materials(op_id)
                            
                            for mat in materials:
                                article_needed = mat.article_composant_id
                                # Vérifier si cet article est fabriqué par un autre OF
                                if article_needed in article_producers:
                                    for producer_of in article_producers[article_needed]:
                                        if producer_of != urgent_id and propagated_priority.get(producer_of, 0) == 0:
                                            # Propager la priorité
                                            propagated_priority[producer_of] = 1
                                            
                                            # Log détaillé pour le diagnostic
                                            log_entry = {
                                                'source_order': urgent_id,
                                                'source_priority': 1,
                                                'target_order': producer_of,
                                                'article_needed': article_needed,
                                                'reason': f"OF {urgent_id} (urgent, priority=1) consomme {article_needed}. "
                                                          f"Stock peut être insuffisant. OF {producer_of} fabrique {article_needed}. "
                                                          f"OF {producer_of} rendu urgent pour garantir disponibilité."
                                            }
                                            priority_propagation_log.append(log_entry)
                                            logger.info(f"   🔺 OF {producer_of} rendu URGENT (fabrique {article_needed} pour OF {urgent_id})")
                    
                    # Mettre à jour les ordres avec la priorité propagée
                    for o in orders:
                        o['_propagated_priority'] = propagated_priority.get(o.get('id'), 0)
                        o['_is_urgent'] = propagated_priority.get(o.get('id'), 0) == 1
                else:
                    for o in orders:
                        o['_propagated_priority'] = o.get('priority', 0)
                        o['_is_urgent'] = o.get('priority', 0) == 1
            
            # PROPAGATION BASÉE SUR LES DATES DE BESOIN (dépendances matière)
            # Si un OF a une date de besoin et dépend d'un autre OF pour la matière,
            # l'OF producteur doit être planifié en priorité pour permettre au consommateur de respecter sa deadline
            
            # Construire la liste des besoins matière par OF
            material_dependencies = {}  # {consumer_of: [{article, producer_of, due_date}]}
            critical_producers = {}  # {producer_of: earliest_deadline}
            
            if ignore_material_propagation:
                logger.info("\n🚫 PROPAGATION MATIÈRE DÉSACTIVÉE: Les dépendances entre OFs ne sont pas analysées")
                # Aucune dépendance matière ne sera créée, tous les OFs sont indépendants
                for order in orders:
                    order['_critical_for_deadline'] = None
                    order['_is_critical_producer'] = False
            else:
                logger.info("\n📆 ANALYSE DES DÉPENDANCES MATIÈRE POUR DATES DE BESOIN:")
                
                for order in orders:
                    order_id = order.get('id')
                    due_date_str = order.get('due_date')
                    if not due_date_str:
                        continue
                    
                    try:
                        due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                    except:
                        continue
                    
                    # Trouver les opérations de cet OF et leurs besoins matière
                    order_ops = [op for op in operations if op.get('order_id') == order_id]
                    
                    for op in order_ops:
                        op_id = op.get('id')
                        materials = self.material_manager.get_operation_materials(op_id)
                        
                        for mat in materials:
                            article_needed = mat.article_composant_id
                            qty_needed = mat.quantity
                            
                            # Vérifier si cet article est fabriqué par un autre OF
                            if article_needed in article_producers:
                                # IMPORTANT: Ne propager la priorité que si le stock projeté est INSUFFISANT
                                # Le stock projeté au moment du démarrage de l'opération consommatrice
                                # doit être vérifié SANS compter les productions de cet OF
                                
                                # Estimer la date de démarrage de l'opération consommatrice
                                # Pour simplifier, on utilise le scheduling_start + un délai estimé
                                estimated_start = self.scheduling_start
                                
                                # Calculer le stock projeté à cette date (hors productions non encore planifiées)
                                projected_stock = self.material_manager.get_projected_stock(article_needed, estimated_start)
                                
                                # Si le stock projeté est suffisant, pas besoin de propager la priorité
                                if projected_stock >= qty_needed:
                                    logger.info(f"   ✓ {order_id}/{op_id}: stock projeté de {article_needed} suffisant ({projected_stock} >= {qty_needed}) - pas de propagation")
                                    continue
                                
                                # Stock insuffisant - propager la priorité vers le producteur
                                for producer_of in article_producers[article_needed]:
                                    if producer_of != order_id:
                                        if order_id not in material_dependencies:
                                            material_dependencies[order_id] = []
                                        material_dependencies[order_id].append({
                                            'article': article_needed,
                                            'producer_of': producer_of,
                                            'due_date': due_date,
                                            'operation_id': op_id,
                                            'qty_needed': qty_needed,
                                            'projected_stock': projected_stock
                                        })
                                        logger.info(f"   📦 {order_id} (besoin: {due_date.strftime('%d/%m %H:%M')}) dépend de {producer_of} pour {article_needed} (stock={projected_stock} < besoin={qty_needed})")
                
                # Marquer les OFs producteurs comme "critiques" pour la planification
                # Ils devront être planifiés en priorité pour respecter les deadlines des consommateurs
                
                for consumer_of, deps in material_dependencies.items():
                    for dep in deps:
                        producer_of = dep['producer_of']
                        due_date = dep['due_date']
                        
                        if producer_of not in critical_producers or due_date < critical_producers[producer_of]:
                            critical_producers[producer_of] = due_date
                
                # Mettre à jour les ordres avec les infos de criticité
                for order in orders:
                    order_id = order.get('id')
                    if order_id in critical_producers:
                        order['_critical_for_deadline'] = critical_producers[order_id].isoformat()
                        order['_is_critical_producer'] = True
                        logger.info(f"   🔴 {order_id} marqué CRITIQUE (doit finir avant {critical_producers[order_id].strftime('%d/%m %H:%M')} pour un OF consommateur)")
                    else:
                        order['_critical_for_deadline'] = None
                        order['_is_critical_producer'] = False
            
            # PHASE 1.5: AUTO-ASSIGNATION DES MACHINES
            # PHASE 1.5: CRÉATION DE MACHINES VIRTUELLES pour les centres sans machines
            # Identifier les centres de charge utilisés par les opérations mais sans machines
            op_centres = {}
            for op in operations:
                centre = op.get('centre_de_charge_id')
                if centre:
                    if centre not in op_centres:
                        op_centres[centre] = {'count': 0, 'total_duration': 0}
                    op_centres[centre]['count'] += 1
                    duration = (op.get('production_time_minutes', 0) or 0) + (op.get('setup_time_minutes', 0) or 0)
                    op_centres[centre]['total_duration'] += duration
            
            machine_centres = set(m.get('centre_de_charge_id') for m in machines if m.get('centre_de_charge_id'))
            missing_centres = set(op_centres.keys()) - machine_centres
            
            if missing_centres:
                logger.info(f"\n🏭 CRÉATION DE MACHINES VIRTUELLES pour {len(missing_centres)} centres sans machines:")
                
                # Calculer le nombre de machines nécessaires basé sur la charge
                horizon_days = 14
                work_hours_per_day = 9  # 7h45 - 16h45
                capacity_per_machine = horizon_days * work_hours_per_day * 60  # en minutes
                
                for centre_id in sorted(missing_centres):
                    centre_data = op_centres.get(centre_id, {'count': 0, 'total_duration': 0})
                    total_duration = centre_data['total_duration']
                    
                    # Calculer le nombre de machines nécessaires
                    num_machines = max(1, int(total_duration / capacity_per_machine) + 1)
                    # Limiter à un maximum raisonnable
                    num_machines = min(num_machines, 10)
                    
                    for i in range(num_machines):
                        machine_id = f'VIRTUAL_{centre_id}' if num_machines == 1 else f'VIRTUAL_{centre_id}_{i+1}'
                        virtual_machine = {
                            'id': machine_id,
                            'nom': f'Machine virtuelle {centre_id}' + (f' #{i+1}' if num_machines > 1 else ''),
                            'centre_de_charge_id': centre_id,
                            'is_virtual': True
                        }
                        machines.append(virtual_machine)
                    
                    if num_machines > 1:
                        logger.info(f"   ✓ Centre {centre_id}: {num_machines} machines virtuelles créées (charge={total_duration/60:.0f}h, capacité={capacity_per_machine*num_machines/60:.0f}h)")
                    else:
                        logger.info(f"   ✓ Machine virtuelle créée: VIRTUAL_{centre_id} (charge={total_duration/60:.0f}h)")
                
                # Log récapitulatif après ajout
                machine_centres_after = set(m.get('centre_de_charge_id') for m in machines if m.get('centre_de_charge_id'))
                logger.info(f"   Total machines après ajout: {len(machines)} - Centres couverts: {len(machine_centres_after)}")
            
            # L'auto-assignation est TOUJOURS nécessaire si les opérations n'ont pas de machine
            # La condition ignore_rules ne doit pas bloquer l'assignation de base
            if auto_assign_machines:
                logger.info("\n🤖 Auto-assignation des machines activée")
                # IMPORTANT: Recréer le MachineAssigner APRÈS l'ajout des machines virtuelles
                # pour que l'index machines_by_centre soit à jour
                assigner = MachineAssigner(machines, rules_engine if not ignore_rules else None)
                assignment_result = assigner.assign_machines_to_operations(operations, orders)
                self.diagnostics.report['machine_assignment'] = assignment_result
                
                # Log du résultat de l'assignation
                assigned_count = sum(1 for op in operations if op.get('machine_id'))
                logger.info(f"   Opérations avec machine assignée: {assigned_count}/{len(operations)}")
            
            # PHASE 1.6: FRACTIONNEMENT DES OPÉRATIONS LONGUES
            # Si une opération dépasse la durée de travail quotidienne, elle est fractionnée
            # en plusieurs sous-opérations qui reprennent à la période d'ouverture suivante
            split_stats = {
                'split_enabled': allow_splitting,
                'original_operations_count': len(operations),
                'operations_split': 0,
                'sub_operations_created': 0
            }
            
            if allow_splitting and self.calendar_manager and not ignore_calendars:
                logger.info("\n✂️  FRACTIONNEMENT DES OPÉRATIONS LONGUES:")
                
                new_operations = []
                operations_to_remove = []
                
                for op in operations:
                    op_id = op.get('id')
                    machine_id = op.get('machine_id')
                    
                    if not machine_id:
                        continue
                    
                    # Calculer la durée totale de l'opération
                    production_time = op.get('production_time_minutes', 0) or 0
                    setup_time = op.get('setup_time_minutes', 0) or 0
                    total_duration = production_time + setup_time
                    
                    # Récupérer les heures de travail quotidiennes pour cette machine
                    calendar = self.calendar_manager.get_calendar_for_machine(machine_id)
                    work_start_str = calendar.get('start_time', '')
                    work_end_str = calendar.get('end_time', '')
                    
                    if work_start_str and ':' in work_start_str:
                        parts = work_start_str.split(':')
                        work_start_min = int(parts[0]) * 60 + int(parts[1])
                    else:
                        work_start_min = calendar.get('start_hour', 0) * 60
                    
                    if work_end_str and ':' in work_end_str:
                        parts = work_end_str.split(':')
                        work_end_min = int(parts[0]) * 60 + int(parts[1])
                    else:
                        work_end_min = calendar.get('end_hour', 24) * 60
                    
                    daily_work_minutes = work_end_min - work_start_min
                    
                    # Si calendrier 24/7, pas besoin de fractionner
                    if daily_work_minutes >= 24 * 60 - 60:  # 23h ou plus
                        continue
                    
                    # Vérifier si l'opération doit être fractionnée
                    if total_duration > daily_work_minutes:
                        # Calculer le nombre de fractions nécessaires
                        num_splits = math.ceil(total_duration / daily_work_minutes)
                        
                        # Limiter le nombre de fractions pour éviter l'explosion
                        max_splits = 10
                        if num_splits > max_splits:
                            logger.warning(f"   ⚠️  Op {op_id}: Durée {total_duration}min nécessiterait {num_splits} fractions, limité à {max_splits}")
                            num_splits = max_splits
                        
                        logger.info(f"   ✂️  Op {op_id}: {total_duration}min > {daily_work_minutes}min/jour → {num_splits} fractions")
                        
                        # Marquer l'opération originale pour suppression
                        operations_to_remove.append(op_id)
                        split_stats['operations_split'] += 1
                        
                        # Créer les sous-opérations
                        remaining_duration = total_duration
                        for i in range(num_splits):
                            # Durée de cette fraction
                            fraction_duration = min(daily_work_minutes, remaining_duration)
                            remaining_duration -= fraction_duration
                            
                            # Créer la sous-opération
                            sub_op = op.copy()
                            sub_op['id'] = f"{op_id}_PART{i+1}"
                            sub_op['_parent_operation_id'] = op_id
                            sub_op['_is_split_operation'] = True
                            sub_op['_split_index'] = i
                            sub_op['_split_total'] = num_splits
                            
                            # La première fraction inclut le setup time
                            if i == 0:
                                sub_op['production_time_minutes'] = fraction_duration - setup_time if fraction_duration > setup_time else fraction_duration
                                sub_op['setup_time_minutes'] = setup_time if fraction_duration > setup_time else 0
                            else:
                                sub_op['production_time_minutes'] = fraction_duration
                                sub_op['setup_time_minutes'] = 0  # Pas de setup pour les fractions suivantes
                            
                            new_operations.append(sub_op)
                            split_stats['sub_operations_created'] += 1
                
                # Appliquer les modifications
                if operations_to_remove:
                    operations = [op for op in operations if op.get('id') not in operations_to_remove]
                    operations.extend(new_operations)
                    
                    logger.info(f"\n   📊 RÉSUMÉ DU FRACTIONNEMENT:")
                    logger.info(f"      Opérations fractionnées: {split_stats['operations_split']}")
                    logger.info(f"      Sous-opérations créées: {split_stats['sub_operations_created']}")
                    logger.info(f"      Total opérations: {len(operations)}")
            else:
                if allow_splitting:
                    logger.info("\n✂️  FRACTIONNEMENT: Désactivé (calendriers ignorés ou non définis)")
                else:
                    logger.info("\n✂️  FRACTIONNEMENT: Désactivé par option")
            
            split_stats['final_operations_count'] = len(operations)
            
            # PHASE 2: ANALYSE DE FAISABILITÉ
            feasible_count, blocked_count = self.diagnostics.analyze_all_operations(
                operations, orders, machines, rules_engine, material_checker
            )
            
            # PHASE 2.5: PRÉ-ESTIMATION DES PRODUCTIONS (pour vérification matière)
            # Estimer quand chaque OF va produire son article, basé sur les durées des opérations
            if not ignore_material:
                logger.info("\n📦 PRÉ-ESTIMATION DES PRODUCTIONS:")
                
                # Regrouper les opérations par OF
                ops_by_order = {}
                for op in operations:
                    order_id = op.get('order_id')
                    if order_id:
                        if order_id not in ops_by_order:
                            ops_by_order[order_id] = []
                        ops_by_order[order_id].append(op)
                
                # Pour chaque OF, calculer la durée totale estimée
                for order in orders:
                    order_id = order.get('id')
                    article_produit = order.get('article_id') or order.get('article')
                    quantity_produite = order.get('quantity', 0)
                    
                    if not article_produit or not order_id:
                        continue
                    
                    order_ops = ops_by_order.get(order_id, [])
                    if not order_ops:
                        continue
                    
                    # Calculer la durée totale (somme des durées + transferts)
                    total_duration = 0
                    last_transfer_time = 0
                    for op in sorted(order_ops, key=lambda x: x.get('id', '').rsplit('_', 1)[-1] if '_' in x.get('id', '') else '0'):
                        duration = op.get('duration_minutes') or op.get('planned_duration', 0)
                        transfer = op.get('transfer_time_minutes', 0)
                        total_duration += duration + transfer
                        last_transfer_time = transfer
                    
                    # Date de fin estimée = scheduling_start + durée totale
                    # On ajoute une marge de 8h (1 journée de travail) pour les contraintes calendrier
                    estimated_end = self.scheduling_start + timedelta(minutes=total_duration + 480)
                    
                    # Ajouter la production estimée au MaterialManager
                    self.material_manager.add_planned_production(
                        order_id=order_id,
                        article_id=article_produit,
                        quantity=quantity_produite,
                        end_date=estimated_end
                    )
                    logger.info(f"   📦 {order_id} -> {article_produit} x{quantity_produite} estimé le {estimated_end.strftime('%d/%m %H:%M')}")
            
            # PHASE 3: FILTRAGE ET TRI DES OPÉRATIONS VALIDES
            # Index des ordres pour enrichissement
            orders_by_id = {o.get('id'): o for o in orders}
            
            valid_operations = []
            blocked_operations = []
            material_delayed_operations = []  # Opérations reportées pour manque matière
            
            for op in operations:
                order_id = op.get('order_id')
                order = orders_by_id.get(order_id)
                op_id = op.get('id')
                
                is_valid = True
                blocking_reason = None
                material_status = None
                earliest_material_date = None
                
                # Vérification machine
                machine_id = op.get('machine_id')
                if not machine_id:
                    is_valid = False
                    blocking_reason = 'Aucune machine assignée'
                elif not any(m.get('id') == machine_id for m in machines):
                    is_valid = False
                    blocking_reason = f'Machine {machine_id} introuvable'
                
                # Vérification matière avec projection
                if is_valid and not ignore_material:
                    # Vérifier les besoins matière de l'opération
                    material_status = self.material_manager.check_operation_materials(
                        op_id,
                        self.scheduling_start
                    )
                    
                    if not material_status.all_available:
                        # Reporter l'opération à la date de disponibilité
                        earliest_material_date = material_status.earliest_start_date
                        if earliest_material_date:
                            logger.info(f"⏳ Opération {op_id} reportée pour matière: {material_status.blocking_components}")
                            logger.info(f"   Disponible à partir de: {earliest_material_date}")
                            material_delayed_operations.append({
                                'operation_id': op_id,
                                'blocking_components': material_status.blocking_components,
                                'earliest_date': earliest_material_date.isoformat()
                            })
                        else:
                            is_valid = False
                            blocking_reason = f'Matière insuffisante: {material_status.blocking_components}'
                
                if is_valid:
                    # Enrichir avec date_besoin pour le tri et informations d'urgence
                    is_urgent = order.get('_is_urgent', False) if order else False
                    propagated_priority = order.get('_propagated_priority', 0) if order else 0
                    order_quantity = order.get('quantity', 0) if order else 0
                    
                    op_enriched = {
                        **op,
                        '_date_besoin': order.get('due_date') if order else None,
                        '_priority': propagated_priority,  # Utiliser la priorité propagée
                        '_original_priority': order.get('priority', 0) if order else 0,
                        '_is_urgent': is_urgent,
                        '_article_id': (order.get('article_id') or order.get('article')) if order else None,
                        '_order_quantity': order_quantity,
                        '_material_earliest_date': earliest_material_date,
                        '_material_status': material_status
                    }
                    valid_operations.append(op_enriched)
                else:
                    # Récupérer l'article_id de l'ordre si disponible
                    article_id = None
                    if order:
                        article_id = order.get('article_id') or order.get('article')
                    
                    blocked_operations.append({
                        'operation_id': op.get('id'),
                        'order_id': op.get('order_id'),
                        'article_id': article_id,
                        'reason': blocking_reason or 'Raison inconnue'
                    })
            
            logger.info(f"📊 Opérations valides pour le solveur: {len(valid_operations)}")
            logger.info(f"📊 Opérations bloquées: {len(blocked_operations)}")
            logger.info(f"📊 Opérations reportées matière: {len(material_delayed_operations)}")
            
            if len(valid_operations) == 0:
                logger.error("❌ Aucune opération valide pour l'ordonnancement")
                return {
                    'status': 'NO_VALID_OPERATIONS',
                    'operations': [],
                    'conflicts': blocked_operations,
                    'material_delayed': material_delayed_operations,
                    'solver_time': 0,
                    'diagnostics': self.diagnostics.get_report()
                }
            
            # Trier les opérations par urgence (date_besoin)
            def get_sort_key(op):
                date_besoin = op.get('_date_besoin')
                priority = op.get('_priority', 0)
                if date_besoin:
                    dt = self._parse_datetime(date_besoin)
                    if dt:
                        # S'assurer que la date a une timezone pour la comparaison
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=PARIS_TZ)
                        return (dt, -priority)
                # Utiliser une date max avec timezone pour la comparaison
                return (datetime.max.replace(tzinfo=PARIS_TZ), -priority)
            
            valid_operations.sort(key=get_sort_key)
            
            # PHASE 4: CONSTRUCTION DU MODÈLE OR-TOOLS
            model = cp_model.CpModel()
            
            # Horizon de planification basé sur le paramètre utilisateur
            # IMPORTANT: Le paramètre horizon_days est un FILTRE sur les ordres à inclure,
            # PAS une limite sur la durée du planning. Le solveur doit pouvoir planifier
            # au-delà si nécessaire (ex: dépendances, ordres en retard).
            user_horizon_days = options.get('horizon_days', 14)
            logger.info(f"\n   📅 Horizon de sélection: {user_horizon_days} jours" if user_horizon_days > 0 else "")
            
            # Calculer l'horizon nécessaire en fonction des contraintes matière et des temps de transfert
            max_material_constraint = 0
            for op in valid_operations:
                op_id = op.get('id')
                if op_id in material_date_constraints:
                    min_date = material_date_constraints[op_id]
                    min_minutes = self._datetime_to_minutes(min_date)
                    max_material_constraint = max(max_material_constraint, min_minutes)
                elif op.get('_material_earliest_date') and op.get('_material_earliest_date') > self.scheduling_start:
                    min_date = op.get('_material_earliest_date')
                    min_minutes = self._datetime_to_minutes(min_date)
                    max_material_constraint = max(max_material_constraint, min_minutes)
            
            # L'horizon du solveur est TOUJOURS suffisamment grand pour accueillir toutes les opérations
            # Base: max(30 jours, contrainte matière max + 14 jours de marge pour les séquences)
            base_horizon = 30 * 24 * 60  # 30 jours minimum
            horizon = max(base_horizon, max_material_constraint + 14 * 24 * 60)
            
            logger.info(f"   📐 Horizon de planification effectif: {horizon} minutes ({horizon // (24*60)} jours)")
            
            # Stocker l'horizon utilisateur pour référence (pas pour contraindre les fins)
            user_horizon_minutes = user_horizon_days * 24 * 60 if user_horizon_days > 0 else 0
            
            # Index des ordres pour accéder à _horizon_inclusion_reason
            orders_index = {o.get('id'): o for o in orders}
            
            # Variables de décision
            start_vars = {}
            end_vars = {}
            interval_vars = {}
            machine_to_intervals = {}
            
            # Convertir l'horizon en entier
            horizon = int(horizon)
            
            # Créer les variables pour chaque opération valide
            for op in valid_operations:
                op_id = op.get('id')
                # OR-Tools nécessite des entiers - arrondir la durée
                duration = int(op.get('production_time_minutes', 60) + op.get('setup_time_minutes', 0))
                
                # CORRECTION: Durée minimum de 1 minute pour éviter les opérations de durée 0
                # qui peuvent contourner les contraintes de calendrier et ne pas s'afficher sur le Gantt
                if duration < 1:
                    duration = 1
                    logger.info(f"   ⚠️ Op {op_id}: durée forcée à 1 min (était 0)")
                
                # CONTRAINTE MATIÈRE: Date minimum de début
                # IMPORTANT: N'utiliser que les contraintes des itérations précédentes
                # qui sont basées sur les vraies dates de production calculées par le solver.
                # CORRECTION: La contrainte matière doit TOUJOURS être appliquée même à la 1ère itération
                min_start = 0
                min_date_source = None
                
                # D'abord, vérifier les contraintes des itérations précédentes (priorité)
                if op_id in material_date_constraints:
                    # Contrainte des itérations précédentes (date de production réelle)
                    min_date = material_date_constraints[op_id]
                    min_start = int(self._datetime_to_minutes(min_date))
                    min_start = max(0, min_start)
                    min_date_source = f"itération précédente ({min_date.strftime('%d/%m %H:%M')})"
                
                # CORRECTION: Appliquer aussi la contrainte de pré-validation matière si pas d'autre contrainte
                # Cette contrainte est STRICTE - une opération NE PEUT PAS commencer avant que la matière soit disponible
                elif not ignore_material and op.get('_material_earliest_date'):
                    mat_earliest = op.get('_material_earliest_date')
                    if mat_earliest and mat_earliest > self.scheduling_start:
                        min_start = int(self._datetime_to_minutes(mat_earliest))
                        min_start = max(0, min_start)
                        min_date_source = f"disponibilité matière ({mat_earliest.strftime('%d/%m %H:%M')})"
                
                if min_date_source:
                    logger.info(f"   📦 {op_id}: contrainte matière start >= {min_start} min - {min_date_source}")
                
                # Vérifier que le domaine est valide (min_start < horizon - duration)
                max_start = horizon - duration
                if min_start > max_start:
                    # L'opération ne peut pas tenir dans l'horizon avec la contrainte matière
                    # On l'exclut et on l'ajoute aux opérations bloquées
                    logger.warning(f"   ❌ {op_id}: Contrainte matière ({min_start}min) dépasse l'horizon ({max_start}min) - Opération exclue")
                    blocked_operations.append({
                        'operation_id': op_id,
                        'order_id': op.get('order_id'),
                        'article_id': op.get('_article_id'),
                        'reason': f"Matière non disponible avant la fin de l'horizon ({min_date_source})"
                    })
                    continue  # Passer à l'opération suivante
                
                # Variable de début (avec contrainte matière si applicable)
                start_var = model.new_int_var(min_start, max_start, f'start_{op_id}')
                start_vars[op_id] = start_var
                
                # Variable de fin
                end_var = model.new_int_var(duration + min_start, horizon, f'end_{op_id}')
                end_vars[op_id] = end_var
                
                # Lier début et fin
                model.add(end_var == start_var + duration)
                
                # NOTE: L'horizon est un FILTRE sur les ordres, pas une contrainte de fin
                # Les opérations peuvent se terminer après J+horizon si nécessaire
                # (ex: séquences avec temps de transfert longs)
                
                # Variable d'intervalle pour NoOverlap
                interval_var = model.new_interval_var(
                    start_var, duration, end_var, f'interval_{op_id}'
                )
                interval_vars[op_id] = interval_var
                
                # Grouper par machine pour la contrainte NoOverlap
                machine_id = op.get('machine_id')
                if machine_id:
                    if machine_id not in machine_to_intervals:
                        machine_to_intervals[machine_id] = []
                    machine_to_intervals[machine_id].append({
                        'interval': interval_var,
                        'op_id': op_id,
                        'duration': duration,
                        'min_start': min_start
                    })
            
            # Log des contraintes matière actives
            if material_date_constraints:
                logger.info(f"\n📦 ITÉRATION {current_iteration}: {len(material_date_constraints)} contraintes matière actives")
            
            # Log solver input
            self.diagnostics.log_solver_input(valid_operations, machine_to_intervals, horizon)
            
            # CONTRAINTE CRITIQUE: Non-chevauchement par machine
            logger.info("\n📌 CONTRAINTES DE NON-CHEVAUCHEMENT:")
            for machine_id, intervals_data in machine_to_intervals.items():
                intervals = [i['interval'] for i in intervals_data]
                if len(intervals) > 1:
                    model.add_no_overlap(intervals)
                    op_ids = [i['op_id'] for i in intervals_data]
                    logger.info(f"   ✓ Machine {machine_id}: {len(intervals)} opérations")
                    logger.info(f"      Opérations: {op_ids}")
                elif len(intervals) == 1:
                    logger.info(f"   ○ Machine {machine_id}: 1 seule opération (pas de contrainte)")
            
            # CONTRAINTES DE CALENDRIER: Restreindre les opérations aux plages de travail
            calendar_constraints_count = 0
            if self.calendar_manager and not ignore_calendars:
                logger.info("\n📌 CONTRAINTES DE CALENDRIER:")
                
                for machine_id, intervals_data in machine_to_intervals.items():
                    calendar = self.calendar_manager.get_calendar_for_machine(machine_id)
                    working_days = set(calendar.get('working_days', [0, 1, 2, 3, 4, 5, 6]))
                    
                    # Récupérer les heures de travail
                    start_time_str = calendar.get('start_time', '')
                    end_time_str = calendar.get('end_time', '')
                    
                    if start_time_str and ':' in start_time_str:
                        parts = start_time_str.split(':')
                        work_start_hour = int(parts[0])
                        work_start_min = int(parts[1]) if len(parts) > 1 else 0
                    else:
                        work_start_hour = calendar.get('start_hour', 0)
                        work_start_min = 0
                    
                    if end_time_str and ':' in end_time_str:
                        parts = end_time_str.split(':')
                        work_end_hour = int(parts[0])
                        work_end_min = int(parts[1]) if len(parts) > 1 else 0
                    else:
                        work_end_hour = calendar.get('end_hour', 24)
                        work_end_min = 0
                    
                    work_start_minutes = work_start_hour * 60 + work_start_min
                    work_end_minutes = work_end_hour * 60 + work_end_min
                    daily_work_minutes = work_end_minutes - work_start_minutes
                    
                    # Vérifier si le calendrier est 24/7 (pas de contrainte)
                    if working_days == {0, 1, 2, 3, 4, 5, 6} and work_start_minutes == 0 and work_end_minutes >= 23*60:
                        logger.info(f"   ○ Machine {machine_id}: Calendrier 24/7 (pas de contrainte)")
                        continue
                    
                    # Calculer les plages interdites
                    forbidden_slots = []
                    base_date = self.scheduling_start.replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    for day_offset in range(21):  # 3 semaines
                        day_start = base_date + timedelta(days=day_offset)
                        day_weekday = day_start.weekday()
                        day_start_min = int((day_start - self.scheduling_start).total_seconds() / 60)
                        
                        if day_weekday not in working_days:
                            # Journée entière non travaillée (week-end)
                            slot_start = day_start_min
                            slot_end = day_start_min + 24 * 60
                            if slot_end > 0 and slot_start < horizon:
                                forbidden_slots.append((max(0, slot_start), min(slot_end, horizon)))
                        else:
                            # Jour travaillé - ajouter MATIN et SOIR
                            if work_start_minutes > 0:
                                slot_start = day_start_min
                                slot_end = day_start_min + work_start_minutes
                                if slot_end > 0 and slot_start < horizon:
                                    forbidden_slots.append((max(0, slot_start), min(slot_end, horizon)))
                            
                            if work_end_minutes < 24 * 60:
                                slot_start = day_start_min + work_end_minutes
                                slot_end = day_start_min + 24 * 60
                                if slot_end > 0 and slot_start < horizon:
                                    forbidden_slots.append((max(0, slot_start), min(slot_end, horizon)))
                    
                    if not forbidden_slots:
                        continue
                    
                    # Fusionner les plages adjacentes
                    forbidden_slots.sort()
                    merged_slots = []
                    for slot in forbidden_slots:
                        if merged_slots and slot[0] <= merged_slots[-1][1]:
                            merged_slots[-1] = (merged_slots[-1][0], max(merged_slots[-1][1], slot[1]))
                        else:
                            merged_slots.append(slot)
                    
                    # Séparer week-ends et horaires journaliers
                    weekend_slots = [(s, e) for s, e in merged_slots if (e - s) >= 24*60]
                    daily_slots = [(s, e) for s, e in merged_slots if (e - s) < 24*60]
                    
                    logger.info(f"   ✓ Machine {machine_id}: {len(weekend_slots)} week-ends, {len(daily_slots)} plages horaires")
                    logger.info(f"      Horaires: {work_start_hour:02d}:{work_start_min:02d} - {work_end_hour:02d}:{work_end_min:02d} ({daily_work_minutes}min/jour)")
                    
                    for interval_data in intervals_data:
                        op_id = interval_data['op_id']
                        if op_id not in start_vars or op_id not in end_vars:
                            continue
                        
                        start_var = start_vars[op_id]
                        end_var = end_vars[op_id]
                        op_duration = interval_data['duration']
                        
                        # TOUJOURS contraindre les week-ends (plages longues)
                        for slot_start, slot_end in weekend_slots:
                            b = model.new_bool_var(f'weekend_{op_id}_{slot_start}')
                            model.add(end_var <= slot_start).only_enforce_if(b)
                            model.add(start_var >= slot_end).only_enforce_if(b.Not())
                            calendar_constraints_count += 1
                        
                        # Contraindre les horaires journaliers SEULEMENT si l'opération peut tenir dans une journée
                        # Si l'opération dure plus longtemps que la journée de travail, on la laisse dépasser
                        if op_duration <= daily_work_minutes:
                            for slot_start, slot_end in daily_slots:
                                b = model.new_bool_var(f'daily_{op_id}_{slot_start}')
                                model.add(end_var <= slot_start).only_enforce_if(b)
                                model.add(start_var >= slot_end).only_enforce_if(b.Not())
                                calendar_constraints_count += 1
                        else:
                            logger.info(f"      ⚠️  Op {op_id}: durée {op_duration}min > {daily_work_minutes}min/jour - horaires assouplis")
                
                logger.info(f"\n   Total: {calendar_constraints_count} contraintes de calendrier")
            else:
                logger.info("\n📌 CONTRAINTES DE CALENDRIER: Désactivées")
            
            # CONTRAINTES D'INDISPONIBILITÉ MACHINES
            unavailability_constraints_count = 0
            if self.unavailability_manager.machine_unavailabilities:
                logger.info("\n📌 CONTRAINTES D'INDISPONIBILITÉ MACHINES:")
                
                for machine_id, machine_intervals in machine_to_intervals.items():
                    unavails = self.unavailability_manager.get_unavailabilities_for_machine(machine_id)
                    
                    if not unavails:
                        continue
                    
                    logger.info(f"   Machine {machine_id}: {len(unavails)} période(s) d'indisponibilité")
                    
                    for interval_data in machine_intervals:
                        op_id = interval_data['op_id']
                        if op_id not in start_vars or op_id not in end_vars:
                            continue
                        
                        start_var = start_vars[op_id]
                        end_var = end_vars[op_id]
                        
                        for unavail in unavails:
                            unavail_start = unavail['start_minutes']
                            unavail_end = unavail['end_minutes']
                            
                            # L'opération doit être SOIT avant SOIT après l'indisponibilité
                            b = model.new_bool_var(f'unavail_{op_id}_{unavail_start}')
                            
                            # Si b=True: L'opération se termine AVANT l'indisponibilité
                            model.add(end_var <= unavail_start).only_enforce_if(b)
                            # Si b=False: L'opération commence APRÈS l'indisponibilité
                            model.add(start_var >= unavail_end).only_enforce_if(b.Not())
                            
                            unavailability_constraints_count += 1
                            logger.info(f"      🚫 {op_id}: éviter [{unavail['start_datetime'].strftime('%d/%m %H:%M')} - {unavail['end_datetime'].strftime('%d/%m %H:%M')}] ({unavail['reason']})")
                
                logger.info(f"\n   Total: {unavailability_constraints_count} contraintes d'indisponibilité")
            
            # Contraintes de séquence (opérations d'un même OF)
            operations_by_order = {}
            for op in valid_operations:
                order_id = op.get('order_id')
                if order_id:
                    if order_id not in operations_by_order:
                        operations_by_order[order_id] = []
                    operations_by_order[order_id].append(op)
            
            sequence_constraints_count = 0
            transfer_time_applied = 0
            logger.info("\n📌 CONTRAINTES DE SÉQUENCE (gammes) + TEMPS DE TRANSFERT:")
            for order_id, order_ops in operations_by_order.items():
                # Trier par numéro d'opération dans la gamme
                sorted_ops = sorted(order_ops, key=lambda x: x.get('operation_id', 0))
                for i in range(len(sorted_ops) - 1):
                    op1 = sorted_ops[i]
                    op2 = sorted_ops[i + 1]
                    op1_id = op1.get('id')
                    op2_id = op2.get('id')
                    
                    # Récupérer le temps de transfert de l'opération 1 (temps pour aller vers op2)
                    # OR-Tools nécessite des entiers
                    # LIMITE: Maximum 8 heures (480 min) de temps de transfert pour éviter les problèmes infaisables
                    # Les temps > 8h sont probablement des délais d'attente, pas des transports physiques
                    MAX_TRANSFER_TIME = 480  # 8 heures
                    raw_transfer_time = int(op1.get('transfer_time_minutes', 0))
                    transfer_time = min(raw_transfer_time, MAX_TRANSFER_TIME)
                    
                    if raw_transfer_time > MAX_TRANSFER_TIME:
                        logger.debug(f"      ⚠️ {op1_id}: temps transfert réduit {raw_transfer_time} -> {MAX_TRANSFER_TIME} min")
                    
                    if op1_id in end_vars and op2_id in start_vars:
                        # Vérifier si op2 a une contrainte matière
                        op2_material_constraint = material_date_constraints.get(op2_id)
                        op2_prevalidation_constraint = op2.get('_material_earliest_date')
                        
                        if op2_material_constraint or op2_prevalidation_constraint:
                            # Si op2 a une contrainte matière, la contrainte de séquence est:
                            # start(op2) >= max(end(op1) + transfer_time, contrainte_matière)
                            # OR-Tools gère cela automatiquement via les bornes des variables,
                            # donc on ajoute quand même la contrainte de séquence
                            model.add(start_vars[op2_id] >= end_vars[op1_id] + transfer_time)
                            sequence_constraints_count += 1
                            if transfer_time > 0:
                                transfer_time_applied += 1
                                constraint_date = op2_material_constraint or op2_prevalidation_constraint
                                logger.info(f"      🚚 {op1_id} -> {op2_id}: +{transfer_time} min transfert (matière: {constraint_date.strftime('%d/%m %H:%M')})")
                        else:
                            # Pas de contrainte matière, séquence normale
                            model.add(start_vars[op2_id] >= end_vars[op1_id] + transfer_time)
                            sequence_constraints_count += 1
                            if transfer_time > 0:
                                transfer_time_applied += 1
                                logger.info(f"      🚚 {op1_id} -> {op2_id}: +{transfer_time} min de transfert")
                
                if len(sorted_ops) > 1:
                    ops_seq = [f"{o.get('id')}(op{o.get('operation_id')})" for o in sorted_ops]
                    logger.info(f"   ✓ OF {order_id}: {' -> '.join(ops_seq)}")
            
            logger.info(f"\n   Total: {sequence_constraints_count} contraintes de séquence, {transfer_time_applied} avec temps de transfert")
            
            # Récupérer la stratégie de planification
            scheduling_strategy = options.get('scheduling_strategy', 'ASAP')
            
            # Index des ordres pour accéder aux infos
            orders_by_id = {o.get('id'): o for o in orders}
            
            # STRATÉGIE ASAP (Au plus tôt) - Comportement par défaut
            # Objectif: minimiser le makespan + prioriser les producteurs critiques
            if scheduling_strategy == 'ASAP':
                # Identifier les opérations des producteurs critiques
                critical_producer_ops = []
                for op in valid_operations:
                    order_id = op.get('order_id')
                    order = orders_by_id.get(order_id, {})
                    if order.get('_is_critical_producer'):
                        op_id = op.get('id')
                        if op_id in end_vars:
                            critical_producer_ops.append(op_id)
                
                if critical_producer_ops:
                    logger.info("\n   🎯 PRIORISATION DES PRODUCTEURS CRITIQUES:")
                    logger.info(f"   {len(critical_producer_ops)} opérations de producteurs critiques")
                    
                    # Objectif multi-critères:
                    # 1. Minimiser la somme des fins des producteurs critiques (les terminer tôt)
                    # 2. Minimiser le makespan global
                    CRITICAL_PRIORITY_WEIGHT = 1000
                    
                    # Somme des fins des producteurs critiques
                    sum_critical_ends = model.new_int_var(0, horizon * len(critical_producer_ops), 'sum_critical_ends')
                    model.add(sum_critical_ends == sum(end_vars[op_id] for op_id in critical_producer_ops))
                    
                    # Makespan global
                    makespan = model.new_int_var(0, horizon, 'makespan')
                    model.add_max_equality(makespan, list(end_vars.values()))
                    
                    # Objectif combiné: minimiser (WEIGHT * sum_critical_ends + makespan)
                    combined_objective = model.new_int_var(0, CRITICAL_PRIORITY_WEIGHT * horizon * len(critical_producer_ops) + horizon, 'combined_objective')
                    model.add(combined_objective == CRITICAL_PRIORITY_WEIGHT * sum_critical_ends + makespan)
                    model.minimize(combined_objective)
                    
                    logger.info(f"   ✓ Objectif: minimiser {CRITICAL_PRIORITY_WEIGHT}×fins_critiques + makespan")
                else:
                    # Pas de producteurs critiques, minimiser simplement le makespan
                    if end_vars:
                        makespan = model.new_int_var(0, horizon, 'makespan')
                        model.add_max_equality(makespan, list(end_vars.values()))
                        model.minimize(makespan)
                
                logger.info("   ✓ Stratégie: ASAP (Au plus tôt)")
            
            # STRATÉGIE JIT (Juste-à-temps / Au plus tard)
            # Objectif: maximiser les temps de début tout en respectant les dates de besoin
            # Si la date de besoin ne peut pas être respectée, l'ordre est planifié en retard
            elif scheduling_strategy == 'JIT':
                logger.info("   ✓ Stratégie: JIT (Au plus tard)")
                
                # Index des ordres pour accéder aux dates de besoin
                orders_by_id = {o.get('id'): o for o in orders}
                
                # ÉTAPE 1: Identifier les producteurs critiques et leur deadline dérivée
                # Un producteur critique doit finir avant la deadline de son consommateur
                # pour que le consommateur puisse utiliser le composant à temps
                producer_derived_deadlines = {}  # {producer_of: derived_deadline}
                
                # D'abord, calculer la durée totale de chaque OF consommateur
                # (somme des durées de toutes ses opérations)
                consumer_total_durations = {}  # {order_id: total_minutes}
                for op in valid_operations:
                    order_id = op.get('order_id')
                    duration = op.get('production_time_minutes', 60) + op.get('setup_time_minutes', 0)
                    if order_id not in consumer_total_durations:
                        consumer_total_durations[order_id] = 0
                    consumer_total_durations[order_id] += duration
                
                for consumer_of, deps in material_dependencies.items():
                    consumer_order = orders_by_id.get(consumer_of, {})
                    consumer_due_date_str = consumer_order.get('due_date')
                    
                    if consumer_due_date_str:
                        try:
                            consumer_due_date = datetime.fromisoformat(consumer_due_date_str.replace('Z', '+00:00'))
                            
                            # Durée totale du consommateur
                            consumer_duration = consumer_total_durations.get(consumer_of, 0)
                            
                            for dep in deps:
                                producer_of = dep['producer_of']
                                
                                # Le producteur doit finir AVANT que le consommateur ne commence
                                # Deadline dérivée = deadline_consommateur - durée_consommateur
                                # Cela garantit que le composant est disponible quand le consommateur en a besoin
                                derived_deadline = consumer_due_date - timedelta(minutes=consumer_duration)
                                
                                # On garde la deadline la plus contraignante
                                if producer_of not in producer_derived_deadlines or derived_deadline < producer_derived_deadlines[producer_of]:
                                    producer_derived_deadlines[producer_of] = derived_deadline
                                    logger.info(f"   🎯 {producer_of}: deadline dérivée = {consumer_of} due {consumer_due_date.strftime('%d/%m %H:%M')} - {consumer_duration}min (durée OF) = {derived_deadline.strftime('%d/%m %H:%M')}")
                        except Exception:
                            pass
                
                # Identifier la dernière opération de chaque OF 
                # On utilise sequence_number si disponible, sinon on parse le suffixe de l'ID (ex: OF1_20 -> 20)
                last_ops_per_order = {}
                for op in valid_operations:
                    order_id = op.get('order_id')
                    op_id = op.get('id')
                    
                    # Déterminer le numéro de séquence
                    seq_num = op.get('sequence_number')
                    if seq_num is None:
                        # Extraire le numéro du suffixe (ex: OF1_20 -> 20)
                        try:
                            parts = op_id.rsplit('_', 1)
                            if len(parts) == 2:
                                seq_num = int(parts[1])
                            else:
                                seq_num = 0
                        except (ValueError, IndexError):
                            seq_num = 0
                    
                    if order_id not in last_ops_per_order or seq_num > last_ops_per_order[order_id]['sequence_number']:
                        last_ops_per_order[order_id] = {'op_id': op_id, 'sequence_number': seq_num, 'transfer_time': op.get('transfer_time_minutes', 0)}
                
                # Variables de retard pour chaque OF (contraintes souples)
                lateness_vars = {}  # Stocke la variable de retard par ordre
                due_date_targets = {}  # Stocke la date cible par ordre
                jit_constraints_added = 0
                ops_without_due_date = []
                
                # ÉTAPE 2: Créer les contraintes de deadline (souples) pour les consommateurs ET les producteurs
                for order_id, last_op_info in last_ops_per_order.items():
                    op_id = last_op_info['op_id']
                    order = orders_by_id.get(order_id, {})
                    # OR-Tools nécessite des entiers
                    transfer_time = int(last_op_info['transfer_time'])
                    
                    # Déterminer la date cible : deadline propre OU deadline dérivée (pour les producteurs critiques)
                    due_date_str = order.get('due_date')
                    derived_deadline = producer_derived_deadlines.get(order_id)
                    
                    # Choisir la deadline la plus contraignante
                    effective_deadline = None
                    deadline_source = None
                    
                    if due_date_str:
                        try:
                            own_deadline = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
                            effective_deadline = own_deadline
                            deadline_source = "propre"
                        except Exception:
                            pass
                    
                    if derived_deadline:
                        if effective_deadline is None or derived_deadline < effective_deadline:
                            effective_deadline = derived_deadline
                            deadline_source = "dérivée (producteur critique)"
                    
                    if effective_deadline and op_id in end_vars:
                        due_date_minutes = int(self._datetime_to_minutes(effective_deadline))
                        
                        # Date cible = date de besoin - temps de transfert final
                        target_end = int(due_date_minutes - transfer_time)
                        due_date_targets[order_id] = {
                            'due_date': effective_deadline,
                            'due_date_minutes': due_date_minutes,
                            'target_end': target_end,
                            'transfer_time': transfer_time,
                            'op_id': op_id,
                            'source': deadline_source
                        }
                        
                        # Contrainte SOUPLE: créer une variable de retard
                        # lateness = max(0, end_time - target_end)
                        lateness = model.new_int_var(0, horizon, f'lateness_{order_id}')
                        lateness_vars[order_id] = lateness
                        
                        # lateness >= end_time - target_end (si end > target, lateness capte le dépassement)
                        model.add(lateness >= end_vars[op_id] - target_end)
                        
                        jit_constraints_added += 1
                        logger.info(f"      📅 {op_id} (OF {order_id}): cible fin <= {effective_deadline.strftime('%d/%m %H:%M')} - {transfer_time}min transfert ({deadline_source})")
                    else:
                        ops_without_due_date.append(order_id)
                
                if ops_without_due_date:
                    logger.info(f"      ℹ️ {len(ops_without_due_date)} ordres sans date de besoin (planification ASAP)")
                
                logger.info(f"   ✓ {jit_constraints_added} contraintes de date de besoin ajoutées (souples)")
                
                # FLUX TIRÉ: Minimiser l'encours entre opérations d'un même OF
                # Pour chaque paire d'opérations consécutives, on calcule le "temps d'attente"
                # (temps entre la fin de op_n + transfert et le début de op_n+1)
                encours_vars = []  # Variables représentant le temps d'attente entre ops
                
                logger.info("\n   📦 MINIMISATION ENCOURS (flux tiré):")
                for order_id, order_ops in operations_by_order.items():
                    if len(order_ops) < 2:
                        continue
                    
                    sorted_ops = sorted(order_ops, key=lambda x: x.get('id', '').rsplit('_', 1)[-1] if '_' in x.get('id', '') else x.get('operation_id', 0))
                    
                    for i in range(len(sorted_ops) - 1):
                        op1 = sorted_ops[i]
                        op2 = sorted_ops[i + 1]
                        op1_id = op1.get('id')
                        op2_id = op2.get('id')
                        # OR-Tools nécessite des entiers
                        transfer_time = int(op1.get('transfer_time_minutes', 0))
                        
                        if op1_id in end_vars and op2_id in start_vars:
                            # Temps d'attente = start(op2) - (end(op1) + transfer_time)
                            # On veut minimiser ce temps d'attente
                            wait_time = model.new_int_var(0, horizon, f'wait_{op1_id}_{op2_id}')
                            
                            # wait_time >= start(op2) - end(op1) - transfer_time
                            model.add(wait_time >= start_vars[op2_id] - end_vars[op1_id] - transfer_time)
                            
                            encours_vars.append(wait_time)
                            logger.info(f"      {op1_id} -> {op2_id}: minimiser attente après transfert ({transfer_time}min)")
                
                logger.info(f"   ✓ {len(encours_vars)} variables d'encours créées")
                
                # Objectif JIT multi-critères:
                # 1. Minimiser les retards (priorité haute - pénalité forte)
                # 2. Minimiser les encours entre opérations (flux tiré)
                # 3. Maximiser les temps de début (planifier au plus tard)
                if start_vars:
                    # Pénalités
                    LATENESS_PENALTY = 100000  # Très forte pour éviter les retards
                    ENCOURS_PENALTY = 100      # Modérée pour réduire les encours
                    START_BONUS = 1            # Faible pour planifier tard (objectif secondaire)
                    
                    # Calculer la somme des débuts (à maximiser = planifier tard)
                    sum_starts = model.new_int_var(0, horizon * len(start_vars), 'sum_starts')
                    model.add(sum_starts == sum(start_vars.values()))
                    
                    # Calculer la somme des encours (à minimiser)
                    sum_encours = model.new_int_var(0, horizon * len(encours_vars) if encours_vars else 1, 'sum_encours')
                    if encours_vars:
                        model.add(sum_encours == sum(encours_vars))
                    else:
                        model.add(sum_encours == 0)
                    
                    # Calculer la somme des retards (à minimiser)
                    if lateness_vars:
                        sum_lateness = model.new_int_var(0, horizon * len(lateness_vars), 'sum_lateness')
                        model.add(sum_lateness == sum(lateness_vars.values()))
                        
                        # Objectif: maximiser (START_BONUS × sum_starts - ENCOURS_PENALTY × sum_encours - LATENESS_PENALTY × sum_lateness)
                        max_value = horizon * len(start_vars) * START_BONUS
                        min_value = -(horizon * len(lateness_vars) * LATENESS_PENALTY + horizon * len(encours_vars) * ENCOURS_PENALTY if encours_vars else horizon * len(lateness_vars) * LATENESS_PENALTY)
                        
                        objective = model.new_int_var(min_value, max_value, 'jit_objective')
                        model.add(objective == START_BONUS * sum_starts - ENCOURS_PENALTY * sum_encours - LATENESS_PENALTY * sum_lateness)
                        model.maximize(objective)
                        logger.info(f"   ✓ Objectif JIT: +{START_BONUS}×débuts - {ENCOURS_PENALTY}×encours - {LATENESS_PENALTY}×retards")
                    else:
                        # Pas de dates de besoin -> minimiser encours + maximiser débuts
                        max_value = horizon * len(start_vars) * START_BONUS
                        min_value = -(horizon * len(encours_vars) * ENCOURS_PENALTY if encours_vars else 0)
                        
                        objective = model.new_int_var(min_value, max_value, 'jit_objective')
                        model.add(objective == START_BONUS * sum_starts - ENCOURS_PENALTY * sum_encours)
                        model.maximize(objective)
                        logger.info(f"   ✓ Objectif JIT: +{START_BONUS}×débuts - {ENCOURS_PENALTY}×encours")
                
                # Stocker les infos de due_date pour le post-traitement
                jit_due_date_info = due_date_targets
            
            # PHASE 5: RÉSOLUTION
            solver = cp_model.CpSolver()
            # Utiliser le temps d'itération calculé (budget temps restant réparti)
            solver.parameters.max_time_in_seconds = iteration_time
            solver.parameters.num_search_workers = 4
            # Gap d'optimalité : arrêter si la solution est à moins de X% de l'optimum théorique
            solver.parameters.relative_gap_limit = optimization_gap
            
            logger.info(f"\n🔄 ITÉRATION {current_iteration} - Lancement du solveur OR-Tools CP-SAT")
            logger.info(f"   Budget temps total: {max_solver_time_seconds}s")
            logger.info(f"   Temps écoulé: {elapsed_time:.1f}s")
            logger.info(f"   Temps restant: {remaining_time:.1f}s")
            logger.info(f"   Temps alloué cette itération: {iteration_time:.1f}s")
            logger.info(f"   Gap d'optimalité: {optimization_gap*100:.1f}%")
            
            status = solver.solve(model)
            status_str = self._get_status_string(status)
            
            # Mettre à jour le temps cumulé
            total_solver_time += solver.wall_time
            logger.info(f"✓ Solveur terminé - Status: {status_str} (temps: {solver.wall_time:.2f}s, cumulé: {total_solver_time:.2f}s)")
            
            result = {
                'status': status_str,
                'operations': [],
                'conflicts': blocked_operations,
                'material_delayed': material_delayed_operations,
                'solver_time': solver.wall_time,
                'max_solver_time': max_solver_time_seconds,
                'objective_value': solver.objective_value if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else None,
                'scheduling_start': self.scheduling_start.isoformat(),
                'material_iteration': current_iteration,
                'scheduling_strategy': scheduling_strategy,  # Stocker la stratégie utilisée
                # Options avancées actives pour le diagnostic
                'active_options': {
                    'ignore_rules': ignore_rules,
                    'ignore_material': ignore_material,
                    'ignore_calendars': ignore_calendars,
                    'ignore_priorities': ignore_priorities,
                    'ignore_priority_propagation': ignore_priority_propagation,
                    'ignore_material_propagation': ignore_material_propagation
                }
            }
            
            # Extraire la solution
            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                logger.info(f"\n📊 SOLUTION TROUVÉE (itération {current_iteration}):")
                
                # Regrouper les opérations par OF pour identifier la dernière de chaque gamme
                ops_by_order = {}
                for op in valid_operations:
                    order_id = op.get('order_id')
                    if order_id not in ops_by_order:
                        ops_by_order[order_id] = []
                    ops_by_order[order_id].append(op)
                
                # Identifier la dernière opération de chaque OF
                last_op_of_order = {}
                for order_id, order_ops in ops_by_order.items():
                    sorted_ops = sorted(order_ops, key=lambda x: x.get('operation_id', 0))
                    if sorted_ops:
                        last_op_of_order[sorted_ops[-1].get('id')] = order_id
                
                scheduled_ops = []
                for op in valid_operations:
                    op_id = op.get('id')
                    if op_id in start_vars:
                        op_start_minutes = solver.value(start_vars[op_id])
                        op_end_minutes = solver.value(end_vars[op_id])
                        
                        # Temps de transfert vers l'opération suivante
                        transfer_time = op.get('transfer_time_minutes', 0)
                        
                        # Récupérer les matières premières de l'opération pour l'infobulle
                        materials_list = []
                        if self.material_manager:
                            op_materials = self.material_manager.get_operation_materials(op_id)
                            for mat in op_materials:
                                # Calculer le stock disponible à la date de début de l'opération
                                op_start_datetime = self._minutes_to_datetime(op_start_minutes)
                                projected_stock = self.material_manager.get_projected_stock(
                                    mat.article_composant_id, 
                                    op_start_datetime
                                )
                                materials_list.append({
                                    'article_id': mat.article_composant_id,
                                    'needed': mat.quantity,
                                    'in_stock': projected_stock,
                                    'available': projected_stock >= mat.quantity,
                                    'magasin': mat.magasin or 'Principal'
                                })
                        
                        scheduled_op = {
                            'operation_id': op_id,
                            'order_id': op.get('order_id'),
                            'article_id': op.get('_article_id'),
                            'machine_id': op.get('machine_id'),
                            'start_minutes': op_start_minutes,
                            'end_minutes': op_end_minutes,
                            'duration_minutes': op_end_minutes - op_start_minutes,
                            'start_datetime': self._minutes_to_datetime(op_start_minutes).isoformat(),
                            'end_datetime': self._minutes_to_datetime(op_end_minutes).isoformat(),
                            'date_besoin': op.get('_date_besoin'),
                            # Nouvelles infos pour UI
                            'is_urgent': op.get('_is_urgent', False),
                            'priority': op.get('_priority', 0),
                            'original_priority': op.get('_original_priority', 0),
                            'order_quantity': op.get('_order_quantity', 0),
                            'transfer_time_minutes': transfer_time,
                            'is_last_operation': op_id in last_op_of_order,
                            'is_late': False,  # Sera mis à jour après analyse
                            'lateness_minutes': 0,  # Durée du retard en minutes
                            # Matières premières pour l'infobulle
                            'materials': materials_list
                        }
                        scheduled_ops.append(scheduled_op)
                
                # POST-TRAITEMENT JIT: Détecter les ordres en retard
                late_orders = []
                if scheduling_strategy == 'JIT' and 'jit_due_date_info' in dir():
                    logger.info("\n⏰ ANALYSE DES RETARDS (stratégie JIT):")
                    
                    # Index des opérations planifiées par ID
                    scheduled_ops_by_id = {op['operation_id']: op for op in scheduled_ops}
                    
                    for order_id, due_info in jit_due_date_info.items():
                        op_id = due_info['op_id']
                        target_end = due_info['target_end']
                        due_date = due_info['due_date']
                        due_date_minutes = due_info['due_date_minutes']
                        transfer_time = due_info['transfer_time']
                        
                        if op_id in scheduled_ops_by_id:
                            scheduled_op = scheduled_ops_by_id[op_id]
                            actual_end = scheduled_op['end_minutes']
                            # Fin réelle avec transfert = fin opération + temps de transfert
                            actual_completion = actual_end + transfer_time
                            
                            if actual_completion > due_date_minutes:
                                lateness = actual_completion - due_date_minutes
                                late_orders.append({
                                    'order_id': order_id,
                                    'operation_id': op_id,
                                    'due_date': due_date.isoformat(),
                                    'actual_completion': self._minutes_to_datetime(actual_completion).isoformat(),
                                    'lateness_minutes': lateness,
                                    'lateness_hours': round(lateness / 60, 1)
                                })
                                
                                # Marquer toutes les opérations de cet ordre comme en retard
                                for op in scheduled_ops:
                                    if op['order_id'] == order_id:
                                        op['is_late'] = True
                                        op['lateness_minutes'] = lateness
                                
                                logger.info(f"   🔴 OF {order_id}: EN RETARD de {lateness} min ({round(lateness/60, 1)}h)")
                                logger.info(f"      Besoin: {due_date.strftime('%d/%m %H:%M')}, Fin réelle: {self._minutes_to_datetime(actual_completion).strftime('%d/%m %H:%M')}")
                            else:
                                logger.info(f"   ✅ OF {order_id}: À l'heure (fin: {self._minutes_to_datetime(actual_completion).strftime('%d/%m %H:%M')} <= besoin: {due_date.strftime('%d/%m %H:%M')})")
                    
                    if late_orders:
                        logger.info(f"   ⚠️ Total: {len(late_orders)} ordre(s) en retard")
                    else:
                        logger.info("   ✅ Tous les ordres respectent leurs dates de besoin")
                
                # POST-TRAITEMENT MATIÈRE: Vérifier les ruptures et replanifier si nécessaire
                # Continuer tant qu'il reste du temps dans le budget global
                time_remaining_for_replan = max_solver_time_seconds - (time.time() - start_time)
                
                if not ignore_material and self.material_manager and time_remaining_for_replan > 2:
                    logger.info(f"\n📦 POST-TRAITEMENT MATIÈRE (itération {current_iteration}):")
                    logger.info(f"   Temps restant pour replanification: {time_remaining_for_replan:.1f}s")
                    
                    # Trier par date de début pour simuler dans l'ordre
                    ops_by_start = sorted(scheduled_ops, key=lambda x: x['start_minutes'])
                    
                    # Réinitialiser les consommations planifiées ET les productions
                    self.material_manager.planned_consumptions = {}
                    self.material_manager.clear_planned_productions()
                    
                    # ÉTAPE 1: Enregistrer les PRODUCTIONS (articles fabriqués) 
                    # pour qu'ils soient disponibles pour les opérations suivantes
                    for op in ops_by_start:
                        if op.get('is_last_operation'):
                            order_id = op.get('order_id')
                            order = orders_by_id.get(order_id, {})
                            article_fab = order.get('article_id')
                            qty = order.get('quantity', 0)
                            if article_fab and qty > 0:
                                # L'article entre en stock à la fin de l'opération + temps de transfert
                                transfer_time = op.get('transfer_time_minutes', 0)
                                stock_entry_minutes = op['end_minutes'] + transfer_time
                                stock_entry_date = self._minutes_to_datetime(stock_entry_minutes)
                                
                                self.material_manager.add_planned_production(
                                    order_id=order_id,
                                    article_id=article_fab,
                                    quantity=qty,
                                    end_date=stock_entry_date
                                )
                    
                    # ÉTAPE 2: Tracker les nouvelles contraintes et les OFs avec première op bloquée
                    new_constraints = {}
                    first_op_blocked_orders = set()  # OFs dont la PREMIÈRE opération est bloquée
                    truly_unschedulable = []
                    
                    # ÉTAPE 3: Vérifier les matières pour chaque opération
                    for op in ops_by_start:
                        op_id = op['operation_id']
                        order_id = op.get('order_id')
                        start_dt = self._minutes_to_datetime(op['start_minutes'])
                        
                        # Si la PREMIÈRE opération de cet OF est bloquée, les suivantes doivent
                        # être vérifiées mais pas réservées (car elles seront décalées par la séquence)
                        skip_reservation = order_id in first_op_blocked_orders
                        
                        # Vérifier la disponibilité à cette date
                        material_status = self.material_manager.check_operation_materials(op_id, start_dt)
                        
                        if material_status.all_available:
                            # OK - réserver les matières (sauf si l'OF est déjà bloqué en amont)
                            if not skip_reservation:
                                self.material_manager.reserve_materials(op_id, start_dt)
                            # Sinon, on ne réserve pas car cette op sera décalée par la séquence
                        else:
                            # RUPTURE - chercher la date de disponibilité
                            earliest = material_status.earliest_start_date
                            
                            if earliest and earliest > start_dt:
                                # Reporter cette opération
                                new_constraints[op_id] = earliest
                                first_op_blocked_orders.add(order_id)
                                logger.info(f"   📅 {op_id}: rupture à {start_dt.strftime('%d/%m %H:%M')}, reporter à {earliest.strftime('%d/%m %H:%M')}")
                            else:
                                # Pas de réception future - vraiment non planifiable
                                truly_unschedulable.append({
                                    'operation_id': op_id,
                                    'order_id': order_id,
                                    'article_id': op.get('article_id'),
                                    'blocking_components': material_status.blocking_components,
                                    'reason': "Aucune réception fournisseur planifiée pour les composants manquants"
                                })
                                first_op_blocked_orders.add(order_id)
                                logger.warning(f"   ⛔ {op_id}: NON PLANIFIABLE - pas de réception future")
                    
                    # Si des opérations doivent être reportées ET qu'il reste du temps, relancer
                    if new_constraints and time_remaining_for_replan > 3:
                        logger.info(f"\n🔄 REPLANIFICATION NÉCESSAIRE: {len(new_constraints)} opérations à reporter")
                        logger.info(f"   Temps restant: {time_remaining_for_replan:.1f}s - Lancement itération {current_iteration + 1}")
                        
                        # CORRECTION BUG: Toujours remplacer les contraintes par les nouvelles
                        # car les nouvelles reflètent la date de production RÉELLE calculée par le solver.
                        # L'ancienne logique (new_date > old_date) ignorait les cas où un producteur
                        # est avancé, ce qui laissait une contrainte obsolète et créait des délais artificiels.
                        updated_constraints = dict(material_date_constraints)
                        for op_id, new_date in new_constraints.items():
                            old_date = updated_constraints.get(op_id)
                            if old_date and new_date != old_date:
                                logger.info(f"   🔄 {op_id}: contrainte matière mise à jour {old_date.strftime('%d/%m %H:%M')} -> {new_date.strftime('%d/%m %H:%M')}")
                            updated_constraints[op_id] = new_date  # Toujours remplacer
                        
                        # Relancer la planification avec les nouvelles contraintes
                        new_options = dict(options)
                        new_options['_material_date_constraints'] = updated_constraints
                        new_options['_iteration'] = current_iteration + 1
                        new_options['_start_time'] = start_time
                        new_options['_total_solver_time'] = total_solver_time
                        
                        return await self.schedule(
                            orders, operations, machines, rules_engine, material_checker, new_options
                        )
                    elif new_constraints:
                        # Pas assez de temps pour replanifier - signaler les ruptures
                        logger.warning(f"\n⚠️ TEMPS ÉPUISÉ: {len(new_constraints)} opérations avec rupture non reportées")
                        for op_id, new_date in new_constraints.items():
                            truly_unschedulable.append({
                                'operation_id': op_id,
                                'order_id': next((o['order_id'] for o in scheduled_ops if o['operation_id'] == op_id), None),
                                'blocking_components': [],
                                'reason': f"Temps épuisé - devrait être reporté au {new_date.strftime('%d/%m %H:%M')}"
                            })
                    
                    # Ajouter les opérations vraiment non planifiables au résultat
                    if truly_unschedulable:
                        result['unscheduled_operations'] = truly_unschedulable
                        result['unscheduled_count'] = len(truly_unschedulable)
                        logger.warning(f"   Total: {len(truly_unschedulable)} opérations non planifiables")
                    else:
                        logger.info(f"   ✅ ORDONNANCEMENT OPTIMAL SANS RUPTURE en {current_iteration} itération(s)")
                
                # Ajouter les métriques de temps au résultat
                result['total_solver_time'] = total_solver_time
                final_elapsed = time.time() - start_time
                result['total_elapsed_time'] = final_elapsed
                logger.info(f"   ⏱️ Métriques temps: start_time={start_time}, now={time.time()}, elapsed={final_elapsed:.2f}s")
                
                # Vérifier l'absence de chevauchement (post-validation)
                overlap_errors = self._verify_no_overlap(scheduled_ops)
                if overlap_errors:
                    logger.error("⚠️ ERREUR: Chevauchements détectés!")
                    for err in overlap_errors:
                        logger.error(f"   {err}")
                    result['overlap_errors'] = overlap_errors
                else:
                    logger.info("   ✓ Aucun chevauchement détecté")
                
                # Trier par machine puis par heure de début
                scheduled_ops.sort(key=lambda x: (x['machine_id'], x['start_minutes']))
                
                # Log le planning par machine
                current_machine = None
                for op in scheduled_ops:
                    if op['machine_id'] != current_machine:
                        current_machine = op['machine_id']
                        logger.info(f"\n   Machine {current_machine}:")
                    logger.info(f"      {op['start_datetime']} - {op['end_datetime']}: {op['operation_id']} (OF: {op['order_id']})")
                
                result['operations'] = scheduled_ops
                
                # DIAGNOSTIC INTÉGRÉ: Ajouter les informations détaillées au résultat
                # 1. Productions planifiées (entrées en stock des articles fabriqués)
                # IMPORTANT: L'article entre en stock à la fin de la dernière opération + temps de transfert final
                productions = []
                for op in scheduled_ops:
                    if op.get('is_last_operation'):
                        order_id = op.get('order_id')
                        order = orders_by_id.get(order_id, {})
                        article_fab = order.get('article_id')
                        qty = order.get('quantity', 0)
                        if article_fab and qty > 0:
                            # Ajouter le temps de transfert final pour l'entrée en stock
                            transfer_time = op.get('transfer_time_minutes', 0)
                            stock_entry_minutes = op['end_minutes'] + transfer_time
                            stock_entry_datetime = self._minutes_to_datetime(stock_entry_minutes)
                            
                            productions.append({
                                'order_id': order_id,
                                'article_id': article_fab,
                                'quantity': qty,
                                'end_datetime': stock_entry_datetime.isoformat(),
                                'end_minutes': stock_entry_minutes,
                                'operation_end_datetime': op['end_datetime'],
                                'transfer_time_minutes': transfer_time,
                                'type': 'PRODUCTION'
                            })
                            logger.info(f"   �icing PRODUCTION: {order_id} -> {article_fab} x{qty} disponible à {stock_entry_datetime.strftime('%d/%m %H:%M')} (fin op: {op['end_datetime'][:16]} + {transfer_time}min transfert)")
                result['productions'] = productions
                
                # 2. Propagation de priorité (pour diagnostic)
                result['priority_propagation'] = priority_propagation_log if 'priority_propagation_log' in dir() else []
                
                # 3. OFs urgents (originaux + propagés)
                urgent_of_ids = [o.get('id') for o in orders if o.get('_is_urgent', False)]
                result['urgent_orders'] = urgent_of_ids
                
                # 4. Ordres en retard (stratégie JIT)
                result['late_orders'] = late_orders if 'late_orders' in dir() else []
                
                # 5. STATISTIQUES DE DIAGNOSTIC DÉTAILLÉES
                total_elapsed = time.time() - start_time
                
                # Grouper les opérations planifiées par machine pour le calcul d'utilisation
                ops_by_machine = {}
                for op in scheduled_ops:
                    m_id = op.get('machine_id')
                    if m_id:
                        if m_id not in ops_by_machine:
                            ops_by_machine[m_id] = []
                        ops_by_machine[m_id].append(op)
                
                # Calculer le taux de remplissage machine
                machine_utilization = {}
                total_work_time = 0
                total_available_time = 0
                
                for machine_id, ops in ops_by_machine.items():
                    ops_sorted = sorted(ops, key=lambda x: x['start_minutes'])
                    if ops_sorted:
                        first_start = min(op['start_minutes'] for op in ops_sorted)
                        last_end = max(op['end_minutes'] for op in ops_sorted)
                        span = last_end - first_start
                        work = sum(op['duration_minutes'] for op in ops_sorted)
                        utilization = (work / span * 100) if span > 0 else 0
                        machine_utilization[machine_id] = {
                            'operations_count': len(ops_sorted),
                            'work_time_minutes': work,
                            'span_minutes': span,
                            'utilization_percent': round(utilization, 1)
                        }
                        total_work_time += work
                        total_available_time += span
                
                global_utilization = (total_work_time / total_available_time * 100) if total_available_time > 0 else 0
                
                result['scheduling_stats'] = {
                    'max_solver_time_configured': max_solver_time_seconds,
                    'actual_solver_time': round(solver.wall_time, 2),
                    'total_elapsed_time': round(total_elapsed, 2),
                    'iterations_count': current_iteration,
                    'total_operations_input': len(operations),
                    'operations_scheduled': len(scheduled_ops),
                    'operations_blocked': len(blocked_operations),
                    'operations_material_delayed': len(material_delayed_operations),
                    'global_utilization_percent': round(global_utilization, 1),
                    'machine_utilization': machine_utilization,
                    'blocked_reasons_summary': self._summarize_blocked_reasons(blocked_operations),
                    # Statistiques d'horizon
                    'horizon_stats': horizon_stats,
                    # Statistiques de fractionnement
                    'split_stats': split_stats
                }
            
            # Log solver result
            self.diagnostics.log_solver_result(
                result['status'],
                result['operations'],
                result['conflicts'],
                result['solver_time']
            )
            
            result['diagnostics'] = self.diagnostics.get_report()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur d'ordonnancement: {str(e)}", exc_info=True)
            return self._error_result(str(e))
    
    def _verify_no_overlap(self, scheduled_ops: List[Dict]) -> List[str]:
        """
        Vérifie qu'il n'y a pas de chevauchement sur une même machine.
        Retourne une liste d'erreurs si des chevauchements sont détectés.
        """
        errors = []
        
        # Grouper par machine
        ops_by_machine = {}
        for op in scheduled_ops:
            machine_id = op['machine_id']
            if machine_id not in ops_by_machine:
                ops_by_machine[machine_id] = []
            ops_by_machine[machine_id].append(op)
        
        # Vérifier chaque machine
        for machine_id, ops in ops_by_machine.items():
            # Trier par début
            ops.sort(key=lambda x: x['start_minutes'])
            
            for i in range(len(ops) - 1):
                op1 = ops[i]
                op2 = ops[i + 1]
                
                # Chevauchement si fin de op1 > début de op2
                if op1['end_minutes'] > op2['start_minutes']:
                    errors.append(
                        f"Machine {machine_id}: {op1['operation_id']} ({op1['start_minutes']}-{op1['end_minutes']}) "
                        f"chevauche {op2['operation_id']} ({op2['start_minutes']}-{op2['end_minutes']})"
                    )
        
        return errors
    
    def _error_result(self, error_msg: str) -> Dict:
        """Génère un résultat d'erreur."""
        return {
            'status': 'ERROR',
            'operations': [],
            'conflicts': [{'error': error_msg}],
            'solver_time': 0,
            'diagnostics': self.diagnostics.get_report() if self.diagnostics else None
        }
    
    def _get_status_string(self, status) -> str:
        status_map = {
            cp_model.OPTIMAL: 'OPTIMAL',
            cp_model.FEASIBLE: 'FEASIBLE',
            cp_model.INFEASIBLE: 'INFEASIBLE',
            cp_model.MODEL_INVALID: 'MODEL_INVALID',
            cp_model.UNKNOWN: 'UNKNOWN'
        }
        return status_map.get(status, 'UNKNOWN')
    
    def _summarize_blocked_reasons(self, blocked_operations: List[Dict]) -> Dict[str, int]:
        """Résume les raisons de blocage par catégorie."""
        reasons_count = {}
        for blocked in blocked_operations:
            reason = blocked.get('reason', 'Raison inconnue')
            # Catégoriser les raisons
            if 'machine' in reason.lower():
                category = 'machine_missing'
            elif 'matière' in reason.lower() or 'material' in reason.lower():
                category = 'material_shortage'
            elif 'calendrier' in reason.lower() or 'calendar' in reason.lower():
                category = 'calendar_constraint'
            elif 'règle' in reason.lower() or 'rule' in reason.lower():
                category = 'business_rule'
            else:
                category = 'other'
            
            if category not in reasons_count:
                reasons_count[category] = 0
            reasons_count[category] += 1
        
        return reasons_count
# Trigger reload
