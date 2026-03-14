from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RuleType(str, Enum):
    ALLOW = "ALLOW"
    FORBID = "FORBID"
    PREFER = "PREFER"


class BusinessRule(BaseModel):
    """
    Règle métier simplifiée pour le POC.
    Utilise des codes métier lisibles (pas d'UUID).
    
    Champs:
    - id: code métier unique de la règle
    - name: nom descriptif
    - tache_id: code de la tâche (ex: PLIAGE, USINAGE)
    - centre_de_charge_id: code du centre de charge (ex: PLI01, USI01)
    - article_id: code article (optionnel)
    - rule_type: ALLOW, FORBID, PREFER
    - machine_id: code de la machine cible (ex: PLIEUSE_01)
    - active: état de la règle
    
    Logique de matching:
    - Une règle matche si TOUS ses critères définis correspondent
    - Un critère non défini (None) signifie "tous" (wildcard)
    - Exemple: tache_id="PLIAGE", article_id=None -> matche toutes les opérations de pliage
    """
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: "")
    name: str
    
    # Critères de ciblage (codes métier, pas UUID)
    tache_id: Optional[str] = None
    centre_de_charge_id: Optional[str] = None
    article_id: Optional[str] = None
    
    # Type de règle
    rule_type: RuleType
    
    # Machine cible (code métier, pas UUID)
    machine_id: str
    
    # État
    active: bool = Field(default=True)
    
    @field_validator('rule_type', mode='before')
    @classmethod
    def uppercase_rule_type(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v

    def matches_operation(
        self, 
        tache_id: Optional[str], 
        centre_de_charge_id: Optional[str], 
        article_id: Optional[str] = None
    ) -> bool:
        """
        Vérifie si cette règle s'applique aux critères donnés.
        
        Logique de matching:
        - Si un critère est défini dans la règle, il doit correspondre exactement
        - Si un critère n'est PAS défini dans la règle (None), il est ignoré (wildcard)
        - TOUS les critères définis doivent matcher pour que la règle s'applique
        
        Args:
            tache_id: Code de la tâche de l'opération
            centre_de_charge_id: Code du centre de charge de l'opération
            article_id: Code article de l'ordre de fabrication (via jointure order_id)
        
        Returns:
            True si la règle s'applique à cette opération
        """
        if not self.active:
            logger.debug(f"  Règle '{self.name}' inactive, ignorée")
            return False
        
        # Log pour debug
        logger.debug(f"  Matching règle '{self.name}':")
        logger.debug(f"    Règle: tache={self.tache_id}, centre={self.centre_de_charge_id}, article={self.article_id}")
        logger.debug(f"    Op:    tache={tache_id}, centre={centre_de_charge_id}, article={article_id}")
        
        # Vérifier tache_id si défini dans la règle
        if self.tache_id is not None and self.tache_id != '':
            if tache_id != self.tache_id:
                logger.debug(f"    -> NO MATCH (tache: {tache_id} != {self.tache_id})")
                return False
        
        # Vérifier centre_de_charge_id si défini dans la règle
        if self.centre_de_charge_id is not None and self.centre_de_charge_id != '':
            if centre_de_charge_id != self.centre_de_charge_id:
                logger.debug(f"    -> NO MATCH (centre: {centre_de_charge_id} != {self.centre_de_charge_id})")
                return False
        
        # Vérifier article_id si défini dans la règle
        # C'est ici que le bug était: on doit comparer avec l'article_id de l'ORDRE, pas de l'opération
        if self.article_id is not None and self.article_id != '':
            if article_id is None or article_id != self.article_id:
                logger.debug(f"    -> NO MATCH (article: {article_id} != {self.article_id})")
                return False
        
        logger.debug(f"    -> MATCH!")
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
        return " + ".join(parts) if parts else "Aucun critère"
