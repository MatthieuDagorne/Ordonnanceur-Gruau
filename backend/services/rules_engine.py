import logging
from typing import List, Dict, Any, Tuple, Optional
from models.business_rule import BusinessRule, RuleType

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Moteur de règles métier simplifié pour le POC.
    
    Types de règles: ALLOW, FORBID, PREFER
    
    Critères de matching (depuis l'opération/ordre):
    - task_id: type de tâche
    - work_center_id: centre de charge
    - article_id: article (depuis l'ordre de fabrication)
    
    IMPORTANT: N'utilise JAMAIS l'id de l'opération pour le matching.
    """
    
    def __init__(self, rules_data: List[Dict]):
        self.rules: List[BusinessRule] = []
        self.invalid_rules: List[Dict] = []
        self.applied_rules_log: List[Dict] = []
        
        logger.info("\n" + "="*80)
        logger.info("CHARGEMENT DES REGLES METIER")
        logger.info("="*80)
        
        for rule_data in rules_data:
            try:
                rule = BusinessRule(**rule_data)
                
                # Validation: au moins task_id ou work_center_id
                if not rule.task_id and not rule.work_center_id:
                    logger.warning(f"  [IGNORE] '{rule.name}': article_id seul non autorise")
                    self.invalid_rules.append({
                        'name': rule.name,
                        'reason': 'Doit avoir task_id et/ou work_center_id'
                    })
                    continue
                
                self.rules.append(rule)
                
                # Log détaillé de la règle
                criteria = []
                if rule.task_id:
                    criteria.append(f"task_id={rule.task_id}")
                if rule.work_center_id:
                    criteria.append(f"work_center_id={rule.work_center_id}")
                if rule.article_id:
                    criteria.append(f"article_id={rule.article_id}")
                
                logger.info(f"  [OK] {rule.name}")
                logger.info(f"       Type: {rule.rule_type.value}")
                logger.info(f"       Criteres: {' + '.join(criteria)}")
                logger.info(f"       Machine cible: {rule.machine_id}")
                
            except Exception as e:
                logger.warning(f"  [ERREUR] Regle invalide: {e}")
                self.invalid_rules.append({
                    'name': rule_data.get('name', 'Unknown'),
                    'reason': str(e)
                })
        
        logger.info(f"\nResume: {len(self.rules)} regle(s) valide(s), {len(self.invalid_rules)} ignoree(s)")
        logger.info("="*80 + "\n")
    
    def _matches_rule(self, rule: BusinessRule, context: Dict) -> Tuple[bool, str]:
        """
        Vérifie si une règle correspond au contexte donné.
        
        Le contexte contient: task_id, work_center_id, article_id
        (PAS l'id de l'opération)
        
        Returns:
            (matches: bool, reason: str)
        """
        if not rule.active:
            return False, "Regle inactive"
        
        # Matching sur task_id
        if rule.task_id:
            ctx_task = context.get('task_id')
            if ctx_task != rule.task_id:
                return False, f"task_id ne correspond pas ({ctx_task} != {rule.task_id})"
        
        # Matching sur work_center_id
        if rule.work_center_id:
            ctx_wc = context.get('work_center_id')
            if ctx_wc != rule.work_center_id:
                return False, f"work_center_id ne correspond pas ({ctx_wc} != {rule.work_center_id})"
        
        # Matching sur article_id
        if rule.article_id:
            ctx_article = context.get('article_id')
            if ctx_article != rule.article_id:
                return False, f"article_id ne correspond pas ({ctx_article} != {rule.article_id})"
        
        return True, "Tous les criteres correspondent"
    
    def _get_applicable_rules(self, context: Dict) -> List[BusinessRule]:
        """
        Retourne toutes les règles qui correspondent au contexte.
        
        Args:
            context: dict avec task_id, work_center_id, article_id
        """
        applicable = []
        for rule in self.rules:
            matches, _ = self._matches_rule(rule, context)
            if matches:
                applicable.append(rule)
        return applicable
    
    def evaluate_machine_for_operation(
        self, 
        context: Dict, 
        machine_id: str,
        machine_name: Optional[str] = None
    ) -> Tuple[bool, List[str], int]:
        """
        Évalue si une machine peut être utilisée pour le contexte donné.
        
        Args:
            context: dict avec task_id, work_center_id, article_id
            machine_id: ID de la machine à évaluer
            machine_name: Nom de la machine (pour les logs)
        
        Returns:
            (allowed: bool, reasons: List[str], preference_score: int)
        """
        applicable_rules = self._get_applicable_rules(context)
        
        if not applicable_rules:
            return True, ["Aucune regle applicable"], 0
        
        allowed = True
        reasons = []
        preference_score = 0
        
        for rule in applicable_rules:
            # La règle cible cette machine spécifique?
            if rule.machine_id == machine_id:
                if rule.rule_type == RuleType.FORBID:
                    allowed = False
                    reason = f"FORBID par '{rule.name}'"
                    reasons.append(reason)
                    self._log_application(context, rule, machine_id, machine_name, "BLOQUE")
                    
                elif rule.rule_type == RuleType.ALLOW:
                    reason = f"ALLOW par '{rule.name}'"
                    reasons.append(reason)
                    self._log_application(context, rule, machine_id, machine_name, "AUTORISE")
                    
                elif rule.rule_type == RuleType.PREFER:
                    preference_score += 100
                    reason = f"PREFER par '{rule.name}' (+100)"
                    reasons.append(reason)
                    self._log_application(context, rule, machine_id, machine_name, "PREFEREE")
        
        if not reasons:
            reasons.append("Aucune regle ne cible cette machine")
        
        return allowed, reasons, preference_score
    
    def _log_application(
        self, 
        context: Dict, 
        rule: BusinessRule, 
        machine_id: str,
        machine_name: Optional[str],
        result: str
    ):
        """Enregistre l'application d'une règle."""
        self.applied_rules_log.append({
            'task_id': context.get('task_id'),
            'work_center_id': context.get('work_center_id'),
            'article_id': context.get('article_id'),
            'rule_name': rule.name,
            'rule_type': rule.rule_type.value,
            'rule_criteria': rule.get_criteria_display(),
            'machine_id': machine_id,
            'machine_name': machine_name,
            'result': result
        })
    
    def get_allowed_machines(
        self, 
        context: Dict, 
        available_machines: List[Dict]
    ) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Filtre les machines selon les règles.
        
        Args:
            context: dict avec task_id, work_center_id, article_id
            available_machines: liste des machines candidates
        
        Returns:
            (allowed_machines, forbidden_machines, diagnostics)
        """
        allowed = []
        forbidden = []
        
        # Log du contexte
        task_id = context.get('task_id')
        work_center_id = context.get('work_center_id')
        article_id = context.get('article_id')
        
        logger.info(f"\n    Evaluation des regles:")
        logger.info(f"      Contexte: task={task_id}, wc={work_center_id}, article={article_id or '-'}")
        
        # Récupérer les règles applicables
        applicable_rules = self._get_applicable_rules(context)
        
        diagnostics = {
            'task_id': task_id,
            'work_center_id': work_center_id,
            'article_id': article_id,
            'applicable_rules': [
                {
                    'name': r.name, 
                    'type': r.rule_type.value, 
                    'machine_id': r.machine_id,
                    'criteria': r.get_criteria_display()
                }
                for r in applicable_rules
            ],
            'allowed_machines': [],
            'forbidden_machines': []
        }
        
        if applicable_rules:
            logger.info(f"      {len(applicable_rules)} regle(s) applicable(s):")
            for r in applicable_rules:
                logger.info(f"        - {r.name} ({r.rule_type.value}) -> machine {r.machine_id}")
        else:
            logger.info(f"      Aucune regle applicable")
        
        # Évaluer chaque machine
        for machine in available_machines:
            machine_id = machine.get('id')
            machine_name = machine.get('name', machine_id)
            
            is_allowed, reasons, score = self.evaluate_machine_for_operation(
                context, machine_id, machine_name
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
