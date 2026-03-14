# APS Scheduler Pro - PRD

## Énoncé du Problème
Application web APS (Advanced Planning & Scheduling) pour l'ordonnancement industriel d'un site de production.

## Architecture Technique
- **Backend**: Python FastAPI
- **Frontend**: React
- **Base de données**: MongoDB
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)
- **Module APS**: BOM, MRP, Capacité finie

## Modèle de Données

### Principes Clés
- **Codes métier** (pas UUID) : `PLI01`, `TP5000_1`, `LV1100007`
- **Terminologie française** : `centre_de_charge_id`, `tache_id`
- **Clé de jointure** : `order_id` (opération → ordre)
- **article_id** : récupéré depuis l'ordre via la jointure

### Format DateTime (ISO 8601)
```
YYYY-MM-DDTHH:MM:SS
```

## Fonctionnalités APS Implémentées

### 1. Dashboard APS avec KPIs ✅ (14 mars 2026)
- **OTD (On-Time Delivery)** : % des ordres livrés à temps
- **Ordres en Retard** : Liste avec délai en heures
- **Utilisation Machines** : Capacité vs Charge (7 jours)
- **WIP** : Ordres en cours et opérations planifiées

### 2. Capacité Finie avec Calendriers ✅ (14 mars 2026)
- **production_time_minutes + setup_time_minutes** : Pris en compte pour la charge
- **Calendriers par centre de charge** : Heures de travail par jour
- **Barres de capacité** : Visualisation charge/capacité par machine

### 3. Planification Multi-Niveaux (BOM/MRP) ✅ (14 mars 2026)
- **Import BOM** : `parent_article_id, child_article_id, quantity, level, scrap_rate`
- **Explosion de nomenclature** : Multi-niveaux avec taux de rebut
- **Calcul MRP** : Besoins bruts, stock disponible, besoins nets
- **Dates de consommation** : Basées sur `scheduled_start` de l'ordonnanceur

### 4. Édition des Règles Métier ✅ (14 mars 2026)
- **PUT /api/rules/{id}** : Modifier une règle existante
- **Interface UI** : Bouton éditer avec formulaire pré-rempli
- **Bouton "Mettre à jour"** : Différent de "Créer" en mode édition

### 5. Règles Métier sur Attributs ✅
- **Attributs articles** : `largeur`, `epaisseur`, `couleur`, `type_matiere`, `longueur`
- **Opérateurs** : GT, GE, LT, LE, EQ, NE, IN, NOT_IN
- **Exemple** : FORBID si largeur > 5000mm sur machine X

### 6. Calendriers par Centre de Charge ✅
- **Affectation calendrier** : Dropdown dans l'interface
- **Contraintes OR-Tools** : Plages horaires de travail respectées
- **24 contraintes** : Appliquées par l'ordonnanceur

### 7. Stock Projeté avec Timestamps ✅
- **Timeline temporelle** : Stock à chaque instant
- **Dates de consommation** : `scheduled_datetime` si ordonnancé
- **Indicateur** : Compteur "Ordonnancées X/Y"

## Endpoints API

### APS
- `GET /api/aps/kpis` - KPIs (OTD, retards, utilisation, WIP)
- `GET /api/aps/capacity?horizon_days=7` - Capacité par machine
- `GET /api/aps/mrp` - Calcul MRP
- `GET /api/aps/bom` - Liste des nomenclatures
- `POST /api/aps/bom` - Créer une ligne BOM
- `POST /api/aps/bom/explode?article_id=X&quantity=Y` - Exploser une nomenclature
- `POST /api/import/bom` - Import CSV nomenclatures

### Règles Métier
- `GET /api/rules` - Liste avec attributs
- `GET /api/rules/{id}` - Détail d'une règle
- `POST /api/rules` - Créer une règle
- `PUT /api/rules/{id}` - Modifier une règle
- `DELETE /api/rules/{id}` - Supprimer une règle

### Stock Projeté
- `GET /api/projected-stock` - Avec timestamps et timeline

## Validation (14 mars 2026)

### Tests Backend: 22/22 PASSED
- PUT /api/rules/{id} - CRUD complet
- GET /api/aps/kpis - Structure correcte
- GET /api/aps/capacity - Par machine
- BOM import et explosion
- MRP calculation

### Tests Frontend: 100% PASSED
- APS Dashboard avec 4 KPIs
- Édition des règles métier
- Barres de capacité
- Navigation APS

## Documentation
- `/app/docs/CSV_FORMAT.md` - Format des fichiers CSV

## Format CSV BOM
```csv
parent_article_id,child_article_id,quantity,level,unit,scrap_rate
100235560,COMP_A,2,1,pièce,0.02
100235560,COMP_B,4,1,pièce,0
COMP_A,MATIERE_X,0.5,2,kg,0.05
```

## Backlog

### P1 - Prioritaires
- [ ] Persister les assignations en BDD après ordonnancement
- [ ] Alertes en temps réel sur retards et ruptures
- [ ] Simulation "What-if" - Comparer scénarios

### P2 - Secondaires
- [ ] Replanification dynamique (réaction aux aléas)
- [ ] Intégration ERP bidirectionnelle
- [ ] Export planning CSV enrichi

### P3 - Futurs
- [ ] Gantt interactif avec drag-and-drop
- [ ] Optimisation multi-objectifs
- [ ] Dashboard temps réel avec WebSockets
