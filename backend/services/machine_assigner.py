import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MachineAssigner:
    """
    Service d'auto-assignation des machines aux opérations.
    
    Critères de matching (codes métier):
    - tache_id: type de tâche
    - centre_de_charge_id: centre de charge
    - article_id: article (depuis l'ordre de fabrication via order_id)
    - due_date: date/heure de besoin (pour la priorité)
    
    Clé de jointure: order_id
    
    Format datetime: ISO 8601 (YYYY-MM-DDTHH:MM:SS ou YYYY-MM-DD)
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
        
        IMPORTANT: article_id DOIT venir de l'ordre, pas de l'opération!
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
            # article_id DEPUIS L'ORDRE (pas l'opération!)
            enriched['article_id'] = order.get('article_id') or order.get('article')
            # due_date avec support datetime complet
            enriched['due_date'] = order.get('due_date') or order.get('date_besoin')
            enriched['priority'] = order.get('priority', 0)
            enriched['quantity'] = order.get('quantity')
            enriched['ordre_trouve'] = True
        else:
            enriched['article_id'] = None
            enriched['due_date'] = None
            enriched['priority'] = 0
            enriched['quantity'] = None
            enriched['ordre_trouve'] = False
        
        return enriched
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """
        Parse une date/heure en datetime.
        Supporte: YYYY-MM-DDTHH:MM:SS, YYYY-MM-DD HH:MM:SS, YYYY-MM-DD
        """
        if not date_str:
            return None
        
        try:
            # Format ISO complet avec T
            if 'T' in date_str:
                # Gérer les fuseaux horaires
                if '+' in date_str or 'Z' in date_str:
                    date_str = date_str.replace('Z', '+00:00')
                    return datetime.fromisoformat(date_str)
                return datetime.fromisoformat(date_str)
            # Format avec espace
            elif ' ' in date_str:
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            # Format date seule (minuit par défaut)
            else:
                return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception as e:
            logger.warning(f"Impossible de parser la date '{date_str}': {e}")
            return None
    
    def _calculate_urgency(self, due_date_str: str) -> tuple:
        """
        Calcule l'urgence basée sur la date/heure de besoin.
        
        Returns:
            (urgency_score, is_late, minutes_until_due)
        """
        if not due_date_str:
            return (0, False, float('inf'))
        
        due_dt = self._parse_datetime(due_date_str)
        if not due_dt:
            return (0, False, float('inf'))
        
        now = datetime.now()
        
        # Calculer la différence en minutes
        delta = due_dt - now
        minutes_until_due = delta.total_seconds() / 60
        
        is_late = minutes_until_due < 0
        
        if is_late:
            urgency = 10000 + abs(minutes_until_due)  # Plus c'est en retard, plus c'est urgent
        elif minutes_until_due <= 60:  # Moins d'une heure
            urgency = 5000
        elif minutes_until_due <= 240:  # Moins de 4 heures
            urgency = 2000
        elif minutes_until_due <= 1440:  # Moins de 24 heures
            urgency = 1000
        elif minutes_until_due <= 4320:  # Moins de 3 jours
            urgency = 500
        elif minutes_until_due <= 10080:  # Moins de 7 jours
            urgency = 200
        else:
            urgency = 0
        
        return (urgency, is_late, minutes_until_due)
    
    def assign_machine_to_operation(
        self, 
        operation: Dict[str, Any], 
        order: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Diagnostic complet pour l'assignation d'une machine.
        
        Utilise:
        - order_id comme clé de jointure
        - article_id DEPUIS L'ORDRE (pas l'opération!)
        - due_date avec heure pour l'urgence
        - tache_id, centre_de_charge_id depuis l'opération
        """
        # Enrichir l'opération avec les données de l'ordre
        enriched = self._enrich_operation(operation, order)
        
        op_id = enriched['id']
        order_id = enriched['order_id']
        tache_id = enriched['tache_id']
        centre_de_charge_id = enriched['centre_de_charge_id']
        
        # IMPORTANT: article_id vient de L'ORDRE, pas de l'opération!
        article_id = enriched['article_id']
        due_date = enriched['due_date']
        
        # Calculer l'urgence
        urgency, is_late, minutes_until_due = self._calculate_urgency(due_date)
        
        # Diagnostic détaillé
        diagnostic = {
            'operation_id': op_id,
            'order_id': order_id,
            'article_id': article_id,
            'due_date': due_date,
            'tache_id': tache_id,
            'centre_de_charge_id': centre_de_charge_id,
            'urgency': urgency,
            'is_late': is_late,
            'minutes_until_due': minutes_until_due,
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
        logger.info(f"  article_id:          {article_id or 'NON TROUVE'} (depuis l'ordre)")
        logger.info(f"  due_date:            {due_date or 'NON TROUVE'}")
        logger.info(f"  tache_id:            {tache_id or 'NON DEFINI'}")
        logger.info(f"  centre_de_charge_id: {centre_de_charge_id or 'NON DEFINI'}")
        
        urgency_label = ""
        if is_late:
            urgency_label = " (EN RETARD)"
        elif urgency >= 5000:
            urgency_label = " (TRES URGENT - <1h)"
        elif urgency >= 2000:
            urgency_label = " (URGENT - <4h)"
        elif urgency >= 1000:
            urgency_label = " (PRIORITAIRE - <24h)"
        logger.info(f"  urgence:             {urgency}{urgency_label}")
        
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
        # IMPORTANT: Passer article_id depuis l'ordre!
        logger.info(f"\n[ETAPE 3] REGLES METIER")
        logger.info(f"  Critères de matching:")
        logger.info(f"    - tache_id:            {tache_id}")
        logger.info(f"    - centre_de_charge_id: {centre_de_charge_id}")
        logger.info(f"    - article_id:          {article_id} (DEPUIS L'ORDRE)")
        
        allowed_machines, forbidden_machines, rules_diag = self.rules_engine.get_allowed_machines(
            tache_id or '',
            centre_de_charge_id,
            candidate_machines,
            article_id  # article_id DEPUIS L'ORDRE!
        )
        
        diagnostic['regles_applicables'] = [
            f"{r['name']} ({r['type']})" for r in rules_diag.get('applicable_rules', [])
        ]
        
        if diagnostic['regles_applicables']:
            logger.info(f"\n  Règles qui matchent:")
            for r in rules_diag.get('applicable_rules', []):
                logger.info(f"    [{r['type']}] {r['name']} -> machine={r['machine_id']}")
                logger.info(f"         critères: {r.get('criteria', '-')}")
        else:
            logger.info(f"  Aucune règle applicable")
        
        # ÉTAPE 4-6: Machines après règles
        if forbidden_machines:
            logger.info(f"\n[ETAPE 4] MACHINES INTERDITES (FORBID)")
            for m in forbidden_machines:
                diagnostic['machines_interdites'].append(m.get('id'))
                reasons = m.get('rule_reasons', [])
                logger.info(f"  ✗ {m.get('id')}: {', '.join(reasons)}")
        
        if allowed_machines:
            preferred = [m for m in allowed_machines if m.get('preference_score', 0) > 0]
            if preferred:
                logger.info(f"\n[ETAPE 5] MACHINES PREFEREES (PREFER)")
                for m in preferred:
                    diagnostic['machines_preferees'].append(m.get('id'))
                    logger.info(f"  ★ {m.get('id')} (+{m.get('preference_score')})")
        
        # ÉTAPE 7: Candidates finales
        logger.info(f"\n[ETAPE 6] CANDIDATES FINALES")
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
        
        # ÉTAPE 8: Sélection (la première est la meilleure - triée par score)
        selected = allowed_machines[0]
        selected_id = selected.get('id')
        
        diagnostic['machine_choisie'] = selected_id
        diagnostic['is_assigned'] = True
        
        logger.info(f"\n[ETAPE 7] MACHINE CHOISIE: {selected_id}")
        
        # Résumé
        logger.info(f"\n[RESUME]")
        logger.info(f"  Opération: {op_id} (OF: {order_id})")
        logger.info(f"  Article: {article_id} | Due: {due_date}")
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
        
        Tri par:
        1. due_date (plus urgent en premier, avec heure)
        2. priority
        3. order_id (pour stabilité)
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
        
        stats = {
            'assigned': 0, 
            'unassigned': 0, 
            'preferred': 0, 
            'by_failure_cause': {}, 
            'late': 0,
            'urgent': 0
        }
        diagnostics_table = []
        
        # Enrichir et trier les opérations
        enriched_operations = []
        for operation in operations:
            order_id = operation.get('order_id')
            order = orders_by_id.get(order_id)
            enriched = self._enrich_operation(operation, order)
            
            # Calculer urgence pour le tri
            urgency, is_late, minutes_until_due = self._calculate_urgency(enriched.get('due_date'))
            enriched['_urgency'] = urgency
            enriched['_is_late'] = is_late
            enriched['_minutes_until_due'] = minutes_until_due
            enriched['_priority'] = enriched.get('priority', 0)
            enriched['_original'] = operation
            enriched['_order'] = order
            enriched_operations.append(enriched)
        
        # Trier par urgence (décroissant), puis priorité (décroissant), puis order_id
        enriched_operations.sort(
            key=lambda x: (
                -x['_urgency'],  # Plus urgent en premier
                -x['_priority'],  # Plus prioritaire en premier
                x.get('due_date') or '9999-99-99',  # Date de besoin
                x.get('order_id') or ''
            )
        )
        
        logger.info(f"\nOpérations triées par urgence (due_date avec heure):")
        for i, op in enumerate(enriched_operations[:5]):
            urgency_label = "EN RETARD" if op['_is_late'] else f"urgence={op['_urgency']}"
            logger.info(f"  {i+1}. {op['id']} - due={op.get('due_date')} - article={op.get('article_id')} ({urgency_label})")
        
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
                if diag.get('is_late'):
                    stats['late'] += 1
                elif diag.get('urgency', 0) >= 1000:
                    stats['urgent'] += 1
            else:
                stats['unassigned'] += 1
                cause = result.get('failure_cause', 'INCONNU')
                stats['by_failure_cause'][cause] = stats['by_failure_cause'].get(cause, 0) + 1
            
            diag = result.get('diagnostic', {}) or {}
            diagnostics_table.append({
                'operation_id': operation.get('id'),
                'order_id': diag.get('order_id'),
                'article_id': diag.get('article_id'),
                'due_date': diag.get('due_date'),
                'tache_id': diag.get('tache_id'),
                'centre_de_charge_id': diag.get('centre_de_charge_id'),
                'urgency': diag.get('urgency', 0),
                'is_late': diag.get('is_late', False),
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
        logger.info(f"  En retard:  {stats['late']}")
        logger.info(f"  Urgentes:   {stats['urgent']}")
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
            'late_count': stats['late'],
            'urgent_count': stats['urgent'],
            'total_operations': len(operations),
            'failure_causes': stats['by_failure_cause'],
            'diagnostics_table': diagnostics_table,
            'rules_diagnostics': self.rules_engine.get_diagnostics()
        }
