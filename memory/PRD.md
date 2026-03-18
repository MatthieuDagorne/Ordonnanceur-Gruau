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

### Scheduling Engine (Completed)
- Finite capacity scheduling with NoOverlap constraints
- Material availability checking with projected stock
- Calendar constraints for working hours
- Priority propagation between dependent orders
- Asynchronous calculation to avoid proxy timeouts

### Horizon Planning (NEW - Completed 2026-03-18)
- `horizon_days` parameter to limit optimization scope
- Automatic inclusion of:
  - Orders within planning horizon
  - Late orders (past due date)
  - Dependency orders (required for material feasibility)
- Significant performance improvement for large datasets

### Operation Splitting (NEW - Completed 2026-03-18)
- Automatic splitting of long operations (> daily working hours)
- Creates sub-operations (OP_PART1, OP_PART2, etc.)
- Respects sequence constraints between parts
- Only active when calendars are enabled

### Gantt Visualization (Completed)
- Interactive Gantt chart with zoom/pan
- Color coding by machine/center
- Tooltips with operation details
- Conflict highlighting (material, late, urgent)

### Diagnostic & Statistics (Completed)
- Detailed scheduling statistics
- Horizon filtering breakdown (in_horizon, late, dependency)
- Split statistics (operations split, sub-operations created)
- Machine utilization metrics
- Blocked operation reasons

## API Endpoints

### Scheduling
- `POST /api/scheduling/calculate/async` - Start async calculation
- `GET /api/scheduling/status/{job_id}` - Poll calculation status
- `DELETE /api/scenarios/all` - Delete all scenarios

### Data Parameters
```json
{
  "scenario_name": "string",
  "scheduling_strategy": "ASAP|JIT",
  "horizon_days": 14,
  "max_solver_time_seconds": 60,
  "ignore_calendars": false,
  "ignore_material": false,
  "allow_splitting": true
}
```

## Test Results (2026-03-18)
- **7 days horizon, no calendars**: 3077 ops scheduled in 14.75s (FEASIBLE)
- **Performance gain**: From timeout/UNKNOWN to FEASIBLE in seconds

## Known Limitations
- With calendars enabled, 76K+ constraints can cause UNKNOWN status
- Recommendation: Use shorter horizon (7 days) for large datasets with calendars

## Backlog
1. (P1) Import `articles.csv` when available
2. (P2) Operation splitting with calendars (currently limited impact)
3. (P3) Export CSV for finalized planning
4. (P3) Firm horizon implementation
5. (P3) Advanced KPI dashboard
