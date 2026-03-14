import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MachineAssigner:
    """
    Service d'auto-assignation des machines aux opérations.
    
    Logique basée sur:
    - task_id (de l'opération)
    - work_center_id (de l'opération)
    - article_id (de l'ordre de fabrication via jointure)
    
    N'utilise JAMAIS l'id de l'opération pour le matching des règles.
    """
    
    def __init__(self, machines: List[Dict], rules_engine):
        self.machines = machines
        self.rules_engine = rules_engine
        
        # Index machines par work_center_id
        self.machines_by_workcenter: Dict[str, List[Dict]] = {}
        for machine in machines:
            wc_id = machine.get('work_center_id')
            if wc_id:
                if wc_id not in self.machines_by_workcenter:
                    self.machines_by_workcenter[wc_id] = []
                self.machines_by_workcenter[wc_id].append(machine)
        
        # Log l'index des machines
        logger.info("\n" + "-"*60)
        logger.info("INDEX DES MACHINES PAR WORK_CENTER")
        logger.info("-"*60)
        for wc_id, wc_machines in self.machines_by_workcenter.items():
            machine_names = [m.get('name', m.get('id')) for m in wc_machines]
            logger.info(f"  {wc_id}: {', '.join(machine_names)}")
        if not self.machines_by_workcenter:
            logger.warning("  AUCUNE MACHINE INDEXEE!")
        logger.info("-"*60 + "\n")
    
    def assign_machine_to_operation(
        self, 
        operation: Dict[str, Any], 
        order: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Assigne automatiquement une machine à une opération.
        
        Critères utilisés (PAS l'id de l'opération):
        - task_id: de l'opération
        - work_center_id: de l'opération
        - article_id: de l'ordre de fabrication (jointure)
        """
        # Extraire les critères de l'opération
        operation_id = operation.get('id')
        task_id = operation.get('task_id')
        work_center_id = operation.get('work_center_id')
        
        # article_id vient de l'ordre de fabrication (pas de l'opération directement)
        article_id = None
        if order:
            article_id = order.get('article_id') or order.get('article')
        
        # Log détaillé de l'opération
        logger.info(f"\n{'='*60}")
        logger.info(f"ASSIGNATION MACHINE - Operation: {operation_id}")
        logger.info(f"{'='*60}")
        logger.info(f"  Criteres de matching:")
        logger.info(f"    - task_id:        {task_id or 'NON DEFINI'}")
        logger.info(f"    - work_center_id: {work_center_id or 'NON DEFINI'}")
        logger.info(f"    - article_id:     {article_id or 'NON DEFINI (depuis ordre)'}")
        
        # Validation des critères obligatoires
        if not task_id and not work_center_id:
            logger.error(f"  [ERREUR] task_id ET work_center_id manquants!")
            return self._error_result(
                'task_id et work_center_id manquants - impossible de matcher les regles',
                'DONNEES_INCOMPLETES'
            )
        
        if not work_center_id:
            logger.error(f"  [ERREUR] work_center_id manquant - impossible de trouver les machines candidates")
            return self._error_result(
                f'work_center_id manquant pour operation {operation_id}',
                'WORK_CENTER_MANQUANT'
            )
        
        # ÉTAPE 1: Récupérer les machines candidates du work_center
        candidate_machines = self.machines_by_workcenter.get(work_center_id, [])
        candidate_names = [m.get('name', m.get('id')) for m in candidate_machines]
        
        logger.info(f"\n  ETAPE 1: Machines du work_center '{work_center_id}'")
        if len(candidate_machines) == 0:
            logger.error(f"    -> AUCUNE MACHINE rattachee au work_center {work_center_id}")
            logger.error(f"    -> Work centers disponibles: {list(self.machines_by_workcenter.keys())}")
            return self._error_result(
                f'Aucune machine rattachee au work_center {work_center_id}',
                'AUCUNE_MACHINE_DANS_WORK_CENTER'
            )
        else:
            logger.info(f"    -> {len(candidate_machines)} machine(s) trouvee(s): {', '.join(candidate_names)}")
        
        # ÉTAPE 2: Appliquer les règles métier
        logger.info(f"\n  ETAPE 2: Application des regles metier")
        
        # Construire le contexte pour le matching (sans l'id de l'opération!)
        matching_context = {
            'task_id': task_id,
            'work_center_id': work_center_id,
            'article_id': article_id,
            # Note: on n'inclut PAS 'id' de l'opération
        }
        
        allowed_machines, forbidden_machines, diagnostics = self.rules_engine.get_allowed_machines(
            matching_context, 
            candidate_machines
        )
        
        # Log des règles appliquées
        applicable_rules = diagnostics.get('applicable_rules', [])
        if applicable_rules:
            logger.info(f"    -> {len(applicable_rules)} regle(s) applicable(s):")
            for r in applicable_rules:
                logger.info(f"       - {r['name']} ({r['type']}) -> machine {r['machine_id']}")
        else:
            logger.info(f"    -> Aucune regle specifique applicable")
        
        # Log des machines interdites
        if forbidden_machines:
            logger.info(f"\n    Machines INTERDITES par les regles:")
            for m in forbidden_machines:
                reasons = m.get('rule_reasons', ['Interdit'])
                logger.info(f"       - {m.get('name')}: {', '.join(reasons)}")
        
        # Log des machines autorisées
        logger.info(f"\n    Machines AUTORISEES apres regles:")
        if allowed_machines:
            for m in allowed_machines:
                score = m.get('preference_score', 0)
                score_str = f" (PREFEREE +{score})" if score > 0 else ""
                logger.info(f"       - {m.get('name')}{score_str}")
        else:
            logger.warning(f"       -> AUCUNE MACHINE AUTORISEE!")
        
        # ÉTAPE 3: Sélection finale
        logger.info(f"\n  ETAPE 3: Selection finale")
        
        if len(allowed_machines) == 0:
            if len(forbidden_machines) == len(candidate_machines):
                cause = 'Toutes les machines interdites par les regles'
            else:
                cause = 'Aucune machine compatible trouvee'
            
            logger.error(f"    -> ECHEC: {cause}")
            return self._error_result(
                cause,
                'TOUTES_MACHINES_INTERDITES' if forbidden_machines else 'AUCUNE_MACHINE_COMPATIBLE',
                blocked_machines=[
                    {
                        'machine_id': m.get('id'),
                        'machine_name': m.get('name'),
                        'reason': ', '.join(m.get('rule_reasons', []))
                    }
                    for m in forbidden_machines
                ],
                rules_applied=applicable_rules
            )
        
        # Sélectionner la meilleure machine (triées par score décroissant)
        selected = allowed_machines[0]
        selected_id = selected.get('id')
        selected_name = selected.get('name')
        preference_score = selected.get('preference_score', 0)
        
        logger.info(f"    -> SUCCES: Machine selectionnee = {selected_name}")
        if preference_score > 0:
            logger.info(f"       (Machine preferee avec score +{preference_score})")
        
        # Résumé final
        logger.info(f"\n  RESUME:")
        logger.info(f"    Operation:      {operation_id}")
        logger.info(f"    task_id:        {task_id}")
        logger.info(f"    work_center_id: {work_center_id}")
        logger.info(f"    article_id:     {article_id or '-'}")
        logger.info(f"    Machines WC:    {', '.join(candidate_names)}")
        if applicable_rules:
            logger.info(f"    Regles:         {', '.join([r['name'] for r in applicable_rules])}")
        logger.info(f"    Machine finale: {selected_name}")
        logger.info(f"{'='*60}\n")
        
        return {
            'machine_id': selected_id,
            'machine_name': selected_name,
            'is_assigned': True,
            'reason': f'Machine {selected_name} selectionnee (task={task_id}, wc={work_center_id})',
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
            'rules_applied': applicable_rules,
            'failure_cause': None
        }
    
    def _error_result(
        self, 
        reason: str, 
        failure_cause: str,
        blocked_machines: List[Dict] = None,
        rules_applied: List[Dict] = None
    ) -> Dict[str, Any]:
        """Génère un résultat d'échec standardisé."""
        return {
            'machine_id': None,
            'machine_name': None,
            'is_assigned': False,
            'reason': reason,
            'compatible_count': 0,
            'blocked_machines': blocked_machines or [],
            'preference_score': 0,
            'rules_applied': rules_applied or [],
            'failure_cause': failure_cause
        }
    
    def assign_machines_to_operations(
        self, 
        operations: List[Dict], 
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """
        Assigne automatiquement les machines à toutes les opérations.
        """
        logger.info("\n" + "="*80)
        logger.info("AUTO-ASSIGNATION DES MACHINES")
        logger.info("Criteres: task_id + work_center_id + article_id (depuis ordre)")
        logger.info("="*80)
        
        # Index des ordres pour jointure rapide
        orders_by_id = {o.get('id'): o for o in orders}
        
        # Réinitialiser les logs des règles
        self.rules_engine.clear_applied_rules_log()
        
        # Compteurs
        stats = {
            'assigned': 0,
            'unassigned': 0,
            'preferred': 0,
            'by_failure_cause': {}
        }
        assignment_details = []
        
        for operation in operations:
            # Jointure avec l'ordre pour récupérer article_id
            order_id = operation.get('order_id')
            order = orders_by_id.get(order_id)
            
            # Assigner la machine
            assignment = self.assign_machine_to_operation(operation, order)
            
            if assignment['is_assigned']:
                # Mettre à jour l'opération avec la machine assignée
                operation['machine_id'] = assignment['machine_id']
                stats['assigned'] += 1
                if assignment.get('preference_score', 0) > 0:
                    stats['preferred'] += 1
            else:
                stats['unassigned'] += 1
                # Compter par cause d'échec
                cause = assignment.get('failure_cause', 'INCONNU')
                stats['by_failure_cause'][cause] = stats['by_failure_cause'].get(cause, 0) + 1
            
            # Enregistrer le détail
            assignment_details.append({
                'operation_id': operation.get('id'),
                'task_id': operation.get('task_id'),
                'work_center_id': operation.get('work_center_id'),
                'article_id': order.get('article_id') if order else None,
                'order_id': order_id,
                **assignment
            })
        
        # Résumé final
        logger.info("\n" + "="*80)
        logger.info("RESUME ASSIGNATION")
        logger.info("="*80)
        logger.info(f"  Total operations:    {len(operations)}")
        logger.info(f"  Assignees:           {stats['assigned']}")
        if stats['preferred'] > 0:
            logger.info(f"  Avec preference:     {stats['preferred']}")
        logger.info(f"  Non assignees:       {stats['unassigned']}")
        
        if stats['by_failure_cause']:
            logger.info(f"\n  Causes d'echec:")
            for cause, count in stats['by_failure_cause'].items():
                logger.info(f"    - {cause}: {count}")
        
        logger.info("="*80 + "\n")
        
        return {
            'assigned_count': stats['assigned'],
            'unassigned_count': stats['unassigned'],
            'preferred_count': stats['preferred'],
            'total_operations': len(operations),
            'failure_causes': stats['by_failure_cause'],
            'assignment_details': assignment_details,
            'rules_diagnostics': self.rules_engine.get_diagnostics()
        }
