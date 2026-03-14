# APS Scheduler Pro - PRD

## Énoncé du Problème
Application web APS (Advanced Planning & Scheduling) pour l'ordonnancement industriel avec capacité finie, règles métier avancées et fonctionnalités MRP.

## Architecture Technique
- **Backend**: Python FastAPI + MongoDB
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)
- **Design System**: Thème clair/sombre avec variables CSS

## Fonctionnalités Implémentées

### Phase 1 - Fondations ✅
- Calendriers par centre de charge
- Page stock projeté
- Extension attributs articles (type_matière, épaisseur, largeur, etc.)
- Règles métier sur attributs

### Phase 2 - Règles Avancées ✅
- Édition CRUD complète des règles
- Logique ET/OU dans les conditions
- Groupes de conditions multiples
- Opérateurs avancés (GT, GE, LT, LE, EQ, NE, IN, NOT_IN)

### Phase 3 - Transformation APS ✅
- Page Ordonnancement avec scénarios
- Options de priorité (Date, Matière, Équilibré)
- Paramètres solveur (durée, gap optimalité)
- Dashboard APS avec KPIs

### Phase 4 - P1/P2 Features (14 mars 2026) ✅

#### Vue Matricielle Compatibilités (/matrix)
- Affichage matrice machines × tâches
- Indicateurs visuels : Autorisé, Interdit, Préféré, Compatible, Incompatible
- Légende explicative
- Statistiques (8 machines, 4 tâches, 5 règles, 32 combinaisons)

#### Comparaison de Scénarios (/scenarios)
- Sélection multiple de scénarios (checkboxes)
- Bouton "Comparer" dynamique (2+ sélections)
- Modal de comparaison avec :
  - Indicateurs "Best" : Moins de conflits, Plus court, Moins de retards, Plus rapide
  - Tableau comparatif : opérations, conflits, makespan, retards, machines, temps calcul
  - Trophées pour les meilleurs scores
- Suppression de scénarios

#### Gantt Interactif (/gantt/:id)
- Visualisation temporelle par machine
- Barres de tâches colorées par machine
- Zoom (50% - 300%)
- Tooltips au survol : ID, ordre, article, dates, durée
- Indicateurs visuels pour retards (rouge)
- Export CSV
- Statistiques : opérations, durée totale, machines, statut

#### Stock Projeté Avancé
- API `/api/projected-stock/advanced`
- Utilise les dates de début d'opération ordonnancées
- Distingue consommations ordonnancées vs non-ordonnancées
- Timeline détaillée avec détection de ruptures

### Phase 5 - UI/UX Refonte ✅
- Système de thème clair/sombre
- Variables CSS cohérentes
- Classes personnalisées pour composants spéciaux
- Coins arrondis (rounded-lg)
- Lisibilité validée sur toutes les pages

## APIs Principales

### Nouvelles (P1/P2)
- `GET /api/matrix/machine-task` - Matrice compatibilités
- `GET /api/scenarios/compare?ids=...` - Comparaison scénarios
- `DELETE /api/scenarios/{id}` - Suppression scénario
- `GET /api/gantt/data/{id}` - Données Gantt formatées
- `GET /api/projected-stock/advanced` - Stock projeté avec dates ordonnancées

### Existantes
- `POST /api/schedule/run` - Lancer ordonnancement
- `GET /api/aps/kpis` - Dashboard APS
- `POST /api/rules` - Créer règle
- `PUT /api/rules/{id}` - Modifier règle

## Validation Tests (14 mars 2026)

### Backend : 100% (12/12 tests)
- Matrix API ✅
- Scenarios Compare API ✅
- Gantt Data API ✅
- Projected Stock Advanced API ✅
- Scenario Delete API ✅

### Frontend : 100%
- Navigation complète ✅
- Matrice compatibilités ✅
- Comparaison scénarios (modal) ✅
- Gantt interactif (zoom, tooltips) ✅
- Thème clair/sombre ✅

## Backlog

### P1 - Complété ✅
- ~~Logique MRP dans aps_engine.py~~
- ~~Dates consommation avec ordonnancement~~

### P2 - Complété ✅
- ~~Vue matricielle compatibilités~~
- ~~Comparaison What-if scénarios~~
- ~~Gantt interactif~~

### P3 - À Faire
- [ ] Export CSV du planning
- [ ] Dashboard temps réel WebSockets
- [ ] Replanification dynamique
- [ ] Multi-sites
- [ ] IA prédictive
- [ ] Intégration ERP

## Fichiers Clés

```
/app/
├── backend/
│   ├── server.py          # Tous endpoints API
│   ├── services/
│   │   ├── aps_engine.py    # MRP, BOM, Capacité
│   │   ├── scheduler_engine.py  # OR-Tools
│   │   └── rules_engine.py    # Moteur règles
│   └── tests/
│       └── test_p1p2_features.py  # Tests régression
└── frontend/
    └── src/
        ├── pages/
        │   ├── MatrixView.js         # Nouvelle
        │   ├── ScenariosComparison.js # Nouvelle
        │   ├── GanttInteractive.js   # Nouvelle
        │   ├── BusinessRules.js
        │   └── ...
        ├── components/
        │   └── Layout.js
        └── App.css
```
