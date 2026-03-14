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

### 2. Règles sur Attributs Articles ✅ (14 mars 2026)
- **Nouveaux attributs articles** : `largeur`, `epaisseur`, `couleur`, `type_matiere`, `longueur`
- **Format CSV import** : `id,description,type_matiere,epaisseur,couleur,largeur,longueur`
- **Mapping automatique** : FR → EN (type_matiere → material_type, etc.)
- **Opérateurs** : GT, GE, LT, LE, EQ, NE, IN, NOT_IN
- **Exemple** : FORBID si largeur > 5000mm sur machine X

### 3. Calendriers par Centre de Charge ✅ (14 mars 2026)
- **Affectation calendrier** : chaque centre peut avoir un calendrier spécifique
- **Interface UI** : dropdown dans la page Centres de Charge
- **Contraintes OR-Tools** : le scheduler respecte les plages horaires de travail
- **Exemple** : Horaires Usine (Lun-Ven 8h-17h) assigné à LVC001

### 4. Stock Projeté avec Timestamps ✅ (14 mars 2026)
- **Timeline temporelle** : stock à chaque instant basé sur l'ordonnancement
- **Dates de consommation** : `scheduled_datetime` si ordonnancé, sinon `due_date`
- **Indicateur** : compteur "Ordonnancées X/Y" dans le résumé
- **Détection ruptures** : date de première rupture et date de disponibilité

### 5. Date de Besoin avec Heure ✅
- Format `YYYY-MM-DDTHH:MM:SS` supporté
- Utilisé pour priorisation et calcul de retard
- Affiché avec heure dans la page Diagnostic

### 6. Non-Chevauchement Garanti ✅
- Contrainte `NoOverlap` de OR-Tools par machine
- Une machine ne traite qu'une opération à la fois

### 7. Gestion des Matières ✅
- **Nouvelles collections** :
  - `operation_materials` : besoins composants par opération
  - `planned_supplier_receipts` : réceptions fournisseurs planifiées
- **Stock projeté** : initial + réceptions - consommations
- **Report automatique** si manque matière

### 8. Temps Maximum de Calcul ✅
- Paramètre `max_solver_time_seconds` (défaut 60s)
- Le solveur retourne la meilleure solution trouvée

## Endpoints API

### Centres de Charge
- `GET /api/centres-de-charge` - Liste avec calendar_id
- `PUT /api/centres-de-charge/{id}` - Met à jour calendar_id

### Règles Métier
- `POST /api/rules` - Crée règle simple ou sur attribut
- `GET /api/rules` - Liste toutes les règles

### Stock Projeté
- `GET /api/projected-stock` - Avec timestamps et timeline

### Import CSV
- `POST /api/import/articles` - Avec mapping FR→EN des attributs
- `POST /api/import/operation-materials`
- `POST /api/import/planned-supplier-receipts`

### Ordonnancement
- `POST /api/scheduling/calculate`
  - `ignore_rules`, `ignore_material`, `ignore_calendars`
  - `auto_assign_machines`, `max_solver_time_seconds`

## Validation (14 mars 2026)

### Test Règle FORBID sur Article (Bug Récurrent Corrigé)
```
Règle: FORBID article=100235570, machine=TP5000_1
Résultat: OF_TEST_001 assigné à TP5000_2 ✅
```

### Test Règle sur Attribut
```
Règle: FORBID width > 600mm, machine=TP5000_1
Article 100235570 largeur=1000mm → TP5000_1 interdite ✅
```

### Test Calendriers
```
Centre LVC001 avec calendrier "Horaires Usine" (8h-17h)
24 contraintes de calendrier appliquées ✅
```

## Documentation
- `/app/docs/CSV_FORMAT.md` - Format des fichiers CSV

## Backlog

### P1 - Prioritaires
- [ ] Afficher les ordres en retard sur le dashboard
- [ ] Persister les assignations en BDD après ordonnancement

### P2 - Secondaires
- [ ] Import CSV avec validation UI améliorée
- [ ] Vue matricielle machine/tâche
- [ ] Export planning CSV enrichi

### P3 - Futurs
- [ ] Intégration Gantt avec vraie librairie (frappe-gantt, etc.)
- [ ] Drag-and-drop sur le Gantt
- [ ] Comparaison de scénarios
