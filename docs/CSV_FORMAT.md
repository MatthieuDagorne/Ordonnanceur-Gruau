# Contrat de Données CSV - Shop Scheduler Pro

## Formats DateTime

### Format Standard
Le format datetime recommandé est **ISO 8601** :
```
YYYY-MM-DDTHH:MM:SS
```

### Exemples valides
```
2026-03-18T14:30:00    # Date + heure (recommandé)
2026-03-18 14:30:00    # Date + heure avec espace
2026-03-18             # Date seule (minuit par défaut)
```

### Utilisation dans l'application
- **due_date** : Priorisation des opérations, calcul des retards
- **scheduled_start/end** : Horaires planifiés par le moteur

---

## 1. Ordres de Fabrication (`manufacturing_orders.csv`)

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `id` | string | ✅ | Code OF (ex: `OF001`, `LV1100007`) |
| 2 | `article_id` | string | ✅ | Code article - **clé de jointure pour règles** |
| 3 | `quantity` | float | ✅ | Quantité à produire |
| 4 | `due_date` | datetime | ✅ | Format: `YYYY-MM-DDTHH:MM:SS` |
| 5 | `status` | string | Non | `pending`, `in_progress`, `completed` |
| 6 | `priority` | int | Non | 0=normal, 1=prioritaire, 2=urgent |

**Exemple :**
```csv
id,article_id,quantity,due_date,status,priority
LV1100007,100235570,10,2026-03-20T10:00:00,pending,1
LV1100008,100235571,5,2026-03-19T08:00:00,pending,2
```

---

## 2. Opérations (`operations.csv`)

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `id` | string | ✅ | Code opération (ex: `LV1100007_10`) |
| 2 | `order_id` | string | ✅ | **Clé de jointure** → `manufacturing_orders.id` |
| 3 | `operation_id` | int | ✅ | N° dans la gamme (10, 20, 30...) |
| 4 | `tache_id` | string | ✅ | Type tâche (ex: `PLIAGE`, `LVT001`) |
| 5 | `centre_de_charge_id` | string | ✅ | Code centre (ex: `PLI01`, `LVC001`) |
| 6 | `production_time_minutes` | int | ✅ | Durée production |
| 7 | `setup_time_minutes` | int | Non | Durée réglage |
| 8 | `status` | string | Non | `pending`, `scheduled`, `completed` |

> ⚠️ **Important** : L'`article_id` n'est PAS dans l'opération. Il est récupéré via la jointure `order_id` → `manufacturing_orders.id`.

**Exemple :**
```csv
id,order_id,operation_id,tache_id,centre_de_charge_id,production_time_minutes,setup_time_minutes,status
LV1100007_10,LV1100007,10,LVT001,LVC001,60,15,pending
LV1100008_10,LV1100008,10,LVT001,LVC001,45,10,pending
```

---

## 3. Articles (`articles.csv`)

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `id` | string | ✅ | Code article |
| 2 | `description` | string | ✅ | Libellé |

---

## 4. Stocks (`stocks.csv`)

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `article_id` | string | ✅ | → `articles.id` |
| 2 | `quantity` | float | ✅ | Stock disponible |

---

## 5. Centres de Charge (`centres_de_charge.csv`)

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `id` | string | ✅ | Code centre (ex: `PLI01`, `LVC001`) |
| 2 | `nom` | string | ✅ | Libellé |

---

## 6. Machines (`machines.csv`)

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `id` | string | ✅ | Code machine (ex: `PLIEUSE_01`, `TP5000_1`) |
| 2 | `nom` | string | ✅ | Libellé |
| 3 | `centre_de_charge_id` | string | ✅ | → `centres_de_charge.id` |

---

## Clés de Jointure

```
manufacturing_orders.id  ←──  operations.order_id
                         
manufacturing_orders.article_id  ←→  articles.id  ←→  stocks.article_id

centres_de_charge.id  ←──  machines.centre_de_charge_id
                      ←──  operations.centre_de_charge_id
```

---

## Règles Métier

### Format
```json
{
  "name": "Interdire TP5000_1 pour article 100235570",
  "tache_id": "LVT001",
  "centre_de_charge_id": "LVC001",
  "article_id": "100235570",
  "rule_type": "FORBID",
  "machine_id": "TP5000_1"
}
```

### Logique de Matching
- **FORBID** : La machine est interdite pour les opérations matchant les critères
- **PREFER** : La machine est préférée (+100 score)
- **ALLOW** : La machine est autorisée

### Critères de Matching
Les règles matchent si **TOUS** les critères définis correspondent :
- `tache_id` : doit correspondre à l'opération
- `centre_de_charge_id` : doit correspondre à l'opération
- `article_id` : **récupéré depuis l'ordre via `order_id`**

Un critère `null` = wildcard (matche tout).

---

## Garanties du Moteur

1. **Non-chevauchement** : Une machine ne traite qu'une opération à la fois
2. **Séquence** : Les opérations d'un OF respectent l'ordre des gammes
3. **Priorité** : Les opérations urgentes (due_date proche) sont planifiées en premier
4. **Règles** : Les FORBID excluent, les PREFER priorisent
