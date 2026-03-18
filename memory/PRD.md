# APS Scheduler Pro - Product Requirements Document

## Overview
Advanced Planning & Scheduling (APS) application for industrial manufacturing, using OR-Tools CP-SAT solver for finite capacity scheduling.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Solver**: Google OR-Tools CP-SAT

## Recent Updates (2026-03-18)

### BUG CRITIQUE RÉSOLU: Stock projeté - Opérations marquées "non planifié" à tort

**Problème**: Dans la section "Stock projeté" du scénario, toutes les opérations apparaissaient comme "non planifié" même si elles étaient réellement planifiées. Cela faussait les consommations horodatées et donc les calculs de stock projeté.

**Cause identifiée**:
- Le code utilisait `mat.get('id')` pour récupérer l'ID de l'opération
- Mais dans `operation_materials`, l'ID est dans `mat.get('operation_id')` (format: `LV1139402_10`)
- La jointure avec les opérations planifiées échouait systématiquement

**Correction**:
```python
# AVANT (bugué)
op_id = mat.get('id')

# APRÈS (corrigé)
op_id = mat.get('operation_id') or mat.get('id')
```

**Fichiers corrigés**:
- `backend/server.py` lignes ~842 et ~1102

**Résultat validé**:
- Opération LV1139402_10 pour article 0157041: ✅ Planifiée au 19/03/2026 14:00
- Timeline stock projeté: 9 consommations planifiées au lieu de 0

### BUG CRITIQUE RÉSOLU: Opérations planifiées le week-end

**Problème**: Des opérations étaient planifiées samedi/dimanche malgré le calendrier Lun-Ven.

**Causes et corrections**:
1. Convention jours 1-7 (frontend) vs 0-6 (Python) → Conversion `d-1`
2. Horizon contraintes calendrier 21 jours → Étendu à `max(30, horizon_solveur + 7)`
3. Contraintes booléennes non strictes → Ajout `add_bool_or()`

**Résultat validé**: 822 opérations planifiées, **0 le week-end** ✅

### Améliorations UI (Sujets 4-9)

| Sujet | Description | Statut |
|-------|-------------|--------|
| 4 | Traduction règles métier FR (REQUIRE/Interdit/Préféré) | ✅ |
| 5 | Tooltips Gantt enrichis (description tâche + article) | ✅ |
| 6 | Section "Contraintes Appliquées" retirée | ✅ |
| 7 | Module BOM retiré de l'import | ✅ |
| 8 | Page Ordres Fab. avec Op. Seq et descriptions | ✅ |
| 9 | Barre de progression avec timer (mm:ss + %) | ✅ |

## Tests validés

| Test | Résultat |
|------|----------|
| Calendrier: 0 ops week-end | ✅ PASS |
| Stock projeté: ops horodatées | ✅ PASS |
| LV1139402_10 planifié 19/03 14h | ✅ PASS |

## Backlog
1. (P0) Implémenter la règle REQUIRE dans rules_engine
2. (P1) Valider comportement matière première sans réception (0157042)
3. (P2) Export CSV du planning
