import logging
from typing import List, Dict, Any, Tuple
from models.business_rule import BusinessRule

logger = logging.getLogger(__name__)

class RulesEngine:
    """
    Moteur de règles métier basé sur task_id et work_center_id.
    """
    def __init__(self, rules_data: List[Dict]):
        # Convertir les dicts en objets BusinessRule
        self.rules = []
        for rule_data in rules_data:
            try:
                rule = BusinessRule(**rule_data)
                self.rules.append(rule)
            except Exception as e:
                logger.warning(f"⚠️  Règle invalide ignorée: {e}")
    
    def get_applicable_rules(self, operation: Dict) -> List[BusinessRule]:
        """
        Retourne toutes les règles applicables à une opération.
        """
        applicable = []
        for rule in self.rules:
            if rule.matches_operation(operation):
                applicable.append(rule)
        return applicable
    
    def evaluate_machine_for_operation(self, operation: Dict, machine_id: str) -> Tuple[bool, str, int]:
        """
        Évalue si une machine peut exécuter une opération selon les règles.
        
        Returns:
            (allowed: bool, reason: str, penalty: int)
        """
        task_id = operation.get('task_id')
        work_center_id = operation.get('work_center_id')
        
        # Récupérer les règles applicables
        applicable_rules = self.get_applicable_rules(operation)
        
        if not applicable_rules:
            return True, "Aucune règle spécifique", 0
        
        total_penalty = 0
        reasons = []
        
        for rule in applicable_rules:
            allowed, reason, penalty = rule.evaluate_for_machine(machine_id)
            
            if not allowed:
                # Règle dure bloquante
                logger.info(f"  ✗ {reason}")
                return False, reason, 0
            
            if penalty != 0:
                total_penalty += penalty
                reasons.append(reason)
        
        if reasons:
            combined_reason = " | ".join(reasons)
            return True, combined_reason, total_penalty
        
        return True, "Autorisé par défaut", 0
    
    def get_setup_time_for_operation(self, operation: Dict, machine_id: str) -> int:
        """
        Calcule le temps de réglage additionnel pour une opération sur une machine.
        """
        applicable_rules = self.get_applicable_rules(operation)
        total_setup = 0
        
        for rule in applicable_rules:
            if rule.machine_id and rule.machine_id != machine_id:
                continue
            setup = rule.get_setup_time()
            if setup > 0:
                total_setup += setup
                logger.info(f"  ⏱  Règle {rule.name}: +{setup} min de réglage")
        
        return total_setup
    
    def get_preferred_machine(self, operation: Dict) -> str:
        """
        Retourne l'ID de la machine préférée selon les règles, si applicable.
        """
        applicable_rules = self.get_applicable_rules(operation)
        
        for rule in applicable_rules:
            if rule.action_type == "preferred_machine" and rule.action_value:
                logger.info(f"  ⭐ Machine préférée: {rule.action_value}")
                return rule.action_value
        
        return None
    
    def log_rules_summary(self):
        """
        Affiche un résumé des règles chargées.
        """
        logger.info(f"\n📋 {len(self.rules)} règle(s) métier chargée(s):")
        for rule in self.rules:
            criteria = []
            if rule.task_id:
                criteria.append(f"task={rule.task_id}")
            if rule.work_center_id:
                criteria.append(f"wc={rule.work_center_id}")
            if rule.machine_id:
                criteria.append(f"machine={rule.machine_id}")
            
            criteria_str = " + ".join(criteria) if criteria else "Générale"
            logger.info(f"   • {rule.name}: {criteria_str} → {rule.action_type}")
    
    # Méthodes de compatibilité pour l'ancien code
    def is_task_allowed_on_machine(self, task_id: str, machine_id: str) -> Tuple[bool, str, int]:
        """Compatibilité: évalue règles basées sur task_id."""
        operation = {'task_id': task_id}
        return self.evaluate_machine_for_operation(operation, machine_id)
    
    def is_workcenter_allowed_on_machine(self, work_center_id: str, machine_id: str) -> Tuple[bool, str, int]:
        """Compatibilité: évalue règles basées sur work_center_id."""
        operation = {'work_center_id': work_center_id}
        return self.evaluate_machine_for_operation(operation, machine_id)
    
    def is_article_allowed_on_machine(self, article_id: str, machine_id: str) -> Tuple[bool, str]:
        """Compatibilité: évalue règles basées sur article_id."""
        operation = {'article_id': article_id}
        allowed, reason, _ = self.evaluate_machine_for_operation(operation, machine_id)
        return allowed, reason