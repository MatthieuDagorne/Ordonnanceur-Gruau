# Shop Scheduler Pro - PRD

## Énoncé du Problème
Application web d'ordonnancement industriel pour un site de production, permettant de planifier les opérations de fabrication sur les machines disponibles en respectant les contraintes métier.

## Architecture Technique
- **Backend**: Python FastAPI
- **Frontend**: React
- **Base de données**: MongoDB (V1 - migration PostgreSQL prévue)
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)

## Fonctionnalités Implémentées

### Module de Diagnostic d'Assignation ✅ (NOUVEAU)
**Dernière mise à jour: 14 Mars 2026**

Page `/diagnostic` avec tableau détaillé affichant pour chaque opération:
- operation_id, task_id, work_center_id
- Machines du work_center
- Règles métier appliquées
- Machines interdites (FORBID)
- Machines préférées (PREFER)
- Machine finale choisie
- Cause d'échec si aucune machine

Causes d'échec identifiées:
- `AUCUNE_MACHINE_DANS_WORK_CENTER_XXX` : Aucune machine rattachée à ce work_center_id
- `WORK_CENTER_ID_MANQUANT` : L'opération n'a pas de work_center_id
- `TOUTES_MACHINES_INTERDITES_PAR_FORBID` : Toutes les machines sont bloquées par des règles

### Module de Règles Métier (POC - Simplifié) ✅
Structure d'une règle:
- `id`, `name`
- `task_id`, `work_center_id`, `article_id` (critères de matching)
- `rule_type`: ALLOW | FORBID | PREFER
- `machine_id`: machine cible
- `active`: état de la règle

**IMPORTANT - Logique de matching:**
- Les règles utilisent UNIQUEMENT `task_id`, `work_center_id` et `article_id`
- L'`id` de l'opération n'est JAMAIS utilisé pour le matching

### Moteur d'Auto-Assignation des Machines ✅
Logique étape par étape:
1. Extraire `task_id` et `work_center_id` de l'opération
2. Trouver les machines du `work_center_id` requis
3. Appliquer les règles métier (FORBID exclut, PREFER donne +100 score)
4. Sélectionner la machine avec le meilleur score

Logs détaillés à chaque étape dans la console backend.

## Endpoints API Principaux
- `GET /api/diagnostic/assignment` - Diagnostic complet d'assignation
- `GET/POST /api/rules` - Gestion des règles métier
- `POST /api/scheduling/calculate` - Lancement ordonnancement

## PROBLÈME IDENTIFIÉ
Les opérations importées utilisent des `work_center_id` (LVC001, LVC002...) qui ne correspondent pas aux `work_center_id` des machines (qui sont des UUIDs).
**Solution**: S'assurer que les machines sont rattachées aux mêmes work_center_id que ceux utilisés dans les opérations importées.

## Backlog

### P1 - Prochaines Tâches
- [ ] Aligner les work_center_id des machines avec ceux des opérations
- [ ] Créer un jeu de données de démonstration cohérent

### P2 - Fonctionnalités Futures
- [ ] Vue matricielle compatibilités machine/tâche
- [ ] Comparaison de scénarios
- [ ] Export du planning en CSV
