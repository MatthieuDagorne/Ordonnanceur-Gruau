import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MachineAssigner:
    """
    Service d'auto-assignation des machines aux opérations.
    Utilise le moteur de règles simplifié (ALLOW, FORBID, PREFER).
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
        2. Appliquer les règles ALLOW/FORBID/PREFER
        3. Choisir la meilleure machine (score de préférence)
        """
        task_id = operation.get('task_id')
        work_center_id = operation.get('work_center_id')
        article_id = operation.get('article_id')
        operation_id = operation.get('id')
        
        if not task_id or not work_center_id:
            logger.error(f"  [ERREUR] Op {operation_id}: task_id ou work_center_id manquant")
            return {
                'machine_id': None,
                'is_assigned': False,
                'reason': 'task_id ou work_center_id manquant',
                'compatible_count': 0,
                'blocked_machines': [],
                'rules_applied': []
            }
        
        # Étape 1: Filtrer machines du work_center requis
        candidate_machines = self.machines_by_workcenter.get(work_center_id, [])
        
        if len(candidate_machines) == 0:
            logger.warning(f"  [ATTENTION] Op {operation_id}: Aucune machine pour work_center {work_center_id}")
            return {
                'machine_id': None,
                'is_assigned': False,
                'reason': f'Aucune machine pour work_center {work_center_id}',
                'compatible_count': 0,
                'blocked_machines': [],
                'rules_applied': []
            }
        
        logger.info(f"  Op {operation_id}: {len(candidate_machines)} machine(s) dans work_center {work_center_id}")
        
        # Étape 2: Appliquer les règles métier avec le nouveau moteur
        allowed_machines, forbidden_machines, diagnostics = self.rules_engine.get_allowed_machines(
            operation, candidate_machines
        )
        
        # Log les règles appliquées
        rules_applied = diagnostics.get('applicable_rules', [])
        if rules_applied:
            logger.info(f"    -> {len(rules_applied)} regle(s) appliquee(s)")
            for r in rules_applied:
                logger.info(f"       - {r['name']} ({r['type']})")
        
        # Étape 3: Choisir la meilleure machine
        if len(allowed_machines) == 0:
            logger.warning(f"  [ATTENTION] Op {operation_id}: Aucune machine compatible apres regles")
            blocked_info = [
                {
                    'machine_id': m.get('id'),
                    'machine_name': m.get('name'),
                    'reason': ', '.join(m.get('rule_reasons', ['Interdit par regle']))
                }
                for m in forbidden_machines
            ]
            return {
                'machine_id': None,
                'is_assigned': False,
                'reason': 'Aucune machine compatible apres regles metier',
                'compatible_count': 0,
                'blocked_machines': blocked_info,
                'rules_applied': rules_applied
            }
        
        # Sélectionner la machine avec le meilleur score (déjà triée)
        selected_machine = allowed_machines[0]
        selected_machine_id = selected_machine.get('id')
        selected_machine_name = selected_machine.get('name')
        preference_score = selected_machine.get('preference_score', 0)
        
        reason_parts = [f"Machine {selected_machine_name}"]
        if preference_score > 0:
            reason_parts.append(f"preferee (score: +{preference_score})")
        reason_parts.append(f"task: {task_id}, wc: {work_center_id}")
        reason = ' - '.join(reason_parts)
        
        logger.info(f"  [OK] Op {operation_id}: Assignee a {selected_machine_name} (score: {preference_score})")
        
        return {
            'machine_id': selected_machine_id,
            'machine_name': selected_machine_name,
            'is_assigned': True,
            'reason': reason,
            'compatible_count': len(allowed_machines),
            'blocked_machines': [
                {
                    'machine_id': m.get('id'),
                    'machine_name': m.get('name'),
                    'reason': ', '.join(m.get('rule_reasons', []))
                }
                for m in forbidden_machines
            ],
            'preference_score': preference_score,
            'rules_applied': rules_applied
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
        
        # Réinitialiser le log des règles appliquées
        self.rules_engine.clear_applied_rules_log()
        
        assigned_count = 0
        unassigned_count = 0
        preferred_count = 0
        assignment_details = []
        
        for operation in operations:
            # Trouver l'ordre correspondant (jointure sur order_id)
            order = next((o for o in orders if o.get('id') == operation.get('order_id')), None)
            
            # Assigner machine
            assignment = self.assign_machine_to_operation(operation, order)
            
            if assignment['is_assigned']:
                operation['machine_id'] = assignment['machine_id']
                assigned_count += 1
                if assignment.get('preference_score', 0) > 0:
                    preferred_count += 1
            else:
                unassigned_count += 1
            
            assignment_details.append({
                'operation_id': operation.get('id'),
                'task_id': operation.get('task_id'),
                'work_center_id': operation.get('work_center_id'),
                'article_id': operation.get('article_id'),
                'order_id': operation.get('order_id'),
                **assignment
            })
        
        logger.info(f"\nResume assignation:")
        logger.info(f"   [OK] {assigned_count} operations assignees")
        if preferred_count > 0:
            logger.info(f"   [PREFER] {preferred_count} avec machine preferee")
        logger.info(f"   [NOK] {unassigned_count} operations non assignees")
        logger.info("="*80 + "\n")
        
        return {
            'assigned_count': assigned_count,
            'unassigned_count': unassigned_count,
            'preferred_count': preferred_count,
            'total_operations': len(operations),
            'assignment_details': assignment_details,
            'rules_diagnostics': self.rules_engine.get_diagnostics()
        }
