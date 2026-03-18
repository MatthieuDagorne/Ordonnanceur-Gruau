# APS Scheduler Pro - Product Requirements Document

## Overview
Advanced Planning & Scheduling (APS) application for industrial manufacturing, using OR-Tools CP-SAT solver for finite capacity scheduling.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Solver**: Google OR-Tools CP-SAT

## Recent Updates (2026-03-18)

### BUG CRITIQUE RÉSOLU: Opérations planifiées malgré stock projeté négatif

**Problème**: Des opérations consommant l'article 0157042 étaient planifiées même quand le stock projeté à leur date était négatif (106 opérations avec stock négatif).

**Causes identifiées et corrigées**:

1. **`get_projected_stock` utilisait un total global au lieu des mouvements horodatés**
   - Le code soustrayait `planned_consumptions[article_id]` (total cumulé de TOUTES les réservations)
   - **Fix**: Parcourir `self.movements` et ne compter que les consommations AVANT la date demandée

2. **Les IDs d'opérations n'étaient pas correctement mappés**
   - Le code utilisait `mat.get('id')` au lieu de `mat.get('operation_id')`
   - **Fix**: `op_id = mat.get('operation_id') or mat.get('id')`

**Code corrigé** (`material_manager.py`):
```python
def get_projected_stock(self, article_id, at_date):
    stock = self.initial_stocks.get(article_id, 0)
    # + réceptions avant at_date
    # + productions avant at_date
    
    # CORRECTION: Parcourir les mouvements horodatés
    for movement in self.movements:
        if movement.article_id == article_id and movement.movement_type == 'CONSUMPTION':
            if _normalize_datetime(movement.date) <= at_date:
                stock -= abs(movement.quantity)
    return stock
```

**Résultat validé**:
- Article 0157042 : **10 opérations planifiées, 0 avec stock négatif** ✅
- Avant correction : 106 opérations avec stock négatif

### BUG CRITIQUE RÉSOLU: Opérations planifiées le week-end
- Cause: Convention jours 1-7 vs 0-6, horizon contraintes 21j
- Fix: Conversion jours, extension horizon, `add_bool_or()`
- Résultat: 0 opérations le week-end ✅

### BUG CRITIQUE RÉSOLU: Stock projeté - Opérations marquées "non planifié"
- Cause: Mauvais mapping `mat.get('id')` vs `mat.get('operation_id')`
- Fix: `op_id = mat.get('operation_id') or mat.get('id')`
- Résultat: Timeline correctement horodatée ✅

### Améliorations UI (Sujets 4-9)
- Traduction règles métier FR
- Tooltips Gantt enrichis
- Barre de progression avec timer
- Page Ordres Fab. avec descriptions

## Tests validés

| Test | Avant | Après | Statut |
|------|-------|-------|--------|
| Article 0157042 stock négatif | 106 ops | 0 ops | ✅ PASS |
| Calendrier week-end | Ops samedi | 0 ops | ✅ PASS |
| Stock projeté horodaté | Non planifié | Planifié | ✅ PASS |

## Backlog
1. (P0) Implémenter la règle REQUIRE dans rules_engine
2. (P2) Export CSV du planning
