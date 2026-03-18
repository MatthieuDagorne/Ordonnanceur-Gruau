import logging
from typing import List, Dict, Any, Tuple, Optional
from models.business_rule import BusinessRule, RuleType

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Moteur de règles métier.
    
    Types de règles:
    - REQUIRE: Machine obligatoire/exclusive - SEULE cette machine peut traiter l'opération
    - FORBID: Machine interdite - Cette machine ne peut PAS traiter l'opération
    - PREFER: Machine préférée - Bonus de préférence (non contraignant)
    - ALLOW: DEPRECATED - Remplacé par REQUIRE
    
    Critères de matching:
    1. Règles simples: tache_id, centre_de_charge_id, article_id
    2. Règles sur attributs: basées sur les caractéristiques de l'article
       (width, thickness, material_type, color, length)
    
    Opérateurs pour attributs: GT, GE, LT, LE, EQ, NE, IN, NOT_IN
    """
    
    def __init__(self, rules_data: List[Dict], articles_data: List[Dict] = None):
        self.rules: List[BusinessRule] = []
        self.invalid_rules: List[Dict] = []
        self.applied_rules_log: List[Dict] = []
        
        # Index des articles par ID pour lookup rapide
        self.articles_by_id: Dict[str, Dict] = {}
        if articles_data:
            for article in articles_data:
                article_id = article.get('id')
                if article_id:
                    self.articles_by_id[str(article_id)] = article
        
        logger.info("\n" + "="*80)
        logger.info("CHARGEMENT DES REGLES METIER")
        logger.info("="*80)
        logger.info(f"Articles indexés: {len(self.articles_by_id)}")
        
        for rule_data in rules_data:
            try:
                rule = BusinessRule(**rule_data)
                
                # Validation minimale
                has_simple_criteria = rule.tache_id or rule.centre_de_charge_id or rule.article_id
                has_attribute_criteria = rule.attribute_name and rule.attribute_operator
                
                if not has_simple_criteria and not has_attribute_criteria:
                    logger.warning(f"  [IGNORE] '{rule.name}': aucun critère défini")
                    self.invalid_rules.append({
                        'name': rule.name,
                        'reason': 'Aucun critère défini'
                    })
                    continue
                
                self.rules.append(rule)
                
                logger.info(f"  [OK] {rule.name}")
                logger.info(f"       Type: {rule.rule_type.value}")
                logger.info(f"       Critères: {rule.get_criteria_display()}")
                logger.info(f"       Machine cible: {rule.machine_id}")
                
            except Exception as e:
                logger.warning(f"  [ERREUR] Règle invalide: {e}")
                self.invalid_rules.append({
                    'name': rule_data.get('name', 'Unknown'),
                    'reason': str(e)
                })
        
        logger.info(f"\nRésumé: {len(self.rules)} règle(s) valide(s), {len(self.invalid_rules)} ignorée(s)")
        logger.info("="*80 + "\n")
    
    def get_article_data(self, article_id: str) -> Optional[Dict]:
        """Récupère les données complètes d'un article."""
        return self.articles_by_id.get(str(article_id)) if article_id else None
    
    def _get_applicable_rules(
        self, 
        tache_id: str, 
        centre_de_charge_id: str, 
        article_id: Optional[str] = None,
        article_data: Optional[Dict] = None
    ) -> List[BusinessRule]:
        """
        Retourne toutes les règles qui correspondent aux critères.
        """
        applicable = []
        
        logger.info(f"\n  Recherche de règles pour:")
        logger.info(f"    tache_id: {tache_id}")
        logger.info(f"    centre_de_charge_id: {centre_de_charge_id}")
        logger.info(f"    article_id: {article_id}")
        if article_data:
            logger.info(f"    article_data: width={article_data.get('width')}, thickness={article_data.get('thickness')}, material={article_data.get('material_type')}")
        
        for rule in self.rules:
            if rule.matches_operation(tache_id, centre_de_charge_id, article_id, article_data):
                applicable.append(rule)
        
        return applicable
    
    def evaluate_machine(
        self, 
        tache_id: str,
        centre_de_charge_id: str,
        machine_id: str,
        article_id: Optional[str] = None,
        article_data: Optional[Dict] = None
    ) -> Tuple[bool, List[str], int]:
        """
        Évalue si une machine peut être utilisée pour les critères donnés.
        
        Logique des règles:
        - REQUIRE: SEULE la machine spécifiée est autorisée (toutes les autres sont interdites)
        - FORBID: Cette machine spécifique est interdite
        - PREFER: Cette machine a un bonus de préférence
        
        Returns:
            (allowed: bool, reasons: List[str], preference_score: int)
        """
        # Si pas de données article, essayer de les récupérer
        if not article_data and article_id:
            article_data = self.get_article_data(article_id)
        
        applicable_rules = self._get_applicable_rules(
            tache_id, centre_de_charge_id, article_id, article_data
        )
        
        if not applicable_rules:
            return True, ["Aucune règle applicable"], 0
        
        allowed = True
        reasons = []
        preference_score = 0
        
        # Vérifier s'il y a des règles REQUIRE pour cette opération
        require_rules = [r for r in applicable_rules if r.rule_type == RuleType.REQUIRE or r.rule_type == RuleType.ALLOW]
        
        if require_rules:
            # Il y a des règles REQUIRE - seules ces machines sont autorisées
            required_machine_ids = [r.machine_id for r in require_rules]
            
            if machine_id in required_machine_ids:
                # Cette machine est requise
                matching_rule = next(r for r in require_rules if r.machine_id == machine_id)
                criteria_display = matching_rule.get_criteria_display()
                reason = f"REQUIS par '{matching_rule.name}' ({criteria_display})"
                reasons.append(reason)
                self._log_application(tache_id, centre_de_charge_id, article_id, matching_rule, machine_id, "REQUIS")
            else:
                # Cette machine n'est PAS dans la liste des machines requises
                allowed = False
                rule_names = ", ".join([r.name for r in require_rules])
                reason = f"NON AUTORISÉ - Seules les machines requises sont permises: {required_machine_ids} (règles: {rule_names})"
                reasons.append(reason)
        
        # Vérifier les règles FORBID
        for rule in applicable_rules:
            if rule.machine_id == machine_id and rule.rule_type == RuleType.FORBID:
                allowed = False
                criteria_display = rule.get_criteria_display()
                reason = f"INTERDIT par '{rule.name}' ({criteria_display})"
                reasons.append(reason)
                self._log_application(tache_id, centre_de_charge_id, article_id, rule, machine_id, "INTERDIT")
        
        # Vérifier les règles PREFER
        for rule in applicable_rules:
            if rule.machine_id == machine_id and rule.rule_type == RuleType.PREFER:
                preference_score += 100
                reason = f"PRÉFÉRÉ par '{rule.name}' (+100)"
                reasons.append(reason)
                self._log_application(tache_id, centre_de_charge_id, article_id, rule, machine_id, "PRÉFÉRÉ")
        
        if not reasons:
            reasons.append("Aucune règle ne cible cette machine")
        
        return allowed, reasons, preference_score
    
    def _log_application(
        self, 
        tache_id: str,
        centre_de_charge_id: str,
        article_id: Optional[str],
        rule: BusinessRule, 
        machine_id: str,
        result: str
    ):
        """Enregistre l'application d'une règle."""
        self.applied_rules_log.append({
            'tache_id': tache_id,
            'centre_de_charge_id': centre_de_charge_id,
            'article_id': article_id,
            'rule_name': rule.name,
            'rule_type': rule.rule_type.value,
            'rule_article_id': rule.article_id,
            'rule_attribute': f"{rule.attribute_name} {rule.attribute_operator} {rule.attribute_value}" if rule.attribute_name else None,
            'machine_id': machine_id,
            'result': result
        })
    
    def get_allowed_machines(
        self, 
        tache_id: str,
        centre_de_charge_id: str,
        available_machines: List[Dict],
        article_id: Optional[str] = None,
        article_data: Optional[Dict] = None
    ) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Filtre les machines selon les règles.
        """
        allowed = []
        forbidden = []
        
        # Si pas de données article, essayer de les récupérer
        if not article_data and article_id:
            article_data = self.get_article_data(article_id)
        
        logger.info(f"\n    Évaluation des règles:")
        logger.info(f"      Critères:")
        logger.info(f"        - tache_id: {tache_id}")
        logger.info(f"        - centre_de_charge_id: {centre_de_charge_id}")
        logger.info(f"        - article_id: {article_id}")
        if article_data:
            logger.info(f"        - article_data: {article_data}")
        
        applicable_rules = self._get_applicable_rules(
            tache_id, centre_de_charge_id, article_id, article_data
        )
        
        diagnostics = {
            'tache_id': tache_id,
            'centre_de_charge_id': centre_de_charge_id,
            'article_id': article_id,
            'article_data': article_data,
            'applicable_rules': [
                {
                    'name': r.name, 
                    'type': r.rule_type.value, 
                    'machine_id': r.machine_id,
                    'criteria': r.get_criteria_display(),
                    'rule_tache_id': r.tache_id,
                    'rule_centre_id': r.centre_de_charge_id,
                    'rule_article_id': r.article_id,
                    'rule_attribute': f"{r.attribute_name} {r.attribute_operator} {r.attribute_value}" if r.attribute_name else None
                }
                for r in applicable_rules
            ],
            'allowed_machines': [],
            'forbidden_machines': []
        }
        
        if applicable_rules:
            logger.info(f"      {len(applicable_rules)} règle(s) applicable(s):")
            for r in applicable_rules:
                logger.info(f"        [{r.rule_type.value}] {r.name}")
                logger.info(f"          Critères: {r.get_criteria_display()}")
                logger.info(f"          Machine cible: {r.machine_id}")
        else:
            logger.info(f"      Aucune règle applicable")
        
        # Évaluer chaque machine
        for machine in available_machines:
            machine_id = machine.get('id')
            
            is_allowed, reasons, score = self.evaluate_machine(
                tache_id, centre_de_charge_id, machine_id, article_id, article_data
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
                    'score': score,
                    'reasons': reasons
                })
            else:
                forbidden.append(machine_info)
                diagnostics['forbidden_machines'].append({
                    'id': machine_id,
                    'reasons': reasons
                })
                logger.info(f"      ✗ Machine {machine_id} INTERDITE: {reasons}")
        
        # Trier par score de préférence
        allowed.sort(key=lambda m: m.get('preference_score', 0), reverse=True)
        
        return allowed, forbidden, diagnostics
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Retourne les statistiques de diagnostic."""
        rules_by_type = {
            'REQUIRE': len([r for r in self.rules if r.rule_type == RuleType.REQUIRE or r.rule_type == RuleType.ALLOW]),
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
                    'type': 'REQUIRE' if r.rule_type in [RuleType.REQUIRE, RuleType.ALLOW] else r.rule_type.value,
                    'tache_id': r.tache_id,
                    'centre_de_charge_id': r.centre_de_charge_id,
                    'article_id': r.article_id,
                    'attribute_name': r.attribute_name,
                    'attribute_operator': r.attribute_operator,
                    'attribute_value': r.attribute_value,
                    'machine_id': r.machine_id,
                    'active': r.active,
                    'criteria_display': r.get_criteria_display()
                }
                for r in self.rules
            ]
        }
    
    def clear_applied_rules_log(self):
        """Réinitialise le log des règles appliquées."""
        self.applied_rules_log = []
    
    def evaluate_machine_for_operation(
        self,
        matching_context: Dict[str, Any],
        machine_id: str
    ) -> Tuple[bool, List[str], int]:
        """
        Méthode de compatibilité avec l'ancien code.
        """
        tache_id = matching_context.get('task_id') or matching_context.get('tache_id')
        centre_id = matching_context.get('work_center_id') or matching_context.get('centre_de_charge_id')
        article_id = matching_context.get('article_id')
        article_data = matching_context.get('article_data')
        
        allowed, reasons, score = self.evaluate_machine(
            tache_id or '',
            centre_id or '',
            machine_id,
            article_id,
            article_data
        )
        
        penalty = -score if score < 0 else 0
        return allowed, reasons, penalty
