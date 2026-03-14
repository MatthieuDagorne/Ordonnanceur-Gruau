from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from enum import Enum
import uuid


class RuleType(str, Enum):
    ALLOW = "ALLOW"
    FORBID = "FORBID"
    PREFER = "PREFER"


class BusinessRule(BaseModel):
    """
    Modèle simplifié de règle métier pour le POC.
    Gère uniquement les règles d'affectation machine.
    """
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    
    # Critères de ciblage (au moins task_id ou work_center_id requis)
    task_id: Optional[str] = None
    work_center_id: Optional[str] = None
    article_id: Optional[str] = None  # Ne peut pas être seul
    
    # Type de règle
    rule_type: RuleType  # ALLOW, FORBID, PREFER
    
    # Machine cible (obligatoire)
    machine_id: str
    
    # État
    active: bool = Field(default=True)
    
    @field_validator('rule_type', mode='before')
    @classmethod
    def uppercase_rule_type(cls, v):
        if isinstance(v, str):
            return v.upper()
        return v

    def matches_operation(self, operation: dict) -> bool:
        """
        Vérifie si cette règle s'applique à l'opération donnée.
        Une règle correspond si TOUS ses critères définis correspondent.
        """
        if not self.active:
            return False
        
        # Vérifier task_id si défini
        if self.task_id:
            if operation.get('task_id') != self.task_id:
                return False
        
        # Vérifier work_center_id si défini
        if self.work_center_id:
            if operation.get('work_center_id') != self.work_center_id:
                return False
        
        # Vérifier article_id si défini
        if self.article_id:
            if operation.get('article_id') != self.article_id:
                return False
        
        return True

    def get_criteria_display(self) -> str:
        """Retourne une représentation lisible des critères."""
        parts = []
        if self.task_id:
            parts.append(f"task={self.task_id}")
        if self.work_center_id:
            parts.append(f"wc={self.work_center_id}")
        if self.article_id:
            parts.append(f"article={self.article_id}")
        return " + ".join(parts) if parts else "Aucun critère"
