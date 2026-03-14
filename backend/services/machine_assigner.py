import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MachineAssigner:
    """
    Service d'auto-assignation des machines aux opérations.
    
    Critères de matching (codes métier):
    - tache_id: type de tâche
    - centre_de_charge_id: centre de charge
    - article_id: article (depuis l'ordre de fabrication via order_id)
    - date_besoin: date de besoin (pour la priorité)
    
    Clé de jointure: order_id
    """
    
    def __init__(self, machines: List[Dict], rules_engine):
        self.machines = machines
        self.rules_engine = rules_engine
        
        # Index machines par centre_de_charge_id
        self.machines_by_centre: Dict[str, List[Dict]] = {}
        for machine in machines:
            centre_id = machine.get('centre_de_charge_id')
            if centre_id:
                if centre_id not in self.machines_by_centre:
                    self.machines_by_centre[centre_id] = []
                self.machines_by_centre[centre_id].append(machine)
        
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
    
    def _enrich_operation(self, operation: Dict, order: Optional[Dict]) -> Dict:
        """
        Enrichit une opération avec les données de l'ordre de fabrication.
        Jointure sur order_id.
        """
        enriched = {
            # Données de l'opération
            'id': operation.get('id'),
            'order_id': operation.get('order_id'),
            'operation_id': operation.get('operation_id'),
            'tache_id': operation.get('tache_id') or operation.get('task_id'),
            'centre_de_charge_id': operation.get('centre_de_charge_id') or operation.get('work_center_id'),
            'production_time_minutes': operation.get('production_time_minutes', 0),
            'setup_time_minutes': operation.get('setup_time_minutes', 0),
        }
        
        # Enrichir avec les données de l'ordre (jointure sur order_id)
        if order:
            enriched['article_id'] = order.get('article_id') or order.get('article')
            enriched['date_besoin'] = order.get('due_date') or order.get('date_besoin')
            enriched['priority'] = order.get('priority', 0)
            enriched['quantity'] = order.get('quantity')
            enriched['ordre_trouve'] = True
        else:
            enriched['article_id'] = None
            enriched['date_besoin'] = None
            enriched['priority'] = 0
            enriched['quantity'] = None
            enriched['ordre_trouve'] = False
        
        return enriched
    
    def _calculate_urgency(self, date_besoin: str) -> int:
        """
        Calcule l'urgence basée sur la date de besoin.
        Plus la date est proche, plus l'urgence est élevée.
        """
        if not date_besoin:
            return 0
        
        try:
            due = datetime.strptime(date_besoin[:10], '%Y-%m-%d')
            today = datetime.now()
            days_until_due = (due - today).days
            
            if days_until_due < 0:
                return 1000  # En retard
            elif days_until_due <= 3:
                return 500   # Urgent
            elif days_until_due <= 7:
                return 200   # Prioritaire
            else:
                return 0
        except:
            return 0
    
    def assign_machine_to_operation(
        self, 
        operation: Dict[str, Any], 
        order: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Diagnostic complet pour l'assignation d'une machine.
        
        Utilise:
        - order_id comme clé de jointure
        - article_id, date_besoin depuis l'ordre
        - tache_id, centre_de_charge_id depuis l'opération
        """
        # Enrichir l'opération avec les données de l'ordre
        enriched = self._enrich_operation(operation, order)
        
        op_id = enriched['id']
        order_id = enriched['order_id']
        tache_id = enriched['tache_id']
        centre_de_charge_id = enriched['centre_de_charge_id']
        article_id = enriched['article_id']
        date_besoin = enriched['date_besoin']
        
        # Calculer l'urgence
        urgency = self._calculate_urgency(date_besoin)
        
        # Diagnostic détaillé
        diagnostic = {
            'operation_id': op_id,
            'order_id': order_id,
            'article_id': article_id,
            'date_besoin': date_besoin,
            'tache_id': tache_id,
            'centre_de_charge_id': centre_de_charge_id,
            'urgency': urgency,
            'ordre_trouve': enriched['ordre_trouve'],
            'machines_du_centre': [],
            'regles_applicables': [],
            'machines_interdites': [],
            'machines_preferees': [],
            'candidates_finales': [],
            'machine_choisie': None,
            'cause_echec': None,
            'is_assigned': False
        }
        
        logger.info(f"\n{'='*80}")
        logger.info(f"ASSIGNATION - Opération: {op_id}")
        logger.info(f"{'='*80}")
        
        # ÉTAPE 1: Afficher les critères enrichis
        logger.info(f"\n[ETAPE 1] CRITERES (jointure order_id)")
        logger.info(f"  operation_id:        {op_id}")
        logger.info(f"  order_id:            {order_id}")
        logger.info(f"  article_id:          {article_id or 'NON TROUVE'}")
        logger.info(f"  date_besoin:         {date_besoin or 'NON TROUVE'}")
        logger.info(f"  tache_id:            {tache_id or 'NON DEFINI'}")
        logger.info(f"  centre_de_charge_id: {centre_de_charge_id or 'NON DEFINI'}")
        logger.info(f"  urgence:             {urgency}" + (" (EN RETARD)" if urgency >= 1000 else " (URGENT)" if urgency >= 500 else ""))
        
        if not enriched['ordre_trouve']:
            logger.warning(f"  [ATTENTION] Ordre de fabrication {order_id} non trouvé!")
        
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
        
        # ÉTAPE 3: Règles métier applicables
        logger.info(f"\n[ETAPE 3] REGLES METIER")
        logger.info(f"  Critères: tache={tache_id}, centre={centre_de_charge_id}, article={article_id}")
        
        allowed_machines, forbidden_machines, rules_diag = self.rules_engine.get_allowed_machines(
            tache_id or '',
            centre_de_charge_id,
            candidate_machines,
            article_id  # Utiliser article_id pour les règles
        )
        
        diagnostic['regles_applicables'] = [
            f"{r['name']} ({r['type']})" for r in rules_diag.get('applicable_rules', [])
        ]
        
        if diagnostic['regles_applicables']:
            for r in diagnostic['regles_applicables']:
                logger.info(f"  -> {r}")
        else:
            logger.info(f"  Aucune règle applicable")
        
        # ÉTAPE 4-6: Machines après règles
        for m in forbidden_machines:
            diagnostic['machines_interdites'].append(m.get('id'))
            logger.info(f"  [FORBID] {m.get('id')}")
        
        for m in allowed_machines:
            if m.get('preference_score', 0) > 0:
                diagnostic['machines_preferees'].append(m.get('id'))
                logger.info(f"  [PREFER] {m.get('id')} (+{m.get('preference_score')})")
        
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
        logger.info(f"  Opération: {op_id} (OF: {order_id})")
        logger.info(f"  Article: {article_id} | Date besoin: {date_besoin}")
        logger.info(f"  Tâche: {tache_id} | Centre: {centre_de_charge_id}")
        logger.info(f"  Machines centre: {diagnostic['machines_du_centre']}")
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
        """
        Assigne les machines à toutes les opérations.
        Utilise order_id comme clé de jointure avec les ordres.
        """
        logger.info("\n" + "#"*80)
        logger.info("AUTO-ASSIGNATION DES MACHINES")
        logger.info(f"Clé de jointure: order_id")
        logger.info(f"Total opérations: {len(operations)}")
        logger.info(f"Total ordres: {len(orders)}")
        logger.info("#"*80)
        
        # Index des ordres par order_id (clé de jointure)
        orders_by_id = {o.get('id'): o for o in orders}
        
        self.rules_engine.clear_applied_rules_log()
        
        stats = {'assigned': 0, 'unassigned': 0, 'preferred': 0, 'by_failure_cause': {}, 'en_retard': 0}
        diagnostics_table = []
        
        # Enrichir et trier les opérations par urgence (date_besoin)
        enriched_operations = []
        for operation in operations:
            order_id = operation.get('order_id')
            order = orders_by_id.get(order_id)
            enriched = self._enrich_operation(operation, order)
            enriched['_original'] = operation
            enriched['_order'] = order
            enriched_operations.append(enriched)
        
        # Trier par date_besoin (plus urgent en premier)
        enriched_operations.sort(key=lambda x: (x.get('date_besoin') or '9999-99-99', x.get('order_id') or ''))
        
        logger.info(f"\nOpérations triées par date_besoin:")
        for i, op in enumerate(enriched_operations[:5]):
            logger.info(f"  {i+1}. {op['id']} - date_besoin: {op.get('date_besoin')} - article: {op.get('article_id')}")
        
        for enriched in enriched_operations:
            operation = enriched['_original']
            order = enriched['_order']
            
            result = self.assign_machine_to_operation(operation, order)
            
            if result['is_assigned']:
                operation['machine_id'] = result['machine_id']
                stats['assigned'] += 1
                diag = result.get('diagnostic', {})
                if diag.get('machines_preferees'):
                    stats['preferred'] += 1
                if diag.get('urgency', 0) >= 1000:
                    stats['en_retard'] += 1
            else:
                stats['unassigned'] += 1
                cause = result.get('failure_cause', 'INCONNU')
                stats['by_failure_cause'][cause] = stats['by_failure_cause'].get(cause, 0) + 1
            
            diag = result.get('diagnostic', {}) or {}
            diagnostics_table.append({
                'operation_id': operation.get('id'),
                'order_id': diag.get('order_id'),
                'article_id': diag.get('article_id'),
                'date_besoin': diag.get('date_besoin'),
                'tache_id': diag.get('tache_id'),
                'centre_de_charge_id': diag.get('centre_de_charge_id'),
                'urgency': diag.get('urgency', 0),
                'ordre_trouve': diag.get('ordre_trouve', False),
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
        logger.info(f"  En retard:  {stats['en_retard']}")
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
            'en_retard_count': stats['en_retard'],
            'total_operations': len(operations),
            'failure_causes': stats['by_failure_cause'],
            'diagnostics_table': diagnostics_table,
            'rules_diagnostics': self.rules_engine.get_diagnostics()
        }
