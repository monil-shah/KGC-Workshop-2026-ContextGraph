# AFS Namespace Configurations

**Version**: 1.0 | **Last Updated**: 2025-03-01 | **Owner**: AFS Engineering

## Overview

Namespaces group related metrics that share a common source query. Each namespace defines:
- A source query executed against DataStudio Redshift
- One or more MetricDefinitions applied to the query output
- Period-based snapshots (MTD, QTD, YTD)

## Namespace: veritas_po_metrics

```json
{
  "name": "veritas_po_metrics",
  "query": "SELECT * FROM po_ordering_table WHERE account_code = 20999",
  "definitions": [
    {
      "name": "po_total_spend",
      "type": "SUM",
      "value": {"value_column": "po_amount", "breakdown_column": "currency"},
      "period_column": "po_received_at",
      "dimensions": [
        {"name": "entity", "column": "entity"},
        {"name": "region", "column": "region"},
        {"name": "cost_center", "column": "cost_center"}
      ],
      "filters": [
        {"column": "po_amount", "operator": ">", "value": 300},
        {"column": "line_category", "operator": "in", "value": ["AHU", "GENERATOR"]}
      ],
      "collections": [{"column": "po_number"}],
      "periods": ["mtd", "qtd", "ytd"]
    },
    {
      "name": "po_aging_not_invoiced",
      "type": "COUNT",
      "value": {"value_column": "po_amount"},
      "period_column": "po_received_at",
      "dimensions": [
        {"name": "entity", "column": "entity"},
        {"name": "currency", "column": "currency"}
      ],
      "filters": [
        {"column": "days_since_receipt", "operator": ">", "value": 90},
        {"column": "invoice_status", "operator": "=", "value": "PENDING"}
      ],
      "periods": ["mtd", "qtd"]
    }
  ]
}
```

## Namespace: afs_asset_metrics

```json
{
  "name": "afs_asset_metrics",
  "query": "SELECT * FROM afs_asset_transactions WHERE status IN ('CREATED','FAILED','PENDING')",
  "definitions": [
    {
      "name": "asset_create_count",
      "type": "COUNT",
      "value": {"value_column": "asset_id"},
      "period_column": "created_at",
      "dimensions": [
        {"name": "entity", "column": "entity"},
        {"name": "asset_category", "column": "asset_category"},
        {"name": "region", "column": "region"}
      ],
      "periods": ["mtd", "qtd", "ytd"]
    },
    {
      "name": "failed_asset_creates",
      "type": "COUNT",
      "value": {"value_column": "asset_amount"},
      "period_column": "created_at",
      "dimensions": [
        {"name": "entity", "column": "entity"},
        {"name": "asset_category", "column": "asset_category"},
        {"name": "failure_reason", "column": "failure_reason"}
      ],
      "filters": [
        {"column": "status", "operator": "=", "value": "FAILED"}
      ],
      "periods": ["mtd", "qtd"]
    }
  ]
}
```

## Namespace: lle_reconciliation

```json
{
  "name": "lle_reconciliation",
  "query": "SELECT * FROM lle_reconciliation_view WHERE category = 'LLE'",
  "definitions": [
    {
      "name": "afs_vs_ofa_coverage",
      "type": "SUM",
      "value": {"value_column": "functional_amount", "breakdown_column": "system_source"},
      "period_column": "period_end_date",
      "dimensions": [
        {"name": "entity", "column": "entity"},
        {"name": "asset_category", "column": "asset_category"}
      ],
      "periods": ["mtd", "qtd", "ytd"]
    }
  ]
}
```

## Processing Architecture

### NamespaceRefreshJobSubmit Lambda

Pulls all configured namespaces and submits an individual Glue job for each namespace to refresh underlying metrics.

### NamespaceRefreshJob (PySpark)

1. Fetch NamespaceDefinition by name
2. Submit query to DataStudio Redshift
3. Fetch accounting calendar periods
4. Loop through all MetricDefinitions:
   - Apply filters and aggregations
   - Calculate period-based outputs (MTD, QTD, YTD)
5. Output MetricCalculationOutput to data lake

### MetricOutput Schema

| Field | Type | Example |
|-------|------|---------|
| namespace | String | veritas_po_metrics |
| metric_name | String | po_total_spend |
| period | String | 2025-03 |
| period_type | String | MTD |
| metric_value | JSON | {"total": "5000000.00", "group_by": {"USD": "2000000.00", "EUR": "2500000.00"}} |
| breakdown | JSON | {"EMEA": {"total": "3000000.00", ...}, "NA": {"total": "2000000.00", ...}} |
| snapshot_date | String | 2025-03-05 |

## Decision Log

### DEC-001: DataStudio Redshift over LakeFormation

- **Date**: 2025-01-15
- **Decision**: Use DataStudio Redshift for query compute
- **Rationale**: Customers can test queries in DataStudio and have easier transition to onboard into metrics framework. Simpler implementation using existing infrastructure.
- **Trade-off**: Less control over data pipeline vs LakeFormation's full serverless flexibility.

### DEC-002: PySpark over Deequ for metric processing

- **Date**: 2025-01-20
- **Decision**: Use PySpark for metric calculation
- **Rationale**: Full flexibility in calculations, custom aggregations, complex hierarchical rollups. Native support for grouping sets and pivoting.
- **Trade-off**: More initial development time vs Deequ's faster setup for standard metrics.

### DEC-003: PO aging threshold change (60 → 90 days)

- **Date**: 2024-10-15
- **Decision**: Changed PO aging threshold from 60 to 90 days
- **Rationale**: Q4 2024 audit found that 60-day threshold was generating approximately 40% false positives, overwhelming the investigation team.
- **Impact**: Reduced false positives by ~35%, allowing team to focus on genuine aging issues.

### DEC-004: LLE category reclassification

- **Date**: 2024-07-01
- **Decision**: Added GENERATOR to LLE line categories alongside AHU
- **Rationale**: FY2024 GAAP update required reclassification of generator assets under LLE.
- **Impact**: Increased LLE transaction volume by ~15%.

### DEC-005: Capitalization aging threshold (120 → 180 days)

- **Date**: 2024-08-01
- **Decision**: Extended capitalization aging threshold from 120 to 180 days
- **Rationale**: FY2024 GAAP update allowed extended capitalization windows for complex infrastructure assets.
- **Impact**: Reduced false aging alerts by ~25%.
