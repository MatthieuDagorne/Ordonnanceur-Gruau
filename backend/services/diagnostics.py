import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class SchedulingDiagnostics:
    def __init__(self, db):
        self.db = db
        self.report = {
            'pre_validation': {},
            'operations_analysis': [],
            'blocking_reasons': [],
            'solver_info': {},
            'recommendations': []
        }
    
    async def run_pre_validation(self, orders, operations, machines, rules, stocks):
        """
        Phase de validation avant ordonnancement.
        """
        logger.info("=" * 80)
        logger.info("DÉMARRAGE DIAGNOSTIC D'ORDONNANCEMENT")
        logger.info("=" * 80)
        
        # Validation des données importées
        self.report['pre_validation'] = {
            'orders_count': len(orders),
            'operations_count': len(operations),
            'machines_count': len(machines),
            'rules_count': len(rules),
            'stocks_count': len(stocks),
            'has_data': len(orders) > 0 and len(operations) > 0 and len(machines) > 0
        }
        
        logger.info(f"📊 Ordres de fabrication détectés: {len(orders)}")
        logger.info(f"📊 Opérations détectées: {len(operations)}")
        logger.info(f"📊 Machines configurées: {len(machines)}")
        logger.info(f"📊 Règles métier: {len(rules)}")
        logger.info(f"📊 Articles en stock: {len(stocks)}")
        
        # Validation minimale
        if len(orders) == 0:
            self.report['blocking_reasons'].append({
                'type': 'CRITICAL',
                'reason': 'Aucun ordre de fabrication importé',
                'solution': 'Importez des ordres via Import CSV'
            })
            logger.error("❌ BLOQUANT: Aucun ordre de fabrication")
        
        if len(operations) == 0:
            self.report['blocking_reasons'].append({
                'type': 'CRITICAL',
                'reason': 'Aucune opération importée',
                'solution': 'Importez des opérations via Import CSV'
            })
            logger.error("❌ BLOQUANT: Aucune opération")
        
        if len(machines) == 0:
            self.report['blocking_reasons'].append({
                'type': 'CRITICAL',
                'reason': 'Aucune machine configurée',
                'solution': 'Créez des machines dans le référentiel atelier'
            })
            logger.error("❌ BLOQUANT: Aucune machine")
        
        # Analyse des calendriers
        calendars = await self.db.calendars.find({}, {"_id": 0}).to_list(100)
        self.report['pre_validation']['calendars_count'] = len(calendars)
        logger.info(f"📅 Calendriers configurés: {len(calendars)}")
        
        if len(calendars) == 0:
            self.report['blocking_reasons'].append({
                'type': 'WARNING',
                'reason': 'Aucun calendrier configuré',
                'solution': 'Le système utilisera un calendrier par défaut 24/7'
            })
            logger.warning("⚠️  Aucun calendrier - utilisation calendrier par défaut")
        
        return self.report
    
    def analyze_operation_feasibility(self, operation, machines, rules_engine, material_checker, order):
        """
        Analyse de faisabilité pour une opération donnée.
        Utilise task_id, work_center_id et article_id pour le matching des règles.
        """
        analysis = {
            'operation_id': operation.get('id'),
            'task_id': operation.get('task_id'),
            'work_center_id': operation.get('work_center_id'),
            'order_id': operation.get('order_id'),
            'article_id': order.get('article_id') if order else None,
            'is_feasible': True,
            'blocking_reasons': [],
            'warnings': [],
            'compatible_machines': [],
            'material_available': True
        }
        
        # Vérification machine assignée
        assigned_machine = operation.get('machine_id')
        if not assigned_machine:
            analysis['is_feasible'] = False
            analysis['blocking_reasons'].append('Aucune machine assignée à l\'opération')
            logger.warning(f"⚠️  Op {operation.get('id')}: Aucune machine assignée")
        else:
            # Vérifier si la machine existe
            machine_exists = any(m.get('id') == assigned_machine for m in machines)
            if not machine_exists:
                analysis['is_feasible'] = False
                analysis['blocking_reasons'].append(f'Machine {assigned_machine} introuvable')
                logger.error(f"❌ Op {operation.get('id')}: Machine {assigned_machine} n'existe pas")
            else:
                analysis['compatible_machines'].append(assigned_machine)
                logger.info(f"✓ Op {operation.get('id')}: Machine {assigned_machine} trouvée")
        
        # Vérification règles métier (avec le nouveau contexte)
        if assigned_machine:
            # Construire le contexte de matching (sans l'id de l'opération!)
            matching_context = {
                'task_id': operation.get('task_id'),
                'work_center_id': operation.get('work_center_id'),
                'article_id': order.get('article_id') if order else operation.get('article_id')
            }
            
            allowed, reasons, penalty = rules_engine.evaluate_machine_for_operation(
                matching_context, assigned_machine
            )
            
            if not allowed:
                analysis['is_feasible'] = False
                analysis['blocking_reasons'].append(f'Règle métier interdit: {", ".join(reasons)}')
                logger.error(f"❌ Op {operation.get('id')}: {', '.join(reasons)}")
            elif penalty > 0:
                analysis['warnings'].append(f'Pénalité appliquée: {penalty}')
                logger.info(f"⚠️  Op {operation.get('id')}: Pénalité {penalty}")
        
        # Vérification disponibilité matière
        if order:
            article_id = order.get('article_id') or order.get('article')
            quantity = order.get('quantity', 0)
            if not material_checker.check_availability(article_id, quantity):
                analysis['is_feasible'] = False
                analysis['material_available'] = False
                missing = material_checker.get_missing_materials(article_id, quantity)
                analysis['blocking_reasons'].append(
                    f'Matière insuffisante: {article_id} (manque {missing} unités)'
                )
                logger.error(f"❌ Op {operation.get('id')}: Matière insuffisante pour {article_id}")
            else:
                logger.info(f"✓ Op {operation.get('id')}: Matière disponible pour {article_id}")
        
        # Vérification temps de production
        prod_time = operation.get('production_time_minutes', 0)
        setup_time = operation.get('setup_time_minutes', 0)
        if prod_time <= 0 and setup_time <= 0:
            analysis['warnings'].append('Temps de production = 0')
            logger.warning(f"⚠️  Op {operation.get('id')}: Temps de production nul")
        
        return analysis
    
    def analyze_all_operations(self, operations, orders, machines, rules_engine, material_checker):
        """
        Analyse toutes les opérations.
        """
        logger.info("\n" + "="*80)
        logger.info("ANALYSE DE FAISABILITÉ DES OPÉRATIONS")
        logger.info("="*80)
        
        feasible_count = 0
        blocked_count = 0
        
        for op in operations:
            order = next((o for o in orders if o.get('id') == op.get('order_id')), None)
            analysis = self.analyze_operation_feasibility(
                op, machines, rules_engine, material_checker, order
            )
            
            self.report['operations_analysis'].append(analysis)
            
            if analysis['is_feasible']:
                feasible_count += 1
            else:
                blocked_count += 1
                self.report['blocking_reasons'].append({
                    'type': 'OPERATION_BLOCKED',
                    'operation_id': op.get('id'),
                    'reasons': analysis['blocking_reasons']
                })
        
        logger.info(f"\n📊 Résumé analyse opérations:")
        logger.info(f"   ✓ Opérations planifiables: {feasible_count}")
        logger.info(f"   ❌ Opérations bloquées: {blocked_count}")
        
        if blocked_count > 0:
            logger.warning(f"\n⚠️  {blocked_count} opération(s) ne peuvent pas être planifiées")
            logger.warning("Consultez le rapport de diagnostic pour les détails")
        
        self.report['pre_validation']['feasible_operations'] = feasible_count
        self.report['pre_validation']['blocked_operations'] = blocked_count
        
        return feasible_count, blocked_count
    
    def log_solver_input(self, valid_operations, machine_to_intervals, horizon):
        """
        Log des informations envoyées au solveur.
        """
        logger.info("\n" + "="*80)
        logger.info("CONFIGURATION DU SOLVEUR OR-TOOLS CP-SAT")
        logger.info("="*80)
        
        logger.info(f"🔧 Opérations envoyées au solveur: {len(valid_operations)}")
        logger.info(f"🔧 Machines utilisées: {len(machine_to_intervals)}")
        logger.info(f"🔧 Horizon de planification: {horizon} minutes ({horizon/60/24:.1f} jours)")
        
        for machine_id, intervals in machine_to_intervals.items():
            logger.info(f"   Machine {machine_id}: {len(intervals)} opération(s)")
        
        self.report['solver_info'] = {
            'operations_sent': len(valid_operations),
            'machines_used': len(machine_to_intervals),
            'horizon_minutes': horizon,
            'horizon_days': horizon / 60 / 24
        }
    
    def log_solver_result(self, status, scheduled_ops, conflicts, solver_time):
        """
        Log du résultat du solveur.
        """
        logger.info("\n" + "="*80)
        logger.info("RÉSULTAT DU SOLVEUR")
        logger.info("="*80)
        
        logger.info(f"📈 Statut: {status}")
        logger.info(f"📈 Opérations planifiées: {len(scheduled_ops)}")
        logger.info(f"📈 Conflits détectés: {len(conflicts)}")
        logger.info(f"📈 Temps de calcul: {solver_time:.2f}s")
        
        self.report['solver_info']['status'] = status
        self.report['solver_info']['operations_scheduled'] = len(scheduled_ops)
        self.report['solver_info']['conflicts'] = len(conflicts)
        self.report['solver_info']['solver_time'] = solver_time
        
        if len(scheduled_ops) == 0:
            logger.error("\n❌ AUCUNE OPÉRATION PLANIFIÉE")
            if status == 'INFEASIBLE':
                logger.error("   Le problème est INFAISABLE avec les contraintes actuelles")
                self.report['recommendations'].append(
                    'Problème infaisable: vérifiez les contraintes (règles métier, calendriers, machines)'
                )
            elif status == 'MODEL_INVALID':
                logger.error("   Le modèle est INVALIDE")
                self.report['recommendations'].append(
                    'Modèle invalide: contactez le support technique'
                )
        else:
            logger.info(f"\n✓ {len(scheduled_ops)} opération(s) planifiée(s) avec succès")
        
        logger.info("\n" + "="*80)
        logger.info("FIN DU DIAGNOSTIC")
        logger.info("="*80 + "\n")
    
    def get_report(self):
        """Retourne le rapport complet."""
        return self.report