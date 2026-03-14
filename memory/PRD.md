# APS Scheduler Pro - PRD

## Énoncé du Problème
Application web APS (Advanced Planning & Scheduling) pour l'ordonnancement industriel avec capacité finie, règles métier avancées et fonctionnalités MRP.

## Architecture Technique
- **Backend**: Python FastAPI + MongoDB
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)
- **Design System**: Thème clair/sombre avec variables CSS

## Fonctionnalités Implémentées

### Phase 1-5 - Fondations et APS ✅
- Calendriers par centre de charge avec horaires personnalisables
- Règles métier avec logique ET/OU
- Vue Matricielle, Comparaison de Scénarios
- Gantt Interactif, Stock Projeté Avancé
- Filtres intelligents sur toutes les pages

### Phase 6 - UI Uniformisation + CRUD Edit (14 mars 2026) ✅
- Machines, Centres de Charge, Indisponibilités : Design moderne + boutons Modifier
- Tests: Backend 17/17 (100%), Frontend 10/10 (100%)

### Phase 7 - Améliorations Gantt + Correction Calendriers (14 mars 2026) ✅

#### Améliorations Gantt
| Fonctionnalité | Description |
|----------------|-------------|
| Infobulles enrichies | Section "Matières premières" avec disponibilité stock |
| Axe temporel absolu | Dates réelles (ex: "16 mars, 08:01") au lieu de "+1h" |
| Périodes de fermeture | Zones grisées "Hors horaires" basées sur calendriers |
| Filtre Centre de Charge | Boutons de filtre multi-sélection + compteur machines |

#### Correction Bug Critique Calendriers ✅
**Problème résolu**: Les opérations étaient planifiées en dehors des heures de travail du calendrier.

**Corrections apportées**:
1. `scheduling_start` arrondi à la minute supérieure (évite les microsecondes)
2. Calcul des zones interdites avec `math.ceil()` pour être conservateur
3. **Zone interdite immédiate**: Si l'ordonnancement démarre après l'heure de fermeture ou avant l'ouverture, une zone interdite est créée de t=0 jusqu'au prochain créneau de travail
4. Fusion des plages interdites qui se chevauchent

**Résultat**: Toutes les opérations sont maintenant strictement planifiées entre les heures d'ouverture et de fermeture définies dans les calendriers (ex: 08:00-17:00).

## APIs Principales

### Gantt Data Enrichi
```json
GET /api/gantt/data/{scenario_id}
{
  "scheduling_start": "2026-03-14T18:19:00",
  "machines": [{
    "machine_id": "...",
    "centre_de_charge_id": "...",
    "tasks": [{
      "materials": [{"article_id": "...", "needed": 5, "in_stock": 10, "available": true}],
      "materials_ok": true
    }]
  }],
  "centres_de_charge": [{"id": "...", "nom": "..."}],
  "calendars": [{"start_hour": 8, "end_hour": 17, "working_days": [0,1,2,3,4,5]}]
}
```

## Backlog

### P3 - À Faire
- [ ] Export CSV du planning
- [ ] Horizon ferme (geler planning court terme)
- [ ] Dashboard temps réel WebSockets
- [ ] Replanification dynamique

## Fichiers Modifiés (Phase 7)

```
backend/
├── services/scheduler_engine.py  # Correction critique: zones interdites calendrier

frontend/src/pages/
├── GanttInteractive.js           # Filtres, axe temporel, infobulles, zones fermeture
```

## Tests Reports
- `/app/test_reports/iteration_11.json` - Validation P0/P1 (100% pass)
