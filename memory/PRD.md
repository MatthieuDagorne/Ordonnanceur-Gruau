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

### Couleurs
| Variable | Sombre | Clair |
|----------|--------|-------|
| --bg-primary | #0F172A | #F8FAFC |
| --surface | #1E293B | #FFFFFF |
| --text-primary | #F8FAFC | #0F172A |
| --accent-blue | #0284C7 | #0284C7 |
| --accent-orange | #F97316 | #F97316 |

### Typographie
- **Titres**: Chivo (Bold 700-900)
- **Corps**: IBM Plex Sans
- **Données**: JetBrains Mono

### Animations
- `animate-fade-in-up` - Entrée des pages
- `animate-slide-in-left` - Sidebar
- `hover-lift` - Cards avec translateY(-2px)
- `animate-pulse-slow` - Indicateur de statut

## Fonctionnalités APS

### 1. Règles Métier avec ET/OU ✅
- Conditions multiples combinées
- Opérateurs: GT, GE, LT, LE, EQ, NE, IN, NOT_IN
- Attributs: largeur, épaisseur, type_matière, couleur, longueur

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

## Validation (14 mars 2026)

### Tests Système de Thème: 100% PASSED
- Toggle dans sidebar
- Persistence localStorage
- 21 éléments avec animations
- Hover effects sur cards
- KPI cards avec gradients

## Backlog

### P1 - Prioritaires
- [ ] Simulation What-if
- [ ] Alertes temps réel
- [ ] Persister assignations

### P2 - Secondaires
- [ ] Gantt interactif
- [ ] Replanification dynamique
- [ ] Intégration ERP

### P3 - Futurs
- [ ] Dashboard temps réel WebSockets
- [ ] Multi-sites
- [ ] IA prédictive
