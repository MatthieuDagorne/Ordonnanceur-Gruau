# APS Scheduler Pro - PRD

## Énoncé du Problème
Application web APS (Advanced Planning & Scheduling) pour l'ordonnancement industriel avec capacité finie, règles métier avancées et fonctionnalités MRP.

## Architecture Technique
- **Backend**: Python FastAPI + MongoDB
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)
- **Design System**: Thème clair/sombre avec variables CSS

## Fonctionnalités Implémentées

### Phase 1-7 - Fondations et APS ✅
- Calendriers par centre de charge avec horaires personnalisables
- Règles métier avec logique ET/OU et attributs (couleur, épaisseur...)
- Vue Matricielle, Comparaison de Scénarios
- Gantt Interactif, Stock Projeté Avancé
- Filtres intelligents sur toutes les pages
- Load Balancing multi-machines

### Phase 8 - Nouvelles Fonctionnalités APS (16 mars 2026) ✅

#### 8.1 Précision Calendriers au Quart d'Heure (P0) ✅
- Format HH:MM pour `start_time` et `end_time` (ex: "07:45", "16:30")
- Calcul des zones interdites en minutes exactes
- Validation jours invalides (seuls 0-6 acceptés)

#### 8.2 Logique Matière Temporelle avec REPLANIFICATION AUTOMATIQUE (P0 - CRITIQUE) ✅
| Fonctionnalité | Description |
|----------------|-------------|
| Stock projeté dynamique | Calcul du stock à l'horodatage exact de chaque opération |
| Replanification itérative | Jusqu'à 5 itérations pour reporter les opérations en rupture |
| Cascade de gamme | Si op1 bloquée, op2+ du même OF automatiquement bloquées |
| `unscheduled_operations` | Liste des opérations vraiment non planifiables (pas de réception future) |

**Workflow de replanification** :
1. **Première passe** : Planifier normalement
2. **Post-traitement** : Simuler les consommations dans l'ordre chronologique
3. **Si rupture avec réception future** : Reporter l'opération à cette date
4. **Relancer** avec nouvelles contraintes jusqu'à convergence

**Exemple validé** :
- Stock ART5=2
- OF1_10 consomme 2 → stock=0
- OF2_10 besoin de 2 → RUPTURE
- Réception ART5 le 20/03 : +3
- **OF2_10 automatiquement reporté au 20/03 10:00** ✅

#### 8.3 Page "Stock Projeté par Scénario" (P1) ✅
| Fonctionnalité | Description |
|----------------|-------------|
| Route | `/projected-stock/:scenarioId` |
| Vue articles | Liste avec badge rupture/OK |
| Timeline | Chronologie des réceptions et consommations |
| Détails | Initial, Réceptions, Consommations, Final |

**Frontend** :
- `ProjectedStockScenario.js` : Page dédiée
- Bouton "Stock Projeté" dans le Gantt
- Filtre "Ruptures" pour voir seulement les articles en rupture

#### 8.4 Temps de Déplacement (P1) ✅
- Champ `transfer_time_minutes` dans le modèle Operation
- Contrainte : `start(op2) >= end(op1) + transfer_time(op1)`
- Import CSV supporté

**Contrat de données operations.csv** :
```csv
id,order_id,operation_id,tache_id,centre_de_charge_id,production_time_minutes,setup_time_minutes,status,transfer_time_minutes
OF1_10,OF1,10,T001,C001,50,5,pending,30
```

#### 8.5 Affichage des Opérations Non Planifiées (P1) ✅
- Badge rouge dans le Gantt si `unscheduled_count > 0`
- Liste déroulante avec détails (raison, composants bloquants)

## APIs Principales

### Stock Projeté par Scénario
```
GET /api/projected-stock/{scenario_id}?article_id=XXX
```

### Ordonnancement avec Replanification
```
POST /api/scheduling/calculate
Response: {
  "material_iteration": 3,  // Nombre d'itérations
  "unscheduled_operations": [...],  // Opérations vraiment non planifiables
  "unscheduled_count": 0
}
```

## Backlog

### P2 - En cours
- [ ] Améliorer les infobulles du Gantt avec stock projeté à t

### P3 - À Faire
- [ ] Export CSV du planning
- [ ] Horizon ferme (geler planning court terme)
- [ ] Dashboard temps réel WebSockets
- [ ] Replanification dynamique

## Fichiers Modifiés (Phase 8)

```
backend/
├── services/
│   ├── scheduler_engine.py  # Replanification itérative, contraintes matière
│   └── material_manager.py  # Détection "jamais disponible"
└── server.py                # Endpoints stocks, articles, projected-stock/scenario

frontend/src/
├── pages/
│   ├── GanttInteractive.js  # Badge non planifiées, bouton Stock Projeté
│   └── ProjectedStockScenario.js  # Nouvelle page
└── App.js                   # Route /projected-stock/:scenarioId
```

## Tests Validés

### Replanification Automatique
| Scénario | Résultat |
|----------|----------|
| OF2_10 en rupture ART5 | ✅ Reporté au 20/03 (date réception) après 3 itérations |
| Stock projeté timeline | ✅ OF1_10 le 18/03, OF2_10 le 20/03 |
| Transfer time 30min | ✅ OF1_10 finit à 10:55, OF1_20 commence à 11:25 |
