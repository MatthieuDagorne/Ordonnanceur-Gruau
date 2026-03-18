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
- **NEW: Articles.csv import** with material, thickness, width, length, color attributes

### Scheduling Engine (Completed)
- Finite capacity scheduling with NoOverlap constraints
- Material availability checking with projected stock
- Calendar constraints for working hours
- Priority propagation between dependent orders
- Asynchronous calculation to avoid proxy timeouts

### Horizon Planning (UPDATED 2026-03-18)
- `horizon_days` parameter with **manual numeric input** (not dropdown)
- **STRICT enforcement**: Operations "in horizon" are constrained to END within J+horizon
- Automatic inclusion of:
  - Orders within planning horizon → Must finish within horizon
  - Late orders (past due date) → Can extend beyond horizon if needed
  - Dependency orders (for material feasibility) → Can extend beyond horizon if needed
- **Performance validated**: 14j horizon = 4668 ops in 13.74s (FEASIBLE)

### Operation Splitting (Completed)
- Automatic splitting of long operations (> daily working hours)
- Creates sub-operations (OP_PART1, OP_PART2, etc.)
- Only active when calendars are enabled

### Gantt Visualization (Completed)
- Interactive Gantt chart with zoom/pan
- Color coding by machine/center
- Tooltips with operation details
- Conflict highlighting (material, late, urgent)

### Diagnostic & Statistics (Completed)
- Detailed scheduling statistics
- Horizon filtering breakdown (in_horizon, late, dependency)
- Split statistics
- Machine utilization metrics
- Blocked operation reasons

## API Endpoints

### Scheduling
- `POST /api/scheduling/calculate/async` - Start async calculation
- `GET /api/scheduling/status/{job_id}` - Poll calculation status
- `DELETE /api/scenarios/all` - Delete all scenarios

### Data Import
- `POST /api/import/articles` - Import articles.csv (ERP format supported)
- `POST /api/import/operations` - Import operations
- `POST /api/import/manufacturing-orders` - Import orders

### Data Parameters
```json
{
  "scenario_name": "string",
  "scheduling_strategy": "ASAP|JIT",
  "horizon_days": 14,  // 0 = all orders
  "max_solver_time_seconds": 60,
  "ignore_calendars": false,
  "ignore_material": false,
  "allow_splitting": true
}
```

## Test Results (2026-03-18)
- **Horizon 14j, no calendars**: 4668 ops in 13.74s (FEASIBLE)
- **Planning range**: 12 days (respects horizon constraint)
- **Articles imported**: 3104 articles with attributes

## Data Model - Articles
```json
{
  "id": "U01073350",
  "article_id": "U01073350", 
  "name": "Article 1",
  "article_label": "Article 1",
  "material": "Acier",
  "thickness": 0.05,
  "length": 500,
  "width": 1050,
  "color": "Gris"
}
```

## Known Limitations
- With calendars enabled, constraint count can cause UNKNOWN status for large datasets
- Recommendation: Use shorter horizon (7-14 days) or disable calendars for initial tests

## Backlog
1. (P1) Validate operation splitting with calendars active
2. (P2) Create business rules using article attributes (material, thickness, etc.)
3. (P3) Export CSV for finalized planning
4. (P3) Firm horizon implementation
5. (P3) Advanced KPI dashboard
