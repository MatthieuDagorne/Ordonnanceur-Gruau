"""
Service de gestion des matières et du stock projeté.

Gère:
- Stock actuel
- Consommations par opération (operation_materials)
- Réceptions fournisseurs planifiées (planned_supplier_receipts)
- Projection du stock dans le temps
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MaterialRequirement:
    """Besoin matière pour une opération."""
    operation_id: str
    order_id: str
    operation_seq: int
    article_composant_id: str
    quantity: float


@dataclass
class PlannedReceipt:
    """Réception fournisseur planifiée."""
    article_id: str
    quantity: float
    planned_date: datetime


@dataclass
class StockMovement:
    """Mouvement de stock (entrée ou sortie)."""
    date: datetime
    article_id: str
    quantity: float  # Positif = entrée, négatif = sortie
    movement_type: str  # 'INITIAL', 'RECEIPT', 'CONSUMPTION'
    reference: str  # ID de l'opération ou de la réception


@dataclass
class MaterialAvailability:
    """Disponibilité d'un composant pour une opération."""
    article_id: str
    required_quantity: float
    available_quantity: float
    is_available: bool
    earliest_available_date: Optional[datetime] = None
    shortage_quantity: float = 0


@dataclass
class OperationMaterialStatus:
    """Statut matière complet pour une opération."""
    operation_id: str
    order_id: str
    components: List[MaterialAvailability] = field(default_factory=list)
    all_available: bool = False
    earliest_start_date: Optional[datetime] = None
    blocking_components: List[str] = field(default_factory=list)


class MaterialManager:
    """
    Gestionnaire de matières avec projection du stock.
    
    Calcule la disponibilité des composants en tenant compte:
    - Du stock initial
    - Des réceptions fournisseurs planifiées
    - Des consommations des opérations déjà planifiées
    """
    
    def __init__(
        self,
        initial_stocks: List[Dict],
        operation_materials: List[Dict],
        planned_receipts: List[Dict]
    ):
        # Stock initial par article
        self.initial_stocks: Dict[str, float] = {}
        for stock in initial_stocks:
            article_id = stock.get('article_id')
            qty = stock.get('quantity', 0)
            self.initial_stocks[article_id] = qty
        
        # Besoins matière par opération
        self.operation_materials: Dict[str, List[MaterialRequirement]] = {}
        for mat in operation_materials:
            op_id = mat.get('id') or mat.get('operation_id')
            if op_id:
                if op_id not in self.operation_materials:
                    self.operation_materials[op_id] = []
                self.operation_materials[op_id].append(MaterialRequirement(
                    operation_id=op_id,
                    order_id=mat.get('order_id', ''),
                    operation_seq=mat.get('operation_id', 0),
                    article_composant_id=mat.get('article_composant_id', ''),
                    quantity=mat.get('quantity', 0)
                ))
        
        # Réceptions planifiées
        self.planned_receipts: List[PlannedReceipt] = []
        for receipt in planned_receipts:
            planned_date = self._parse_datetime(receipt.get('planned_date'))
            if planned_date:
                self.planned_receipts.append(PlannedReceipt(
                    article_id=receipt.get('article_id', ''),
                    quantity=receipt.get('quantity', 0),
                    planned_date=planned_date
                ))
        
        # Trier les réceptions par date
        self.planned_receipts.sort(key=lambda r: r.planned_date)
        
        # Mouvements de stock (pour la projection)
        self.movements: List[StockMovement] = []
        
        # Consommations planifiées par article (éviter les doublons)
        self.planned_consumptions: Dict[str, float] = {}
        
        logger.info(f"\n{'='*60}")
        logger.info("MATERIAL MANAGER INITIALISÉ")
        logger.info(f"{'='*60}")
        logger.info(f"  Stock initial: {len(self.initial_stocks)} articles")
        logger.info(f"  Besoins opérations: {len(self.operation_materials)} opérations")
        logger.info(f"  Réceptions planifiées: {len(self.planned_receipts)}")
        logger.info(f"{'='*60}\n")
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse une date/heure."""
        if not date_str:
            return None
        try:
            if isinstance(date_str, datetime):
                return date_str
            if 'T' in date_str:
                if '+' in date_str or 'Z' in date_str:
                    date_str = date_str.replace('Z', '+00:00')
                    return datetime.fromisoformat(date_str.replace('+00:00', ''))
                return datetime.fromisoformat(date_str)
            elif ' ' in date_str:
                return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            else:
                return datetime.strptime(date_str, '%Y-%m-%d')
        except Exception as e:
            logger.warning(f"Parse date error '{date_str}': {e}")
            return None
    
    def get_operation_materials(self, operation_id: str) -> List[MaterialRequirement]:
        """Retourne les besoins matière d'une opération."""
        return self.operation_materials.get(operation_id, [])
    
    def get_projected_stock(self, article_id: str, at_date: datetime) -> float:
        """
        Calcule le stock projeté d'un article à une date donnée.
        
        Stock projeté = Stock initial + Réceptions avant date - Consommations planifiées avant date
        """
        # Stock initial
        stock = self.initial_stocks.get(article_id, 0)
        
        # Ajouter les réceptions planifiées avant la date
        for receipt in self.planned_receipts:
            if receipt.article_id == article_id and receipt.planned_date <= at_date:
                stock += receipt.quantity
        
        # Soustraire les consommations déjà planifiées
        stock -= self.planned_consumptions.get(article_id, 0)
        
        return stock
    
    def get_earliest_availability_date(
        self, 
        article_id: str, 
        required_quantity: float,
        from_date: datetime
    ) -> Tuple[bool, Optional[datetime]]:
        """
        Trouve la première date où le stock sera suffisant.
        
        Returns:
            (is_available_now, earliest_date)
        """
        # Vérifier si disponible maintenant
        current_stock = self.get_projected_stock(article_id, from_date)
        if current_stock >= required_quantity:
            return True, from_date
        
        # Chercher dans les réceptions futures
        projected_stock = current_stock
        for receipt in self.planned_receipts:
            if receipt.article_id == article_id and receipt.planned_date > from_date:
                projected_stock += receipt.quantity
                if projected_stock >= required_quantity:
                    return False, receipt.planned_date
        
        # Jamais disponible
        return False, None
    
    def check_operation_materials(
        self, 
        operation_id: str,
        planned_start: datetime
    ) -> OperationMaterialStatus:
        """
        Vérifie la disponibilité de tous les composants pour une opération.
        
        Returns:
            OperationMaterialStatus avec le détail par composant
        """
        materials = self.get_operation_materials(operation_id)
        
        status = OperationMaterialStatus(
            operation_id=operation_id,
            order_id='',
            all_available=True,
            earliest_start_date=planned_start
        )
        
        if not materials:
            return status
        
        status.order_id = materials[0].order_id
        latest_available_date = planned_start
        
        for mat in materials:
            required_qty = mat.quantity
            current_stock = self.get_projected_stock(mat.article_composant_id, planned_start)
            
            is_available, earliest_date = self.get_earliest_availability_date(
                mat.article_composant_id,
                required_qty,
                planned_start
            )
            
            availability = MaterialAvailability(
                article_id=mat.article_composant_id,
                required_quantity=required_qty,
                available_quantity=current_stock,
                is_available=is_available,
                earliest_available_date=earliest_date,
                shortage_quantity=max(0, required_qty - current_stock) if not is_available else 0
            )
            status.components.append(availability)
            
            if not is_available:
                status.all_available = False
                status.blocking_components.append(mat.article_composant_id)
                
                if earliest_date and earliest_date > latest_available_date:
                    latest_available_date = earliest_date
        
        status.earliest_start_date = latest_available_date
        
        return status
    
    def reserve_materials(self, operation_id: str, at_date: datetime) -> bool:
        """
        Réserve les matières pour une opération planifiée.
        Enregistre les consommations pour la projection future.
        """
        materials = self.get_operation_materials(operation_id)
        
        for mat in materials:
            article_id = mat.article_composant_id
            qty = mat.quantity
            
            # Ajouter à la consommation planifiée
            if article_id not in self.planned_consumptions:
                self.planned_consumptions[article_id] = 0
            self.planned_consumptions[article_id] += qty
            
            # Enregistrer le mouvement
            self.movements.append(StockMovement(
                date=at_date,
                article_id=article_id,
                quantity=-qty,
                movement_type='CONSUMPTION',
                reference=operation_id
            ))
            
            logger.debug(f"  Réservé {qty} x {article_id} pour {operation_id}")
        
        return True
    
    def get_stock_projection_report(self) -> Dict[str, Any]:
        """Génère un rapport de projection du stock."""
        report = {
            'initial_stocks': dict(self.initial_stocks),
            'planned_receipts': [
                {
                    'article_id': r.article_id,
                    'quantity': r.quantity,
                    'planned_date': r.planned_date.isoformat()
                }
                for r in self.planned_receipts
            ],
            'planned_consumptions': dict(self.planned_consumptions),
            'movements': [
                {
                    'date': m.date.isoformat(),
                    'article_id': m.article_id,
                    'quantity': m.quantity,
                    'type': m.movement_type,
                    'reference': m.reference
                }
                for m in self.movements
            ]
        }
        return report
    
    def check_availability(self, article_id: str, quantity: float) -> bool:
        """
        Vérifie si un article est disponible en quantité suffisante.
        Méthode de compatibilité avec l'ancien MaterialChecker.
        """
        if not article_id:
            return True
        stock = self.initial_stocks.get(article_id, 0)
        return stock >= quantity


# Classe de compatibilité avec l'ancien code
class MaterialChecker:
    """Wrapper de compatibilité pour MaterialManager."""
    
    def __init__(self, stocks: List[Dict]):
        self.stocks = {s.get('article_id'): s.get('quantity', 0) for s in stocks}
    
    def check_availability(self, article_id: str, quantity: float) -> bool:
        if not article_id:
            return True
        return self.stocks.get(article_id, 0) >= quantity
