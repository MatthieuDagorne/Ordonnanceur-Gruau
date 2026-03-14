# Shop Scheduler Pro - PRD

## Énoncé du Problème
Application web d'ordonnancement industriel pour un site de production.

## Architecture Technique
- **Backend**: Python FastAPI
- **Frontend**: React
- **Base de données**: MongoDB
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)

## Modèle de Données (Codes Métier)

### Principes Clés
- **Pas d'UUID** pour les entités métier
- **Codes lisibles** : PLI01, PLIEUSE_01, PLIAGE
- **Terminologie française** : centre_de_charge_id, tache_id
- **Clé de jointure** : order_id (entre opérations et ordres)

### Entités

**Centre de Charge**
```json
{ "id": "PLI01", "nom": "Centre de Pliage" }
```

**Machine**
```json
{ "id": "PLIEUSE_01", "nom": "Plieuse hydraulique", "centre_de_charge_id": "PLI01" }
```

**Ordre de Fabrication**
```json
{ "id": "OF001", "article_id": "ART001", "due_date": "2026-03-18", "quantity": 10 }
```

**Opération** (jointure via order_id)
```json
{
  "id": "OF001_10",
  "order_id": "OF001",
  "tache_id": "PLIAGE",
  "centre_de_charge_id": "PLI01",
  "production_time_minutes": 60
}
```

**Règle Métier**
```json
{
  "name": "Interdire PLIEUSE_01 pour ART003",
  "tache_id": "PLIAGE",
  "centre_de_charge_id": "PLI01",
  "article_id": "ART003",
  "rule_type": "FORBID",
  "machine_id": "PLIEUSE_01"
}
```

## Fonctionnalités Implémentées

### Réinitialisation Complète de la BDD ✅ (14 mars 2026)
- Endpoint `/api/reset-all` : Supprime toutes les collections
- Endpoint `/api/demo/load` : Charge données de démo cohérentes

### Jointure Order_ID ✅ (14 mars 2026)
- Les opérations sont enrichies avec article_id et date_besoin de l'ordre parent
- Endpoint `/api/operations-enrichies` : Vue à plat des opérations jointes
- Tri automatique par date_besoin (plus urgent en premier)

### Module de Diagnostic d'Assignation ✅
Page `/diagnostic` affichant pour chaque opération:
- order_id, article_id, date_besoin (depuis la jointure)
- tache_id, centre_de_charge_id
- Machines du centre (codes métier)
- Règles applicables
- Machines interdites (FORBID)
- Machines préférées (PREFER)
- Machine choisie
- Indicateur d'urgence et de retard

### Moteur d'Auto-Assignation ✅
1. Enrichir l'opération avec article_id et date_besoin (jointure order_id)
2. Trouver les machines du centre_de_charge_id
3. Appliquer règles FORBID/ALLOW/PREFER (y compris par article_id)
4. Sélectionner la meilleure machine
5. Calculer l'urgence basée sur date_besoin

### Règles Métier ✅
Types: ALLOW, FORBID, PREFER
Critères: tache_id, centre_de_charge_id, article_id (codes métier)

### Page Ordres de Fabrication ✅ (14 mars 2026)
- Vue à plat : toutes les opérations enrichies
- Vue groupée : opérations groupées par ordre
- Indicateurs visuels : en retard (rouge), urgent (jaune)
- Validation de jointure (✓ ou ✗)

## Endpoints API
- `POST /api/reset-all` - Reset complet de la BDD
- `POST /api/demo/load` - Charger données de démo
- `GET /api/operations-enrichies` - Opérations avec jointure
- `GET /api/diagnostic/assignment` - Diagnostic complet
- `GET/POST /api/centres-de-charge`
- `GET/POST /api/machines`
- `GET/POST /api/rules`
- `POST /api/scheduling/calculate`

## Validation (14 mars 2026)
- 25/25 tests backend passés
- 7/7 opérations assignées avec succès
- Règle FORBID correctement appliquée (OF003_10 -> PLIEUSE_02, pas PLIEUSE_01)
- Règle PREFER correctement appliquée (USINAGE -> TOUR_CNC_01)
- 2 opérations marquées en retard (OF003)
- Jointure order_id 100% fonctionnelle

## Backlog

### P1 - Prioritaires
- [ ] Intégrer date_besoin dans scheduler_engine.py pour le CP-SAT
- [ ] Afficher les ordres en retard de façon proéminente dans le dashboard

### P2 - Secondaires
- [ ] Import CSV avec terminologie française
- [ ] Vue matricielle compatibilités machine/tâche
- [ ] Comparaison de scénarios
- [ ] Export planning en CSV

### P3 - Futurs
- [ ] Intégration Gantt avec vraie librairie (actuellement placeholder)
- [ ] Drag-and-drop sur le Gantt
