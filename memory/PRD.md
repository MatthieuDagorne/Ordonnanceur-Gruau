# APS Scheduler Pro - Product Requirements Document

## Overview
Advanced Planning & Scheduling (APS) application for industrial manufacturing, using OR-Tools CP-SAT solver for finite capacity scheduling.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Solver**: Google OR-Tools CP-SAT

## Recent Updates (2026-03-18)

### BUG CRITIQUE RÉSOLU: Opérations planifiées le week-end

**Problème**: Les opérations étaient planifiées les samedis et dimanches malgré le calendrier configuré pour Lundi-Vendredi.

**Causes identifiées et corrigées**:

1. **Convention de jours incorrecte** (CORRIGÉ)
   - Le frontend utilisait 1-7 (1=Lundi, 7=Dimanche)
   - Le backend Python `weekday()` utilise 0-6 (0=Lundi, 6=Dimanche)
   - **Fix**: Conversion `d-1` pour transformer 1-7 en 0-6

2. **Horizon de contraintes trop court** (CORRIGÉ)
   - Les contraintes de calendrier ne couvraient que 21 jours
   - Les opérations au-delà étaient planifiées sans contrainte
   - **Fix**: Étendre l'horizon des contraintes à `max(30, horizon_du_solveur + 7)`

3. **Contraintes booléennes inefficaces** (CORRIGÉ)
   - Utilisation de `only_enforce_if()` sans `add_bool_or()` ne garantissait pas le respect
   - **Fix**: Ajout de `model.add_bool_or([before_slot, after_slot])` pour forcer l'une des deux conditions

**Résultat validé**:
- Test avec 822 opérations: **0 opérations le week-end** ✅
- Les contraintes de calendrier sont maintenant strictement respectées

### Autres améliorations (Sujets 4-9)

- **Sujet 4**: Traduction règles métier FR (REQUIRE/Interdit/Préféré)
- **Sujet 5**: Tooltips Gantt enrichis (description tâche + article)
- **Sujet 6**: Section "Contraintes Appliquées" retirée
- **Sujet 7**: Module BOM retiré de l'import
- **Sujet 8**: Page Ordres Fab. avec Op. Seq et descriptions
- **Sujet 9**: Barre de progression avec timer (mm:ss + %)

## Fichiers modifiés (session actuelle)

### Backend
- `backend/services/scheduler_engine.py`:
  - Conversion jours calendrier 1-7 → 0-6
  - Extension horizon contraintes calendrier
  - Ajout `add_bool_or()` pour contraintes strictes
  - Flag `is_split` dans intervals_data

- `backend/server.py`:
  - Enrichissement endpoint Gantt (tache_description, article_description)
  - Enrichissement endpoint operations-enrichies

### Frontend
- `frontend/src/pages/Scheduling.js`: Timer progression
- `frontend/src/pages/GanttInteractive.js`: Tooltips enrichis
- `frontend/src/pages/BusinessRules.js`: Traduction FR
- `frontend/src/pages/ImportData.js`: BOM retiré
- `frontend/src/pages/ManufacturingOrders.js`: Descriptions + Op.Seq

## Tests validés

| Scénario | Ops | Week-end | Statut |
|----------|-----|----------|--------|
| Test_Calendar_Fix_V3 | 822 | 0 | ✅ PASS |

## Backlog
1. (P0) Implémenter la règle REQUIRE dans rules_engine
2. (P1) Valider comportement matière première sans réception (0157042)
3. (P2) Export CSV du planning
