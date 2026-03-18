# APS Scheduler Pro - Product Requirements Document

## Overview
Advanced Planning & Scheduling (APS) application for industrial manufacturing, using OR-Tools CP-SAT solver for finite capacity scheduling.

## Architecture
- **Frontend**: React + TailwindCSS + Shadcn/UI
- **Backend**: FastAPI + MongoDB
- **Solver**: Google OR-Tools CP-SAT

## Recent Updates (2026-03-18)

### FEATURE: Règle REQUIRE (obligatoire/exclusive) ✅

**Implémentation complète** de la règle REQUIRE qui remplace ALLOW :

**Logique des règles métier**:
- **REQUIRE** (Requis): Machine obligatoire/exclusive - SEULE cette machine peut traiter l'opération
- **FORBID** (Interdit): Machine interdite - Cette machine ne peut PAS traiter l'opération
- **PREFER** (Préféré): Machine préférée - Bonus de préférence (non contraignant)
- **ALLOW**: DEPRECATED - Automatiquement converti en REQUIRE

**Backend** (`rules_engine.py`):
```python
def evaluate_machine(self, ...):
    require_rules = [r for r in applicable_rules if r.rule_type in [RuleType.REQUIRE, RuleType.ALLOW]]
    
    if require_rules:
        required_machine_ids = [r.machine_id for r in require_rules]
        if machine_id in required_machine_ids:
            # Machine requise - OK
        else:
            # Machine NON autorisée - Bloquée
            allowed = False
```

**Frontend** (`BusinessRules.js`):
- Traduction française des types de règles
- Couleurs distinctives:
  - Requis: Vert (#16a34a)
  - Interdit: Rouge (#dc2626)
  - Préféré: Orange (#d97706)
- Descriptions explicatives dans le formulaire

### Bugs critiques résolus (session précédente)

1. **Stock projeté négatif**: Opérations planifiées malgré stock insuffisant
   - Fix: Calcul chronologique des mouvements dans `get_projected_stock()`

2. **Opérations le week-end**: Calendrier non respecté
   - Fix: Conversion jours 1-7→0-6, extension horizon contraintes, `add_bool_or()`

3. **Opérations marquées "non planifié"**: Mauvais mapping IDs
   - Fix: `operation_id` au lieu de `id`

### Améliorations UI

| Fonctionnalité | Description | Statut |
|----------------|-------------|--------|
| Règles métier FR | Traduction REQUIRE/Interdit/Préféré | ✅ |
| Tooltips Gantt | Description tâche + article | ✅ |
| Timer progression | mm:ss + % vs temps max | ✅ |
| Page Ordres Fab. | Op.Seq + descriptions | ✅ |

## Tests validés

| Test | Résultat |
|------|----------|
| Règle REQUIRE appliquée | ✅ PASS |
| Affichage FR règles | ✅ PASS |
| Conversion ALLOW→REQUIRE | ✅ PASS |
| Calcul avec règles | 765 ops ✅ |

## API Endpoints

### Rules
- `GET /api/rules` - Liste des règles métier
- `POST /api/rules` - Créer une règle
- `PUT /api/rules/{id}` - Modifier une règle
- `DELETE /api/rules/{id}` - Supprimer une règle

### Scheduling
- `POST /api/scheduling/calculate/async` - Calcul asynchrone
- Options: `ignore_rules: false` pour activer les règles métier

## Backlog
1. (P2) Export CSV du planning finalisé
2. (P2) Règles basées sur attributs d'articles (épaisseur, largeur, etc.)
3. (P3) Tableau de bord KPIs avancé
