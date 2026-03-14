import logging
from typing import List, Dict, Any, Tuple, Optional
from models.business_rule import BusinessRule, RuleType

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Moteur de règles métier simplifié pour le POC.
    Gère uniquement les règles d'affectation machine : ALLOW, FORBID, PREFER.
    """
    
    def __init__(self, rules_data: List[Dict]):
        self.rules: List[BusinessRule] = []
        self.invalid_rules: List[Dict] = []
        self.applied_rules_log: List[Dict] = []  # Pour le diagnostic
        
        logger.info("\n" + "="*80)
        logger.info("CHARGEMENT DES REGLES METIER (POC)")
        logger.info("="*80)
        
        for rule_data in rules_data:
            try:
                rule = BusinessRule(**rule_data)
                
                # Validation : au moins task_id ou work_center_id doit être défini
                if not rule.task_id and not rule.work_center_id:
                    logger.warning(f"  Regle '{rule.name}' ignoree: article_id seul non autorise")
                    self.invalid_rules.append({
                        'name': rule.name,
                        'reason': 'Doit avoir task_id et/ou work_center_id (article_id seul non autorise)'
                    })
                    continue
                
                self.rules.append(rule)
                logger.info(f"  [OK] Regle chargee: {rule.name} ({rule.rule_type.value} -> machine {rule.machine_id})")
                
            except Exception as e:
                logger.warning(f"  [ERREUR] Regle invalide: {e}")
                self.invalid_rules.append({
                    'name': rule_data.get('name', 'Unknown'),
                    'reason': str(e)
                })
        
        logger.info(f"\nResume: {len(self.rules)} regle(s) active(s), {len(self.invalid_rules)} ignoree(s)")
        self._log_rules_summary()
        logger.info("="*80 + "\n")
    
    def _log_rules_summary(self):
        """Affiche un résumé des règles chargées."""
        if not self.rules:
            logger.info("  Aucune regle active.")
            return
        
        logger.info("\nDetail des regles:")
        for rule in self.rules:
            status = "ACTIVE" if rule.active else "INACTIVE"
            logger.info(f"  [{status}] {rule.name}: {rule.get_criteria_display()} -> {rule.rule_type.value} machine={rule.machine_id}")
    
    def evaluate_machine_for_operation(
        self, 
        operation: Dict, 
        machine_id: str,
        machine_name: Optional[str] = None
    ) -> Tuple[bool, List[str], int]:
        """
        Évalue si une machine peut exécuter une opération selon les règles.
        
        Returns:
            (allowed: bool, reasons: List[str], preference_score: int)
            - allowed: False si une règle FORBID s'applique
            - reasons: Liste des règles appliquées
            - preference_score: Score de préférence (plus élevé = meilleur)
        """
        applicable_rules = self._get_applicable_rules(operation)
        
        if not applicable_rules:
            return True, ["Aucune regle specifique"], 0
        
        allowed = True
        reasons = []
        preference_score = 0
        
        for rule in applicable_rules:
            # La règle cible cette machine spécifique
            if rule.machine_id == machine_id:
                if rule.rule_type == RuleType.FORBID:
                    allowed = False
                    reason = f"INTERDIT par '{rule.name}' ({rule.get_criteria_display()})"
                    reasons.append(reason)
                    self._log_rule_application(operation, rule, machine_id, machine_name, "BLOQUE")
                    
                elif rule.rule_type == RuleType.ALLOW:
                    reason = f"AUTORISE par '{rule.name}'"
                    reasons.append(reason)
                    self._log_rule_application(operation, rule, machine_id, machine_name, "AUTORISE")
                    
                elif rule.rule_type == RuleType.PREFER:
                    preference_score += 100  # Bonus de préférence
                    reason = f"PREFEREE par '{rule.name}' (+100)"
                    reasons.append(reason)
                    self._log_rule_application(operation, rule, machine_id, machine_name, "PREFEREE")
        
        if not reasons:
            reasons.append("Aucune regle applicable a cette machine")
        
        return allowed, reasons, preference_score
    
    def _get_applicable_rules(self, operation: Dict) -> List[BusinessRule]:
        """Retourne toutes les règles qui correspondent à l'opération."""
        return [rule for rule in self.rules if rule.matches_operation(operation)]
    
    def _log_rule_application(
        self, 
        operation: Dict, 
        rule: BusinessRule, 
        machine_id: str,
        machine_name: Optional[str],
        result: str
    ):
        """Enregistre l'application d'une règle pour le diagnostic."""
        log_entry = {
            'operation_id': operation.get('id'),
            'task_id': operation.get('task_id'),
            'work_center_id': operation.get('work_center_id'),
            'article_id': operation.get('article_id'),
            'rule_name': rule.name,
            'rule_type': rule.rule_type.value,
            'machine_id': machine_id,
            'machine_name': machine_name,
            'result': result
        }
        self.applied_rules_log.append(log_entry)
        
        logger.info(f"    -> Regle '{rule.name}' ({rule.rule_type.value}): {result} pour machine {machine_name or machine_id}")
    
    def get_allowed_machines(
        self, 
        operation: Dict, 
        available_machines: List[Dict]
    ) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Filtre et ordonne les machines selon les règles.
        
        Returns:
            (allowed_machines, forbidden_machines, diagnostics)
        """
        allowed = []
        forbidden = []
        diagnostics = {
            'operation_id': operation.get('id'),
            'task_id': operation.get('task_id'),
            'work_center_id': operation.get('work_center_id'),
            'rules_evaluated': [],
            'allowed_machines': [],
            'forbidden_machines': []
        }
        
        applicable_rules = self._get_applicable_rules(operation)
        diagnostics['applicable_rules'] = [
            {'name': r.name, 'type': r.rule_type.value, 'machine_id': r.machine_id}
            for r in applicable_rules
        ]
        
        for machine in available_machines:
            machine_id = machine.get('id')
            machine_name = machine.get('name', machine_id)
            
            is_allowed, reasons, score = self.evaluate_machine_for_operation(
                operation, machine_id, machine_name
            )
            
            machine_info = {
                **machine,
                'preference_score': score,
                'rule_reasons': reasons
            }
            
            if is_allowed:
                allowed.append(machine_info)
                diagnostics['allowed_machines'].append({
                    'id': machine_id,
                    'name': machine_name,
                    'score': score,
                    'reasons': reasons
                })
            else:
                forbidden.append(machine_info)
                diagnostics['forbidden_machines'].append({
                    'id': machine_id,
                    'name': machine_name,
                    'reasons': reasons
                })
        
        # Trier par score de préférence (décroissant)
        allowed.sort(key=lambda m: m.get('preference_score', 0), reverse=True)
        
        return allowed, forbidden, diagnostics
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Retourne les statistiques de diagnostic."""
        rules_by_type = {
            'ALLOW': len([r for r in self.rules if r.rule_type == RuleType.ALLOW]),
            'FORBID': len([r for r in self.rules if r.rule_type == RuleType.FORBID]),
            'PREFER': len([r for r in self.rules if r.rule_type == RuleType.PREFER])
        }
        
        return {
            'total_rules': len(self.rules),
            'active_rules': len([r for r in self.rules if r.active]),
            'invalid_rules': self.invalid_rules,
            'rules_by_type': rules_by_type,
            'applied_rules_log': self.applied_rules_log,
            'rules_detail': [
                {
                    'name': r.name,
                    'type': r.rule_type.value,
                    'task_id': r.task_id,
                    'work_center_id': r.work_center_id,
                    'article_id': r.article_id,
                    'machine_id': r.machine_id,
                    'active': r.active
                }
                for r in self.rules
            ]
        }
    
    def clear_applied_rules_log(self):
        """Réinitialise le log des règles appliquées."""
        self.applied_rules_log = []
