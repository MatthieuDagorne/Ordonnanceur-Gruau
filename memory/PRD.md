# APS Scheduler Pro - PRD

## Énoncé du Problème
Application web APS (Advanced Planning & Scheduling) pour l'ordonnancement industriel avec capacité finie, règles métier avancées et fonctionnalités MRP.

## Architecture Technique
- **Backend**: Python FastAPI + MongoDB
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)
- **Design System**: Thème clair/sombre avec variables CSS

## Fonctionnalités Implémentées

### Phase 1-5 - Fondations et APS ✅
- Calendriers par centre de charge avec horaires personnalisables
- Règles métier avec logique ET/OU
- Vue Matricielle, Comparaison de Scénarios
- Gantt Interactif, Stock Projeté Avancé
- Filtres intelligents sur toutes les pages

### Phase 6 - UI Uniformisation + CRUD Edit ✅
- Machines, Centres de Charge, Indisponibilités : Design moderne + boutons Modifier
- Tests: Backend 17/17 (100%), Frontend 10/10 (100%)

### Phase 7 - Améliorations Gantt + Correction Calendriers ✅
- Infobulles enrichies avec matières premières
- Axe temporel absolu (dates réelles)
- Périodes de fermeture visibles
- Filtre Centre de Charge

### Phase 8 - Nouvelles Fonctionnalités APS (16 mars 2026) ✅

#### 8.1 Précision Calendriers au Quart d'Heure (P0) ✅
| Fonctionnalité | Description |
|----------------|-------------|
| Format HH:MM | Calendriers utilisent `start_time` et `end_time` (ex: "07:45", "16:30") |
| Précision minute | Le moteur calcule les zones interdites en minutes exactes |
| Rétro-compatibilité | Fallback sur `start_hour`/`end_hour` si `start_time`/`end_time` absents |
| Validation jours | Filtrage automatique des jours invalides (seuls 0-6 acceptés) |

**Fichiers modifiés:**
- `scheduler_engine.py`: `CalendarManager._normalize_calendar()`, `calculate_forbidden_time_slots()`

#### 8.2 Logique Matière Temporelle (P0 - CRITIQUE) ✅
| Fonctionnalité | Description |
|----------------|-------------|
| Stock projeté dynamique | Calcul du stock disponible à l'horodatage exact de chaque opération |
| Sources de données | Stock initial + Réceptions fournisseurs + Consommations déjà planifiées |
| Report automatique | Si composants manquants, l'opération est reportée à la première date de disponibilité |
| Blocage définitif | Si un composant n'a aucune réception planifiée, l'opération est bloquée |
| Post-traitement | Réservation des matières dans l'ordre du planning après résolution |

**Comportement validé:**
- Stock ART3=0, Réception ART3 le 18/03 → Opérations planifiées à partir du 18/03
- Si ART5 reçu le 20/03 (plus tard) → Opérations reportées au 20/03
- Si aucune réception pour un composant → Opération bloquée avec `is_valid=False`

**Fichiers modifiés:**
- `scheduler_engine.py`: Contraintes matière dans CP-SAT, post-traitement
- `material_manager.py`: `check_operation_materials()` avec détection "jamais disponible"

#### 8.3 Stock Projeté par Scénario (P1) ✅
| Fonctionnalité | Description |
|----------------|-------------|
| Endpoint | `GET /api/projected-stock/{scenario_id}?article_id=XXX` |
| Timeline | Affiche tous les événements (RECEIPT/CONSUMPTION) triés par date |
| Contexte scénario | Utilise les dates des opérations planifiées du scénario spécifique |
| Détection rupture | Identifie si le stock passe en négatif et à quelle date |

**Format réponse:**
```json
{
  "scenario_name": "...",
  "projected_stock": [{
    "article_id": "ART3",
    "initial_stock": 0,
    "total_receipts": 6,
    "total_consumptions": 2,
    "final_stock": 4,
    "has_shortage": false,
    "timeline": [
      {"datetime": "...", "type": "RECEIPT", "quantity_change": 6, "stock_after": 6},
      {"datetime": "...", "type": "CONSUMPTION", "quantity_change": -1, "stock_after": 5}
    ]
  }]
}
```

**Fichiers modifiés:**
- `server.py`: Nouvel endpoint ligne 865

#### 8.4 Temps de Déplacement entre Opérations (P1) ✅
| Fonctionnalité | Description |
|----------------|-------------|
| Nouveau champ | `transfer_time_minutes` dans le modèle Operation (défaut: 0) |
| Contrainte séquence | Si op2 suit op1 dans la gamme: `start(op2) >= end(op1) + transfer_time(op1)` |
| Affichage logs | Les temps de déplacement sont affichés dans les logs du moteur |

**Fichiers modifiés:**
- `server.py`: Modèle Operation ligne 128
- `scheduler_engine.py`: Contraintes de séquence lignes 688-720

## APIs Principales

### Gantt Data Enrichi
```
GET /api/gantt/data/{scenario_id}
```

### Stock Projeté par Scénario
```
GET /api/projected-stock/{scenario_id}?article_id=XXX
```

### Ordonnancement
```
POST /api/scheduling/calculate
{
  "scenario_name": "...",
  "ignore_material": false,
  "ignore_calendars": false,
  "debug_mode": true
}
```

## Backlog

### P2 - En cours
- [ ] Améliorer les messages de blocage matière (afficher seulement les composants manquants)

### P3 - À Faire
- [ ] Export CSV du planning
- [ ] Horizon ferme (geler planning court terme)
- [ ] Dashboard temps réel WebSockets
- [ ] Replanification dynamique

## Fichiers Modifiés (Phase 8)

```
backend/
├── services/
│   ├── scheduler_engine.py  # Précision minute, logique matière
│   └── material_manager.py  # Détection "jamais disponible"
└── server.py                # Endpoint stock projeté par scénario

frontend/src/pages/
└── (Pas de modifications frontend pour cette phase)
```

## Tests Validés

### Logique Matière Temporelle
| Scénario | Résultat |
|----------|----------|
| Stock=0, Réception le 18/03 | ✅ Opérations planifiées à partir du 18/03 10:00 |
| Multi-composants, dates différentes | ✅ Report à la date du dernier composant disponible |
| Composant sans réception | ✅ Opération bloquée définitivement |
| Stock initial suffisant | ✅ Opérations planifiées immédiatement |

### Précision Quart d'Heure
| Scénario | Résultat |
|----------|----------|
| Calendrier 07:45-16:45 | ✅ Opérations planifiées après 07:45 |
| Jour invalide (7) corrigé | ✅ Calendrier FERRAGE utilise [0,3,4,5,6] |
