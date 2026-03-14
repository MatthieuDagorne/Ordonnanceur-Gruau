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

### Phase 3 - Transformation APS ✅
- Page Ordonnancement avec scénarios
- Options de priorité (Date, Matière, Équilibré)
- Dashboard APS avec KPIs

### Phase 4 - P1/P2 Features ✅
- Vue Matricielle Compatibilités (/matrix)
- Comparaison de Scénarios (/scenarios)
- Gantt Interactif (/gantt/:id)
- Stock Projeté Avancé avec dates ordonnancées

### Phase 5 - Améliorations Ergonomiques (14 mars 2026) ✅

#### 1. Calendriers en Quarts d'Heure
- **Inputs** : `type="time"` avec `step="900"` (15 min)
- **Format** : HH:MM (ex: 07:45, 16:45)
- **Exemples** : Affichés sous les inputs
- **Calcul** : Durée/jour automatique

#### 2. État des Données Complet
- **Section ERP** : Ordres Fab., Opérations, Articles, Stocks
- **Section Supply Chain** : Matières/Op., Réceptions Prévues, Nomenclatures (BOM), Indisponibilités
- **Section Configuration** : Machines, Centres Charge, Calendriers, Règles Métier, Scénarios

#### 3. Filtres Intelligents par Page
| Page | Filtres |
|------|---------|
| Règles Métier | Recherche, Machine, Type (ALLOW/FORBID/PREFER), Centre, État actif |
| Ordres Fab. | Recherche, Article, Statut (retard/urgent/ok), Date début/fin |
| Diagnostic | Recherche, Statut (assignées/non assignées), Centre, Article |
| Stock Projeté | Recherche, Statut stock (rupture/ok/faible) |

**Caractéristiques** :
- Recherche textuelle instantanée
- Compteur de résultats (X / Y)
- Bouton "Réinitialiser"
- Performance avec `useMemo`

## APIs Principales

### Data Stats (mis à jour)
```json
GET /api/data/stats
{
  "manufacturing_orders": 10,
  "operations": 24,
  "articles": 10,
  "stocks": 10,
  "machines": 8,
  "work_centers": 4,
  "calendars": 2,
  "rules": 5,
  "scenarios": 2,
  "operation_materials": 10,
  "planned_receipts": 9,
  "bom_lines": 0,
  "unavailabilities": 0
}
```

### Calendars (mis à jour)
```json
POST /api/calendars
{
  "name": "Équipe Matin",
  "working_days": [1, 2, 3, 4, 5],
  "start_time": "07:45",
  "end_time": "16:45",
  "start_hour": 7,
  "end_hour": 16
}
```

## Validation Tests (14 mars 2026)

### Backend : 100% (9/9 tests)
- DataStats API ✅
- Calendars HH:MM ✅
- Rules, Operations, Diagnostic, Stock APIs ✅

### Frontend : 100% (6/6 tests)
- Calendars time inputs ✅
- Import stats sections ✅
- Filtres sur 4 pages ✅

## Backlog

### P3 - À Faire
- [ ] Export CSV du planning
- [ ] Dashboard temps réel WebSockets
- [ ] Replanification dynamique
- [ ] Multi-sites
- [ ] IA prédictive
- [ ] Intégration ERP

## Fichiers Modifiés (Phase 5)

```
backend/
├── server.py              # DataStats model, Calendar model
frontend/src/pages/
├── Calendars.js           # Time inputs HH:MM
├── ImportData.js          # 3 sections de stats
├── BusinessRules.js       # Filtres avec useMemo
├── ManufacturingOrders.js # Filtres avec useMemo
├── DiagnosticAssignment.js# Filtres avec useMemo
├── ProjectedStock.js      # Filtres avec useMemo
```
