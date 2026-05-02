# AFS Integrity Metrics — Metric Definitions

**Version**: 1.0 | **Last Updated**: 2025-03-01 | **Owner**: FBI CapEx Team

## Namespace: veritas_po_metrics

Query: `SELECT * FROM po_ordering_table WHERE account_code = 20999`

### Metric: po_total_spend

- **Type**: SUM
- **Value Column**: po_amount
- **Breakdown Column**: currency
- **Period Column**: po_received_at
- **Periods**: MTD, QTD, YTD
- **Dimensions**: entity, region, cost_center
- **Filters**:
  - po_amount > 300
  - line_category IN [AHU, GENERATOR]
- **Collections**: po_number

### Metric: po_aging_not_invoiced

- **Type**: COUNT, SUM
- **Value Column**: po_amount
- **Period Column**: po_received_at
- **Periods**: MTD, QTD
- **Dimensions**: entity, currency, cost_center
- **Filters**:
  - days_since_receipt > 90
  - invoice_status = 'PENDING'
- **Description**: Number and functional amount of POs aging more than 90 days but not yet invoiced.

### Metric: invoice_variance

- **Type**: COUNT, SUM
- **Value Column**: variance_amount
- **Period Column**: invoice_date
- **Periods**: MTD, QTD, YTD
- **Dimensions**: entity, currency
- **Filters**:
  - variance_pct > 10
- **Description**: Number and functional amount of invoices that led to more than 10% variance than estimated PO price.

## Namespace: afs_asset_metrics

Query: `SELECT * FROM afs_asset_transactions WHERE status IN ('CREATED','FAILED','PENDING')`

### Metric: asset_create_count

- **Type**: COUNT
- **Value Column**: asset_id
- **Period Column**: created_at
- **Periods**: MTD, QTD, YTD
- **Dimensions**: entity, asset_category, region
- **Description**: Total number of assets created by AFS.

### Metric: asset_create_value

- **Type**: SUM
- **Value Column**: asset_amount
- **Breakdown Column**: currency
- **Period Column**: created_at
- **Periods**: MTD, QTD, YTD
- **Dimensions**: entity, asset_category, region, cost_center
- **Description**: Total dollar value of assets created by AFS.

### Metric: failed_asset_creates

- **Type**: COUNT, SUM
- **Value Column**: asset_amount
- **Period Column**: created_at
- **Periods**: MTD, QTD
- **Dimensions**: entity, asset_category, failure_reason
- **Filters**:
  - status = 'FAILED'
- **Description**: Number and dollar value of failed asset create transactions.

### Metric: asset_value_mismatch

- **Type**: COUNT, SUM
- **Value Column**: mismatch_amount
- **Period Column**: reconciled_at
- **Periods**: MTD, QTD
- **Dimensions**: entity, asset_category
- **Filters**:
  - ofa_value != afs_value
- **Description**: Assets where value does not tie out between AFS and OFA.

### Metric: aging_not_capitalized

- **Type**: COUNT, SUM
- **Value Column**: asset_amount
- **Period Column**: received_at
- **Periods**: MTD, QTD
- **Dimensions**: entity, asset_category, region
- **Filters**:
  - days_since_receipt > 180
  - capitalization_status = 'PENDING'
- **Description**: Assets aging more than 180 days but not yet capitalized.

### Metric: erv_variance

- **Type**: COUNT, SUM
- **Value Column**: erv_variance_amount
- **Period Column**: erv_date
- **Periods**: MTD, QTD, YTD
- **Dimensions**: entity, currency
- **Filters**:
  - erv_variance_pct > 5
- **Description**: Assets with more than 5% ERV variance compared to invoice cost.

## Namespace: lle_reconciliation

Query: `SELECT * FROM lle_reconciliation_view WHERE category = 'LLE'`

### Metric: afs_vs_ofa_coverage

- **Type**: SUM
- **Value Column**: functional_amount
- **Breakdown Column**: system_source
- **Period Column**: period_end_date
- **Periods**: MTD, QTD, YTD
- **Dimensions**: entity, asset_category
- **Description**: Proportion of costs processed by AFS vs total balance in OFA for LLE categories.

### Metric: assets_not_created_by_afs

- **Type**: COUNT
- **Value Column**: asset_id
- **Period Column**: created_at
- **Periods**: MTD, QTD
- **Dimensions**: entity, asset_category
- **Filters**:
  - account_code = 20999
  - created_by != 'AFS'
- **Description**: Number of 20999 assets not created by AFS.

## Fixed Dimensions

All metrics support drill-down via these fixed dimensions:

| Dimension | Column | Description |
|-----------|--------|-------------|
| Currency | currency | Transaction currency (USD, EUR, GBP, etc.) |
| GL Segments | gl_segment_1 through gl_segment_7 | 7 General Ledger segments |
| Company Code | company_code | Legal entity code |
| Cost Center | cost_center | Cost center identifier |
| Asset ID | asset_id | Individual asset identifier |
| PO Number | po_number | Purchase order number |
| Invoice Number | invoice_number | Invoice identifier |
