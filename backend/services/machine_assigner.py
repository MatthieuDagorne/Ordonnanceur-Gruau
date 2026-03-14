import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MachineAssigner:
    """
    Service d'auto-assignation des machines aux opérations.
    
    LOGIQUE DE MATCHING:
    1. Récupérer task_id et work_center_id de l'opération
    2. Trouver les machines du work_center_id
    3. Appliquer les règles métier (FORBID, ALLOW, PREFER)
    4. Sélectionner la meilleure machine
    
    N'utilise JAMAIS l'id de l'opération pour le matching.
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
        
        # Log l'index complet
        logger.info("\n" + "="*80)
        logger.info("INDEX DES MACHINES PAR WORK_CENTER_ID")
        logger.info("="*80)
        if self.machines_by_workcenter:
            for wc_id, wc_machines in self.machines_by_workcenter.items():
                machine_names = [f"{m.get('name')} ({m.get('id')[:8]}...)" for m in wc_machines]
                logger.info(f"  work_center_id={wc_id}")
                for name in machine_names:
                    logger.info(f"    -> {name}")
        else:
            logger.warning("  AUCUNE MACHINE INDEXEE - Verifiez que les machines ont un work_center_id!")
        logger.info("="*80 + "\n")
    
    def assign_machine_to_operation(
        self, 
        operation: Dict[str, Any], 
        order: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Diagnostic complet étape par étape pour l'assignation d'une machine.
        """
        # === ÉTAPE 1: Extraire les critères ===
        op_id = operation.get('id')
        task_id = operation.get('task_id')
        work_center_id = operation.get('work_center_id')
        article_id = order.get('article_id') if order else operation.get('article_id')
        
        # Créer le diagnostic détaillé
        diagnostic = {
            'operation_id': op_id,
            'task_id': task_id,
            'work_center_id': work_center_id,
            'article_id': article_id,
            'step1_criteria': {},
            'step2_machines_in_wc': [],
            'step3_rules_found': [],
            'step4_machines_forbidden': [],
            'step5_machines_preferred': [],
            'step6_machines_allowed': [],
            'step7_final_candidates': [],
            'step8_selected_machine': None,
            'step9_failure_cause': None,
            'is_assigned': False
        }
        
        logger.info(f"\n{'='*80}")
        logger.info(f"DIAGNOSTIC ASSIGNATION - Operation: {op_id}")
        logger.info(f"{'='*80}")
        
        # === ÉTAPE 1: Afficher les critères ===
        logger.info(f"\n[ETAPE 1] CRITERES DE L'OPERATION")
        logger.info(f"  operation_id:   {op_id}")
        logger.info(f"  task_id:        {task_id if task_id else 'NON DEFINI'}")
        logger.info(f"  work_center_id: {work_center_id if work_center_id else 'NON DEFINI'}")
        logger.info(f"  article_id:     {article_id if article_id else 'NON DEFINI'}")
        
        diagnostic['step1_criteria'] = {
            'operation_id': op_id,
            'task_id': task_id,
            'work_center_id': work_center_id,
            'article_id': article_id
        }
        
        # Validation
        if not work_center_id:
            diagnostic['step9_failure_cause'] = 'WORK_CENTER_ID_MANQUANT'
            logger.error(f"\n[ECHEC] work_center_id non defini - impossible de trouver les machines")
            return self._build_result(diagnostic)
        
        # === ÉTAPE 2: Machines du work_center_id ===
        logger.info(f"\n[ETAPE 2] MACHINES RATTACHEES AU WORK_CENTER '{work_center_id}'")
        
        candidate_machines = self.machines_by_workcenter.get(work_center_id, [])
        
        if not candidate_machines:
            # Chercher si le work_center existe avec un autre format
            logger.error(f"  AUCUNE MACHINE trouvee pour work_center_id='{work_center_id}'")
            logger.info(f"\n  Work_center_id disponibles dans l'index:")
            for wc in self.machines_by_workcenter.keys():
                logger.info(f"    - {wc}")
            
            diagnostic['step9_failure_cause'] = f'AUCUNE_MACHINE_DANS_WORK_CENTER_{work_center_id}'
            return self._build_result(diagnostic)
        
        for m in candidate_machines:
            machine_info = f"{m.get('name')} (id={m.get('id')})"
            logger.info(f"  -> {machine_info}")
            diagnostic['step2_machines_in_wc'].append({
                'id': m.get('id'),
                'name': m.get('name')
            })
        
        logger.info(f"  Total: {len(candidate_machines)} machine(s)")
        
        # === ÉTAPE 3: Recherche des règles applicables ===
        logger.info(f"\n[ETAPE 3] REGLES METIER APPLICABLES")
        logger.info(f"  Recherche pour: task_id={task_id}, work_center_id={work_center_id}")
        
        matching_context = {
            'task_id': task_id,
            'work_center_id': work_center_id,
            'article_id': article_id
        }
        
        applicable_rules = self.rules_engine._get_applicable_rules(matching_context)
        
        if not applicable_rules:
            logger.info(f"  Aucune regle trouvee pour ces criteres")
        else:
            for rule in applicable_rules:
                rule_info = {
                    'name': rule.name,
                    'type': rule.rule_type.value,
                    'task_id': rule.task_id,
                    'work_center_id': rule.work_center_id,
                    'machine_id': rule.machine_id
                }
                logger.info(f"  -> {rule.name}")
                logger.info(f"     Type: {rule.rule_type.value}")
                logger.info(f"     Cible machine: {rule.machine_id}")
                diagnostic['step3_rules_found'].append(rule_info)
        
        # === ÉTAPE 4-6: Appliquer les règles ===
        logger.info(f"\n[ETAPE 4-6] APPLICATION DES REGLES")
        
        machines_forbidden = []
        machines_preferred = []
        machines_allowed = []
        
        for machine in candidate_machines:
            machine_id = machine.get('id')
            machine_name = machine.get('name')
            
            is_allowed, reasons, score = self.rules_engine.evaluate_machine_for_operation(
                matching_context, machine_id, machine_name
            )
            
            machine_entry = {
                'id': machine_id,
                'name': machine_name,
                'reasons': reasons,
                'score': score
            }
            
            if not is_allowed:
                machines_forbidden.append(machine_entry)
                diagnostic['step4_machines_forbidden'].append(machine_entry)
                logger.info(f"  [FORBID] {machine_name}: {', '.join(reasons)}")
            elif score > 0:
                machines_preferred.append({**machine, 'preference_score': score, 'rule_reasons': reasons})
                diagnostic['step5_machines_preferred'].append(machine_entry)
                logger.info(f"  [PREFER] {machine_name}: score +{score}")
            else:
                machines_allowed.append({**machine, 'preference_score': 0, 'rule_reasons': reasons})
                diagnostic['step6_machines_allowed'].append(machine_entry)
                logger.info(f"  [OK] {machine_name}: autorisee")
        
        # === ÉTAPE 7: Liste finale des candidates ===
        logger.info(f"\n[ETAPE 7] MACHINES CANDIDATES FINALES")
        
        # Combiner préférées + autorisées, triées par score
        final_candidates = machines_preferred + machines_allowed
        final_candidates.sort(key=lambda m: m.get('preference_score', 0), reverse=True)
        
        diagnostic['step7_final_candidates'] = [
            {'id': m.get('id'), 'name': m.get('name'), 'score': m.get('preference_score', 0)}
            for m in final_candidates
        ]
        
        if not final_candidates:
            logger.error(f"  AUCUNE MACHINE CANDIDATE!")
            if machines_forbidden:
                logger.error(f"  Cause: Toutes les {len(machines_forbidden)} machine(s) sont interdites par FORBID")
                diagnostic['step9_failure_cause'] = 'TOUTES_MACHINES_INTERDITES_PAR_FORBID'
            else:
                diagnostic['step9_failure_cause'] = 'AUCUNE_MACHINE_CANDIDATE_BUG_MOTEUR'
            return self._build_result(diagnostic)
        
        for m in final_candidates:
            score_str = f" (PREFEREE +{m.get('preference_score')})" if m.get('preference_score', 0) > 0 else ""
            logger.info(f"  -> {m.get('name')}{score_str}")
        
        # === ÉTAPE 8: Sélection finale ===
        logger.info(f"\n[ETAPE 8] MACHINE SELECTIONNEE")
        
        selected = final_candidates[0]
        selected_id = selected.get('id')
        selected_name = selected.get('name')
        
        diagnostic['step8_selected_machine'] = {
            'id': selected_id,
            'name': selected_name,
            'score': selected.get('preference_score', 0)
        }
        diagnostic['is_assigned'] = True
        
        logger.info(f"  >>> MACHINE CHOISIE: {selected_name} (id={selected_id})")
        
        # === RÉSUMÉ ===
        logger.info(f"\n[RESUME]")
        logger.info(f"  Operation: {op_id}")
        logger.info(f"  task_id: {task_id} | work_center_id: {work_center_id}")
        logger.info(f"  Machines du WC: {[m['name'] for m in diagnostic['step2_machines_in_wc']]}")
        logger.info(f"  Regles: {[r['name'] for r in diagnostic['step3_rules_found']] or 'Aucune'}")
        logger.info(f"  Interdites: {[m['name'] for m in diagnostic['step4_machines_forbidden']] or 'Aucune'}")
        logger.info(f"  Preferees: {[m['name'] for m in diagnostic['step5_machines_preferred']] or 'Aucune'}")
        logger.info(f"  >>> Machine finale: {selected_name}")
        logger.info(f"{'='*80}\n")
        
        return self._build_result(diagnostic)
    
    def _build_result(self, diagnostic: Dict) -> Dict[str, Any]:
        """Construit le résultat à partir du diagnostic."""
        selected = diagnostic.get('step8_selected_machine')
        
        return {
            'machine_id': selected['id'] if selected else None,
            'machine_name': selected['name'] if selected else None,
            'is_assigned': diagnostic['is_assigned'],
            'reason': diagnostic.get('step9_failure_cause') or 'OK',
            'failure_cause': diagnostic.get('step9_failure_cause'),
            'diagnostic': diagnostic  # Inclure le diagnostic complet
        }
    
    def assign_machines_to_operations(
        self, 
        operations: List[Dict], 
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """
        Assigne les machines à toutes les opérations avec diagnostic complet.
        """
        logger.info("\n" + "#"*80)
        logger.info("DEBUT AUTO-ASSIGNATION DES MACHINES")
        logger.info(f"Total operations: {len(operations)}")
        logger.info(f"Total ordres: {len(orders)}")
        logger.info("#"*80)
        
        # Index des ordres
        orders_by_id = {o.get('id'): o for o in orders}
        
        # Reset logs
        self.rules_engine.clear_applied_rules_log()
        
        stats = {
            'assigned': 0,
            'unassigned': 0,
            'preferred': 0,
            'by_failure_cause': {}
        }
        
        assignment_details = []
        diagnostics_table = []  # Tableau de diagnostic pour le frontend
        
        for operation in operations:
            order_id = operation.get('order_id')
            order = orders_by_id.get(order_id)
            
            result = self.assign_machine_to_operation(operation, order)
            
            if result['is_assigned']:
                operation['machine_id'] = result['machine_id']
                stats['assigned'] += 1
                if result.get('diagnostic', {}).get('step5_machines_preferred'):
                    stats['preferred'] += 1
            else:
                stats['unassigned'] += 1
                cause = result.get('failure_cause', 'INCONNU')
                stats['by_failure_cause'][cause] = stats['by_failure_cause'].get(cause, 0) + 1
            
            # Ajouter au tableau de diagnostic
            diag = result.get('diagnostic', {}) or {}
            selected_machine = diag.get('step8_selected_machine')
            diagnostics_table.append({
                'operation_id': operation.get('id'),
                'task_id': operation.get('task_id'),
                'work_center_id': operation.get('work_center_id'),
                'machines_in_wc': [m['name'] for m in diag.get('step2_machines_in_wc', [])],
                'rules_applied': [f"{r['name']} ({r['type']})" for r in diag.get('step3_rules_found', [])],
                'machines_forbidden': [m['name'] for m in diag.get('step4_machines_forbidden', [])],
                'machines_preferred': [m['name'] for m in diag.get('step5_machines_preferred', [])],
                'final_candidates': [m['name'] for m in diag.get('step7_final_candidates', [])],
                'selected_machine': selected_machine.get('name') if selected_machine else None,
                'failure_cause': diag.get('step9_failure_cause'),
                'is_assigned': result['is_assigned']
            })
            
            assignment_details.append({
                'operation_id': operation.get('id'),
                'task_id': operation.get('task_id'),
                'work_center_id': operation.get('work_center_id'),
                **result
            })
        
        # Résumé final
        logger.info("\n" + "#"*80)
        logger.info("RESUME FINAL ASSIGNATION")
        logger.info("#"*80)
        logger.info(f"  Total operations:    {len(operations)}")
        logger.info(f"  Assignees:           {stats['assigned']}")
        logger.info(f"  Avec preference:     {stats['preferred']}")
        logger.info(f"  Non assignees:       {stats['unassigned']}")
        
        if stats['by_failure_cause']:
            logger.info(f"\n  CAUSES D'ECHEC:")
            for cause, count in stats['by_failure_cause'].items():
                logger.info(f"    - {cause}: {count} operation(s)")
        
        logger.info("#"*80 + "\n")
        
        return {
            'assigned_count': stats['assigned'],
            'unassigned_count': stats['unassigned'],
            'preferred_count': stats['preferred'],
            'total_operations': len(operations),
            'failure_causes': stats['by_failure_cause'],
            'assignment_details': assignment_details,
            'diagnostics_table': diagnostics_table,  # Nouveau: tableau pour le frontend
            'rules_diagnostics': self.rules_engine.get_diagnostics()
        }
