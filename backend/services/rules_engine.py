import logging

logger = logging.getLogger(__name__)

class RulesEngine:
    def __init__(self, rules):
        self.rules = rules
    
    def is_operation_allowed_on_machine(self, operation_code, machine_id):
        """
        Check if operation can run on specified machine.
        Returns (allowed: bool, reason: str, penalty: int)
        """
        # Find rules for this combination
        for rule in self.rules:
            if rule.get('rule_type') == 'machine_operation':
                if (rule.get('machine_id') == machine_id and 
                    rule.get('operation_code') == operation_code):
                    
                    if rule.get('is_hard'):
                        # Hard constraint
                        allowed = rule.get('allowed', True)
                        reason = f"Hard rule: operation {operation_code} {'allowed' if allowed else 'forbidden'} on machine {machine_id}"
                        return allowed, reason, 0
                    else:
                        # Soft constraint
                        penalty = rule.get('penalty', 0)
                        reason = f"Soft rule: operation {operation_code} on machine {machine_id} with penalty {penalty}"
                        return True, reason, penalty
        
        # No rule found - allow by default
        return True, "No specific rule", 0
    
    def is_article_allowed_on_machine(self, article_id, machine_id):
        """
        Check if article can be processed on specified machine.
        """
        for rule in self.rules:
            if rule.get('rule_type') == 'article_machine':
                if (rule.get('article_id') == article_id and 
                    rule.get('machine_id') == machine_id):
                    
                    if rule.get('is_hard'):
                        allowed = rule.get('allowed', True)
                        reason = f"Article {article_id} {'allowed' if allowed else 'forbidden'} on machine {machine_id}"
                        return allowed, reason
        
        return True, "No specific rule"
    
    def get_preferred_machines(self, operation_code):
        """
        Get list of preferred machines for operation.
        """
        preferred = []
        for rule in self.rules:
            if rule.get('rule_type') == 'preference':
                if rule.get('operation_code') == operation_code:
                    preferred.append(rule.get('machine_id'))
        return preferred
    
    def get_setup_time_addition(self, machine_id, operation_code):
        """
        Get additional setup time for specific combination.
        """
        for rule in self.rules:
            if (rule.get('machine_id') == machine_id and 
                rule.get('operation_code') == operation_code and
                rule.get('setup_time_minutes') is not None):
                return rule.get('setup_time_minutes')
        return 0