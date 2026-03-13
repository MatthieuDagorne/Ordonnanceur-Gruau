import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MachineAssigner:
    """
    Service d'auto-assignation des machines aux opérations.
    Détermine la meilleure machine selon les règles métier et la disponibilité.
    """
    
    def __init__(self, machines, rules_engine):
        self.machines = machines
        self.rules_engine = rules_engine
    
    def assign_machine_to_operation(self, operation: Dict[str, Any], order: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Assigne automatiquement une machine à une opération selon les règles.
        
        Critères de sélection :
        1. Compatibilité machine/opération (règles dures)
        2. Compatibilité article/machine si article connu
        3. Préférences machines (règles souples)
        4. Première machine disponible sinon
        
        Returns:
            dict avec 'machine_id', 'reason', 'is_assigned'
        """
        operation_code = str(operation.get('operation_number', ''))
        article_id = order.get('article') if order else None
        
        compatible_machines = []
        preferred_machines = []
        blocked_machines = []
        
        # Parcourir toutes les machines
        for machine in self.machines:
            machine_id = machine.get('id')
            
            # Vérifier règle machine/opération
            allowed, reason, penalty = self.rules_engine.is_operation_allowed_on_machine(
                operation_code, machine_id
            )
            
            if not allowed:
                blocked_machines.append({
                    'machine_id': machine_id,
                    'reason': reason
                })
                continue
            
            # Vérifier règle article/machine si applicable
            if article_id:
                article_allowed, article_reason = self.rules_engine.is_article_allowed_on_machine(
                    article_id, machine_id
                )
                if not article_allowed:
                    blocked_machines.append({
                        'machine_id': machine_id,
                        'reason': article_reason
                    })
                    continue
            
            # Machine compatible
            compatible_machines.append({
                'machine_id': machine_id,
                'machine_name': machine.get('name'),
                'penalty': penalty
            })
            
            # Vérifier si c'est une machine préférée
            if penalty == 0:  # Pas de pénalité = préférence neutre ou positive
                preferred_machines.append(machine_id)
        
        # Stratégie d'assignation
        if len(compatible_machines) == 0:
            # Aucune machine compatible
            logger.warning(f"⚠️  Op {operation.get('id')}: Aucune machine compatible trouvée")
            return {
                'machine_id': None,
                'is_assigned': False,
                'reason': 'Aucune machine compatible',
                'compatible_count': 0,
                'blocked_machines': blocked_machines
            }
        
        # Choisir la meilleure machine
        # Priorité 1: Machine préférée (penalty = 0)
        if preferred_machines:
            selected_machine_id = preferred_machines[0]
            selected = next(m for m in compatible_machines if m['machine_id'] == selected_machine_id)
            reason = f"Machine préférée: {selected['machine_name']}"
        else:
            # Priorité 2: Machine avec pénalité minimale
            selected = min(compatible_machines, key=lambda m: m['penalty'])
            selected_machine_id = selected['machine_id']
            reason = f"Machine compatible: {selected['machine_name']} (pénalité: {selected['penalty']})"
        
        logger.info(f"✓ Op {operation.get('id')}: Assignée à {selected['machine_name']}")
        
        return {
            'machine_id': selected_machine_id,
            'is_assigned': True,
            'reason': reason,
            'compatible_count': len(compatible_machines),
            'blocked_machines': blocked_machines
        }
    
    def assign_machines_to_operations(self, operations: List[Dict], orders: List[Dict]) -> Dict[str, Any]:
        """
        Assigne automatiquement les machines à toutes les opérations.
        
        Returns:
            dict avec statistiques d'assignation
        """
        logger.info("\n" + "="*80)
        logger.info("AUTO-ASSIGNATION DES MACHINES")
        logger.info("="*80)
        
        assigned_count = 0
        unassigned_count = 0
        assignment_details = []
        
        for operation in operations:
            # Trouver l'ordre correspondant
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
                'operation_number': operation.get('operation_number'),
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
