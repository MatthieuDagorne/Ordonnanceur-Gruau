from ortools.sat.python import cp_model
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from services.diagnostics import SchedulingDiagnostics
from services.machine_assigner import MachineAssigner

logger = logging.getLogger(__name__)

class SchedulerEngine:
    def __init__(self, db):
        self.db = db
        self.diagnostics = None
    
    async def schedule(self, orders, operations, machines, rules_engine, material_checker, options=None):
        """
        Main scheduling function using OR-Tools CP-SAT with full diagnostics.
        
        options peut contenir:
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
                return {
                    'status': 'ERROR',
                    'operations': [],
                    'conflicts': [],
                    'solver_time': 0,
                    'diagnostics': self.diagnostics.get_report()
                }
            
            # PHASE 1.5: AUTO-ASSIGNATION DES MACHINES
            if auto_assign_machines and not ignore_rules:
                logger.info("\n🤖 Auto-assignation des machines activée")
                assigner = MachineAssigner(machines, rules_engine)
                assignment_result = assigner.assign_machines_to_operations(operations, orders)
                
                # Ajouter les stats d'assignation au diagnostic
                self.diagnostics.report['machine_assignment'] = assignment_result
            
            # Vérification bloquante
            if len(orders) == 0 or len(operations) == 0 or len(machines) == 0:
                logger.error("❌ Données insuffisantes pour l'ordonnancement")
                return {
                    'status': 'ERROR',
                    'operations': [],
                    'conflicts': [],
                    'solver_time': 0,
                    'diagnostics': self.diagnostics.get_report()
                }
            
            # PHASE 2: ANALYSE DE FAISABILITÉ
            feasible_count, blocked_count = self.diagnostics.analyze_all_operations(
                operations, orders, machines, rules_engine, material_checker
            )
            
            # PHASE 3: FILTRAGE DES OPÉRATIONS VALIDES
            valid_operations = []
            blocked_operations = []
            
            for op in operations:
                order_id = op.get('order_id')
                order = next((o for o in orders if o.get('id') == order_id), None)
                
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
                
                # Vérification matière (si non ignorée)
                if is_valid and not ignore_material and order:
                    article_id = order.get('article_id') or order.get('article')
                    if not material_checker.check_availability(article_id, order.get('quantity', 0)):
                        is_valid = False
                        blocking_reason = f'Matière insuffisante pour {article_id}'
                
                # Vérification règles métier (si non ignorées)
                if is_valid and not ignore_rules and machine_id:
                    # Construire le contexte de matching (sans l'id de l'opération!)
                    matching_context = {
                        'task_id': op.get('task_id'),
                        'work_center_id': op.get('work_center_id'),
                        'article_id': order.get('article_id') if order else op.get('article_id')
                    }
                    allowed, reasons, penalty = rules_engine.evaluate_machine_for_operation(
                        matching_context, machine_id
                    )
                    if not allowed:
                        is_valid = False
                        blocking_reason = f'Règle métier: {", ".join(reasons)}'
                
                if is_valid:
                    valid_operations.append(op)
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
            
            # PHASE 4: CONSTRUCTION DU MODÈLE OR-TOOLS
            model = cp_model.CpModel()
            
            # Calculate horizon (7 days in minutes)
            horizon = 7 * 24 * 60
            
            # Decision variables
            start_vars = {}
            end_vars = {}
            interval_vars = {}
            machine_to_intervals = {}
            
            # Create variables for each valid operation
            for op in valid_operations:
                op_id = op.get('id')
                duration = op.get('production_time_minutes', 60) + op.get('setup_time_minutes', 0)
                
                # Start time variable
                start_var = model.new_int_var(0, horizon - duration, f'start_{op_id}')
                start_vars[op_id] = start_var
                
                # End time variable
                end_var = model.new_int_var(duration, horizon, f'end_{op_id}')
                end_vars[op_id] = end_var
                
                # Link start and end
                model.add(end_var == start_var + duration)
                
                # Interval variable
                interval_var = model.new_interval_var(
                    start_var, duration, end_var, f'interval_{op_id}'
                )
                interval_vars[op_id] = interval_var
                
                # Group by machine
                machine_id = op.get('machine_id')
                if machine_id:
                    if machine_id not in machine_to_intervals:
                        machine_to_intervals[machine_id] = []
                    machine_to_intervals[machine_id].append(interval_var)
            
            # Log solver input
            self.diagnostics.log_solver_input(valid_operations, machine_to_intervals, horizon)
            
            # Add no-overlap constraints per machine
            for machine_id, intervals in machine_to_intervals.items():
                if len(intervals) > 1:
                    model.add_no_overlap(intervals)
                    logger.info(f"   ✓ Contrainte no-overlap ajoutée pour machine {machine_id}: {len(intervals)} opérations")
            
            # Add sequence constraints (operations of same order must be sequential)
            operations_by_order = {}
            for op in valid_operations:
                order_id = op.get('order_id')
                if order_id not in operations_by_order:
                    operations_by_order[order_id] = []
                operations_by_order[order_id].append(op)
            
            sequence_constraints_count = 0
            for order_id, order_ops in operations_by_order.items():
                # Sort by sequence
                sorted_ops = sorted(order_ops, key=lambda x: x.get('sequence', 0))
                for i in range(len(sorted_ops) - 1):
                    op1_id = sorted_ops[i].get('id')
                    op2_id = sorted_ops[i + 1].get('id')
                    if op1_id in end_vars and op2_id in start_vars:
                        model.add(start_vars[op2_id] >= end_vars[op1_id])
                        sequence_constraints_count += 1
            
            logger.info(f"   ✓ {sequence_constraints_count} contraintes de séquence ajoutées")
            
            # Objective: minimize makespan
            if end_vars:
                makespan = model.new_int_var(0, horizon, 'makespan')
                model.add_max_equality(makespan, list(end_vars.values()))
                model.minimize(makespan)
                logger.info(f"   ✓ Objectif: minimiser makespan")
            
            # PHASE 5: RÉSOLUTION
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 60
            solver.parameters.num_search_workers = 4
            
            logger.info("\\n🔄 Lancement du solveur OR-Tools CP-SAT...")
            status = solver.solve(model)
            logger.info(f"✓ Solveur terminé - Status: {self._get_status_string(status)}")
            
            result = {
                'status': self._get_status_string(status),
                'operations': [],
                'conflicts': blocked_operations,
                'solver_time': solver.wall_time,
                'objective_value': solver.objective_value if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else None
            }
            
            # Extract solution
            logger.info(f"📊 Extraction solution: status={status}, OPTIMAL={cp_model.OPTIMAL}, FEASIBLE={cp_model.FEASIBLE}")
            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                logger.info(f"   Valid operations count: {len(valid_operations)}")
                for op in valid_operations:
                    op_id = op.get('id')
                    if op_id in start_vars:
                        start_time = solver.value(start_vars[op_id])
                        end_time = solver.value(end_vars[op_id])
                        
                        result['operations'].append({
                            'operation_id': op_id,
                            'order_id': op.get('order_id'),
                            'machine_id': op.get('machine_id'),
                            'start_time': start_time,
                            'end_time': end_time,
                            'start_date': self._minutes_to_datetime(start_time).isoformat(),
                            'end_date': self._minutes_to_datetime(end_time).isoformat(),
                            'decision_reason': f'Assigné à machine {op.get("machine_id")}'
                        })
                logger.info(f"   Operations extracted: {len(result['operations'])}")
            
            # Log solver result
            self.diagnostics.log_solver_result(
                result['status'],
                result['operations'],
                result['conflicts'],
                result['solver_time']
            )
            
            # Add diagnostics to result
            result['diagnostics'] = self.diagnostics.get_report()
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur d'ordonnancement: {str(e)}", exc_info=True)
            if self.diagnostics:
                return {
                    'status': 'ERROR',
                    'operations': [],
                    'conflicts': [{'error': str(e)}],
                    'solver_time': 0,
                    'diagnostics': self.diagnostics.get_report()
                }
            else:
                return {
                    'status': 'ERROR',
                    'operations': [],
                    'conflicts': [{'error': str(e)}],
                    'solver_time': 0
                }
    
    def _get_status_string(self, status):
        status_map = {
            cp_model.OPTIMAL: 'OPTIMAL',
            cp_model.FEASIBLE: 'FEASIBLE',
            cp_model.INFEASIBLE: 'INFEASIBLE',
            cp_model.MODEL_INVALID: 'MODEL_INVALID',
            cp_model.UNKNOWN: 'UNKNOWN'
        }
        return status_map.get(status, 'UNKNOWN')
    
    def _minutes_to_datetime(self, minutes):
        """Convert minutes from horizon start to datetime."""
        start = datetime.now()
        return start + timedelta(minutes=minutes)
