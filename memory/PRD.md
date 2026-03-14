# Shop Scheduler Pro - PRD

## Énoncé du Problème
Application web d'ordonnancement industriel pour un site de production, permettant de planifier les opérations de fabrication sur les machines disponibles en respectant les contraintes métier.

## Architecture Technique
- **Backend**: Python FastAPI
- **Frontend**: React
- **Base de données**: MongoDB (V1 - migration PostgreSQL prévue)
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)

## Fonctionnalités Implémentées

### Module de Règles Métier (POC - Simplifié) ✅
**Dernière mise à jour: 14 Mars 2026**

Structure d'une règle:
- `id`: identifiant unique
- `name`: nom descriptif
- `task_id`: (optionnel) type de tâche
- `work_center_id`: (optionnel) centre de charge
- `article_id`: (optionnel, ne peut pas être seul)
- `rule_type`: ALLOW | FORBID | PREFER
- `machine_id`: machine cible (obligatoire, dropdown)
- `active`: état de la règle

Types de règles:
- **ALLOW**: autorise explicitement une machine
- **FORBID**: interdit une machine (exclue du planning)
- **PREFER**: préfère une machine (prioritaire si possible, +100 score)

**IMPORTANT - Logique de matching:**
- Les règles utilisent UNIQUEMENT `task_id`, `work_center_id` et `article_id` pour le matching
- L'`id` de l'opération n'est JAMAIS utilisé pour le matching des règles
- L'`article_id` provient de l'ordre de fabrication (jointure sur `order_id`)

### Moteur d'Auto-Assignation des Machines ✅
**Dernière mise à jour: 14 Mars 2026**

Logique de fonctionnement:
1. Pour chaque opération, récupérer `task_id` et `work_center_id`
2. Filtrer les machines appartenant au `work_center_id` requis
3. Appliquer les règles métier (FORBID exclut, PREFER donne +100 score)
4. Sélectionner la machine avec le meilleur score

Logs détaillés:
- Critères de matching affichés pour chaque opération
- Machines candidates avant règles
- Règles appliquées avec leur effet
- Machines restantes après règles
- Cause claire en cas d'échec (ex: "AUCUNE_MACHINE_DANS_WORK_CENTER")

### Gestion du Référentiel Atelier ✅
- Postes de travail (work centers)
- Machines (avec assignation à un work center)
- Calendriers de travail
- Indisponibilités machines

### Import de Données (POC) ✅
- Import CSV en mode "remplacement complet"
- Types: ordres de fabrication, opérations, articles, stocks
- Fonction de réinitialisation des données opérationnelles

### Ordonnancement ✅
- Moteur OR-Tools CP-SAT
- Auto-assignation des machines basée sur task_id + work_center_id
- Application des règles métier (ALLOW/FORBID/PREFER)
- Contraintes de capacité finie (no-overlap)
- Contraintes de séquence (opérations d'un même ordre)

### Diagnostic ✅
- Rapport de pré-validation (données manquantes)
- Analyse de faisabilité par opération
- Log des règles appliquées avec contexte
- Statistiques d'assignation avec causes d'échec

## Endpoints API Principaux
- `GET/POST /api/rules` - Gestion des règles métier
- `DELETE /api/rules/{id}` - Suppression d'une règle
- `POST /api/scheduling/calculate` - Lancement ordonnancement
- `POST /api/data/reset` - Réinitialisation données
- `POST /api/import/{type}` - Import CSV

## Backlog

### P1 - Prochaines Tâches
- [ ] Créer un jeu de données de démonstration avec règles métier
- [ ] Développer vue matricielle pour compatibilités machine/tâche

### P2 - Fonctionnalités Futures
- [ ] Comparaison de scénarios
- [ ] Export du planning en CSV
- [ ] Améliorer interactivité Gantt (drag-and-drop)

### P3 - Améliorations
- [ ] Sauvegarde automatique avant suppression
- [ ] Intégrer vraie bibliothèque Gantt (frappe-gantt)
