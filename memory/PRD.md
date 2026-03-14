# Shop Scheduler Pro - PRD

## Énoncé du Problème
Application web d'ordonnancement industriel pour un site de production.

## Architecture Technique
- **Backend**: Python FastAPI
- **Frontend**: React
- **Base de données**: MongoDB
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)

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
Exemples : `2026-03-20T14:30:00`

## Fonctionnalités Implémentées

### 1. Moteur de Règles Métier ✅
- **FORBID** : Interdit une machine pour les critères donnés
- **PREFER** : Préfère une machine (+100 score)
- **ALLOW** : Autorise une machine
- Matching sur : `tache_id`, `centre_de_charge_id`, `article_id`
- **article_id récupéré depuis l'ordre** via jointure `order_id`

### 2. Date de Besoin avec Heure ✅ (Corrigé 14 mars 2026)
- Format `YYYY-MM-DDTHH:MM:SS` supporté
- Utilisé pour priorisation et calcul de retard
- Affiché avec heure dans la page Diagnostic

### 3. Non-Chevauchement Garanti ✅
- Contrainte `NoOverlap` de OR-Tools par machine
- Une machine ne traite qu'une opération à la fois

### 4. Gestion des Matières ✅ (14 mars 2026)
- **Nouvelles collections** :
  - `operation_materials` : besoins composants par opération
  - `planned_supplier_receipts` : réceptions fournisseurs planifiées
- **Stock projeté** : initial + réceptions - consommations
- **Report automatique** si manque matière
- **Diagnostic matière** affiché par opération

### 5. Temps Maximum de Calcul ✅
- Paramètre `max_solver_time_seconds` (défaut 60s)
- Le solveur retourne la meilleure solution trouvée

## Endpoints API

### Nouvelles Collections
- `GET/POST/DELETE /api/operation-materials` - Besoins matière
- `GET/POST/DELETE /api/planned-supplier-receipts` - Réceptions planifiées
- `POST /api/import/operation-materials` - Import CSV
- `POST /api/import/planned-supplier-receipts` - Import CSV

### Ordonnancement
- `POST /api/scheduling/calculate`
  - `ignore_rules`, `ignore_material`, `auto_assign_machines`
  - `max_solver_time_seconds`

### Diagnostic
- `GET /api/diagnostic/assignment` - Avec diagnostic matière

## Validation (14 mars 2026)

### Test date_besoin
```
Ordre: LV1100007 avec due_date=2026-03-20T14:30:00
Diagnostic affiche: date_besoin=2026-03-20 14:30 ✅
```

### Test Règle FORBID sur Article
```
Règle: FORBID article=100235570, machine=TP5000_1
Résultat: TP5000_1 interdite → TP5000_2 choisie ✅
```

### Test Contrainte Matière
```
Stock 100541201=2, Besoin=5
Réception planifiée le 2026-03-16T10:00:00 (+5)
Résultat: Opération reportée jusqu'à disponibilité ✅
```

## Documentation
- `/app/docs/CSV_FORMAT.md` - Format des fichiers CSV (mis à jour)

## Backlog

### P1 - Prioritaires
- [ ] Afficher les ordres en retard sur le dashboard
- [ ] Persister les assignations en BDD

### P2 - Secondaires
- [ ] Import CSV avec validation UI améliorée
- [ ] Vue matricielle machine/tâche
- [ ] Export planning CSV enrichi

### P3 - Futurs
- [ ] Intégration Gantt avec vraie librairie
- [ ] Drag-and-drop sur le Gantt
- [ ] Comparaison de scénarios
