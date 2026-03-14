"""
APS Engine - Advanced Planning & Scheduling
============================================

Module responsable de:
- Explosion de nomenclature (BOM)
- Calcul MRP (Material Requirements Planning)
- Planification capacité finie
- Calcul des dates de consommation matière
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class BOMExploder:
    """
    Explosion de nomenclature multi-niveaux.
    
    Permet de calculer les besoins en composants pour un produit fini
    à travers tous les niveaux de la nomenclature.
    """
    
    def __init__(self, bom_lines: List[Dict]):
        """
        Initialise l'exploseur avec les lignes de nomenclature.
        
        Args:
            bom_lines: Liste des lignes BOM avec parent_article_id, child_article_id, quantity
        """
        # Index: parent -> [(child, quantity, level)]
        self.bom_by_parent = defaultdict(list)
        for line in bom_lines:
            parent = line.get('parent_article_id')
            child = line.get('child_article_id')
            qty = line.get('quantity', 1.0)
            level = line.get('level', 1)
            scrap_rate = line.get('scrap_rate', 0.0)
            
            if parent and child:
                self.bom_by_parent[parent].append({
                    'child_article_id': child,
                    'quantity': qty,
                    'level': level,
                    'scrap_rate': scrap_rate
                })
        
        logger.info(f"BOM chargé: {len(bom_lines)} lignes, {len(self.bom_by_parent)} parents")
    
    def explode(self, article_id: str, quantity: float = 1.0, max_level: int = 10) -> List[Dict]:
        """
        Explose la nomenclature pour un article donné.
        
        Args:
            article_id: ID de l'article parent
            quantity: Quantité du parent
            max_level: Niveau maximum d'explosion
            
        Returns:
            Liste des composants avec quantités cumulées
        """
        result = []
        
        def _explode_recursive(parent_id: str, parent_qty: float, current_level: int):
            if current_level > max_level:
                return
            
            children = self.bom_by_parent.get(parent_id, [])
            for child in children:
                child_id = child['child_article_id']
                child_qty = child['quantity'] * parent_qty
                scrap_rate = child.get('scrap_rate', 0.0)
                
                # Ajuster pour le taux de rebut
                adjusted_qty = child_qty * (1 + scrap_rate)
                
                result.append({
                    'article_id': child_id,
                    'quantity': adjusted_qty,
                    'level': current_level,
                    'parent_article_id': parent_id,
                    'base_quantity': child['quantity'],
                    'scrap_rate': scrap_rate
                })
                
                # Explosion récursive si le composant a lui-même des composants
                _explode_recursive(child_id, adjusted_qty, current_level + 1)
        
        _explode_recursive(article_id, quantity, 1)
        return result
    
    def get_all_components(self, article_id: str, quantity: float = 1.0) -> Dict[str, float]:
        """
        Retourne la liste agrégée des composants avec quantités totales.
        
        Args:
            article_id: Article à exploser
            quantity: Quantité demandée
            
        Returns:
            Dict article_id -> quantité totale
        """
        explosion = self.explode(article_id, quantity)
        
        totals = defaultdict(float)
        for item in explosion:
            totals[item['article_id']] += item['quantity']
        
        return dict(totals)


class MRPCalculator:
    """
    Calcul MRP (Material Requirements Planning).
    
    Calcule les besoins nets en composants en tenant compte:
    - Stock disponible
    - Réceptions planifiées (fournisseurs et production)
    - Ordres de fabrication existants
    """
    
    def __init__(self, db):
        self.db = db
    
    async def calculate_mrp(
        self,
        orders: List[Dict],
        bom_exploder: BOMExploder,
        stocks: Dict[str, float],
        planned_receipts: List[Dict],
        scheduled_operations: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Calcule le MRP complet.
        
        Args:
            orders: Ordres de fabrication
            bom_exploder: Exploseur de nomenclature
            stocks: Stock par article {article_id: quantity}
            planned_receipts: Réceptions fournisseurs planifiées
            scheduled_operations: Opérations déjà ordonnancées (pour dates de consommation)
            
        Returns:
            Résultat MRP avec besoins nets et dates
        """
        scheduled_operations = scheduled_operations or []
        
        # Index des opérations ordonnancées par order_id
        scheduled_by_order = {}
        for op in scheduled_operations:
            order_id = op.get('order_id')
            if order_id:
                if order_id not in scheduled_by_order:
                    scheduled_by_order[order_id] = []
                scheduled_by_order[order_id].append(op)
        
        # Index des réceptions par article et date
        receipts_by_article = defaultdict(list)
        for receipt in planned_receipts:
            article_id = receipt.get('article_id')
            receipts_by_article[article_id].append({
                'quantity': receipt.get('quantity', 0),
                'date': receipt.get('planned_date')
            })
        
        # Calculer les besoins bruts
        gross_requirements = defaultdict(list)  # article_id -> [(quantity, date, order_id)]
        
        for order in orders:
            order_id = order.get('id')
            article_id = order.get('article_id')
            quantity = order.get('quantity', 1)
            due_date = order.get('due_date')
            
            # Déterminer la date de consommation
            # Priorité: scheduled_start de la première opération, sinon due_date
            consumption_date = due_date
            if order_id in scheduled_by_order:
                ops = scheduled_by_order[order_id]
                # Prendre la date de début de la première opération
                first_op = min(ops, key=lambda x: x.get('start_datetime', '9999'))
                consumption_date = first_op.get('start_datetime') or due_date
            
            # Ajouter le besoin brut pour l'article fini
            gross_requirements[article_id].append({
                'quantity': quantity,
                'date': consumption_date,
                'order_id': order_id,
                'type': 'finished_product'
            })
            
            # Exploser la nomenclature pour obtenir les composants
            components = bom_exploder.get_all_components(article_id, quantity)
            for comp_id, comp_qty in components.items():
                gross_requirements[comp_id].append({
                    'quantity': comp_qty,
                    'date': consumption_date,
                    'order_id': order_id,
                    'type': 'component'
                })
        
        # Calculer les besoins nets par article
        mrp_results = []
        
        for article_id in sorted(gross_requirements.keys()):
            requirements = gross_requirements[article_id]
            on_hand = stocks.get(article_id, 0)
            receipts = receipts_by_article.get(article_id, [])
            
            # Trier par date
            requirements.sort(key=lambda x: x.get('date') or '9999')
            receipts.sort(key=lambda x: x.get('date') or '9999')
            
            total_gross = sum(r['quantity'] for r in requirements)
            total_receipts = sum(r['quantity'] for r in receipts)
            
            # Calculer le besoin net
            net_requirement = max(0, total_gross - on_hand - total_receipts)
            
            # Calculer la timeline et détecter les ruptures
            current_stock = on_hand
            shortage_date = None
            timeline = []
            
            # Fusionner requirements et receipts dans l'ordre chronologique
            events = []
            for req in requirements:
                events.append({
                    'date': req['date'],
                    'type': 'requirement',
                    'quantity': -req['quantity'],
                    'order_id': req.get('order_id')
                })
            for rec in receipts:
                events.append({
                    'date': rec['date'],
                    'type': 'receipt',
                    'quantity': rec['quantity']
                })
            
            events.sort(key=lambda x: x.get('date') or '9999')
            
            for event in events:
                current_stock += event['quantity']
                timeline.append({
                    'date': event['date'],
                    'type': event['type'],
                    'quantity_change': event['quantity'],
                    'stock_after': current_stock
                })
                
                if current_stock < 0 and shortage_date is None:
                    shortage_date = event['date']
            
            mrp_results.append({
                'article_id': article_id,
                'gross_requirement': total_gross,
                'on_hand': on_hand,
                'scheduled_receipts': total_receipts,
                'net_requirement': net_requirement,
                'has_shortage': net_requirement > 0,
                'shortage_date': shortage_date,
                'timeline': timeline[:20],  # Limiter pour l'affichage
                'requirements_detail': requirements[:10]
            })
        
        # Trier par criticité (ruptures en premier)
        mrp_results.sort(key=lambda x: (0 if x['has_shortage'] else 1, x.get('shortage_date') or '9999'))
        
        return {
            'mrp_results': mrp_results,
            'summary': {
                'total_articles': len(mrp_results),
                'articles_with_shortage': len([r for r in mrp_results if r['has_shortage']]),
                'articles_ok': len([r for r in mrp_results if not r['has_shortage']]),
                'total_orders': len(orders),
                'orders_scheduled': len(scheduled_by_order)
            }
        }


class CapacityPlanner:
    """
    Planification de capacité finie.
    
    Gère:
    - Capacité disponible par machine selon calendriers
    - Charge planifiée (production_time + setup_time)
    - Taux d'utilisation
    """
    
    def __init__(self, machines: List[Dict], calendars: List[Dict], centres: List[Dict]):
        self.machines = machines
        self.calendars_by_id = {c.get('id'): c for c in calendars}
        self.centres_by_id = {c.get('id'): c for c in centres}
        
        # Construire l'index machine -> calendrier
        self.machine_calendar = {}
        for machine in machines:
            machine_id = machine.get('id')
            centre_id = machine.get('centre_de_charge_id')
            centre = self.centres_by_id.get(centre_id, {})
            calendar_id = centre.get('calendar_id')
            
            if calendar_id and calendar_id in self.calendars_by_id:
                self.machine_calendar[machine_id] = self.calendars_by_id[calendar_id]
            else:
                # Calendrier par défaut 24/7
                self.machine_calendar[machine_id] = {
                    'working_days': [0, 1, 2, 3, 4, 5, 6],
                    'start_hour': 0,
                    'end_hour': 24
                }
    
    def get_capacity_minutes_per_day(self, machine_id: str) -> int:
        """Retourne la capacité en minutes par jour pour une machine."""
        calendar = self.machine_calendar.get(machine_id, {})
        start_hour = calendar.get('start_hour', 0)
        end_hour = calendar.get('end_hour', 24)
        return (end_hour - start_hour) * 60
    
    def calculate_capacity_load(
        self, 
        operations: List[Dict], 
        start_date: str, 
        horizon_days: int = 7
    ) -> Dict[str, Any]:
        """
        Calcule la charge vs capacité par machine et par jour.
        
        Args:
            operations: Opérations avec machine_id, production_time_minutes, setup_time_minutes
            start_date: Date de début de l'horizon
            horizon_days: Nombre de jours à planifier
            
        Returns:
            Charge et capacité par machine/jour
        """
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            start_dt = datetime.now()
        
        # Calculer la charge par machine et par jour
        load_by_machine_day = defaultdict(lambda: defaultdict(int))  # machine_id -> date -> minutes
        
        for op in operations:
            machine_id = op.get('machine_id')
            if not machine_id:
                continue
            
            prod_time = op.get('production_time_minutes', 0)
            setup_time = op.get('setup_time_minutes', 0)
            total_time = prod_time + setup_time
            
            # Déterminer le jour de l'opération
            scheduled_start = op.get('scheduled_start') or op.get('start_datetime')
            if scheduled_start:
                try:
                    op_date = datetime.fromisoformat(scheduled_start.replace('Z', '+00:00')).date()
                except (ValueError, AttributeError):
                    op_date = start_dt.date()
            else:
                op_date = start_dt.date()
            
            load_by_machine_day[machine_id][str(op_date)] += total_time
        
        # Générer le rapport capacité/charge
        capacity_slots = []
        
        for machine in self.machines:
            machine_id = machine.get('id')
            calendar = self.machine_calendar.get(machine_id, {})
            working_days = set(calendar.get('working_days', [0, 1, 2, 3, 4, 5, 6]))
            capacity_per_day = self.get_capacity_minutes_per_day(machine_id)
            
            for day_offset in range(horizon_days):
                current_date = start_dt.date() + timedelta(days=day_offset)
                
                # Vérifier si c'est un jour travaillé
                if current_date.weekday() not in working_days:
                    continue
                
                date_str = str(current_date)
                loaded = load_by_machine_day.get(machine_id, {}).get(date_str, 0)
                utilization = (loaded / capacity_per_day * 100) if capacity_per_day > 0 else 0
                
                capacity_slots.append({
                    'machine_id': machine_id,
                    'date': date_str,
                    'capacity_minutes': capacity_per_day,
                    'loaded_minutes': loaded,
                    'available_minutes': max(0, capacity_per_day - loaded),
                    'utilization_rate': round(utilization, 1),
                    'is_overloaded': loaded > capacity_per_day
                })
        
        # Calculer les résumés par machine
        summary_by_machine = {}
        for machine in self.machines:
            machine_id = machine.get('id')
            slots = [s for s in capacity_slots if s['machine_id'] == machine_id]
            total_capacity = sum(s['capacity_minutes'] for s in slots)
            total_loaded = sum(s['loaded_minutes'] for s in slots)
            
            summary_by_machine[machine_id] = {
                'total_capacity_hours': round(total_capacity / 60, 1),
                'total_loaded_hours': round(total_loaded / 60, 1),
                'average_utilization': round(total_loaded / total_capacity * 100, 1) if total_capacity > 0 else 0,
                'overloaded_days': len([s for s in slots if s['is_overloaded']])
            }
        
        return {
            'capacity_slots': capacity_slots,
            'summary_by_machine': summary_by_machine,
            'total_machines': len(self.machines),
            'horizon_days': horizon_days
        }


class APSEngine:
    """
    Moteur APS principal.
    
    Coordonne:
    - Explosion de nomenclature
    - Calcul MRP
    - Planification capacité finie
    - Intégration avec l'ordonnanceur
    """
    
    def __init__(self, db):
        self.db = db
    
    async def run_mrp(self, scheduled_operations: List[Dict] = None) -> Dict[str, Any]:
        """
        Exécute le calcul MRP complet.
        
        Args:
            scheduled_operations: Opérations déjà ordonnancées (optionnel)
            
        Returns:
            Résultat MRP
        """
        # Charger les données
        orders = await self.db.manufacturing_orders.find({}, {"_id": 0}).to_list(1000)
        bom_lines = await self.db.bom.find({}, {"_id": 0}).to_list(10000)
        stocks_list = await self.db.stocks.find({}, {"_id": 0}).to_list(1000)
        planned_receipts = await self.db.planned_supplier_receipts.find({}, {"_id": 0}).to_list(1000)
        
        # Convertir stocks en dict
        stocks = {s.get('article_id'): s.get('quantity', 0) for s in stocks_list}
        
        # Créer l'exploseur BOM
        bom_exploder = BOMExploder(bom_lines)
        
        # Calculer MRP
        mrp_calculator = MRPCalculator(self.db)
        result = await mrp_calculator.calculate_mrp(
            orders=orders,
            bom_exploder=bom_exploder,
            stocks=stocks,
            planned_receipts=planned_receipts,
            scheduled_operations=scheduled_operations
        )
        
        return result
    
    async def calculate_capacity(
        self, 
        operations: List[Dict] = None, 
        horizon_days: int = 7
    ) -> Dict[str, Any]:
        """
        Calcule la charge vs capacité.
        
        Args:
            operations: Opérations à planifier (si None, charge depuis BDD)
            horizon_days: Horizon de planification
            
        Returns:
            Rapport capacité/charge
        """
        machines = await self.db.machines.find({}, {"_id": 0}).to_list(100)
        calendars = await self.db.calendars.find({}, {"_id": 0}).to_list(100)
        centres = await self.db.centres_de_charge.find({}, {"_id": 0}).to_list(100)
        
        if operations is None:
            operations = await self.db.operations.find({}, {"_id": 0}).to_list(1000)
        
        planner = CapacityPlanner(machines, calendars, centres)
        return planner.calculate_capacity_load(
            operations=operations,
            start_date=datetime.now().isoformat(),
            horizon_days=horizon_days
        )
