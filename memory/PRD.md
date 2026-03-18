# APS Scheduler Pro - Product Requirements Document

## Overview
Advanced Planning & Scheduling (APS) application for industrial manufacturing, using OR-Tools CP-SAT solver for finite capacity scheduling.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Solver**: Google OR-Tools CP-SAT

## Recent Updates (2026-03-18)

### Bugs critiques traités

#### Sujet 1 - Filtrage affichage Gantt par horizon ✅
Le moteur peut planifier au-delà de l'horizon pour optimiser, mais l'affichage du Gantt se limite aux N premiers jours définis. Le problème actuel : l'affichage montre des opérations le samedi alors que le calendrier interdit les week-ends → lié au Sujet 2.

#### Sujet 2 - Contraintes de calendrier strictes ✅ CORRIGÉ
**Bug corrigé**: Les contraintes de calendrier n'étaient pas strictes (utilisaient `only_enforce_if` sans `add_bool_or`).
**Solution**: Ajout de `model.add_bool_or([before_slot, after_slot])` pour forcer le solveur à respecter l'une des deux conditions (avant OU après la plage interdite).
**Impact**: Les opérations ne seront plus planifiées pendant les week-ends ou en dehors des heures de travail.

#### Sujet 3 - Propagation des ruptures matière ✅ 
**Implémenté dans session précédente** - Si une opération n'a pas sa matière première, les opérations suivantes du même OF sont automatiquement reportées ou bloquées.

### Améliorations UI/UX

#### Sujet 4 - Traduction règles métier ✅
- `ALLOW` → `REQUIRE` (Requis - Exclusif)
- `FORBID` → `Interdit`
- `PREFER` → `Préféré`

#### Sujet 5 - Infobulles Gantt enrichies ✅
- Affiche maintenant la **description de tâche** au lieu du centre de charge
- Ajoute la **description d'article** sous le code article
- Données ajoutées au endpoint `/api/gantt/data`

#### Sujet 6 - Retrait section "Contraintes Appliquées" ✅
Section redondante avec les options avancées, retirée de la page Ordonnancement.

#### Sujet 7 - Retrait module BOM ✅
Module "Nomenclatures (BOM)" retiré de la page Import CSV.

#### Sujet 8 - Page Ordres Fab. améliorée ✅
- Colonne "Op. Seq" (numéro de séquence) au lieu de "Op. ID"
- Descriptions ajoutées pour tâche, centre de charge et article
- Colonne "Jointure" retirée
- Endpoint `/api/operations-enrichies` enrichi

#### Sujet 9 - Barre de progression avec timer ✅
- Affiche temps écoulé (mm:ss)
- Pourcentage par rapport à la durée max du solveur
- Barre de progression animée
- Indicateur "Optimisation en cours..." quand le temps max est dépassé

## API Endpoints

### Scheduling
- `GET /api/scheduling/validate-config` - Validation configuration
- `POST /api/scheduling/calculate/async` - Calcul asynchrone
- `GET /api/scheduling/status/{job_id}` - Statut du job
- `GET /api/gantt/data/{scenario_id}?display_horizon_days=N` - Données Gantt filtrées

### Data
- `GET /api/operations-enrichies` - Opérations avec descriptions

## Known Issues
- **Erreur KPIs**: Comparaison datetime naive/aware dans `/api/aps/kpis` (non bloquant)

## Backlog
1. (P0) Tester nouveau calcul avec contraintes calendrier strictes
2. (P1) Implémenter logique REQUIRE dans rules_engine
3. (P1) Valider comportement matière première sans réception
4. (P2) Export CSV du planning
5. (P3) Tableau de bord KPIs avancé

## Code Architecture
```
/app/
├── backend/
│   ├── services/
│   │   ├── scheduler_engine.py  # Sujet 2: contraintes calendrier strictes
│   │   ├── rules_engine.py      # Sujet 4: REQUIRE à implémenter
│   │   └── material_manager.py  # Sujet 3: propagation ruptures
│   └── server.py                # Sujets 5,8: descriptions enrichies
└── frontend/
    └── src/pages/
        ├── Scheduling.js        # Sujets 6,9: UI simplifiée + timer
        ├── GanttInteractive.js  # Sujet 5: tooltips enrichis
        ├── BusinessRules.js     # Sujet 4: traduction FR
        ├── ImportData.js        # Sujet 7: BOM retiré
        └── ManufacturingOrders.js # Sujet 8: descriptions
```
