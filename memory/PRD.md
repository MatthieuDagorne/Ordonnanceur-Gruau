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
- **PREFER**: préfère une machine (prioritaire si possible)

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
- Log des règles appliquées
- Statistiques d'assignation

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
