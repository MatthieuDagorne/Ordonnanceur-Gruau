from ortools.sat.python import cp_model
import logging
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
        """
        calendar = self.get_calendar_for_machine(machine_id)
        working_days = set(calendar.get('working_days', [0, 1, 2, 3, 4, 5, 6]))
        start_hour = calendar.get('start_hour', 0)
        end_hour = calendar.get('end_hour', 24)
        
        # Si calendrier 24/7, pas de plages interdites
        if working_days == {0, 1, 2, 3, 4, 5, 6} and start_hour == 0 and end_hour == 24:
            return []
        
        forbidden_slots = []
        current_date = scheduling_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for day_offset in range(horizon_days + 1):
            day_start = current_date + timedelta(days=day_offset)
            day_weekday = day_start.weekday()
            
            if day_weekday not in working_days:
                # Journée entière non travaillée
                slot_start = int((day_start - scheduling_start).total_seconds() / 60)
                slot_end = slot_start + 24 * 60
                if slot_start >= 0:  # Ne pas inclure les périodes avant le début
                    forbidden_slots.append((max(0, slot_start), slot_end))
            else:
                # Ajouter les plages hors heures de travail
                # Avant le début du travail
                if start_hour > 0:
                    slot_start = int((day_start - scheduling_start).total_seconds() / 60)
                    slot_end = slot_start + start_hour * 60
                    if slot_end > 0:
                        forbidden_slots.append((max(0, slot_start), slot_end))
                
                # Après la fin du travail
                if end_hour < 24:
                    slot_start = int((day_start - scheduling_start).total_seconds() / 60) + end_hour * 60
                    slot_end = slot_start + (24 - end_hour) * 60
                    forbidden_slots.append((slot_start, slot_end))
        
        return forbidden_slots


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
        self.scheduling_start = datetime.now()
        
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
            
            # Initialiser le gestionnaire de matières
            material_manager = MaterialManager(stocks, operation_materials, planned_receipts)
            
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
                
                # Vérification matière avec projection
                if is_valid and not ignore_material:
                    # Vérifier les besoins matière de l'opération
                    material_status = material_manager.check_operation_materials(
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
                
                # Variable de début
                start_var = model.new_int_var(0, horizon - duration, f'start_{op_id}')
                start_vars[op_id] = start_var
                
                # Variable de fin
                end_var = model.new_int_var(duration, horizon, f'end_{op_id}')
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
                        'duration': duration
                    })
            
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
                logger.info("\n📌 CONTRAINTES DE CALENDRIER:")
                
                for machine_id, intervals_data in machine_to_intervals.items():
                    calendar = self.calendar_manager.get_calendar_for_machine(machine_id)
                    working_days = set(calendar.get('working_days', [0, 1, 2, 3, 4, 5, 6]))
                    start_hour = calendar.get('start_hour', 0)
                    end_hour = calendar.get('end_hour', 24)
                    
                    # Vérifier si le calendrier est 24/7 (pas de contrainte)
                    is_24_7 = (working_days == {0, 1, 2, 3, 4, 5, 6} and start_hour == 0 and end_hour >= 23)
                    
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
                    logger.info(f"      Calendrier: jours={list(working_days)}, heures={start_hour}-{end_hour}")
                    
                    # Pour chaque opération sur cette machine, contraindre le début
                    # à éviter les plages interdites
                    for interval_data in intervals_data:
                        op_id = interval_data['op_id']
                        if op_id not in start_vars:
                            continue
                        
                        start_var = start_vars[op_id]
                        
                        # Créer les contraintes pour éviter chaque plage interdite
                        # Une opération ne doit PAS commencer dans une plage interdite
                        for slot_start, slot_end in forbidden_slots[:50]:  # Limiter pour performance
                            # L'opération ne doit pas commencer dans [slot_start, slot_end)
                            # Soit start < slot_start, soit start >= slot_end
                            b = model.new_bool_var(f'calendar_{op_id}_{slot_start}')
                            
                            # Si b=True: start < slot_start
                            # Si b=False: start >= slot_end
                            model.add(start_var < slot_start).only_enforce_if(b)
                            model.add(start_var >= slot_end).only_enforce_if(b.Not())
                            
                            calendar_constraints_count += 1
                
                logger.info(f"\n   Total: {calendar_constraints_count} contraintes de calendrier")
            else:
                logger.info("\n📌 CONTRAINTES DE CALENDRIER: Désactivées")
            
            
            # Contraintes de séquence (opérations d'un même OF)
            operations_by_order = {}
            for op in valid_operations:
                order_id = op.get('order_id')
                if order_id:
                    if order_id not in operations_by_order:
                        operations_by_order[order_id] = []
                    operations_by_order[order_id].append(op)
            
            sequence_constraints_count = 0
            logger.info("\n📌 CONTRAINTES DE SÉQUENCE (gammes):")
            for order_id, order_ops in operations_by_order.items():
                # Trier par numéro d'opération dans la gamme
                sorted_ops = sorted(order_ops, key=lambda x: x.get('operation_id', 0))
                for i in range(len(sorted_ops) - 1):
                    op1_id = sorted_ops[i].get('id')
                    op2_id = sorted_ops[i + 1].get('id')
                    if op1_id in end_vars and op2_id in start_vars:
                        model.add(start_vars[op2_id] >= end_vars[op1_id])
                        sequence_constraints_count += 1
                
                if len(sorted_ops) > 1:
                    ops_seq = [f"{o.get('id')}(op{o.get('operation_id')})" for o in sorted_ops]
                    logger.info(f"   ✓ OF {order_id}: {' -> '.join(ops_seq)}")
            
            logger.info(f"\n   Total: {sequence_constraints_count} contraintes de séquence")
            
            # Objectif: minimiser le makespan (temps total)
            if end_vars:
                makespan = model.new_int_var(0, horizon, 'makespan')
                model.add_max_equality(makespan, list(end_vars.values()))
                model.minimize(makespan)
                logger.info(f"   ✓ Objectif: minimiser makespan")
            
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
                logger.info(f"\n📊 SOLUTION TROUVÉE:")
                
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
                
                # Vérifier l'absence de chevauchement (post-validation)
                overlap_errors = self._verify_no_overlap(scheduled_ops)
                if overlap_errors:
                    logger.error(f"⚠️ ERREUR: Chevauchements détectés!")
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
