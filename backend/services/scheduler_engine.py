from ortools.sat.python import cp_model
import logging
import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta, timezone
from services.diagnostics import SchedulingDiagnostics
from services.machine_assigner import MachineAssigner
from services.material_manager import MaterialManager

logger = logging.getLogger(__name__)


class CalendarManager:
    """
    Gestionnaire des calendriers pour les centres de charge.
    
    Permet de:
    - Déterminer les plages horaires de travail par machine
    - Calculer le temps effectif de travail
    - Créer des contraintes de calendrier pour le solveur
    
    PRÉCISION QUART D'HEURE:
    - Utilise start_time/end_time (format HH:MM) pour une précision à la minute
    - Rétro-compatible avec start_hour/end_hour si start_time/end_time absents
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
                cal = self.calendars_by_id[calendar_id]
                # Normaliser le calendrier avec précision minute
                self.machine_calendar[machine_id] = self._normalize_calendar(cal)
            else:
                # Calendrier par défaut: 24/7
                self.machine_calendar[machine_id] = {
                    'id': 'default',
                    'name': 'Default 24/7',
                    'working_days': [0, 1, 2, 3, 4, 5, 6],
                    'start_time': '00:00',
                    'end_time': '24:00',
                    'start_minutes': 0,
                    'end_minutes': 1440  # 24 * 60
                }
        
        logger.info("\n" + "="*60)
        logger.info("CALENDRIERS DES CENTRES DE CHARGE (PRÉCISION MINUTE)")
        logger.info("="*60)
        for machine_id, cal in self.machine_calendar.items():
            centre_id = next((m.get('centre_de_charge_id') for m in machines if m.get('id') == machine_id), None)
            logger.info(f"  Machine {machine_id} (centre {centre_id}): {cal.get('name', 'Default')}")
            logger.info(f"    Jours: {cal.get('working_days')}, Horaires: {cal.get('start_time')}-{cal.get('end_time')} ({cal.get('start_minutes')}-{cal.get('end_minutes')} min)")
        logger.info("="*60 + "\n")
    
    def _normalize_calendar(self, cal: Dict) -> Dict:
        """
        Normalise un calendrier pour avoir les minutes précises.
        Utilise start_time/end_time si disponible, sinon start_hour/end_hour.
        """
        normalized = dict(cal)
        
        # Filtrer les jours invalides (0-6 uniquement)
        working_days = cal.get('working_days', [0, 1, 2, 3, 4, 5, 6])
        normalized['working_days'] = [d for d in working_days if 0 <= d <= 6]
        
        # Parser start_time (format HH:MM)
        start_time = cal.get('start_time')
        if start_time and ':' in str(start_time):
            try:
                parts = str(start_time).split(':')
                hours = int(parts[0])
                minutes = int(parts[1]) if len(parts) > 1 else 0
                normalized['start_minutes'] = hours * 60 + minutes
                normalized['start_time'] = start_time
            except (ValueError, IndexError):
                # Fallback sur start_hour
                normalized['start_minutes'] = cal.get('start_hour', 0) * 60
                normalized['start_time'] = f"{cal.get('start_hour', 0):02d}:00"
        else:
            # Utiliser start_hour
            start_hour = cal.get('start_hour', 0)
            normalized['start_minutes'] = start_hour * 60
            normalized['start_time'] = f"{start_hour:02d}:00"
        
        # Parser end_time (format HH:MM)
        end_time = cal.get('end_time')
        if end_time and ':' in str(end_time):
            try:
                parts = str(end_time).split(':')
                hours = int(parts[0])
                minutes = int(parts[1]) if len(parts) > 1 else 0
                normalized['end_minutes'] = hours * 60 + minutes
                normalized['end_time'] = end_time
            except (ValueError, IndexError):
                # Fallback sur end_hour
                normalized['end_minutes'] = cal.get('end_hour', 24) * 60
                normalized['end_time'] = f"{cal.get('end_hour', 24):02d}:00"
        else:
            # Utiliser end_hour
            end_hour = cal.get('end_hour', 24)
            normalized['end_minutes'] = end_hour * 60
            normalized['end_time'] = f"{end_hour:02d}:00"
        
        return normalized
    
    def get_calendar_for_machine(self, machine_id: str) -> Dict:
        """Retourne le calendrier pour une machine."""
        return self.machine_calendar.get(machine_id, {
            'working_days': [0, 1, 2, 3, 4, 5, 6],
            'start_time': '00:00',
            'end_time': '24:00',
            'start_minutes': 0,
            'end_minutes': 1440
        })
    
    def is_working_time(self, machine_id: str, dt: datetime) -> bool:
        """
        Vérifie si un moment donné est un temps de travail pour la machine.
        PRÉCISION À LA MINUTE.
        """
        calendar = self.get_calendar_for_machine(machine_id)
        working_days = calendar.get('working_days', [0, 1, 2, 3, 4, 5, 6])
        start_minutes = calendar.get('start_minutes', 0)
        end_minutes = calendar.get('end_minutes', 1440)
        
        # weekday(): 0=Lundi, 6=Dimanche
        if dt.weekday() not in working_days:
            return False
        
        # Minutes depuis minuit
        current_minutes = dt.hour * 60 + dt.minute
        if current_minutes < start_minutes or current_minutes >= end_minutes:
            return False
        
        return True
    
    def get_working_minutes_per_day(self, machine_id: str) -> int:
        """Retourne le nombre de minutes de travail par jour pour une machine."""
        calendar = self.get_calendar_for_machine(machine_id)
        start_minutes = calendar.get('start_minutes', 0)
        end_minutes = calendar.get('end_minutes', 1440)
        return max(0, end_minutes - start_minutes)
    
    def get_working_hours_per_day(self, machine_id: str) -> float:
        """Retourne le nombre d'heures de travail par jour pour une machine."""
        return self.get_working_minutes_per_day(machine_id) / 60
    
    def calculate_forbidden_time_slots(
        self, 
        machine_id: str, 
        scheduling_start: datetime, 
        horizon_days: int = 7
    ) -> List[Tuple[int, int]]:
        """
        Calcule les plages horaires interdites (hors calendrier) pour une machine.
        
        PRÉCISION À LA MINUTE (supporte les quarts d'heure comme 07:45, 16:30, etc.)
        
        Retourne une liste de tuples (start_minute, end_minute) relatifs au scheduling_start.
        Ces plages représentent les périodes où la machine ne peut pas travailler.
        
        IMPORTANT: Utilise ceil() pour être conservateur et garantir qu'aucune opération
        ne puisse commencer ou se terminer dans une plage interdite.
        """
        calendar = self.get_calendar_for_machine(machine_id)
        working_days = set(calendar.get('working_days', [0, 1, 2, 3, 4, 5, 6]))
        start_minutes_of_day = calendar.get('start_minutes', 0)  # Ex: 7*60+45 = 465 pour 07:45
        end_minutes_of_day = calendar.get('end_minutes', 1440)   # Ex: 16*60+45 = 1005 pour 16:45
        
        # Si calendrier 24/7, pas de plages interdites
        if working_days == {0, 1, 2, 3, 4, 5, 6} and start_minutes_of_day == 0 and end_minutes_of_day >= 1440:
            return []
        
        forbidden_slots = []
        
        # Normaliser scheduling_start au début de la journée pour les calculs
        base_date = scheduling_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # IMPORTANT: Ajouter une zone interdite immédiate si on est hors des heures de travail
        # au moment du scheduling_start
        current_minutes_in_day = scheduling_start.hour * 60 + scheduling_start.minute
        current_weekday = scheduling_start.weekday()
        
        if current_weekday not in working_days:
            # On démarre un jour non travaillé - tout est interdit jusqu'au prochain jour travaillé
            # Cette situation sera gérée par la boucle ci-dessous
            pass
        elif current_minutes_in_day >= end_minutes_of_day:
            # On est APRÈS l'heure de fermeture - zone interdite de maintenant jusqu'au lendemain matin
            # Chercher le prochain jour travaillé
            next_work_day = base_date + timedelta(days=1)
            for d in range(7):
                check_day = base_date + timedelta(days=1 + d)
                if check_day.weekday() in working_days:
                    next_work_day = check_day
                    break
            
            # Zone interdite de 0 (maintenant) jusqu'à l'heure d'ouverture du prochain jour travaillé
            # Utilise start_minutes_of_day pour la précision minute
            next_opening = next_work_day + timedelta(minutes=start_minutes_of_day)
            slot_end = math.ceil((next_opening - scheduling_start).total_seconds() / 60) + 1
            forbidden_slots.append((0, slot_end))
            logger.info(f"      Zone immédiate (après fermeture): [0 - {slot_end}] (jusqu'à {next_opening.strftime('%d/%m %H:%M')})")
        elif current_minutes_in_day < start_minutes_of_day:
            # On est AVANT l'heure d'ouverture - zone interdite de maintenant jusqu'à l'ouverture
            today_opening = base_date + timedelta(minutes=start_minutes_of_day)
            slot_end = math.ceil((today_opening - scheduling_start).total_seconds() / 60) + 1
            forbidden_slots.append((0, slot_end))
            logger.info(f"      Zone immédiate (avant ouverture): [0 - {slot_end}] (jusqu'à {today_opening.strftime('%d/%m %H:%M')})")
        
        # Calculer les zones interdites pour chaque jour de l'horizon
        for day_offset in range(horizon_days + 1):
            day_start = base_date + timedelta(days=day_offset)
            day_weekday = day_start.weekday()
            
            if day_weekday not in working_days:
                # Journée entière non travaillée (weekend ou jour férié)
                slot_start_dt = day_start
                slot_end_dt = day_start + timedelta(days=1)
                
                # Convertir en minutes relatives au scheduling_start
                slot_start = math.ceil((slot_start_dt - scheduling_start).total_seconds() / 60)
                slot_end = math.ceil((slot_end_dt - scheduling_start).total_seconds() / 60)
                
                if slot_end > 0:  # La plage chevauche ou est après le scheduling_start
                    forbidden_slots.append((max(0, slot_start), slot_end))
            else:
                # Jour travaillé - ajouter les plages hors heures de travail
                
                # MATIN: De minuit jusqu'à l'heure d'ouverture (précision minute)
                if start_minutes_of_day > 0:
                    slot_start_dt = day_start  # 00:00
                    slot_end_dt = day_start + timedelta(minutes=start_minutes_of_day)  # Ex: 07:45
                    
                    slot_start = math.ceil((slot_start_dt - scheduling_start).total_seconds() / 60)
                    # +1 pour s'assurer que l'heure d'ouverture est APRÈS la zone interdite
                    slot_end = math.ceil((slot_end_dt - scheduling_start).total_seconds() / 60) + 1
                    
                    if slot_end > 0:
                        forbidden_slots.append((max(0, slot_start), slot_end))
                
                # SOIR: De l'heure de fermeture jusqu'à minuit (précision minute)
                if end_minutes_of_day < 1440:
                    slot_start_dt = day_start + timedelta(minutes=end_minutes_of_day)  # Ex: 16:45
                    slot_end_dt = day_start + timedelta(days=1)  # Minuit du jour suivant
                    
                    slot_start = math.ceil((slot_start_dt - scheduling_start).total_seconds() / 60)
                    slot_end = math.ceil((slot_end_dt - scheduling_start).total_seconds() / 60)
                    
                    # Ajouter même si slot_start < 0 (on est déjà dans la zone interdite)
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


class SchedulerEngine:
    """
    Moteur d'ordonnancement basé sur OR-Tools CP-SAT.
    
    Garanties:
    1. Non-chevauchement: une machine ne peut traiter qu'une opération à la fois
    2. Séquence: les opérations d'un même OF respectent l'ordre des gammes
    3. Priorité: les opérations urgentes (due_date proche) sont planifiées en premier
    4. Disponibilité matière avec projection du stock DYNAMIQUE
    5. Respect des calendriers des centres de charge avec PRÉCISION MINUTE
    
    Format datetime: ISO 8601 (YYYY-MM-DDTHH:MM:SS)
    
    LOGIQUE MATIÈRE TEMPORELLE:
    - Calcule le stock projeté à l'horodatage exact de chaque opération
    - Tient compte des 3 sources: stock initial, réceptions fournisseurs, consommations déjà planifiées
    - Reporte automatiquement les opérations si composants manquants
    """
    
    def __init__(self, db):
        self.db = db
        self.diagnostics = None
        self.scheduling_start = None
        self.calendar_manager = None
        self.material_manager = None  # Pour la logique matière temporelle
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """
        Parse une date/heure en datetime.
        Supporte: YYYY-MM-DDTHH:MM:SS, YYYY-MM-DD HH:MM:SS, YYYY-MM-DD
        """
        if not date_str:
            return None
        
        try:
            if 'T' in date_str:
                if '+' in date_str or 'Z' in date_str:
                    date_str = date_str.replace('Z', '+00:00')
                    return datetime.fromisoformat(date_str)
                return datetime.fromisoformat(date_str)
            elif ' ' in date_str:
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            else:
                return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception as e:
            logger.warning(f"Impossible de parser la date '{date_str}': {e}")
            return None
    
    def _datetime_to_minutes(self, dt: datetime) -> int:
        """Convertit un datetime en minutes depuis le début de l'horizon."""
        if not self.scheduling_start:
            self.scheduling_start = datetime.now()
        delta = dt - self.scheduling_start
        return max(0, int(delta.total_seconds() / 60))
    
    def _minutes_to_datetime(self, minutes: int) -> datetime:
        """Convertit des minutes en datetime."""
        if not self.scheduling_start:
            self.scheduling_start = datetime.now()
        return self.scheduling_start + timedelta(minutes=minutes)
    
    async def schedule(self, orders, operations, machines, rules_engine, material_checker, options=None):
        """
        Main scheduling function using OR-Tools CP-SAT.
        
        Garantit:
        - Non-chevauchement sur chaque machine (contrainte NoOverlap)
        - Respect de l'ordre des opérations dans un OF
        - Priorité basée sur due_date avec heure
        - Disponibilité matière avec projection du stock
        - Respect des calendriers des centres de charge
        
        Options:
        - ignore_rules: bool
        - ignore_material: bool
        - ignore_calendars: bool (new)
        - debug_mode: bool
        - auto_assign_machines: bool (default True)
        - max_solver_time_seconds: int (default 60)
        """
        options = options or {}
        debug_mode = options.get('debug_mode', True)
        ignore_rules = options.get('ignore_rules', False)
        ignore_material = options.get('ignore_material', False)
        ignore_calendars = options.get('ignore_calendars', False)
        auto_assign_machines = options.get('auto_assign_machines', True)
        max_solver_time_seconds = options.get('max_solver_time_seconds', 60)
        
        # Point de départ pour l'horizon de planification
        # IMPORTANT: Arrondir à la minute supérieure pour éviter les problèmes de microsecondes
        # qui pourraient permettre des opérations juste avant les heures d'ouverture
        now = datetime.now()
        self.scheduling_start = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        
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
            logger.info(f"  Ignorer calendriers: {ignore_calendars}")
            logger.info(f"{'='*60}\n")
            
            # Initialiser le gestionnaire de calendriers
            self.calendar_manager = None
            if not ignore_calendars:
                self.calendar_manager = CalendarManager(calendars, centres_de_charge, machines)
            
            await self.diagnostics.run_pre_validation(orders, operations, machines, rules, stocks)
            
            # Vérification bloquante
            if len(orders) == 0 or len(operations) == 0 or len(machines) == 0:
                logger.error("❌ Données insuffisantes pour l'ordonnancement")
                return self._error_result("Données insuffisantes")
            
            # Initialiser le gestionnaire de matières (LOGIQUE TEMPORELLE)
            self.material_manager = MaterialManager(stocks, operation_materials, planned_receipts)
            
            logger.info("\n📦 LOGIQUE MATIÈRE TEMPORELLE ACTIVÉE")
            logger.info(f"   Stock initial: {len(stocks)} articles")
            logger.info(f"   Réceptions planifiées: {len(planned_receipts)}")
            logger.info(f"   Besoins opérations: {len(operation_materials)}")
            for receipt in planned_receipts[:5]:
                logger.info(f"   📥 {receipt.get('article_id')}: +{receipt.get('quantity')} le {receipt.get('planned_date')}")
            
            # PHASE 1.5: AUTO-ASSIGNATION DES MACHINES
            if auto_assign_machines and not ignore_rules:
                logger.info("\n🤖 Auto-assignation des machines activée")
                assigner = MachineAssigner(machines, rules_engine)
                assignment_result = assigner.assign_machines_to_operations(operations, orders)
                self.diagnostics.report['machine_assignment'] = assignment_result
            
            # PHASE 2: ANALYSE DE FAISABILITÉ
            feasible_count, blocked_count = self.diagnostics.analyze_all_operations(
                operations, orders, machines, rules_engine, material_checker
            )
            
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
                
                # Vérification matière avec projection TEMPORELLE
                if is_valid and not ignore_material:
                    # Vérifier les besoins matière de l'opération à t=scheduling_start
                    # La contrainte exacte sera ajoutée au modèle CP-SAT plus tard
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
                    # Enrichir avec date_besoin pour le tri
                    op_enriched = {
                        **op,
                        '_date_besoin': order.get('due_date') if order else None,
                        '_priority': order.get('priority', 0) if order else 0,
                        '_article_id': (order.get('article_id') or order.get('article')) if order else None,
                        '_material_earliest_date': earliest_material_date,
                        '_material_status': material_status
                    }
                    valid_operations.append(op_enriched)
                else:
                    blocked_operations.append({
                        'operation_id': op.get('id'),
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
                    return (dt or datetime.max, -priority)
                return (datetime.max, -priority)
            
            valid_operations.sort(key=get_sort_key)
            
            # PHASE 4: CONSTRUCTION DU MODÈLE OR-TOOLS
            model = cp_model.CpModel()
            
            # Horizon: 7 jours en minutes
            horizon = 7 * 24 * 60
            
            # Variables de décision
            start_vars = {}
            end_vars = {}
            interval_vars = {}
            machine_to_intervals = {}
            
            # Créer les variables pour chaque opération valide
            for op in valid_operations:
                op_id = op.get('id')
                duration = op.get('production_time_minutes', 60) + op.get('setup_time_minutes', 0)
                
                # Calculer la contrainte matière: date minimum de début
                earliest_material_date = op.get('_material_earliest_date')
                min_start = 0
                if earliest_material_date:
                    min_start = self._datetime_to_minutes(earliest_material_date)
                    min_start = max(0, min_start)  # Pas de valeur négative
                
                # Variable de début (avec contrainte matière intégrée)
                start_var = model.new_int_var(min_start, horizon - duration, f'start_{op_id}')
                start_vars[op_id] = start_var
                
                # Variable de fin
                end_var = model.new_int_var(duration + min_start, horizon, f'end_{op_id}')
                end_vars[op_id] = end_var
                
                # Lier début et fin
                model.add(end_var == start_var + duration)
                
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
                        'min_start': min_start,
                        'earliest_material_date': earliest_material_date
                    })
            
            # Log des contraintes matière
            material_constraint_count = sum(1 for op in valid_operations if op.get('_material_earliest_date'))
            if material_constraint_count > 0:
                logger.info(f"\n📦 CONTRAINTES MATIÈRE TEMPORELLE: {material_constraint_count} opérations avec date minimum")
                for op in valid_operations:
                    if op.get('_material_earliest_date'):
                        min_start = self._datetime_to_minutes(op['_material_earliest_date'])
                        logger.info(f"   ✓ {op['id']}: start >= {min_start} min ({op['_material_earliest_date'].strftime('%d/%m %H:%M')})")
            
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
            
            # CONTRAINTES DE CALENDRIER: Interdire les plages hors horaires de travail
            calendar_constraints_count = 0
            if self.calendar_manager and not ignore_calendars:
                logger.info("\n📌 CONTRAINTES DE CALENDRIER (PRÉCISION MINUTE):")
                
                for machine_id, intervals_data in machine_to_intervals.items():
                    calendar = self.calendar_manager.get_calendar_for_machine(machine_id)
                    working_days = set(calendar.get('working_days', [0, 1, 2, 3, 4, 5, 6]))
                    start_minutes = calendar.get('start_minutes', 0)
                    end_minutes = calendar.get('end_minutes', 1440)
                    start_time = calendar.get('start_time', '00:00')
                    end_time = calendar.get('end_time', '24:00')
                    
                    # Vérifier si le calendrier est 24/7 (pas de contrainte)
                    is_24_7 = (working_days == {0, 1, 2, 3, 4, 5, 6} and start_minutes == 0 and end_minutes >= 1440)
                    
                    if is_24_7:
                        logger.info(f"   ○ Machine {machine_id}: Calendrier 24/7 (pas de contrainte)")
                        continue
                    
                    # Calculer les plages horaires interdites
                    forbidden_slots = self.calendar_manager.calculate_forbidden_time_slots(
                        machine_id, self.scheduling_start, horizon_days=7
                    )
                    
                    if not forbidden_slots:
                        logger.info(f"   ○ Machine {machine_id}: Pas de plages interdites calculées")
                        continue
                    
                    logger.info(f"   ✓ Machine {machine_id}: {len(forbidden_slots)} plages interdites")
                    logger.info(f"      Calendrier: jours={list(working_days)}, horaires={start_time}-{end_time}")
                    # Log des premières plages pour debug
                    for i, (fs, fe) in enumerate(forbidden_slots[:3]):
                        fs_dt = self.scheduling_start + timedelta(minutes=fs)
                        fe_dt = self.scheduling_start + timedelta(minutes=fe)
                        logger.info(f"      Plage {i+1}: [{fs}-{fe}] = [{fs_dt.strftime('%d/%m %H:%M')} - {fe_dt.strftime('%d/%m %H:%M')}]")
                    
                    # Pour chaque opération sur cette machine, contraindre le début et la fin
                    # pour éviter les plages interdites
                    for interval_data in intervals_data:
                        op_id = interval_data['op_id']
                        if op_id not in start_vars or op_id not in end_vars:
                            continue
                        
                        start_var = start_vars[op_id]
                        end_var = end_vars[op_id]
                        
                        # Créer les contraintes pour éviter chaque plage interdite
                        # L'opération entière doit être SOIT avant SOIT après la plage
                        # Soit end <= slot_start (termine avant la fermeture)
                        # Soit start >= slot_end (commence après la fermeture)
                        for slot_start, slot_end in forbidden_slots[:50]:  # Limiter pour performance
                            b = model.new_bool_var(f'calendar_{op_id}_{slot_start}')
                            
                            # Si b=True: L'opération se termine AVANT la plage interdite
                            model.add(end_var <= slot_start).only_enforce_if(b)
                            # Si b=False: L'opération commence APRÈS la plage interdite
                            model.add(start_var >= slot_end).only_enforce_if(b.Not())
                            
                            calendar_constraints_count += 1
                
                logger.info(f"\n   Total: {calendar_constraints_count} contraintes de calendrier")
            else:
                logger.info("\n📌 CONTRAINTES DE CALENDRIER: Désactivées")
            
            
            # Contraintes de séquence (opérations d'un même OF) avec TEMPS DE DÉPLACEMENT
            operations_by_order = {}
            for op in valid_operations:
                order_id = op.get('order_id')
                if order_id:
                    if order_id not in operations_by_order:
                        operations_by_order[order_id] = []
                    operations_by_order[order_id].append(op)
            
            sequence_constraints_count = 0
            transfer_time_constraints_count = 0
            logger.info("\n📌 CONTRAINTES DE SÉQUENCE (gammes) + TEMPS DE DÉPLACEMENT:")
            for order_id, order_ops in operations_by_order.items():
                # Trier par numéro d'opération dans la gamme
                sorted_ops = sorted(order_ops, key=lambda x: x.get('operation_id', 0))
                for i in range(len(sorted_ops) - 1):
                    op1 = sorted_ops[i]
                    op2 = sorted_ops[i + 1]
                    op1_id = op1.get('id')
                    op2_id = op2.get('id')
                    
                    if op1_id in end_vars and op2_id in start_vars:
                        # Temps de déplacement entre op1 et op2
                        transfer_time = op1.get('transfer_time_minutes', 0)
                        
                        # Contrainte: op2 commence APRÈS fin de op1 + temps de déplacement
                        if transfer_time > 0:
                            model.add(start_vars[op2_id] >= end_vars[op1_id] + transfer_time)
                            transfer_time_constraints_count += 1
                        else:
                            model.add(start_vars[op2_id] >= end_vars[op1_id])
                        
                        sequence_constraints_count += 1
                
                if len(sorted_ops) > 1:
                    ops_seq = []
                    for j, o in enumerate(sorted_ops):
                        transfer = o.get('transfer_time_minutes', 0)
                        if transfer > 0 and j < len(sorted_ops) - 1:
                            ops_seq.append(f"{o.get('id')}(op{o.get('operation_id')}) +{transfer}min")
                        else:
                            ops_seq.append(f"{o.get('id')}(op{o.get('operation_id')})")
                    logger.info(f"   ✓ OF {order_id}: {' -> '.join(ops_seq)}")
            
            logger.info(f"\n   Total: {sequence_constraints_count} contraintes de séquence")
            if transfer_time_constraints_count > 0:
                logger.info(f"   🚚 Dont {transfer_time_constraints_count} avec temps de déplacement")
            
            # Objectif: minimiser le makespan (temps total)
            if end_vars:
                makespan = model.new_int_var(0, horizon, 'makespan')
                model.add_max_equality(makespan, list(end_vars.values()))
                model.minimize(makespan)
                logger.info("   ✓ Objectif: minimiser makespan")
            
            # PHASE 5: RÉSOLUTION
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = max_solver_time_seconds
            solver.parameters.num_search_workers = 4
            
            logger.info(f"\n🔄 Lancement du solveur OR-Tools CP-SAT (max {max_solver_time_seconds}s)...")
            status = solver.solve(model)
            status_str = self._get_status_string(status)
            logger.info(f"✓ Solveur terminé - Status: {status_str}")
            
            result = {
                'status': status_str,
                'operations': [],
                'conflicts': blocked_operations,
                'material_delayed': material_delayed_operations,
                'solver_time': solver.wall_time,
                'max_solver_time': max_solver_time_seconds,
                'objective_value': solver.objective_value if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else None,
                'scheduling_start': self.scheduling_start.isoformat()
            }
            
            # Extraire la solution
            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                logger.info("\n📊 SOLUTION TROUVÉE:")
                
                scheduled_ops = []
                for op in valid_operations:
                    op_id = op.get('id')
                    if op_id in start_vars:
                        start_time = solver.value(start_vars[op_id])
                        end_time = solver.value(end_vars[op_id])
                        
                        scheduled_op = {
                            'operation_id': op_id,
                            'order_id': op.get('order_id'),
                            'article_id': op.get('_article_id'),
                            'machine_id': op.get('machine_id'),
                            'start_minutes': start_time,
                            'end_minutes': end_time,
                            'duration_minutes': end_time - start_time,
                            'start_datetime': self._minutes_to_datetime(start_time).isoformat(),
                            'end_datetime': self._minutes_to_datetime(end_time).isoformat(),
                            'date_besoin': op.get('_date_besoin')
                        }
                        scheduled_ops.append(scheduled_op)
                
                # POST-TRAITEMENT MATIÈRE: Réserver les matières dans l'ordre du planning
                # et identifier les opérations en rupture de stock
                unscheduled_due_to_material = []
                scheduled_ops_final = []
                blocked_orders = set()  # OFs dont une opération précédente est bloquée
                
                if not ignore_material and self.material_manager:
                    logger.info("\n📦 POST-TRAITEMENT MATIÈRE TEMPORELLE:")
                    # Trier par date de début pour simuler l'ordre réel d'exécution
                    ops_by_start = sorted(scheduled_ops, key=lambda x: x['start_minutes'])
                    
                    # Réinitialiser les consommations planifiées pour une simulation propre
                    self.material_manager.planned_consumptions = {}
                    
                    # Index pour vérifier les dépendances de gamme
                    ops_by_order = {}
                    for op in scheduled_ops:
                        oid = op.get('order_id')
                        if oid not in ops_by_order:
                            ops_by_order[oid] = []
                        ops_by_order[oid].append(op)
                    
                    for op in ops_by_start:
                        op_id = op['operation_id']
                        order_id = op.get('order_id')
                        start_dt = self._minutes_to_datetime(op['start_minutes'])
                        
                        # Vérifier si une opération précédente de cet OF est bloquée
                        if order_id in blocked_orders:
                            unscheduled_op = {
                                'operation_id': op_id,
                                'order_id': order_id,
                                'article_id': op.get('article_id'),
                                'originally_planned': op['start_datetime'],
                                'blocking_components': [],
                                'reason': f"Opération précédente de l'OF {order_id} non planifiable",
                                'earliest_possible_date': None
                            }
                            unscheduled_due_to_material.append(unscheduled_op)
                            logger.warning(f"   ⛔ {op_id}: NON PLANIFIABLE - dépend d'une op précédente bloquée")
                            continue
                        
                        # Vérifier la disponibilité à t=start AVEC les consommations précédentes
                        material_status = self.material_manager.check_operation_materials(op_id, start_dt)
                        
                        if not material_status.all_available:
                            # RUPTURE DE STOCK - cette opération ne peut pas être planifiée
                            # Marquer l'OF comme bloqué pour les opérations suivantes
                            blocked_orders.add(order_id)
                            
                            # Chercher la prochaine date de disponibilité
                            earliest = material_status.earliest_start_date
                            
                            unscheduled_op = {
                                'operation_id': op_id,
                                'order_id': order_id,
                                'article_id': op.get('article_id'),
                                'originally_planned': op['start_datetime'],
                                'blocking_components': material_status.blocking_components,
                                'reason': f"Stock insuffisant à {start_dt.strftime('%d/%m %H:%M')}",
                                'earliest_possible_date': earliest.isoformat() if earliest else None
                            }
                            unscheduled_due_to_material.append(unscheduled_op)
                            logger.warning(f"   ⛔ {op_id}: NON PLANIFIABLE - {unscheduled_op['reason']}")
                            logger.warning(f"      Composants manquants: {material_status.blocking_components}")
                            if earliest:
                                logger.warning(f"      Disponible au plus tôt: {earliest.strftime('%d/%m %H:%M')}")
                        else:
                            # Réserver les matières (consommer du stock projeté)
                            self.material_manager.reserve_materials(op_id, start_dt)
                            scheduled_ops_final.append(op)
                            logger.debug(f"   ✓ {op_id}: Matières réservées à {start_dt.strftime('%d/%m %H:%M')}")
                    
                    if unscheduled_due_to_material:
                        result['unscheduled_operations'] = unscheduled_due_to_material
                        result['unscheduled_count'] = len(unscheduled_due_to_material)
                        logger.warning(f"\n   ⚠️ {len(unscheduled_due_to_material)} opérations NON PLANIFIÉES (rupture matière)")
                    else:
                        logger.info("   ✓ Toutes les matières disponibles et réservées")
                    
                    # Utiliser les opérations validées uniquement
                    scheduled_ops = scheduled_ops_final
                else:
                    # Sans vérification matière, toutes les opérations sont planifiées
                    pass
                
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
