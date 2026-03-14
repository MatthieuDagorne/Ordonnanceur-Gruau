# APS Scheduler Pro - PRD

## Énoncé du Problème
Application web APS (Advanced Planning & Scheduling) pour l'ordonnancement industriel d'un site de production.

## Architecture Technique
- **Backend**: Python FastAPI
- **Frontend**: React
- **Base de données**: MongoDB
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)
- **Module APS**: BOM, MRP, Capacité finie

## Fonctionnalités APS Implémentées

### 1. Page Ordonnancement APS Complète ✅ (14 mars 2026)

#### Modes de Priorité
- **Priorité Date de Besoin** : Minimise les retards en priorisant les dates dues
- **Priorité Disponibilité Matière** : Planifie dès que les composants sont disponibles
- **Mode Équilibré** : Optimise selon les poids définis (sliders)

#### Poids de Priorité (Mode Équilibré)
- Date de besoin (0-100)
- Disponibilité matière (0-100)
- Minimiser temps de setup (0-100)

#### Paramètres du Solveur
- **Durée Maximum d'Optimisation** : 30s, 1min, 2min, 5min, 10min
- **Gap d'Optimalité** : 1-20% (arrête si solution à moins de X% de l'optimum)

#### Options Avancées (collapsibles)
- Ignorer les règles métier
- Ignorer la disponibilité matière
- Ignorer les calendriers machines
- Respecter l'ordre des opérations dans l'OF

#### Contraintes Appliquées (indicateurs visuels)
- Règles métier d'affectation
- Disponibilité matière
- Calendriers machines
- Capacité finie (non-chevauchement)
- Séquence des gammes
- production_time + setup_time

### 2. Dashboard APS avec KPIs ✅
- **OTD (On-Time Delivery)** : % des ordres livrés à temps
- **Ordres en Retard** : Liste avec délai en heures
- **Utilisation Machines** : Capacité vs Charge (7 jours)
- **WIP** : Ordres en cours et opérations planifiées

### 3. Capacité Finie avec Calendriers ✅
- **production_time_minutes + setup_time_minutes** : Pris en compte pour la charge
- **Calendriers par centre de charge** : Heures de travail par jour
- **Barres de capacité** : Visualisation charge/capacité par machine

### 4. Planification Multi-Niveaux (BOM/MRP) ✅
- **Import BOM** : `parent_article_id, child_article_id, quantity, level, scrap_rate`
- **Explosion de nomenclature** : Multi-niveaux avec taux de rebut
- **Calcul MRP** : Besoins bruts, stock disponible, besoins nets
- **Dates de consommation** : Basées sur `scheduled_start` de l'ordonnanceur

### 5. Édition des Règles Métier ✅
- **PUT /api/rules/{id}** : Modifier une règle existante
- **Interface UI** : Bouton éditer avec formulaire pré-rempli

### 6. Règles Métier sur Attributs ✅
- **Attributs articles** : `largeur`, `epaisseur`, `couleur`, `type_matiere`, `longueur`
- **Opérateurs** : GT, GE, LT, LE, EQ, NE, IN, NOT_IN

## API Ordonnancement

### POST /api/scheduling/calculate
```json
{
  "scenario_name": "Planning Semaine 12",
  "priority_mode": "balanced",
  "due_date_weight": 100,
  "material_weight": 50,
  "setup_time_weight": 20,
  "max_solver_time_seconds": 60,
  "optimization_gap": 0.05,
  "ignore_rules": false,
  "ignore_material": false,
  "ignore_calendars": false,
  "respect_sequence": true
}
```

### Réponse
```json
{
  "status": "completed",
  "scenario_id": "uuid",
  "result": {
    "status": "OPTIMAL",
    "operations": [...],
    "solver_time": 0.08
  }
}
```

## Validation (14 mars 2026)

### Tests Backend: 22/22 PASSED
- Tous les modes de priorité acceptés
- Tous les paramètres de poids acceptés
- Durées max 30s à 600s acceptées
- Gap d'optimalité 1-20% accepté
- Options avancées fonctionnelles

### Tests Frontend: 100% PASSED
- 3 modes de priorité sélectionnables
- Sliders de poids visibles en mode équilibré
- Dropdown durée avec 5 options
- Section Options Avancées collapsible
- Indicateurs visuels des contraintes

## Backlog

### P1 - Prioritaires
- [ ] Simulation "What-if" - Dupliquer et comparer des scénarios
- [ ] Alertes en temps réel sur retards et ruptures
- [ ] Persister les assignations en BDD après ordonnancement

### P2 - Secondaires
- [ ] Replanification dynamique (réaction aux aléas)
- [ ] Intégration ERP bidirectionnelle
- [ ] Export planning CSV enrichi

### P3 - Futurs
- [ ] Gantt interactif avec drag-and-drop
- [ ] Optimisation multi-objectifs avancée
- [ ] Dashboard temps réel avec WebSockets
