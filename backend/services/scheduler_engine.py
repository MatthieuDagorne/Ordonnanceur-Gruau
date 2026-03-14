from ortools.sat.python import cp_model
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from services.diagnostics import SchedulingDiagnostics
from services.machine_assigner import MachineAssigner

logger = logging.getLogger(__name__)


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
        
        Options:
        - ignore_rules: bool
        - ignore_material: bool
        - debug_mode: bool
        - auto_assign_machines: bool (default True)
        """
        options = options or {}
        debug_mode = options.get('debug_mode', True)
        ignore_rules = options.get('ignore_rules', False)
        ignore_material = options.get('ignore_material', False)
        auto_assign_machines = options.get('auto_assign_machines', True)
        
        # Point de départ pour l'horizon de planification
        self.scheduling_start = datetime.now()
        
        # Initialiser le diagnostic
        self.diagnostics = SchedulingDiagnostics(self.db)
        
        try:
            # PHASE 1: PRE-VALIDATION
            stocks = await self.db.stocks.find({}, {"_id": 0}).to_list(1000)
            rules = await self.db.business_rules.find({}, {"_id": 0}).to_list(1000)
            
            await self.diagnostics.run_pre_validation(orders, operations, machines, rules, stocks)
            
            # Vérification bloquante
            if len(orders) == 0 or len(operations) == 0 or len(machines) == 0:
                logger.error("❌ Données insuffisantes pour l'ordonnancement")
                return self._error_result("Données insuffisantes")
            
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
            
            for op in operations:
                order_id = op.get('order_id')
                order = orders_by_id.get(order_id)
                
                is_valid = True
                blocking_reason = None
                
                # Vérification machine
                machine_id = op.get('machine_id')
                if not machine_id:
                    is_valid = False
                    blocking_reason = 'Aucune machine assignée'
                elif not any(m.get('id') == machine_id for m in machines):
                    is_valid = False
                    blocking_reason = f'Machine {machine_id} introuvable'
                
                # Vérification matière
                if is_valid and not ignore_material and order:
                    article_id = order.get('article_id') or order.get('article')
                    if not material_checker.check_availability(article_id, order.get('quantity', 0)):
                        is_valid = False
                        blocking_reason = f'Matière insuffisante pour {article_id}'
                
                if is_valid:
                    # Enrichir avec due_date pour le tri
                    op_enriched = {
                        **op,
                        '_due_date': order.get('due_date') if order else None,
                        '_priority': order.get('priority', 0) if order else 0,
                        '_article_id': (order.get('article_id') or order.get('article')) if order else None
                    }
                    valid_operations.append(op_enriched)
                else:
                    blocked_operations.append({
                        'operation_id': op.get('id'),
                        'reason': blocking_reason or 'Raison inconnue'
                    })
            
            logger.info(f"📊 Opérations valides pour le solveur: {len(valid_operations)}")
            logger.info(f"📊 Opérations bloquées: {len(blocked_operations)}")
            
            if len(valid_operations) == 0:
                logger.error("❌ Aucune opération valide pour l'ordonnancement")
                return {
                    'status': 'NO_VALID_OPERATIONS',
                    'operations': [],
                    'conflicts': blocked_operations,
                    'solver_time': 0,
                    'diagnostics': self.diagnostics.get_report()
                }
            
            # Trier les opérations par urgence (due_date)
            def get_sort_key(op):
                due_date = op.get('_due_date')
                priority = op.get('_priority', 0)
                if due_date:
                    dt = self._parse_datetime(due_date)
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
            solver.parameters.max_time_in_seconds = 60
            solver.parameters.num_search_workers = 4
            
            logger.info("\n🔄 Lancement du solveur OR-Tools CP-SAT...")
            status = solver.solve(model)
            status_str = self._get_status_string(status)
            logger.info(f"✓ Solveur terminé - Status: {status_str}")
            
            result = {
                'status': status_str,
                'operations': [],
                'conflicts': blocked_operations,
                'solver_time': solver.wall_time,
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
                            'due_date': op.get('_due_date')
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
