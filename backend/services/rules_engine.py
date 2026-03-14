import logging
from typing import List, Dict, Any, Tuple, Optional
from models.business_rule import BusinessRule, RuleType

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Moteur de règles métier.
    
    Types de règles: ALLOW, FORBID, PREFER
    
    Critères de matching (codes métier, pas UUID):
    - tache_id: code de la tâche (ex: PLIAGE, USINAGE, LVT001)
    - centre_de_charge_id: code du centre de charge (ex: PLI01, LVC001)
    - article_id: code article (ex: 100235570) - DOIT VENIR DE L'ORDRE!
    
    Logique:
    - Une règle matche si TOUS ses critères définis correspondent
    - Un critère non défini (None) = wildcard (matche tout)
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
                
                # Validation: au moins tache_id ou centre_de_charge_id
                if not rule.tache_id and not rule.centre_de_charge_id:
                    logger.warning(f"  [IGNORE] '{rule.name}': doit avoir tache_id et/ou centre_de_charge_id")
                    self.invalid_rules.append({
                        'name': rule.name,
                        'reason': 'Doit avoir tache_id et/ou centre_de_charge_id'
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
    
    def _get_applicable_rules(
        self, 
        tache_id: str, 
        centre_de_charge_id: str, 
        article_id: Optional[str] = None
    ) -> List[BusinessRule]:
        """
        Retourne toutes les règles qui correspondent aux critères.
        
        IMPORTANT: article_id doit être passé depuis l'ordre de fabrication!
        """
        applicable = []
        
        logger.debug(f"\n  Recherche de règles pour:")
        logger.debug(f"    tache_id: {tache_id}")
        logger.debug(f"    centre_de_charge_id: {centre_de_charge_id}")
        logger.debug(f"    article_id: {article_id} (depuis l'ordre)")
        
        for rule in self.rules:
            if rule.matches_operation(tache_id, centre_de_charge_id, article_id):
                logger.debug(f"    -> MATCH: {rule.name} ({rule.rule_type.value})")
                applicable.append(rule)
            else:
                logger.debug(f"    -> no match: {rule.name}")
        
        return applicable
    
    def evaluate_machine(
        self, 
        tache_id: str,
        centre_de_charge_id: str,
        machine_id: str,
        article_id: Optional[str] = None
    ) -> Tuple[bool, List[str], int]:
        """
        Évalue si une machine peut être utilisée pour les critères donnés.
        
        Args:
            tache_id: Code de la tâche
            centre_de_charge_id: Code du centre de charge
            machine_id: Code de la machine à évaluer
            article_id: Code article (DEPUIS L'ORDRE!)
        
        Returns:
            (allowed: bool, reasons: List[str], preference_score: int)
        """
        applicable_rules = self._get_applicable_rules(tache_id, centre_de_charge_id, article_id)
        
        if not applicable_rules:
            return True, ["Aucune règle applicable"], 0
        
        allowed = True
        reasons = []
        preference_score = 0
        
        for rule in applicable_rules:
            # La règle cible cette machine?
            if rule.machine_id == machine_id:
                if rule.rule_type == RuleType.FORBID:
                    allowed = False
                    reason = f"INTERDIT par '{rule.name}' (critères: {rule.get_criteria_display()})"
                    reasons.append(reason)
                    self._log_application(tache_id, centre_de_charge_id, article_id, rule, machine_id, "BLOQUE")
                    
                elif rule.rule_type == RuleType.ALLOW:
                    reason = f"AUTORISE par '{rule.name}'"
                    reasons.append(reason)
                    self._log_application(tache_id, centre_de_charge_id, article_id, rule, machine_id, "AUTORISE")
                    
                elif rule.rule_type == RuleType.PREFER:
                    preference_score += 100
                    reason = f"PREFEREE par '{rule.name}' (+100)"
                    reasons.append(reason)
                    self._log_application(tache_id, centre_de_charge_id, article_id, rule, machine_id, "PREFEREE")
        
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
            'machine_id': machine_id,
            'result': result
        })
    
    def get_allowed_machines(
        self, 
        tache_id: str,
        centre_de_charge_id: str,
        available_machines: List[Dict],
        article_id: Optional[str] = None
    ) -> Tuple[List[Dict], List[Dict], Dict]:
        """
        Filtre les machines selon les règles.
        
        Args:
            tache_id: Code de la tâche
            centre_de_charge_id: Code du centre de charge
            available_machines: Liste des machines candidates
            article_id: Code article (DEPUIS L'ORDRE!)
        
        Returns:
            (allowed_machines, forbidden_machines, diagnostics)
        """
        allowed = []
        forbidden = []
        
        logger.info(f"\n    Évaluation des règles:")
        logger.info(f"      Critères:")
        logger.info(f"        - tache_id: {tache_id}")
        logger.info(f"        - centre_de_charge_id: {centre_de_charge_id}")
        logger.info(f"        - article_id: {article_id} (DEPUIS L'ORDRE)")
        
        applicable_rules = self._get_applicable_rules(tache_id, centre_de_charge_id, article_id)
        
        diagnostics = {
            'tache_id': tache_id,
            'centre_de_charge_id': centre_de_charge_id,
            'article_id': article_id,
            'applicable_rules': [
                {
                    'name': r.name, 
                    'type': r.rule_type.value, 
                    'machine_id': r.machine_id,
                    'criteria': r.get_criteria_display(),
                    'rule_tache_id': r.tache_id,
                    'rule_centre_id': r.centre_de_charge_id,
                    'rule_article_id': r.article_id
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
                logger.info(f"          Critères règle: tache={r.tache_id}, centre={r.centre_de_charge_id}, article={r.article_id}")
                logger.info(f"          Machine cible: {r.machine_id}")
        else:
            logger.info(f"      Aucune règle applicable")
        
        # Évaluer chaque machine
        for machine in available_machines:
            machine_id = machine.get('id')
            
            is_allowed, reasons, score = self.evaluate_machine(
                tache_id, centre_de_charge_id, machine_id, article_id
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
                    'tache_id': r.tache_id,
                    'centre_de_charge_id': r.centre_de_charge_id,
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
    
    def evaluate_machine_for_operation(
        self,
        matching_context: Dict[str, Any],
        machine_id: str
    ) -> Tuple[bool, List[str], int]:
        """
        Évalue si une machine peut être utilisée pour un contexte d'opération.
        Méthode de compatibilité avec l'ancien code.
        
        Args:
            matching_context: Dict avec task_id, work_center_id, article_id
            machine_id: Code de la machine à évaluer
        
        Returns:
            (allowed: bool, reasons: List[str], penalty: int)
        """
        # Adapter les noms de champs
        tache_id = matching_context.get('task_id') or matching_context.get('tache_id')
        centre_id = matching_context.get('work_center_id') or matching_context.get('centre_de_charge_id')
        article_id = matching_context.get('article_id')
        
        allowed, reasons, score = self.evaluate_machine(
            tache_id or '',
            centre_id or '',
            machine_id,
            article_id
        )
        
        # Convertir le score en pénalité (inverse)
        penalty = -score if score < 0 else 0
        
        return allowed, reasons, penalty
