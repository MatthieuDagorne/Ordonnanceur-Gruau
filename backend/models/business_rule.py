from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    ALLOW = "ALLOW"
    FORBID = "FORBID"
    PREFER = "PREFER"


class ComparisonOperator(str, Enum):
    """Opérateurs de comparaison pour les règles sur attributs."""
    EQ = "EQ"       # Égal
    NE = "NE"       # Différent
    GT = "GT"       # Supérieur
    GE = "GE"       # Supérieur ou égal
    LT = "LT"       # Inférieur
    LE = "LE"       # Inférieur ou égal
    IN = "IN"       # Dans la liste
    NOT_IN = "NOT_IN"  # Pas dans la liste


class LogicalOperator(str, Enum):
    """Opérateurs logiques pour combiner les conditions."""
    AND = "AND"
    OR = "OR"


class AttributeCondition(BaseModel):
    """
    Une condition sur un attribut d'article.
    
    Exemple: largeur > 500, type_matiere = "Acier", epaisseur <= 10
    """
    attribute_name: str      # width, thickness, material_type, color, length
    operator: str            # GT, LT, EQ, GE, LE, IN, NOT_IN
    value: Any               # Valeur de comparaison
    
    def evaluate(self, article_data: Dict) -> bool:
        """Évalue la condition sur les données de l'article."""
        if not article_data:
            return False
        
        article_value = article_data.get(self.attribute_name)
        if article_value is None:
            return False
        
        op = self.operator.upper() if isinstance(self.operator, str) else self.operator
        rule_value = self.value
        
        try:
            # Convertir en float si possible pour comparaison numérique
            if op in ['GT', 'GE', 'LT', 'LE']:
                article_value = float(article_value)
                rule_value = float(rule_value)
            
            if op == 'EQ':
                return str(article_value).lower() == str(rule_value).lower()
            elif op == 'NE':
                return str(article_value).lower() != str(rule_value).lower()
            elif op == 'GT':
                return article_value > rule_value
            elif op == 'GE':
                return article_value >= rule_value
            elif op == 'LT':
                return article_value < rule_value
            elif op == 'LE':
                return article_value <= rule_value
            elif op == 'IN':
                values = rule_value if isinstance(rule_value, list) else str(rule_value).split(',')
                return str(article_value).lower() in [str(v).strip().lower() for v in values]
            elif op == 'NOT_IN':
                values = rule_value if isinstance(rule_value, list) else str(rule_value).split(',')
                return str(article_value).lower() not in [str(v).strip().lower() for v in values]
        except (ValueError, TypeError) as e:
            logger.warning(f"Erreur de comparaison: {e}")
            return False
        
        return False
    
    def to_display(self) -> str:
        """Retourne une représentation lisible."""
        op_display = {
            'GT': '>', 'GE': '>=', 'LT': '<', 'LE': '<=',
            'EQ': '=', 'NE': '!=', 'IN': 'dans', 'NOT_IN': 'pas dans'
        }.get(self.operator, self.operator)
        return f"{self.attribute_name} {op_display} {self.value}"


class ConditionGroup(BaseModel):
    """
    Un groupe de conditions combinées avec un opérateur logique.
    
    Exemple: (largeur > 500 ET epaisseur < 10) OU (type_matiere = "Acier")
    
    Structure:
    - conditions: Liste de conditions individuelles
    - logic: Opérateur logique entre les conditions (AND/OR)
    """
    conditions: List[AttributeCondition] = []
    logic: str = "AND"  # AND ou OR
    
    def evaluate(self, article_data: Dict) -> bool:
        """Évalue le groupe de conditions."""
        if not self.conditions:
            return True  # Pas de conditions = toujours vrai
        
        results = [cond.evaluate(article_data) for cond in self.conditions]
        
        if self.logic.upper() == "AND":
            return all(results)
        else:  # OR
            return any(results)
    
    def to_display(self) -> str:
        """Retourne une représentation lisible."""
        if not self.conditions:
            return ""
        parts = [cond.to_display() for cond in self.conditions]
        joiner = " ET " if self.logic.upper() == "AND" else " OU "
        return f"({joiner.join(parts)})"


class BusinessRule(BaseModel):
    """
    Règle métier pour l'ordonnancement.
    
    Supporte:
    1. Règle simple: basée sur article_id, tache_id, centre_de_charge_id
    2. Règle sur attribut unique (rétro-compatibilité)
    3. Règle sur attributs multiples avec ET/OU
    
    Structure des conditions multiples:
    - attribute_conditions: Liste de groupes de conditions
    - conditions_logic: Opérateur logique entre les groupes (AND/OR)
    
    Exemple complexe:
    "Si (largeur > 500 ET epaisseur < 10) OU (type_matiere = Acier)"
    -> attribute_conditions: [
         { conditions: [{largeur, GT, 500}, {epaisseur, LT, 10}], logic: AND },
         { conditions: [{type_matiere, EQ, Acier}], logic: AND }
       ]
    -> conditions_logic: OR
    """
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: "")
    name: str
    
    # Critères de ciblage (règle simple)
    tache_id: Optional[str] = None
    centre_de_charge_id: Optional[str] = None
    article_id: Optional[str] = None
    
    # Critères sur attribut unique (rétro-compatibilité)
    attribute_name: Optional[str] = None
    attribute_operator: Optional[str] = None
    attribute_value: Optional[Any] = None
    
    # Critères sur attributs multiples avec ET/OU
    attribute_conditions: Optional[List[Dict]] = None  # Liste de groupes de conditions
    conditions_logic: str = "AND"  # Opérateur entre les groupes
    
    # Type de règle
    rule_type: RuleType
    
    # Machine cible
    machine_id: str
    
    # État
    active: bool = Field(default=True)
    
    @field_validator('rule_type', mode='before')
    @classmethod
    def uppercase_rule_type(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v
    
    @field_validator('attribute_operator', mode='before')
    @classmethod
    def uppercase_operator(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v

    def _compare_single_attribute(self, article_value: Any, operator: str, rule_value: Any) -> bool:
        """Compare la valeur de l'attribut selon l'opérateur défini."""
        if article_value is None:
            return False
        
        op = operator.upper() if isinstance(operator, str) else operator
        
        try:
            if op in ['GT', 'GE', 'LT', 'LE']:
                article_value = float(article_value)
                rule_value = float(rule_value)
            
            if op == 'EQ':
                return str(article_value).lower() == str(rule_value).lower()
            elif op == 'NE':
                return str(article_value).lower() != str(rule_value).lower()
            elif op == 'GT':
                return article_value > rule_value
            elif op == 'GE':
                return article_value >= rule_value
            elif op == 'LT':
                return article_value < rule_value
            elif op == 'LE':
                return article_value <= rule_value
            elif op == 'IN':
                values = rule_value if isinstance(rule_value, list) else str(rule_value).split(',')
                return str(article_value).lower() in [str(v).strip().lower() for v in values]
            elif op == 'NOT_IN':
                values = rule_value if isinstance(rule_value, list) else str(rule_value).split(',')
                return str(article_value).lower() not in [str(v).strip().lower() for v in values]
        except (ValueError, TypeError) as e:
            logger.warning(f"Erreur de comparaison: {e}")
            return False
        
        return False

    def _evaluate_condition_group(self, group: Dict, article_data: Dict) -> bool:
        """Évalue un groupe de conditions."""
        conditions = group.get('conditions', [])
        logic = group.get('logic', 'AND').upper()
        
        if not conditions:
            return True
        
        results = []
        for cond in conditions:
            attr_name = cond.get('attribute_name')
            operator = cond.get('operator')
            value = cond.get('value')
            
            if attr_name and operator and value is not None:
                article_value = article_data.get(attr_name)
                result = self._compare_single_attribute(article_value, operator, value)
                results.append(result)
                logger.info(f"        Condition: {attr_name} {operator} {value} => {result} (valeur article: {article_value})")
        
        if not results:
            return True
        
        if logic == 'AND':
            return all(results)
        else:  # OR
            return any(results)

    def _evaluate_all_conditions(self, article_data: Dict) -> bool:
        """
        Évalue toutes les conditions sur attributs.
        
        Supporte:
        1. Attribut unique (rétro-compatibilité)
        2. Attributs multiples avec ET/OU
        """
        # 1. Vérifier d'abord les conditions multiples (nouvelle structure)
        if self.attribute_conditions and len(self.attribute_conditions) > 0:
            logger.info(f"      Évaluation conditions multiples ({self.conditions_logic}):")
            
            group_results = []
            for i, group in enumerate(self.attribute_conditions):
                result = self._evaluate_condition_group(group, article_data)
                group_results.append(result)
                logger.info(f"      Groupe {i+1}: {result}")
            
            if not group_results:
                return True
            
            if self.conditions_logic.upper() == 'AND':
                final = all(group_results)
            else:  # OR
                final = any(group_results)
            
            logger.info(f"      Résultat final ({self.conditions_logic}): {final}")
            return final
        
        # 2. Sinon, vérifier l'attribut unique (rétro-compatibilité)
        if self.attribute_name and self.attribute_operator and self.attribute_value is not None:
            article_value = article_data.get(self.attribute_name)
            logger.info(f"      Règle attribut unique: {self.attribute_name} {self.attribute_operator} {self.attribute_value}")
            logger.info(f"      Valeur article: {article_value}")
            return self._compare_single_attribute(article_value, self.attribute_operator, self.attribute_value)
        
        # Pas de conditions sur attributs
        return True

    def matches_operation(
        self, 
        tache_id: Optional[str], 
        centre_de_charge_id: Optional[str], 
        article_id: Optional[str] = None,
        article_data: Optional[Dict] = None
    ) -> bool:
        """
        Vérifie si cette règle s'applique aux critères donnés.
        
        Args:
            tache_id: Code de la tâche de l'opération
            centre_de_charge_id: Code du centre de charge de l'opération
            article_id: Code article de l'ordre de fabrication
            article_data: Données complètes de l'article (pour règles sur attributs)
        
        Returns:
            True si la règle s'applique à cette opération
        """
        if not self.active:
            return False
        
        logger.info(f"    Matching règle '{self.name}':")
        logger.info(f"      Règle: tache={self.tache_id}, centre={self.centre_de_charge_id}, article={self.article_id}")
        logger.info(f"      Op:    tache={tache_id}, centre={centre_de_charge_id}, article={article_id}")
        
        # Vérifier tache_id si défini
        if self.tache_id is not None and self.tache_id != '':
            if tache_id != self.tache_id:
                logger.info(f"      -> NO MATCH (tache: {tache_id} != {self.tache_id})")
                return False
        
        # Vérifier centre_de_charge_id si défini
        if self.centre_de_charge_id is not None and self.centre_de_charge_id != '':
            if centre_de_charge_id != self.centre_de_charge_id:
                logger.info(f"      -> NO MATCH (centre: {centre_de_charge_id} != {self.centre_de_charge_id})")
                return False
        
        # Vérifier article_id si défini (règle simple)
        if self.article_id is not None and self.article_id != '':
            if article_id is None or str(article_id) != str(self.article_id):
                logger.info(f"      -> NO MATCH (article: {article_id} != {self.article_id})")
                return False
        
        # Vérifier les conditions sur attributs
        has_attribute_conditions = (
            (self.attribute_conditions and len(self.attribute_conditions) > 0) or
            (self.attribute_name and self.attribute_operator and self.attribute_value is not None)
        )
        
        if has_attribute_conditions:
            if not article_data:
                logger.info(f"      -> NO MATCH (pas de données article pour règle attribut)")
                return False
            
            if not self._evaluate_all_conditions(article_data):
                logger.info(f"      -> NO MATCH (conditions attributs non satisfaites)")
                return False
            
            logger.info(f"      -> MATCH ATTRIBUTS!")
        
        logger.info(f"      -> MATCH!")
        return True

    def get_criteria_display(self) -> str:
        """Retourne une représentation lisible des critères."""
        parts = []
        
        if self.tache_id:
            parts.append(f"tâche={self.tache_id}")
        if self.centre_de_charge_id:
            parts.append(f"centre={self.centre_de_charge_id}")
        if self.article_id:
            parts.append(f"article={self.article_id}")
        
        # Conditions multiples
        if self.attribute_conditions and len(self.attribute_conditions) > 0:
            groups_display = []
            for group in self.attribute_conditions:
                conditions = group.get('conditions', [])
                logic = group.get('logic', 'AND')
                
                cond_parts = []
                for cond in conditions:
                    op_display = {
                        'GT': '>', 'GE': '>=', 'LT': '<', 'LE': '<=',
                        'EQ': '=', 'NE': '!=', 'IN': 'dans', 'NOT_IN': 'pas dans'
                    }.get(cond.get('operator', ''), cond.get('operator', ''))
                    cond_parts.append(f"{cond.get('attribute_name')} {op_display} {cond.get('value')}")
                
                if cond_parts:
                    joiner = " ET " if logic == "AND" else " OU "
                    groups_display.append(f"({joiner.join(cond_parts)})")
            
            if groups_display:
                main_joiner = " ET " if self.conditions_logic == "AND" else " OU "
                parts.append(main_joiner.join(groups_display))
        
        # Attribut unique (rétro-compatibilité)
        elif self.attribute_name and self.attribute_operator:
            op_display = {
                'GT': '>', 'GE': '>=', 'LT': '<', 'LE': '<=',
                'EQ': '=', 'NE': '!=', 'IN': 'dans', 'NOT_IN': 'pas dans'
            }.get(self.attribute_operator, self.attribute_operator)
            parts.append(f"{self.attribute_name} {op_display} {self.attribute_value}")
        
        return " + ".join(parts) if parts else "Aucun critère"
