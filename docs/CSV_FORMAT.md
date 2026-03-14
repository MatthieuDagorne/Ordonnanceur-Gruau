# Contrat de Données CSV - Shop Scheduler Pro

## Formats DateTime

### Format Standard (ISO 8601)
```
YYYY-MM-DDTHH:MM:SS
```

### Exemples valides
| Format | Exemple | Interprétation |
|--------|---------|----------------|
| Date + heure (recommandé) | `2026-03-18T14:30:00` | 18 mars 2026 à 14h30 |
| Date + heure (espace) | `2026-03-18 14:30:00` | 18 mars 2026 à 14h30 |
| Date seule | `2026-03-18` | 18 mars 2026 à **00:00:00** |

---

## 1. Ordres de Fabrication (`manufacturing_orders.csv`)

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `id` | string | ✅ | Code OF (ex: `LV1100007`) |
| 2 | `article_id` | string | ✅ | Code article - **clé pour les règles métier** |
| 3 | `quantity` | float | ✅ | Quantité à produire |
| 4 | `due_date` | datetime | ✅ | Format: `YYYY-MM-DDTHH:MM:SS` |
| 5 | `status` | string | Non | `pending`, `in_progress`, `completed` |
| 6 | `priority` | int | Non | 0=normal, 1=prioritaire, 2=urgent |

**Exemple :**
```csv
id,article_id,quantity,due_date,status,priority
LV1100007,100235570,10,2026-03-20T14:30:00,pending,1
```

---

## 2. Opérations (`operations.csv`)

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `id` | string | ✅ | Code opération (ex: `LV1100007_10`) |
| 2 | `order_id` | string | ✅ | **Clé de jointure** → `manufacturing_orders.id` |
| 3 | `operation_id` | int | ✅ | N° dans la gamme (10, 20, 30...) |
| 4 | `tache_id` | string | ✅ | Type tâche (ex: `LVT001`) |
| 5 | `centre_de_charge_id` | string | ✅ | Code centre (ex: `LVC001`) |
| 6 | `production_time_minutes` | int | ✅ | Durée production |
| 7 | `setup_time_minutes` | int | Non | Durée réglage |
| 8 | `status` | string | Non | `pending`, `scheduled`, `completed` |

> ⚠️ **Important** : L'`article_id` est récupéré via la jointure `order_id` → `manufacturing_orders.id`.

---

## 3. Besoins Matière par Opération (`operation_materials.csv`) 🆕

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `id` | string | ✅ | Code opération (même que `operations.id`) |
| 2 | `order_id` | string | ✅ | Code OF |
| 3 | `operation_id` | int | ✅ | N° opération dans la gamme |
| 4 | `article_composant_id` | string | ✅ | Code du composant nécessaire |
| 5 | `quantity` | float | ✅ | Quantité nécessaire |

> Une opération peut avoir plusieurs lignes (plusieurs composants).

**Exemple :**
```csv
id,order_id,operation_id,article_composant_id,quantity
LV1100001_10,LV1100001,10,100541201,1
LV1100001_10,LV1100001,10,100541202,2
```

---

## 4. Réceptions Fournisseurs Planifiées (`planned_supplier_receipts.csv`) 🆕

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `article_id` | string | ✅ | Code article |
| 2 | `quantity` | float | ✅ | Quantité attendue |
| 3 | `planned_date` | datetime | ✅ | Date/heure de réception prévue |

**Exemple :**
```csv
article_id,quantity,planned_date
100541201,5,2026-03-16T10:00:00
100541203,5,2026-03-15T10:30:00
```

---

## 5. Stocks (`stocks.csv`)

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `article_id` | string | ✅ | Code article |
| 2 | `quantity` | float | ✅ | Stock disponible |

---

## 6. Articles (`articles.csv`)

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `id` | string | ✅ | Code article |
| 2 | `description` | string | ✅ | Libellé |

---

## 7. Centres de Charge (`centres_de_charge.csv`)

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `id` | string | ✅ | Code centre (ex: `LVC001`) |
| 2 | `nom` | string | ✅ | Libellé |

---

## 8. Machines (`machines.csv`)

| # | Colonne | Type | Obligatoire | Description |
|---|---------|------|-------------|-------------|
| 1 | `id` | string | ✅ | Code machine (ex: `TP5000_1`) |
| 2 | `nom` | string | ✅ | Libellé |
| 3 | `centre_de_charge_id` | string | ✅ | → `centres_de_charge.id` |

---

## Clés de Jointure

```
manufacturing_orders.id  ←──  operations.order_id
                         ←──  operation_materials.order_id

manufacturing_orders.article_id  ←→  articles.id  ←→  stocks.article_id

operation_materials.article_composant_id  ←→  stocks.article_id
                                          ←→  planned_supplier_receipts.article_id

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

### Critères de Matching
- **article_id** : récupéré depuis l'ordre via `order_id`
- **tache_id** : depuis l'opération
- **centre_de_charge_id** : depuis l'opération

Un critère `null` = wildcard (matche tout).

---

## Garanties du Moteur

1. **Non-chevauchement** : Une machine ne traite qu'une opération à la fois
2. **Séquence** : Les opérations d'un OF respectent l'ordre des gammes
3. **Priorité** : Les opérations urgentes (date_besoin proche) sont planifiées en premier
4. **Règles** : Les FORBID excluent, les PREFER priorisent
5. **Matière** : Vérification de la disponibilité des composants avec projection du stock

---

## Paramètres de l'Ordonnancement

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `ignore_rules` | bool | false | Ignorer les règles métier |
| `ignore_material` | bool | false | Ignorer les contraintes matière |
| `auto_assign_machines` | bool | true | Auto-assignation des machines |
| `max_solver_time_seconds` | int | 60 | Temps maximum de calcul |
