import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class MachineAssigner:
    """
    Service d'auto-assignation des machines aux opérations.
    
    LOGIQUE DE MATCHING (codes métier, pas UUID):
    1. Extraire tache_id et centre_de_charge_id de l'opération
    2. Trouver les machines du centre_de_charge_id
    3. Appliquer les règles métier (FORBID, ALLOW, PREFER)
    4. Sélectionner la meilleure machine
    """
    
    def __init__(self, machines: List[Dict], rules_engine):
        self.machines = machines
        self.rules_engine = rules_engine
        
        # Index machines par centre_de_charge_id (code métier)
        self.machines_by_centre: Dict[str, List[Dict]] = {}
        for machine in machines:
            centre_id = machine.get('centre_de_charge_id')
            if centre_id:
                if centre_id not in self.machines_by_centre:
                    self.machines_by_centre[centre_id] = []
                self.machines_by_centre[centre_id].append(machine)
        
        # Log l'index
        logger.info("\n" + "="*80)
        logger.info("INDEX DES MACHINES PAR CENTRE DE CHARGE")
        logger.info("="*80)
        if self.machines_by_centre:
            for centre_id, centre_machines in self.machines_by_centre.items():
                machine_ids = [m.get('id') for m in centre_machines]
                logger.info(f"  {centre_id}: {machine_ids}")
        else:
            logger.warning("  AUCUNE MACHINE INDEXEE!")
        logger.info("="*80 + "\n")
    
    def assign_machine_to_operation(
        self, 
        operation: Dict[str, Any], 
        order: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Diagnostic complet pour l'assignation d'une machine.
        """
        op_id = operation.get('id')
        tache_id = operation.get('tache_id')
        centre_de_charge_id = operation.get('centre_de_charge_id')
        article_id = order.get('article_id') if order else operation.get('article_id')
        
        # Diagnostic détaillé
        diagnostic = {
            'operation_id': op_id,
            'tache_id': tache_id,
            'centre_de_charge_id': centre_de_charge_id,
            'article_id': article_id,
            'machines_du_centre': [],
            'regles_applicables': [],
            'machines_interdites': [],
            'machines_preferees': [],
            'machines_autorisees': [],
            'candidates_finales': [],
            'machine_choisie': None,
            'cause_echec': None,
            'is_assigned': False
        }
        
        logger.info(f"\n{'='*80}")
        logger.info(f"ASSIGNATION - Opération: {op_id}")
        logger.info(f"{'='*80}")
        
        # ÉTAPE 1: Critères
        logger.info(f"\n[ETAPE 1] CRITERES")
        logger.info(f"  operation_id:        {op_id}")
        logger.info(f"  tache_id:            {tache_id or 'NON DEFINI'}")
        logger.info(f"  centre_de_charge_id: {centre_de_charge_id or 'NON DEFINI'}")
        logger.info(f"  article_id:          {article_id or 'NON DEFINI'}")
        
        if not centre_de_charge_id:
            diagnostic['cause_echec'] = 'CENTRE_DE_CHARGE_ID_MANQUANT'
            logger.error(f"\n[ECHEC] centre_de_charge_id non défini")
            return self._build_result(diagnostic)
        
        # ÉTAPE 2: Machines du centre de charge
        logger.info(f"\n[ETAPE 2] MACHINES DU CENTRE '{centre_de_charge_id}'")
        
        candidate_machines = self.machines_by_centre.get(centre_de_charge_id, [])
        
        if not candidate_machines:
            logger.error(f"  AUCUNE MACHINE pour centre_de_charge_id='{centre_de_charge_id}'")
            logger.info(f"\n  Centres de charge disponibles:")
            for centre in self.machines_by_centre.keys():
                logger.info(f"    - {centre}")
            
            diagnostic['cause_echec'] = f'AUCUNE_MACHINE_DANS_CENTRE_{centre_de_charge_id}'
            return self._build_result(diagnostic)
        
        for m in candidate_machines:
            logger.info(f"  -> {m.get('id')}")
            diagnostic['machines_du_centre'].append(m.get('id'))
        
        # ÉTAPE 3: Règles applicables
        logger.info(f"\n[ETAPE 3] REGLES APPLICABLES")
        
        allowed_machines, forbidden_machines, rules_diag = self.rules_engine.get_allowed_machines(
            tache_id or '',
            centre_de_charge_id,
            candidate_machines,
            article_id
        )
        
        diagnostic['regles_applicables'] = [
            f"{r['name']} ({r['type']})" for r in rules_diag.get('applicable_rules', [])
        ]
        
        # ÉTAPE 4-6: Machines après règles
        for m in forbidden_machines:
            diagnostic['machines_interdites'].append(m.get('id'))
            logger.info(f"  [FORBID] {m.get('id')}")
        
        for m in allowed_machines:
            if m.get('preference_score', 0) > 0:
                diagnostic['machines_preferees'].append(m.get('id'))
                logger.info(f"  [PREFER] {m.get('id')} (+{m.get('preference_score')})")
            else:
                diagnostic['machines_autorisees'].append(m.get('id'))
                logger.info(f"  [OK] {m.get('id')}")
        
        # ÉTAPE 7: Candidates finales
        logger.info(f"\n[ETAPE 7] CANDIDATES FINALES")
        
        diagnostic['candidates_finales'] = [m.get('id') for m in allowed_machines]
        
        if not allowed_machines:
            if forbidden_machines:
                diagnostic['cause_echec'] = 'TOUTES_MACHINES_INTERDITES_PAR_FORBID'
                logger.error(f"  AUCUNE - Toutes interdites par FORBID")
            else:
                diagnostic['cause_echec'] = 'AUCUNE_MACHINE_CANDIDATE'
                logger.error(f"  AUCUNE CANDIDATE")
            return self._build_result(diagnostic)
        
        for m in allowed_machines:
            score = m.get('preference_score', 0)
            logger.info(f"  -> {m.get('id')}" + (f" (PREFEREE +{score})" if score > 0 else ""))
        
        # ÉTAPE 8: Sélection
        selected = allowed_machines[0]
        selected_id = selected.get('id')
        
        diagnostic['machine_choisie'] = selected_id
        diagnostic['is_assigned'] = True
        
        logger.info(f"\n[ETAPE 8] MACHINE CHOISIE: {selected_id}")
        
        # Résumé
        logger.info(f"\n[RESUME]")
        logger.info(f"  Opération: {op_id}")
        logger.info(f"  tache_id: {tache_id} | centre: {centre_de_charge_id}")
        logger.info(f"  Machines du centre: {diagnostic['machines_du_centre']}")
        logger.info(f"  Règles: {diagnostic['regles_applicables'] or 'Aucune'}")
        logger.info(f"  Interdites: {diagnostic['machines_interdites'] or 'Aucune'}")
        logger.info(f"  >>> Machine finale: {selected_id}")
        logger.info(f"{'='*80}\n")
        
        return self._build_result(diagnostic)
    
    def _build_result(self, diagnostic: Dict) -> Dict[str, Any]:
        """Construit le résultat."""
        return {
            'machine_id': diagnostic.get('machine_choisie'),
            'is_assigned': diagnostic['is_assigned'],
            'reason': diagnostic.get('cause_echec') or 'OK',
            'failure_cause': diagnostic.get('cause_echec'),
            'diagnostic': diagnostic
        }
    
    def assign_machines_to_operations(
        self, 
        operations: List[Dict], 
        orders: List[Dict]
    ) -> Dict[str, Any]:
        """Assigne les machines à toutes les opérations."""
        logger.info("\n" + "#"*80)
        logger.info("AUTO-ASSIGNATION DES MACHINES")
        logger.info(f"Total opérations: {len(operations)}")
        logger.info("#"*80)
        
        orders_by_id = {o.get('id'): o for o in orders}
        self.rules_engine.clear_applied_rules_log()
        
        stats = {'assigned': 0, 'unassigned': 0, 'preferred': 0, 'by_failure_cause': {}}
        diagnostics_table = []
        
        for operation in operations:
            order_id = operation.get('order_id')
            order = orders_by_id.get(order_id)
            
            result = self.assign_machine_to_operation(operation, order)
            
            if result['is_assigned']:
                operation['machine_id'] = result['machine_id']
                stats['assigned'] += 1
                diag = result.get('diagnostic', {})
                if diag.get('machines_preferees'):
                    stats['preferred'] += 1
            else:
                stats['unassigned'] += 1
                cause = result.get('failure_cause', 'INCONNU')
                stats['by_failure_cause'][cause] = stats['by_failure_cause'].get(cause, 0) + 1
            
            diag = result.get('diagnostic', {}) or {}
            diagnostics_table.append({
                'operation_id': operation.get('id'),
                'tache_id': operation.get('tache_id'),
                'centre_de_charge_id': operation.get('centre_de_charge_id'),
                'machines_du_centre': diag.get('machines_du_centre', []),
                'regles_applicables': diag.get('regles_applicables', []),
                'machines_interdites': diag.get('machines_interdites', []),
                'machines_preferees': diag.get('machines_preferees', []),
                'candidates_finales': diag.get('candidates_finales', []),
                'machine_choisie': diag.get('machine_choisie'),
                'cause_echec': diag.get('cause_echec'),
                'is_assigned': result['is_assigned']
            })
        
        logger.info("\n" + "#"*80)
        logger.info("RESUME ASSIGNATION")
        logger.info("#"*80)
        logger.info(f"  Total:      {len(operations)}")
        logger.info(f"  Assignées:  {stats['assigned']}")
        logger.info(f"  Préférées:  {stats['preferred']}")
        logger.info(f"  Échecs:     {stats['unassigned']}")
        if stats['by_failure_cause']:
            logger.info(f"\n  Causes d'échec:")
            for cause, count in stats['by_failure_cause'].items():
                logger.info(f"    - {cause}: {count}")
        logger.info("#"*80 + "\n")
        
        return {
            'assigned_count': stats['assigned'],
            'unassigned_count': stats['unassigned'],
            'preferred_count': stats['preferred'],
            'total_operations': len(operations),
            'failure_causes': stats['by_failure_cause'],
            'diagnostics_table': diagnostics_table,
            'rules_diagnostics': self.rules_engine.get_diagnostics()
        }
