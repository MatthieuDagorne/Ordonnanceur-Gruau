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

### Entités

**Centre de Charge**
```json
{ "id": "PLI01", "nom": "Centre de Pliage" }
```

**Machine**
```json
{ "id": "PLIEUSE_01", "nom": "Plieuse hydraulique", "centre_de_charge_id": "PLI01" }
```

**Opération**
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
  "name": "Interdire PLIAGE sur PLIEUSE_01",
  "tache_id": "PLIAGE",
  "centre_de_charge_id": "PLI01",
  "rule_type": "FORBID",
  "machine_id": "PLIEUSE_01"
}
```

## Fonctionnalités Implémentées

### Module de Diagnostic d'Assignation ✅
Page `/diagnostic` affichant pour chaque opération:
- tache_id, centre_de_charge_id
- Machines du centre (codes métier)
- Règles applicables
- Machines interdites (FORBID)
- Machines préférées (PREFER)
- Machine choisie
- Cause d'échec

### Moteur d'Auto-Assignation ✅
1. Extraire tache_id et centre_de_charge_id de l'opération
2. Trouver les machines du centre_de_charge_id
3. Appliquer règles FORBID/ALLOW/PREFER
4. Sélectionner la meilleure machine

### Règles Métier ✅
Types: ALLOW, FORBID, PREFER
Critères: tache_id, centre_de_charge_id, article_id (codes métier)

## Endpoints API
- `GET/POST /api/centres-de-charge`
- `GET/POST /api/machines`
- `GET/POST /api/rules`
- `GET /api/diagnostic/assignment`
- `POST /api/scheduling/calculate`

## Validation Effectuée
- 23/27 opérations assignées avec succès
- Règle FORBID correctement appliquée (M001 exclue)
- Règle PREFER correctement appliquée (M003 prioritaire)
- 10 opérations avec machine préférée

## Backlog
- [ ] Import CSV avec terminologie française
- [ ] Vue matricielle compatibilités machine/tâche
- [ ] Export planning en CSV
