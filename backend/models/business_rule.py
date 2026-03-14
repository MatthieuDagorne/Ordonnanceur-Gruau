from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
import uuid

class BusinessRule(BaseModel):
    """
    Modèle de règle métier flexible basé sur task_id et work_center_id.
    """
    model_config = ConfigDict(extra="ignore")
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    rule_type: str  # "compatibility", "preference", "setup_time", "prohibition"
    is_hard: bool = Field(default=True)  # True = interdiction, False = pénalité/préférence
    
    # Critères de ciblage (au moins un doit être défini)
    task_id: Optional[str] = None
    work_center_id: Optional[str] = None
    machine_id: Optional[str] = None
    article_id: Optional[str] = None
    
    # Condition
    condition_operator: str = Field(default="equals")  # "equals", "in", "not_in", "exists"
    condition_value: Optional[str] = None
    
    # Action
    action_type: str  # "allow", "forbid", "penalty", "setup_time", "preferred_machine"
    action_value: Optional[str] = None  # Valeur numérique ou ID machine
    
    # État
    active: bool = Field(default=True)
    description: Optional[str] = None

    def matches_operation(self, operation: dict) -> bool:
        """
        Vérifie si cette règle s'applique à l'opération donnée.
        """
        if not self.active:
            return False
        
        # Vérifier task_id
        if self.task_id:
            if operation.get('task_id') != self.task_id:
                return False
        
        # Vérifier work_center_id
        if self.work_center_id:
            if operation.get('work_center_id') != self.work_center_id:
                return False
        
        # Vérifier article_id
        if self.article_id:
            if operation.get('article_id') != self.article_id:
                return False
        
        return True
    
    def evaluate_for_machine(self, machine_id: str) -> tuple[bool, str, int]:
        """
        Évalue la règle pour une machine donnée.
        Returns: (allowed, reason, penalty)
        """
        # Si la règle cible une machine spécifique
        if self.machine_id and self.machine_id != machine_id:
            return True, "Règle ne s'applique pas à cette machine", 0
        
        if self.action_type == "forbid":
            if self.is_hard:
                return False, f"Règle {self.name}: {self.description or 'Interdit'}", 0
            else:
                penalty = int(self.action_value) if self.action_value else 1000
                return True, f"Règle {self.name}: forte pénalité", penalty
        
        elif self.action_type == "allow":
            return True, f"Règle {self.name}: Autorisé", 0
        
        elif self.action_type == "penalty":
            penalty = int(self.action_value) if self.action_value else 10
            return True, f"Règle {self.name}: Pénalité {penalty}", penalty
        
        elif self.action_type == "preferred_machine":
            if self.action_value == machine_id:
                return True, f"Règle {self.name}: Machine préférée", -100  # Bonus négatif
            else:
                return True, "Pas la machine préférée", 0
        
        return True, "Règle sans action", 0
    
    def get_setup_time(self) -> int:
        """
        Retourne le temps de réglage additionnel si applicable.
        """
        if self.action_type == "setup_time" and self.action_value:
            try:
                return int(self.action_value)
            except:
                return 0
        return 0