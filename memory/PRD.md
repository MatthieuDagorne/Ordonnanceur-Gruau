# APS Scheduler Pro - PRD

## Énoncé du Problème
Application web APS (Advanced Planning & Scheduling) pour l'ordonnancement industriel avec capacité finie, règles métier avancées et fonctionnalités MRP.

## Architecture Technique
- **Backend**: Python FastAPI + MongoDB
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)
- **Design System**: Thème clair/sombre avec variables CSS

## Fonctionnalités Implémentées

### Phase 1-4 - Fondations et APS ✅
- Calendriers par centre de charge
- Règles métier avec logique ET/OU
- Page Ordonnancement avec scénarios
- Vue Matricielle, Comparaison de Scénarios
- Gantt Interactif, Stock Projeté Avancé

### Phase 5 - Améliorations Ergonomiques (14 mars 2026) ✅
- Calendriers en quarts d'heure (HH:MM)
- État des données complet (ERP, Supply Chain, Configuration)
- Filtres intelligents sur 4 pages

### Phase 6 - UI Uniformisation + CRUD Edit (14 mars 2026) ✅
- **Machines**: Variables CSS, rounded-lg, PUT /api/machines/{id}
- **Centres de Charge**: Variables CSS, rounded-lg, PUT existant
- **Indisponibilités**: Variables CSS, rounded-lg, PUT /api/unavailability/{id}
- **Tests**: Backend 17/17 (100%), Frontend 10/10 (100%)

### Phase 7 - Améliorations Gantt (14 mars 2026) ✅

#### 1. Infobulles Enrichies
- Affichage du centre de charge
- Section "Matières premières" avec disponibilité en stock
- Format: `{article_id}: {in_stock} / {needed} ✓/✗`
- Indicateur visuel (badge orange) pour matière manquante

#### 2. Axe Temporel Absolu
- Remplacement de "+1h, +2h" par dates réelles
- Format: "14 mars, 14:55", "14 mars, 15:55"
- Basé sur `scheduling_start` du scénario

#### 3. Périodes de Fermeture
- Zones grisées pour les horaires hors travail
- Calculées à partir des calendriers (start_time/end_time)
- Légende "Hors horaires" ajoutée

#### 4. Filtre par Centre de Charge
- Boutons de filtre pour chaque centre
- Sélection multiple possible
- Compteur de machines filtrées (X / Y)
- Bouton "Réinitialiser" pour effacer les filtres

## APIs Principales

### Gantt Data Enrichi (mis à jour)
```json
GET /api/gantt/data/{scenario_id}
{
  "scenario_id": "...",
  "scenario_name": "...",
  "scheduling_start": "2026-03-14T14:55:00",
  "machines": [{
    "machine_id": "...",
    "centre_de_charge_id": "LVC002",
    "centre_de_charge_nom": "PLIAGE",
    "tasks": [{
      "operation_id": "...",
      "centre_de_charge_nom": "PLIAGE",
      "materials": [{
        "article_id": "...",
        "needed": 5,
        "in_stock": 10,
        "available": true
      }],
      "materials_ok": true,
      "materials_count": 1
    }]
  }],
  "centres_de_charge": [
    {"id": "LVC001", "nom": "POINCONNAGE"},
    {"id": "LVC002", "nom": "PLIAGE"}
  ],
  "calendars": [{
    "id": "...",
    "name": "Horaires Usine",
    "start_time": "08:00",
    "end_time": "17:00"
  }]
}
```

## Backlog

### P3 - À Faire
- [ ] Export CSV du planning
- [ ] Dashboard temps réel WebSockets
- [ ] Replanification dynamique
- [ ] Multi-sites
- [ ] Horizon ferme (geler planning court terme)

## Fichiers Modifiés (Phase 7)

```
backend/
├── server.py                     # Endpoint /gantt/data enrichi avec matières, centres, calendriers

frontend/src/pages/
├── GanttInteractive.js           # Filtres, axe temporel absolu, infobulles enrichies, zones fermeture
```

## Tests Reports
- `/app/test_reports/iteration_11.json` - Validation P0/P1 (100% pass)
