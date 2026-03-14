# APS Scheduler Pro - PRD

## Énoncé du Problème
Application web APS (Advanced Planning & Scheduling) pour l'ordonnancement industriel.

## Architecture Technique
- **Backend**: Python FastAPI
- **Frontend**: React
- **Base de données**: MongoDB
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)

## Fonctionnalités APS Implémentées

### 1. Règles Métier avec Conditions Multiples ET/OU ✅ (14 mars 2026)

#### Structure des Conditions
```json
{
  "name": "Règle complexe",
  "rule_type": "FORBID",
  "machine_id": "TP5000_1",
  "attribute_conditions": [
    {
      "conditions": [
        {"attribute_name": "width", "operator": "GT", "value": "500"},
        {"attribute_name": "thickness", "operator": "LT", "value": "10"}
      ],
      "logic": "AND"
    },
    {
      "conditions": [
        {"attribute_name": "material_type", "operator": "EQ", "value": "Acier"}
      ],
      "logic": "AND"
    }
  ],
  "conditions_logic": "OR"
}
```

#### Exemple Logique
`(largeur > 500 ET épaisseur < 10) OU (type_matière = Acier)`

#### Interface UI
- Mode **"Simple (ID)"** : article_id, tache_id, centre_de_charge_id
- Mode **"Attributs (ET/OU)"** : Groupes de conditions avec opérateurs
- **Dropdown "Entre groupes"** : ET / OU
- **Dropdown dans groupe** : ET / OU
- **Boutons +/-** : Ajouter/supprimer des conditions
- **Bouton "Ajouter un groupe"** : Créer un nouveau groupe

#### Opérateurs Supportés
- `GT` (>), `GE` (>=), `LT` (<), `LE` (<=)
- `EQ` (=), `NE` (!=)
- `IN` (dans la liste), `NOT_IN` (pas dans la liste)

#### Attributs Disponibles
- `width` (Largeur mm)
- `length` (Longueur mm)
- `thickness` (Épaisseur mm)
- `material_type` (Type de matière)
- `color` (Couleur)

### 2. Page Ordonnancement APS Complète ✅

#### Modes de Priorité
- **Priorité Date de Besoin**
- **Priorité Disponibilité Matière**
- **Mode Équilibré** (avec sliders de poids)

#### Paramètres du Solveur
- Durée Maximum : 30s à 10min
- Gap d'Optimalité : 1-20%

#### Options Avancées
- Ignorer règles/matière/calendriers
- Respecter séquence des gammes

### 3. Dashboard APS avec KPIs ✅
- OTD, Ordres en retard, Utilisation machines, WIP

### 4. Capacité Finie avec Calendriers ✅
- production_time + setup_time
- Calendriers par centre de charge

### 5. Planification Multi-Niveaux (BOM/MRP) ✅
- Import BOM
- Explosion de nomenclature
- Calcul MRP

## Validation (14 mars 2026)

### Tests Conditions Multiples: 13/13 PASSED
- POST /api/rules avec attribute_conditions
- GET /api/rules retourne attribute_conditions
- PUT /api/rules accepte attribute_conditions
- Frontend groupes et dropdowns ET/OU
- Évaluation correcte des conditions

## Backlog

### P1 - Prioritaires
- [ ] Simulation What-if
- [ ] Alertes temps réel
- [ ] Persister assignations

### P2 - Secondaires
- [ ] Replanification dynamique
- [ ] Intégration ERP
- [ ] Export CSV

### P3 - Futurs
- [ ] Gantt interactif
- [ ] Dashboard temps réel
