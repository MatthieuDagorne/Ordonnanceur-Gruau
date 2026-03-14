from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from enum import Enum


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

    def matches_operation(self, tache_id: str, centre_de_charge_id: str, article_id: str = None) -> bool:
        """
        Vérifie si cette règle s'applique aux critères donnés.
        """
        if not self.active:
            return False
        
        # Vérifier tache_id si défini dans la règle
        if self.tache_id and self.tache_id != tache_id:
            return False
        
        # Vérifier centre_de_charge_id si défini dans la règle
        if self.centre_de_charge_id and self.centre_de_charge_id != centre_de_charge_id:
            return False
        
        # Vérifier article_id si défini dans la règle
        if self.article_id and self.article_id != article_id:
            return False
        
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
