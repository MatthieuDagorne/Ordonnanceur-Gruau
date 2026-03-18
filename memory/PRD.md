# APS Scheduler Pro - Product Requirements Document

## Overview
Advanced Planning & Scheduling (APS) application for industrial manufacturing, using OR-Tools CP-SAT solver for finite capacity scheduling.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Solver**: Google OR-Tools CP-SAT

## Recent Updates (2026-03-18)

### SUJET 1: Filtrage de l'affichage du Gantt par horizon - DONE
Le moteur d'ordonnancement peut planifier au-delà de l'horizon demandé pour optimiser, mais l'affichage du Gantt se limite aux N premiers jours définis par l'utilisateur.
- **API**: `GET /api/gantt/data/{scenario_id}?display_horizon_days=N`
- **UI**: Nouveau compteur "Horizon Affiché: X jours" avec indication des opérations au-delà
- **Bénéfices**: Rendu plus rapide, focus sur la période pertinente

### SUJET 2: Maximisation du taux de remplissage - DONE
La fonction objectif du solveur a été améliorée pour maximiser le taux de remplissage des machines.
- **Stratégie ASAP**: Objectif combiné minimisant:
  1. Fins des producteurs critiques (priorité haute)
  2. Somme des temps de démarrage (compaction = meilleur remplissage)
  3. Makespan global
- **Résultat**: Le solveur essaie de compacter les opérations pour éviter les temps morts

### SUJET 3: Propagation des ruptures matière - DONE
Si une opération n'a pas sa matière première disponible, toutes les opérations SUIVANTES du même OF sont automatiquement reportées.
- **Logique**: La chaîne de production est interrompue si un composant manque
- **Alternative**: D'autres opérations peuvent être avancées pour combler les trous
- **Log**: Les propagations sont tracées dans les logs et les diagnostics

### CRITICAL: 0 Operations Bug - RESOLVED
**Root Cause Analysis:**
1. The solver horizon was limited by `horizon_days` parameter, causing `INFEASIBLE` when operations couldn't fit
2. The fix: Horizon is now a **FILTER on orders**, not a constraint on the solver's planning domain
3. The solver horizon is always at least 30 days to accommodate all operations

**Current Status:** WORKING
- Test with 2562 operations: **FEASIBLE** in reasonable time
- Test with 1494 operations: **FEASIBLE** - 1286 affichées dans horizon 14j, 208 au-delà

### UI Improvements
- **Work Centers page**: Sorted by ascending code
- **Machines page**: 
  - Sorted by work center then by machine ID
  - Filters: work center dropdown (sorted), machine search
  - Counter showing filtered results
- **Horizon input**: Manual numeric input (not dropdown) allowing 1, 2, 3... days
- **Gantt stats**: Nouveau panneau "Horizon Affiché" avec compteur des opérations au-delà

### Configuration Validation
- Pre-scheduling validation via `/api/scheduling/validate-config`
- Blocking errors: Work centers without machines
- Warnings: Work centers without calendars

## API Endpoints

### Scheduling
- `GET /api/scheduling/validate-config` - Validate configuration before scheduling
- `POST /api/scheduling/calculate/async` - Start async calculation
- `GET /api/scheduling/status/{job_id}` - Poll calculation status
- `GET /api/gantt/data/{scenario_id}?display_horizon_days=N` - Get Gantt data with optional display filter

### Data Parameters
```json
{
  "scenario_name": "string",
  "scheduling_strategy": "ASAP|JIT",
  "horizon_days": 7,  // Filter on orders, 0 = all
  "max_solver_time_seconds": 60,
  "ignore_calendars": true,  // Recommended for large datasets
  "ignore_material": false
}
```

## Test Results (2026-03-18)
- **1494 operations**: FEASIBLE ✅
  - 1286 affichées dans horizon 14j
  - 208 planifiées au-delà (optimisation du solveur)
  - Taux de remplissage optimisé

## Known Limitations
- Very large datasets (7000+ ops) with calendars may still cause INFEASIBLE
- Recommendation: Use shorter horizon (7-14 days) or disable calendars for initial planning

## Backlog
1. (P0) Implémenter la règle REQUIRE (obligatoire/exclusive) - EN ATTENTE
2. (P1) Utiliser les attributs d'articles dans les règles métier
3. (P1) Optimize calendar constraints for large datasets
4. (P2) Create business rules using article attributes
5. (P3) Export CSV for finalized planning

## Code Architecture
```
/app/
├── backend/
│   ├── services/
│   │   ├── scheduler_engine.py  # Moteur principal - Sujet 2 (remplissage) et Sujet 3 (propagation matière)
│   │   ├── machine_assigner.py  # Assignation des machines
│   │   ├── rules_engine.py      # Règles métier (REQUIRE en attente)
│   │   └── material_manager.py  # Gestion matières et stock projeté
│   └── server.py                # Sujet 1 (filtrage Gantt par horizon)
└── frontend/
    └── src/pages/
        └── GanttInteractive.js  # Affichage Gantt avec indicateur horizon
```
