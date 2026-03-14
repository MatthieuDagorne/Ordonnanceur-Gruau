import logging

logger = logging.getLogger(__name__)

class RulesEngine:
    """
    Moteur de règles métier basé sur task_id et work_center_id.
    """
    def __init__(self, rules):
        self.rules = rules
    
    def is_task_allowed_on_workcenter(self, task_id, work_center_id):
        """
        Vérifie si une tâche peut être exécutée sur un centre de charge.
        Returns: (allowed: bool, reason: str, penalty: int)
        """
        for rule in self.rules:
            if rule.get('rule_type') == 'task_workcenter':
                if (rule.get('task_id') == task_id and 
                    rule.get('work_center_id') == work_center_id):
                    
                    if rule.get('is_hard'):
                        allowed = rule.get('allowed', True)
                        reason = f"Règle dure: tâche {task_id} {'autorisée' if allowed else 'interdite'} sur centre {work_center_id}"
                        return allowed, reason, 0
                    else:
                        penalty = rule.get('penalty', 0)
                        reason = f"Règle souple: tâche {task_id} sur centre {work_center_id} (pénalité: {penalty})"
                        return True, reason, penalty
        
        return True, "Pas de règle spécifique", 0
    
    def is_task_allowed_on_machine(self, task_id, machine_id):
        """
        Vérifie si une tâche peut être exécutée sur une machine spécifique.
        Returns: (allowed: bool, reason: str, penalty: int)
        """
        for rule in self.rules:
            if rule.get('rule_type') == 'task_machine':
                if (rule.get('task_id') == task_id and 
                    rule.get('machine_id') == machine_id):
                    
                    if rule.get('is_hard'):
                        allowed = rule.get('allowed', True)
                        reason = f"Règle dure: tâche {task_id} {'autorisée' if allowed else 'interdite'} sur machine {machine_id}"
                        return allowed, reason, 0
                    else:
                        penalty = rule.get('penalty', 0)
                        reason = f"Règle souple: tâche {task_id} sur machine {machine_id} (pénalité: {penalty})"
                        return True, reason, penalty
        
        return True, "Pas de règle spécifique", 0
    
    def is_workcenter_allowed_on_machine(self, work_center_id, machine_id):
        """
        Vérifie si un centre de charge est compatible avec une machine.
        Returns: (allowed: bool, reason: str, penalty: int)
        """
        for rule in self.rules:
            if rule.get('rule_type') == 'workcenter_machine':
                if (rule.get('work_center_id') == work_center_id and 
                    rule.get('machine_id') == machine_id):
                    
                    if rule.get('is_hard'):
                        allowed = rule.get('allowed', True)
                        reason = f"Règle dure: centre {work_center_id} {'autorisé' if allowed else 'interdit'} sur machine {machine_id}"
                        return allowed, reason, 0
                    else:
                        penalty = rule.get('penalty', 0)
                        reason = f"Règle souple: centre {work_center_id} sur machine {machine_id} (pénalité: {penalty})"
                        return True, reason, penalty
        
        return True, "Pas de règle spécifique", 0
    
    def is_article_allowed_on_machine(self, article_id, machine_id):
        """
        Vérifie si un article peut être traité sur une machine.
        Returns: (allowed: bool, reason: str)
        """
        for rule in self.rules:
            if rule.get('rule_type') == 'article_machine':
                if (rule.get('article_id') == article_id and 
                    rule.get('machine_id') == machine_id):
                    
                    if rule.get('is_hard'):
                        allowed = rule.get('allowed', True)
                        reason = f"Article {article_id} {'autorisé' if allowed else 'interdit'} sur machine {machine_id}"
                        return allowed, reason
        
        return True, "Pas de règle spécifique"
    
    def get_operation_rules(self, operation):
        """
        Récupère toutes les règles applicables à une opération.
        Returns: dict avec toutes les règles trouvées
        """
        task_id = operation.get('task_id')
        work_center_id = operation.get('work_center_id')
        article_id = operation.get('article_id')
        
        applicable_rules = {
            'task_workcenter': [],
            'task_machine': [],
            'workcenter_machine': [],
            'article_machine': []
        }
        
        for rule in self.rules:
            rule_type = rule.get('rule_type')
            
            if rule_type == 'task_workcenter':
                if (rule.get('task_id') == task_id and 
                    rule.get('work_center_id') == work_center_id):
                    applicable_rules['task_workcenter'].append(rule)
            
            elif rule_type == 'task_machine':
                if rule.get('task_id') == task_id:
                    applicable_rules['task_machine'].append(rule)
            
            elif rule_type == 'workcenter_machine':
                if rule.get('work_center_id') == work_center_id:
                    applicable_rules['workcenter_machine'].append(rule)
            
            elif rule_type == 'article_machine':
                if rule.get('article_id') == article_id:
                    applicable_rules['article_machine'].append(rule)
        
        return applicable_rules
    
    def get_setup_time_addition(self, task_id, machine_id):
        """
        Obtient un temps de réglage additionnel pour une combinaison tâche/machine.
        """
        for rule in self.rules:
            if ((rule.get('task_id') == task_id or rule.get('work_center_id')) and
                rule.get('machine_id') == machine_id and
                rule.get('setup_time_minutes') is not None):
                return rule.get('setup_time_minutes')
        return 0

    # Legacy methods for backwards compatibility (deprecated)
    def is_operation_allowed_on_machine(self, operation_code, machine_id):
        """
        DEPRECATED: Use task-based methods instead.
        Kept for backwards compatibility.
        """
        logger.warning("⚠️ is_operation_allowed_on_machine is deprecated. Use task-based methods.")
        return True, "Legacy method - no restriction", 0
    
    def get_preferred_machines(self, operation_code):
        """
        DEPRECATED: Use task-based methods instead.
        """
        logger.warning("⚠️ get_preferred_machines is deprecated. Use task-based methods.")
        return []
