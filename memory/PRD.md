# APS Scheduler Pro - Product Requirements Document

## Overview
Advanced Planning & Scheduling (APS) application for industrial manufacturing, using OR-Tools CP-SAT solver for finite capacity scheduling.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Solver**: Google OR-Tools CP-SAT

## Recent Fixes (2026-03-18)

### CRITICAL: 0 Operations Bug - RESOLVED
**Root Cause Analysis:**
1. The solver horizon was limited by `horizon_days` parameter, causing `INFEASIBLE` when operations couldn't fit
2. The fix: Horizon is now a **FILTER on orders**, not a constraint on the solver's planning domain
3. The solver horizon is always at least 30 days to accommodate all operations

**Current Status:** WORKING
- Test with 2562 operations: **FEASIBLE** in reasonable time
- Test with 1418 operations: **FEASIBLE**

### UI Improvements
- **Work Centers page**: Sorted by ascending code
- **Machines page**: 
  - Sorted by work center then by machine ID
  - Filters: work center dropdown (sorted), machine search
  - Counter showing filtered results
- **Horizon input**: Manual numeric input (not dropdown) allowing 1, 2, 3... days

### Configuration Validation
- Pre-scheduling validation via `/api/scheduling/validate-config`
- Blocking errors: Work centers without machines
- Warnings: Work centers without calendars

## API Endpoints

### Scheduling
- `GET /api/scheduling/validate-config` - Validate configuration before scheduling
- `POST /api/scheduling/calculate/async` - Start async calculation
- `GET /api/scheduling/status/{job_id}` - Poll calculation status

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
- **2562 operations, no calendars**: FEASIBLE ✅
- **1418 operations**: FEASIBLE ✅

## Known Limitations
- Very large datasets (7000+ ops) with calendars may still cause INFEASIBLE
- Recommendation: Use shorter horizon (7-14 days) or disable calendars for initial planning

## Backlog
1. (P1) Optimize calendar constraints for large datasets
2. (P2) Create business rules using article attributes
3. (P3) Export CSV for finalized planning
