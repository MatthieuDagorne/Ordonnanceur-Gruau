# APS Scheduler Pro - PRD

## Énoncé du Problème
Application web APS (Advanced Planning & Scheduling) pour l'ordonnancement industriel avec capacité finie, règles métier avancées et fonctionnalités MRP.

## Architecture Technique
- **Backend**: Python FastAPI + MongoDB
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)
- **Design System**: Thème clair/sombre avec variables CSS

## Fonctionnalités Implémentées

### Phase 1 - Fondations ✅
- Calendriers par centre de charge
- Page stock projeté
- Extension attributs articles (type_matière, épaisseur, largeur, etc.)
- Règles métier sur attributs

### Phase 2 - Règles Avancées ✅
- Édition CRUD complète des règles
- Logique ET/OU dans les conditions
- Groupes de conditions multiples

### Phase 3 - Transformation APS ✅
- Page Ordonnancement avec scénarios
- Options de priorité (Date, Matière, Équilibré)
- Dashboard APS avec KPIs

### Phase 4 - P1/P2 Features ✅
- Vue Matricielle Compatibilités (/matrix)
- Comparaison de Scénarios (/scenarios)
- Gantt Interactif (/gantt/:id)
- Stock Projeté Avancé avec dates ordonnancées

### Phase 5 - Améliorations Ergonomiques (14 mars 2026) ✅
- Calendriers en quarts d'heure (HH:MM)
- État des données complet (ERP, Supply Chain, Configuration)
- Filtres intelligents sur 4 pages

### Phase 6 - UI Uniformisation + CRUD Edit (14 mars 2026) ✅

#### P0 - Uniformisation UI (3 pages)
| Page | Avant | Après |
|------|-------|-------|
| Machines | Boutons noirs, coins carrés, classes Tailwind directes | Variables CSS, coins arrondis (rounded-lg), thème cohérent |
| Centres de Charge | Boutons noirs, coins carrés | Variables CSS, coins arrondis, intégration calendrier |
| Indisponibilités | Boutons noirs, coins carrés | Variables CSS, coins arrondis, icône AlertTriangle |

#### P1 - Fonctionnalité d'Édition (CRUD Complet)
| Page | Endpoints | Fonctionnalités |
|------|-----------|-----------------|
| Machines | PUT /api/machines/{id} | Bouton crayon, formulaire pré-rempli, ID désactivé en édition |
| Centres de Charge | PUT /api/centres-de-charge/{id} | Bouton crayon, formulaire pré-rempli, sélection calendrier |
| Indisponibilités | PUT /api/unavailability/{id} | Bouton crayon, formulaire pré-rempli, dates datetime-local |

**Tests passés**: Backend 17/17 (100%), Frontend 10/10 (100%)

## APIs Principales

### CRUD Machines
```
GET    /api/machines                    # Liste toutes les machines
POST   /api/machines                    # Créer une machine
PUT    /api/machines/{machine_id}       # Modifier (nom, centre, description)
DELETE /api/machines/{machine_id}       # Supprimer
```

### CRUD Centres de Charge
```
GET    /api/centres-de-charge           # Liste tous les centres
POST   /api/centres-de-charge           # Créer un centre
PUT    /api/centres-de-charge/{id}      # Modifier (nom, description, calendar_id)
DELETE /api/centres-de-charge/{id}      # Supprimer
```

### CRUD Indisponibilités
```
GET    /api/unavailability              # Liste toutes les indisponibilités
POST   /api/unavailability              # Créer une indisponibilité
PUT    /api/unavailability/{id}         # Modifier (machine, dates, raison)
DELETE /api/unavailability/{id}         # Supprimer
```

### CRUD Calendriers (déjà complet)
```
GET    /api/calendars
POST   /api/calendars
PUT    /api/calendars/{id}
DELETE /api/calendars/{id}
```

## Backlog

### P2 - Améliorations Gantt (En cours)
- [ ] Infobulles enrichies (disponibilité matières premières)
- [ ] Axe temporel avec dates/heures réelles + périodes fermeture
- [ ] Filtre par centre de charge

### P2 - Documentation
- [ ] Réponse sur concept "Horizon Ferme" (bonnes pratiques industrielles)

### P3 - À Faire
- [ ] Export CSV du planning
- [ ] Dashboard temps réel WebSockets
- [ ] Replanification dynamique
- [ ] Multi-sites
- [ ] IA prédictive
- [ ] Intégration ERP

## Fichiers Modifiés (Phase 6)

```
backend/
├── server.py                     # +PUT /api/machines, +PUT /api/unavailability

frontend/src/pages/
├── Machines.js                   # Refonte UI + CRUD Edit complet
├── CentresDeCharge.js            # Refonte UI + CRUD Edit complet
├── Unavailability.js             # Refonte UI + CRUD Edit complet
```

## Tests Reports
- `/app/test_reports/iteration_11.json` - Validation P0/P1 (100% pass)
