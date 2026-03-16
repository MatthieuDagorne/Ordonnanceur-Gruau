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

**Workflow de replanification basé sur le BUDGET TEMPS (pas de limite d'itérations)** :

| Paramètre | Description |
|-----------|-------------|
| `max_solver_time_seconds` | Budget temps GLOBAL défini par l'utilisateur (30s, 1min, 2min...) |
| Répartition dynamique | 80% du temps restant alloué à chaque itération |
| Condition d'arrêt | Pas de rupture OU budget temps épuisé |

**Algorithme** :
1. **Itération N** : Planifier avec contraintes actuelles
2. **Post-traitement** : Simuler les consommations dans l'ordre chronologique
3. **Si rupture avec réception future** : Ajouter contrainte `start >= date_réception`
4. **Relancer** tant qu'il reste du temps et des ruptures à résoudre

**Exemple validé** :
```
Stock ART5=2, OF1_10 et OF2_10 ont besoin de 2 chacun
Réception ART5 le 20/03 : +3

Itération 1:
  - OF1_10 planifié 18/03 10:00 ✅ (stock suffisant)
  - OF2_10 planifié 18/03 10:55 ❌ (rupture: ART5=0)
  → Contrainte: OF2_10 >= 20/03 10:00

Itération 2:
  - OF1_10: 18/03 10:00 ✅
  - OF2_10: 20/03 10:00 ✅ (après réception)
  → OPTIMAL SANS RUPTURE en 2 itérations
```

**Capacité de production** :
- 200-300 opérations sur horizon 3 jours
- Centaines d'articles et réceptions fournisseurs
- Dizaines de règles métier
- Temps d'optimisation configurable par l'utilisateur

#### 8.3 Page "Stock Projeté par Scénario" (P1) ✅
| Fonctionnalité | Description |
|----------------|-------------|
| Route | `/projected-stock/:scenarioId` |
| Vue articles | Liste avec badge rupture/OK |
| Timeline | Chronologie des réceptions et consommations |
| Lien depuis Gantt | Bouton "Stock Projeté" |

#### 8.4 Temps de Déplacement (P1) ✅
- Champ `transfer_time_minutes` dans le modèle Operation
- Contrainte : `start(op2) >= end(op1) + transfer_time(op1)`

**Contrat de données operations.csv** :
```csv
id,order_id,operation_id,tache_id,centre_de_charge_id,production_time_minutes,setup_time_minutes,status,transfer_time_minutes
OF1_10,OF1,10,T001,C001,50,5,pending,30
```

#### 8.5 Affichage des Opérations Non Planifiables (P1) ✅
- Badge rouge dans le Gantt si `unscheduled_count > 0`
- Liste avec raisons détaillées
- Seules les opérations VRAIMENT non planifiables (pas de réception future) sont listées

## APIs Principales

### Ordonnancement
```json
POST /api/scheduling/calculate
{
  "scenario_name": "...",
  "max_solver_time_seconds": 120,  // Budget temps en secondes
  "ignore_material": false
}

Response: {
  "material_iteration": 2,         // Nombre d'itérations
  "total_solver_time": 0.05,       // Temps CPU solveur
  "total_elapsed_time": 0.08,      // Temps réel total
  "unscheduled_operations": [],    // Opérations sans solution
  "unscheduled_count": 0
}
```

### Stock Projeté par Scénario
```
GET /api/projected-stock/{scenario_id}?article_id=XXX
```

## Backlog

### P2 - En cours
- [ ] Améliorer les infobulles du Gantt avec stock projeté à t

### P3 - À Faire
- [ ] Export CSV du planning
- [ ] Horizon ferme (geler planning court terme)
- [ ] Dashboard temps réel WebSockets
- [ ] Replanification dynamique (événements panne machine)

## Tests Validés

### Replanification Automatique Sans Limite d'Itérations
| Scénario | Résultat |
|----------|----------|
| Budget 30s, 2 itérations nécessaires | ✅ Converge en 0.03s |
| Budget 120s, 2 itérations nécessaires | ✅ Converge en 0.02s |
| OF2_10 en rupture ART5 | ✅ Reporté au 20/03 (date réception) |
| Transfer time 30min | ✅ OF1_10 finit → +30min → OF1_20 commence |
