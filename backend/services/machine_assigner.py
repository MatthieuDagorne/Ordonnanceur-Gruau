import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MachineAssigner:
    """
    Service d'auto-assignation des machines aux opérations.
    Basé sur task_id et work_center_id.
    """
    
    def __init__(self, machines, rules_engine):
        self.machines = machines
        self.rules_engine = rules_engine
        
        # Index machines by work_center_id for fast lookup
        self.machines_by_workcenter = {}
        for machine in machines:
            wc_id = machine.get('work_center_id')
            if wc_id not in self.machines_by_workcenter:
                self.machines_by_workcenter[wc_id] = []
            self.machines_by_workcenter[wc_id].append(machine)
    
    def assign_machine_to_operation(self, operation: Dict[str, Any], order: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Assigne automatiquement une machine à une opération.
        
        Logique :
        1. Filtrer les machines du work_center_id requis
        2. Appliquer les règles task_id / machine
        3. Appliquer les règles article / machine
        4. Choisir la meilleure machine (pénalité minimale)
        """
        task_id = operation.get('task_id')
        work_center_id = operation.get('work_center_id')
        article_id = operation.get('article_id')
        operation_id = operation.get('id')
        
        if not task_id or not work_center_id:
            logger.error(f"❌ Op {operation_id}: task_id ou work_center_id manquant")
            return {
                'machine_id': None,
                'is_assigned': False,
                'reason': 'task_id ou work_center_id manquant',
                'compatible_count': 0,
                'blocked_machines': []
            }
        
        # Étape 1: Filtrer machines du work_center requis
        candidate_machines = self.machines_by_workcenter.get(work_center_id, [])
        
        if len(candidate_machines) == 0:
            logger.warning(f"⚠️  Op {operation_id}: Aucune machine trouvée pour work_center {work_center_id}")
            return {
                'machine_id': None,
                'is_assigned': False,
                'reason': f'Aucune machine pour work_center {work_center_id}',
                'compatible_count': 0,
                'blocked_machines': []
            }
        
        logger.info(f"→ Op {operation_id}: {len(candidate_machines)} machine(s) trouvée(s) pour work_center {work_center_id}")
        
        compatible_machines = []
        blocked_machines = []
        
        # Étape 2: Appliquer règles métier
        for machine in candidate_machines:
            machine_id = machine.get('id')
            machine_name = machine.get('name')
            total_penalty = 0
            blocking_reasons = []
            
            # Vérifier règle task / machine
            allowed_task, reason_task, penalty_task = self.rules_engine.is_task_allowed_on_machine(
                task_id, machine_id
            )
            
            if not allowed_task:
                blocked_machines.append({
                    'machine_id': machine_id,
                    'machine_name': machine_name,
                    'reason': reason_task
                })
                logger.info(f"  ✗ Machine {machine_name}: {reason_task}")
                continue
            
            total_penalty += penalty_task
            
            # Vérifier règle work_center / machine
            allowed_wc, reason_wc, penalty_wc = self.rules_engine.is_workcenter_allowed_on_machine(
                work_center_id, machine_id
            )
            
            if not allowed_wc:
                blocked_machines.append({
                    'machine_id': machine_id,
                    'machine_name': machine_name,
                    'reason': reason_wc
                })
                logger.info(f"  ✗ Machine {machine_name}: {reason_wc}")
                continue
            
            total_penalty += penalty_wc
            
            # Vérifier règle article / machine si applicable
            if article_id:
                allowed_article, reason_article = self.rules_engine.is_article_allowed_on_machine(
                    article_id, machine_id
                )
                
                if not allowed_article:
                    blocked_machines.append({
                        'machine_id': machine_id,
                        'machine_name': machine_name,
                        'reason': reason_article
                    })
                    logger.info(f"  ✗ Machine {machine_name}: {reason_article}")
                    continue
            
            # Machine compatible
            compatible_machines.append({
                'machine_id': machine_id,
                'machine_name': machine_name,
                'penalty': total_penalty
            })
            logger.info(f"  ✓ Machine {machine_name}: compatible (pénalité: {total_penalty})")
        
        # Étape 3: Choisir la meilleure machine
        if len(compatible_machines) == 0:
            logger.warning(f"⚠️  Op {operation_id}: Aucune machine compatible après application des règles")
            return {
                'machine_id': None,
                'is_assigned': False,
                'reason': 'Aucune machine compatible après règles métier',
                'compatible_count': 0,
                'blocked_machines': blocked_machines
            }
        
        # Sélectionner machine avec pénalité minimale
        selected = min(compatible_machines, key=lambda m: m['penalty'])
        selected_machine_id = selected['machine_id']
        selected_machine_name = selected['machine_name']
        
        reason = f"Machine {selected_machine_name} (task: {task_id}, work_center: {work_center_id}, pénalité: {selected['penalty']})"
        
        logger.info(f"✓ Op {operation_id}: Assignée à {selected_machine_name}")
        
        return {
            'machine_id': selected_machine_id,
            'machine_name': selected_machine_name,
            'is_assigned': True,
            'reason': reason,
            'compatible_count': len(compatible_machines),
            'blocked_machines': blocked_machines,
            'penalty': selected['penalty']
        }
    
    def assign_machines_to_operations(self, operations: List[Dict], orders: List[Dict]) -> Dict[str, Any]:
        """
        Assigne automatiquement les machines à toutes les opérations.
        
        Returns:
            dict avec statistiques d'assignation
        """
        logger.info("\n" + "="*80)
        logger.info("AUTO-ASSIGNATION DES MACHINES (TASK_ID + WORK_CENTER_ID)")
        logger.info("="*80)
        
        assigned_count = 0
        unassigned_count = 0
        assignment_details = []
        
        for operation in operations:
            # Trouver l'ordre correspondant (jointure sur order_id)
            order = next((o for o in orders if o.get('id') == operation.get('order_id')), None)
            
            # Assigner machine
            assignment = self.assign_machine_to_operation(operation, order)
            
            if assignment['is_assigned']:
                operation['machine_id'] = assignment['machine_id']
                assigned_count += 1
            else:
                unassigned_count += 1
            
            assignment_details.append({
                'operation_id': operation.get('id'),
                'task_id': operation.get('task_id'),
                'work_center_id': operation.get('work_center_id'),
                'order_id': operation.get('order_id'),
                **assignment
            })
        
        logger.info(f"\n📊 Résumé assignation:")
        logger.info(f"   ✓ {assigned_count} opérations assignées")
        logger.info(f"   ✗ {unassigned_count} opérations non assignées")
        logger.info("="*80 + "\n")
        
        return {
            'assigned_count': assigned_count,
            'unassigned_count': unassigned_count,
            'total_operations': len(operations),
            'assignment_details': assignment_details
        }
