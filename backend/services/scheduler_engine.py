from ortools.sat.python import cp_model
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SchedulerEngine:
    def __init__(self, db):
        self.db = db
    
    async def schedule(self, orders, operations, machines, rules_engine, material_checker):
        """
        Main scheduling function using OR-Tools CP-SAT.
        """
        try:
            model = cp_model.CpModel()
            
            # Calculate horizon (7 days in minutes)
            horizon = 7 * 24 * 60
            
            # Decision variables
            start_vars = {}
            end_vars = {}
            interval_vars = {}
            machine_to_intervals = {}
            
            # Filter operations that pass material check
            valid_operations = []
            blocked_operations = []
            
            for op in operations:
                order_id = op.get('order_id')
                order = next((o for o in orders if o.get('id') == order_id), None)
                
                if order:
                    # Check material availability
                    article = order.get('article')
                    if material_checker.check_availability(article, order.get('quantity', 0)):
                        valid_operations.append(op)
                    else:
                        blocked_operations.append({
                            'operation_id': op.get('id'),
                            'reason': f'Material unavailable for article {article}'
                        })
            
            logger.info(f"Valid operations: {len(valid_operations)}, Blocked: {len(blocked_operations)}")
            
            # Create variables for each operation
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
            
            # Add no-overlap constraints per machine
            for machine_id, intervals in machine_to_intervals.items():
                if len(intervals) > 1:
                    model.add_no_overlap(intervals)
            
            # Add sequence constraints (operations of same order must be sequential)
            operations_by_order = {}
            for op in valid_operations:
                order_id = op.get('order_id')
                if order_id not in operations_by_order:
                    operations_by_order[order_id] = []
                operations_by_order[order_id].append(op)
            
            for order_id, order_ops in operations_by_order.items():
                # Sort by sequence
                sorted_ops = sorted(order_ops, key=lambda x: x.get('sequence', 0))
                for i in range(len(sorted_ops) - 1):
                    op1_id = sorted_ops[i].get('id')
                    op2_id = sorted_ops[i + 1].get('id')
                    if op1_id in end_vars and op2_id in start_vars:
                        model.add(start_vars[op2_id] >= end_vars[op1_id])
            
            # Objective: minimize makespan
            makespan = model.new_int_var(0, horizon, 'makespan')
            if end_vars:
                model.add_max_equality(makespan, list(end_vars.values()))
                model.minimize(makespan)
            
            # Solve
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 60
            solver.parameters.num_search_workers = 4
            
            status = solver.solve(model)
            
            result = {
                'status': self._get_status_string(status),
                'operations': [],
                'conflicts': [],
                'solver_time': solver.wall_time,
                'objective_value': solver.objective_value if status in [cp_model.OPTIMAL, cp_model.FEASIBLE] else None
            }
            
            # Extract solution
            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
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
                            'decision_reason': f'Assigned to machine {op.get("machine_id")}'
                        })
            
            # Add blocked operations to conflicts
            result['conflicts'].extend(blocked_operations)
            
            return result
            
        except Exception as e:
            logger.error(f"Scheduling error: {str(e)}", exc_info=True)
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