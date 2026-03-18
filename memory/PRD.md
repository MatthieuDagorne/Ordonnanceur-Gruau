# APS Scheduler Pro - Product Requirements Document

## Overview
Advanced Planning & Scheduling (APS) application for industrial manufacturing, using OR-Tools CP-SAT solver for finite capacity scheduling.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Solver**: Google OR-Tools CP-SAT

## Core Features

### Data Import (Completed)
- CSV import for operations, orders, machines, stocks
- Automatic center creation from operations
- ERP data transformation
- **Articles.csv import** with material, thickness, width, length, color attributes (3104 articles)

### Scheduling Engine (FIXED 2026-03-18)
- Finite capacity scheduling with NoOverlap constraints
- Material availability checking with projected stock
- Calendar constraints for working hours
- Priority propagation between dependent orders
- Asynchronous calculation to avoid proxy timeouts
- **CRITICAL FIX**: Horizon du solveur maintenant indépendant du filtre d'horizon utilisateur

### Horizon Planning (FIXED 2026-03-18)
- `horizon_days` parameter with **manual numeric input** (1, 2, 3... jours)
- Horizon = **FILTRE sur les ordres**, pas sur la durée du planning
- Le solveur peut planifier au-delà de J+horizon si nécessaire
- Automatic inclusion of: Late orders, Dependency orders
- **VALIDATED**: Horizon 7j = 3204 ops in 10.99s (FEASIBLE)

### Configuration Validation (NEW 2026-03-18)
- Pre-scheduling validation via `/api/scheduling/validate-config`
- **Blocking errors**: Work centers without machines
- **Warnings**: Work centers without calendars
- Visual alert in scheduling UI before launch

### UI Improvements (2026-03-18)
- **Work Centers page**: Sorted by ascending code
- **Machines page**: 
  - Sorted by work center then by machine ID
  - Filters: work center dropdown (sorted), machine search
  - Counter showing filtered results

### Gantt Visualization (Completed)
- Interactive Gantt chart with zoom/pan
- Color coding by machine/center
- Tooltips with operation details
- Conflict highlighting (material, late, urgent)

## API Endpoints

### Scheduling
- `GET /api/scheduling/validate-config` - Validate configuration before scheduling
- `POST /api/scheduling/calculate/async` - Start async calculation
- `GET /api/scheduling/status/{job_id}` - Poll calculation status
- `DELETE /api/scenarios/all` - Delete all scenarios

### Data Parameters
```json
{
  "scenario_name": "string",
  "scheduling_strategy": "ASAP|JIT",
  "horizon_days": 7,  // Filter on orders to include, 0 = all
  "max_solver_time_seconds": 90,
  "ignore_calendars": false,
  "ignore_material": false
}
```

## Test Results (2026-03-18)
- **Horizon 7j, no calendars**: 3204 ops in 10.99s (FEASIBLE)
- **Previous INFEASIBLE bug**: FIXED (horizon was limiting solver domain)
- **Config validation**: Working (validates centers/machines/calendars)

## Known Issues (RESOLVED)
- ~~0 operations scheduled~~ → Fixed by separating horizon filter from solver domain

## Backlog
1. (P1) Validate calculation WITH calendars active
2. (P2) Create business rules using article attributes
3. (P3) Export CSV for finalized planning
4. (P3) Firm horizon implementation
