# APS Scheduler Pro - PRD

## Énoncé du Problème
Application web APS (Advanced Planning & Scheduling) pour l'ordonnancement industriel.

## Architecture Technique
- **Backend**: Python FastAPI + MongoDB
- **Frontend**: React + Tailwind CSS
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)
- **Design System**: Thème clair/sombre avec variables CSS

## Design System ✅ (14 mars 2026)

### Thème Clair/Sombre
- **Toggle** dans la sidebar avec icônes Sun/Moon
- **Persistence** dans localStorage (clé: `aps-theme`)
- **Transition** fluide avec 200ms ease
- **Classes CSS personnalisées** pour éléments spécifiques au thème

### Couleurs (Variables CSS)
| Variable | Sombre | Clair |
|----------|--------|-------|
| --bg-base | #0F172A | #F8FAFC |
| --bg-elevated | #1E293B | #FFFFFF |
| --text-primary | #F1F5F9 | #1E293B |
| --status-info | #60A5FA | #2563EB |
| --status-info-bg | #1E3A5F | #EFF6FF |

### Typographie
- **Titres**: Inter Bold 600-700
- **Corps**: Inter Regular 400
- **Données**: JetBrains Mono

### Composants UI
- Coins arrondis: `rounded-lg` (12px)
- Classes conditions: `.conditions-box`, `.conditions-group`, `.conditions-box-title`
- Animations: `animate-fade-in-up`, `animate-slide-in-left`, `hover-lift`

## Fonctionnalités APS

### 1. Règles Métier avec ET/OU ✅
- Conditions multiples combinées avec logique ET/OU
- Opérateurs: GT, GE, LT, LE, EQ, NE, IN, NOT_IN
- Attributs: largeur, épaisseur, type_matière, couleur, longueur
- Interface lisible dans les deux thèmes

### 2. Page Ordonnancement ✅
- 3 modes de priorité (Date, Matière, Équilibré)
- Durée max optimisation (30s à 10min)
- Gap d'optimalité (1-20%)
- Options avancées collapsibles

### 3. Dashboard APS ✅
- KPIs: OTD, Retards, Utilisation, WIP
- Barres de capacité par machine
- Alertes temps réel

### 4. Capacité Finie ✅
- production_time + setup_time
- Calendriers par centre de charge
- Contraintes NoOverlap

### 5. BOM/MRP ✅
- Explosion de nomenclature multi-niveaux
- Calcul des besoins nets
- Dates de consommation ordonnancées

### 6. Stock Projeté ✅
- Projection temporelle du stock par article
- Détection des ruptures
- Affichage des consommations par opération

## Validation UI/UX (14 mars 2026)

### Tests Frontend: 100% PASSED
- Toggle thème dans sidebar ✅
- Persistence localStorage ✅
- Section "Conditions sur Attributs" lisible ✅
- Page Ordres Fab. badges lisibles ✅
- Page Stock Projeté fonctionnelle ✅
- Navigation sidebar complète ✅
- Thème sombre lisible ✅
- Thème clair lisible ✅

### Bug Fix
- Corrigé: Erreur `'<' not supported between instances of 'NoneType' and 'int'` sur /api/projected-stock

## Backlog

### P1 - Prioritaires
- [ ] Finaliser la transformation APS (logique MRP dans aps_engine.py)
- [ ] Date de consommation matière avec dates ordonnancées
- [ ] Logique solveur avancée (priority_mode, priority_weights)

### P2 - Secondaires
- [ ] Vue matricielle compatibilités machine/tâche
- [ ] Simulation What-if / Comparaison scénarios
- [ ] Gantt interactif (remplacer le placeholder)
- [ ] Export CSV du planning

### P3 - Futurs
- [ ] Dashboard temps réel WebSockets
- [ ] Replanification dynamique
- [ ] Multi-sites
- [ ] IA prédictive
- [ ] Intégration ERP
