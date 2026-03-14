from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, Dict, Any
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


class BusinessRule(BaseModel):
    """
    Règle métier pour l'ordonnancement.
    
    Deux types de règles:
    1. Règle simple: basée sur article_id, tache_id, centre_de_charge_id
    2. Règle sur attribut: basée sur les caractéristiques de l'article (largeur, épaisseur, etc.)
    
    Champs pour règle simple:
    - tache_id, centre_de_charge_id, article_id
    
    Champs pour règle sur attribut:
    - attribute_name: nom de l'attribut (width, thickness, material_type, color, length)
    - attribute_operator: opérateur de comparaison (GT, LT, EQ, etc.)
    - attribute_value: valeur de comparaison
    """
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: "")
    name: str
    
    # Critères de ciblage (règle simple)
    tache_id: Optional[str] = None
    centre_de_charge_id: Optional[str] = None
    article_id: Optional[str] = None
    
    # Critères sur attributs article (règle avancée)
    attribute_name: Optional[str] = None  # width, thickness, material_type, color, length
    attribute_operator: Optional[str] = None  # GT, LT, EQ, GE, LE, IN, NOT_IN
    attribute_value: Optional[Any] = None  # Valeur de comparaison
    
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

    def _compare_attribute(self, article_value: Any) -> bool:
        """
        Compare la valeur de l'attribut selon l'opérateur défini.
        """
        if article_value is None:
            return False
        
        op = self.attribute_operator
        rule_value = self.attribute_value
        
        try:
            # Convertir en float si possible pour comparaison numérique
            if op in ['GT', 'GE', 'LT', 'LE']:
                article_value = float(article_value)
                rule_value = float(rule_value)
            
            if op == 'EQ':
                return str(article_value) == str(rule_value)
            elif op == 'NE':
                return str(article_value) != str(rule_value)
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
                return str(article_value) in [str(v).strip() for v in values]
            elif op == 'NOT_IN':
                values = rule_value if isinstance(rule_value, list) else str(rule_value).split(',')
                return str(article_value) not in [str(v).strip() for v in values]
        except (ValueError, TypeError) as e:
            logger.warning(f"Erreur de comparaison: {e}")
            return False
        
        return False

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
        
        # Log pour debug
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
        
        # Vérifier attribut article si défini (règle avancée)
        if self.attribute_name and self.attribute_operator and self.attribute_value is not None:
            if not article_data:
                logger.info(f"      -> NO MATCH (pas de données article pour règle attribut)")
                return False
            
            article_value = article_data.get(self.attribute_name)
            logger.info(f"      Règle attribut: {self.attribute_name} {self.attribute_operator} {self.attribute_value}")
            logger.info(f"      Valeur article: {article_value}")
            
            if not self._compare_attribute(article_value):
                logger.info(f"      -> NO MATCH (attribut: {article_value} {self.attribute_operator} {self.attribute_value})")
                return False
            
            logger.info(f"      -> MATCH ATTRIBUT!")
        
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
        if self.attribute_name and self.attribute_operator:
            op_display = {
                'GT': '>', 'GE': '>=', 'LT': '<', 'LE': '<=',
                'EQ': '=', 'NE': '!=', 'IN': 'dans', 'NOT_IN': 'pas dans'
            }.get(self.attribute_operator, self.attribute_operator)
            parts.append(f"{self.attribute_name} {op_display} {self.attribute_value}")
        return " + ".join(parts) if parts else "Aucun critère"
