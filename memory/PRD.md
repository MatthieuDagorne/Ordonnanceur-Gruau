# APS Scheduler Pro - PRD

## Énoncé du Problème
Application web APS (Advanced Planning & Scheduling) pour l'ordonnancement industriel avec capacité finie, règles métier avancées et fonctionnalités MRP.

## Architecture Technique
- **Backend**: Python FastAPI + MongoDB
- **Frontend**: React + Tailwind CSS + Shadcn/UI
- **Moteur d'ordonnancement**: Google OR-Tools (CP-SAT)
- **Design System**: Thème clair/sombre avec variables CSS

## Fonctionnalités Implémentées

### Phase 1-7 - Fondations et APS ✅
- Calendriers par centre de charge avec horaires personnalisables
- Règles métier avec logique ET/OU et attributs (couleur, épaisseur...)
- Vue Matricielle, Comparaison de Scénarios
- Gantt Interactif, Stock Projeté Avancé
- Filtres intelligents sur toutes les pages
- Load Balancing multi-machines

### Phase 8 - Nouvelles Fonctionnalités APS (16 mars 2026) ✅

#### 8.0 Stratégies de Planification (16 mars 2026) ✅
**Remplace les 3 anciens modes de priorité par 2 stratégies claires :**

| Stratégie | Description | Objectif OR-Tools |
|-----------|-------------|-------------------|
| **ASAP (Au plus tôt)** | Planifie dès que possible | `minimize(makespan)` |
| **JIT (Au plus tard)** | Planifie le plus tard possible en respectant les dates de besoin | `maximize(sum(start_times))` - PENALTY × retards |

**Mode JIT - Détails :**
- Contrainte de date de besoin sur la **dernière opération** de chaque OF uniquement
- Prend en compte le temps de transfert final : `fin_op <= due_date - transfer_time`
- Si pas de `due_date`, l'OF est planifié en ASAP
- **Contrainte SOUPLE** : Si la date ne peut pas être respectée, l'ordre est planifié en retard (pas d'INFEASIBLE)
- Les ordres/opérations en retard sont marqués `is_late=true` avec `lateness_minutes`
- **Flux tiré (16/03)** : Minimisation des encours entre opérations d'un même OF

**Interface utilisateur :**
- Page Ordonnancement : 2 cartes de sélection (ASAP bleu, JIT violet)
- Page Diagnostic : Onglet "Paramètres" affiche la stratégie utilisée
- Page Diagnostic : Onglet "Retards" liste les ordres en retard avec détails
- Page Gantt : Barres rouges (#EF4444) pour les opérations en retard

### Phase 9 - Améliorations Gantt et Indisponibilités (16 mars 2026) ✅

#### 9.1 Filtres avancés Gantt ✅
- Filtre par **Ordre de Fabrication** (dropdown)
- Filtre par **Article** (dropdown)
- **Plage de dates** (sélecteurs Du/Au)
- Résumé des filtres actifs avec compteur d'opérations
- Bouton "Réinitialiser tout"

#### 9.2 Format de date complet ✅
- Dates affichées au format **"Mercredi 18 mars 2026"**
- Labels sur fond bleu pour meilleure visibilité
- Jours complets en français

#### 9.3 Indisponibilités machines ✅
- Classe `UnavailabilityManager` dans le moteur
- Contraintes `(end <= unavail_start) OR (start >= unavail_end)`
- Si machine indisponible : report automatique après la période
- Log des périodes d'indisponibilité au démarrage

#### 9.4 Fuseau horaire Europe/Paris ✅
- `PARIS_TZ = ZoneInfo('Europe/Paris')` dans le moteur
- `scheduling_start` calculé en heure de Paris
- Cohérence timezone dans tous les calculs

#### 9.5 Suppression page Matrice Compat. ✅
- Route `/matrix` supprimée
- Lien menu supprimé
- Fichier `MatrixView.js` supprimé

#### 8.1 Précision Calendriers au Quart d'Heure (P0) ✅
- Format HH:MM pour `start_time` et `end_time` (ex: "07:45", "16:30")
- Calcul des zones interdites en minutes exactes
- Validation jours invalides (seuls 0-6 acceptés)

#### 8.2 Logique Matière Temporelle avec REPLANIFICATION AUTOMATIQUE (P0 - CRITIQUE) ✅

**Workflow de replanification basé sur le BUDGET TEMPS (pas de limite d'itérations)** :

| Paramètre | Description |
|-----------|-------------|
| `max_solver_time_seconds` | Budget temps GLOBAL défini par l'utilisateur (30s, 1min, 2min...) |
| Répartition dynamique | 80% du temps restant alloué à chaque itération |
| Condition d'arrêt | Pas de rupture OU budget temps épuisé |

**Algorithme** :
1. **Itération N** : Planifier avec contraintes actuelles
2. **Post-traitement** : Simuler les consommations dans l'ordre chronologique
3. **Si rupture avec réception future** : Ajouter contrainte `start >= date_réception`
4. **Relancer** tant qu'il reste du temps et des ruptures à résoudre

**Exemple validé** :
```
Stock ART5=2, OF1_10 et OF2_10 ont besoin de 2 chacun
Réception ART5 le 20/03 : +3

Itération 1:
  - OF1_10 planifié 18/03 10:00 ✅ (stock suffisant)
  - OF2_10 planifié 18/03 10:55 ❌ (rupture: ART5=0)
  → Contrainte: OF2_10 >= 20/03 10:00

Itération 2:
  - OF1_10: 18/03 10:00 ✅
  - OF2_10: 20/03 10:00 ✅ (après réception)
  → OPTIMAL SANS RUPTURE en 2 itérations
```

**Capacité de production** :
- 200-300 opérations sur horizon 3 jours
- Centaines d'articles et réceptions fournisseurs
- Dizaines de règles métier
- Temps d'optimisation configurable par l'utilisateur

#### 8.3 Page "Stock Projeté par Scénario" (P1) ✅
| Fonctionnalité | Description |
|----------------|-------------|
| Route | `/projected-stock/:scenarioId` |
| Vue articles | Liste avec badge rupture/OK |
| Timeline | Chronologie des réceptions et consommations |
| Lien depuis Gantt | Bouton "Stock Projeté" |

#### 8.4 Temps de Déplacement (P1) ✅
- Champ `transfer_time_minutes` dans le modèle Operation
- Contrainte : `start(op2) >= end(op1) + transfer_time(op1)`
- **Bug corrigé 16/03** : La contrainte était manquante dans le moteur, maintenant appliquée systématiquement

**Contrat de données operations.csv** :
```csv
id,order_id,operation_id,tache_id,centre_de_charge_id,production_time_minutes,setup_time_minutes,status,transfer_time_minutes
OF1_10,OF1,10,T001,C001,50,5,pending,30
```

#### 8.5 Affichage des Opérations Non Planifiables (P1) ✅
- Badge rouge dans le Gantt si `unscheduled_count > 0`
- Liste avec raisons détaillées
- Seules les opérations VRAIMENT non planifiables (pas de réception future) sont listées

#### 8.6 Gap d'Optimalité (P1) ✅
- Paramètre `optimization_gap` (défaut 5%) envoyé au solveur OR-Tools
- Arrête la recherche si la solution est à moins de X% de l'optimum théorique
- Paramètre `solver.parameters.relative_gap_limit` utilisé

#### 8.7 Filtrage par Article (Stock Projeté) ✅
- Champ de recherche textuel sur la page `/projected-stock/:scenarioId`
- Filtre en temps réel sur la liste d'articles
- Combinable avec le filtre "Ruptures uniquement"

#### 8.8 Suppression Page Stock Statique ✅
- Ancienne page `/projected-stock` supprimée (données statiques inutiles)
- Navigation mise à jour
- Accès au stock projeté uniquement via le contexte d'un scénario

### Phase 9 - Gestion Avancée des Priorités et Productions (16 mars 2026) ✅

#### 9.1 Temps de Déplacement Clarifié ✅
- Temps de transfert attaché à la fin de l'opération précédente
- Affiché dans l'infobulle du Gantt (ex: "Transfert: +30 min")
- Ne bloque pas l'opération suivante si elle est reportée pour matière

#### 9.2 Entrée en Stock des Articles Fabriqués ✅
- Quand la dernière opération d'un OF termine, la quantité produite entre en stock
- `article_id` de l'ordre = article fabriqué
- `quantity` de l'ordre = quantité entrée en stock
- **Date entrée = fin de la dernière opération + temps de transfert final** (Bug P0 corrigé le 16/03)
- **Le stock fabriqué peut servir à d'autres opérations**
- **Affichage dans Stock Projeté** : Type `PRODUCTION_RECEIPT` avec badge "Fabrication" vert foncé

#### 9.3 Gestion des Priorités (P1) ✅
- `priority=1` → OF urgent, `priority=0` → OF normal
- Toutes les opérations d'un OF urgent deviennent urgentes
- **Propagation de priorité** (1 niveau) : Si OF urgent consomme un article fabriqué par OF non-urgent, ce dernier devient urgent

#### 9.4 Affichage Urgent dans le Gantt ✅
- Badge jaune ⚡ sur les opérations urgentes
- Légende mise à jour avec "Urgent"
- Infobulle enrichie : quantité fabriquée + temps de transfert

#### 9.5 Diagnostic Intégré au Scénario ✅
- Ancienne page statique `/diagnostic` supprimée
- Nouvelle page `/diagnostic/:scenarioId` avec 4 onglets :
  - **Priorités** : OFs urgents, log de propagation détaillé
  - **Matière** : Opérations reportées avec composants bloquants
  - **Productions** : Tableau des entrées en stock (OF, article, qté, date)
  - **Alertes** : Opérations non planifiables
- Accès via bouton "Diagnostic" dans le Gantt

## APIs Principales

### Ordonnancement
```json
POST /api/scheduling/calculate
{
  "scenario_name": "...",
  "max_solver_time_seconds": 120,  // Budget temps en secondes
  "ignore_material": false
}

Response: {
  "material_iteration": 2,         // Nombre d'itérations
  "total_solver_time": 0.05,       // Temps CPU solveur
  "total_elapsed_time": 0.08,      // Temps réel total
  "unscheduled_operations": [],    // Opérations sans solution
  "unscheduled_count": 0
}
```

### Stock Projeté par Scénario
```
GET /api/projected-stock/{scenario_id}?article_id=XXX
```

## Backlog

### P3 - À Faire
- [ ] Export CSV du planning
- [ ] Horizon ferme (geler planning court terme)
- [ ] Dashboard temps réel WebSockets
- [ ] Replanification dynamique (événements panne machine)
- [ ] Propagation de priorité récursive (multi-niveaux)

## Tests Validés

### Replanification Automatique Sans Limite d'Itérations
| Scénario | Résultat |
|----------|----------|
| Budget 30s, 2 itérations nécessaires | ✅ Converge en 0.03s |
| Budget 120s, 2 itérations nécessaires | ✅ Converge en 0.02s |
| OF2_10 en rupture ART5 | ✅ Reporté au 20/03 (date réception) |
| Transfer time 30min | ✅ OF1_10 finit → +30min → OF1_20 commence |
| Gap d'optimalité 5% | ✅ Paramètre passé au solveur |

### Phase 9 - Urgences, Productions, Diagnostic (16 mars 2026)
| Fonctionnalité | Résultat |
|----------------|----------|
| Badge Urgent dans Gantt | ✅ Opérations jaunes avec icône ⚡ |
| Quantité fabriquée dans infobulle | ✅ "Qté fabriquée: 5" |
| Temps de transfert dans infobulle | ✅ "Transfert: +30 min" |
| Productions dans résultat | ✅ Liste des entrées en stock |
| Page Diagnostic intégrée | ✅ 4 onglets: Priorités, Matière, Productions, Alertes |
| Propagation priorité (1 niveau) | ✅ OF non-urgent devient urgent si fournit OF urgent |

### Corrections du 16 mars 2026
| Bug | Correction |
|-----|------------|
| Transfer time non appliqué | Contrainte ajoutée dans la boucle de séquence gamme |
| Gap optimalité ignoré | Paramètre `relative_gap_limit` ajouté au solveur |
| Page stock statique | Supprimée, navigation mise à jour |
| Pas de filtre article | Champ de recherche ajouté |
| Page Diagnostic statique | Supprimée, intégrée au scénario |
| **Entrée en stock sans temps de transfert** | **Date de production = fin_dernière_op + transfer_time** |
| **Productions non visibles dans Stock Projeté** | **Événements PRODUCTION_RECEIPT ajoutés à la timeline** |
| **Infobulle Gantt mal positionnée** | **Tooltip suit le curseur (tooltipPosition state)** |
| **3 modes de priorité confus** | **Remplacés par 2 stratégies claires (ASAP/JIT)** |
| **JIT retourne INFEASIBLE si dates non respectables** | **Contraintes souples avec pénalité de retard** |
