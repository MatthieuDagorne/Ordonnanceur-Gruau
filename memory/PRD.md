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
- **Codes métier** (pas UUID) : `PLI01`, `PLIEUSE_01`, `LV1100007`
- **Terminologie française** : `centre_de_charge_id`, `tache_id`
- **Clé de jointure** : `order_id` (opération → ordre)
- **article_id** : récupéré depuis l'ordre via la jointure

### Format DateTime
```
YYYY-MM-DDTHH:MM:SS  (ISO 8601)
```
Exemples : `2026-03-20T10:00:00`, `2026-03-18 14:30:00`, `2026-03-18`

## Fonctionnalités Implémentées

### Moteur de Règles Métier ✅ (Corrigé 14 mars 2026)
- **FORBID** : Interdit une machine pour les critères donnés
- **PREFER** : Préfère une machine (+100 score)
- **ALLOW** : Autorise une machine
- Matching sur : `tache_id`, `centre_de_charge_id`, `article_id`
- **article_id récupéré depuis l'ordre** via jointure `order_id`

### Moteur d'Ordonnancement ✅ (Corrigé 14 mars 2026)
1. **Non-chevauchement garanti** : Contrainte `NoOverlap` par machine
2. **Séquence respectée** : Opérations d'un OF dans l'ordre des gammes
3. **Priorité par datetime** : `due_date` avec heure pour tri et urgence
4. **Arbitrage** : règles → due_date → priority

### Diagnostic d'Assignation ✅
- Affiche `article_id` depuis l'ordre (via jointure)
- Montre les règles applicables et leur effet
- Indique les machines interdites/préférées

## Endpoints API

### Ordonnancement
- `POST /api/scheduling/calculate` - Lance l'ordonnancement
  - Options : `ignore_rules`, `ignore_material`, `auto_assign_machines`

### Diagnostic
- `GET /api/diagnostic/assignment` - Rapport d'assignation détaillé
- `GET /api/operations-enrichies` - Vue jointe opérations + ordres

### Reset
- `POST /api/reset-all` - Vide toutes les collections

## Validation (14 mars 2026)

### Test Règle FORBID sur Article
```
Règle: FORBID article=100235570, machine=TP5000_1
Ordre: LV1100007 avec article_id=100235570
Résultat: TP5000_1 interdite → TP5000_2 choisie ✅
```

### Test Non-Chevauchement
```
Machine TP5000_1:
  [0-55min]  LV1100008_10
  [55-90min] LV1100008_20
→ Pas de chevauchement ✅
```

## Documentation
- `/app/docs/CSV_FORMAT.md` - Format des fichiers CSV

## Backlog

### P1 - Prioritaires
- [ ] Afficher les ordres en retard sur le dashboard
- [ ] Persister les assignations dans la BDD

### P2 - Secondaires
- [ ] Import CSV avec validation
- [ ] Vue matricielle machine/tâche
- [ ] Export planning CSV

### P3 - Futurs
- [ ] Intégration Gantt avec vraie librairie
- [ ] Drag-and-drop sur le Gantt
- [ ] Comparaison de scénarios
