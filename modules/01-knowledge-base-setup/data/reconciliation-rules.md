# AFS Reconciliation Rules

**Version**: 2.0 | **Last Updated**: 2025-02-15 | **Owner**: FBI CapEx / Accounting

## 1. Overview

Reconciliation ensures that financial transactions flowing through Veritas automation are accurately reflected across all systems. AFS sits in the middle of SC.os, AP, OFA, and FASL+ and is responsible for matching and clearing transactional details.

The current Alteryx automation reduces 1.5M transactions to approximately 150K open transactions that require manual investigation.

## 2. Sub-Ledger to General Ledger Reconciliation

### 2.1 OFA to FASL+ Matching

- **Source**: OFA (Oracle Fixed Assets) General Ledger
- **Target**: FASL+ Fixed Asset Sub-Ledger
- **Match Keys**: asset_id, company_code, period
- **Tolerance**: $0.01 (exact match after rounding)
- **Frequency**: Daily during close, weekly otherwise
- **Escalation**: Mismatches > $10,000 escalate to FBI CapEx lead within 24 hours

### 2.2 AP Sub-Ledger to OFA GL

- **Source**: OFA Accounts Payable Sub-Ledger
- **Target**: OFA General Ledger
- **Match Keys**: invoice_number, company_code, gl_period
- **Tolerance**: $0.01
- **Frequency**: Daily
- **Escalation**: Unmatched invoices > 5 business days trigger automatic ticket

## 3. Upstream Reconciliation

### 3.1 PO to Receipt Matching

- **Source**: SC.os Purchase Orders
- **Target**: Receipt confirmations
- **Match Keys**: po_number, line_number
- **Rules**:
  - Receipt quantity must match PO quantity within 5% tolerance
  - Receipt date must be within 30 days of expected delivery
  - POs without receipts after 90 days flagged as aging (see po_aging_not_invoiced metric)
- **Decision History**: Threshold changed from 60 to 90 days per Q4-2024 audit recommendation. The 60-day threshold was generating approximately 40% false positives.

### 3.2 Receipt to Invoice Matching

- **Source**: Receipt confirmations
- **Target**: AP Invoices
- **Match Keys**: po_number, receipt_number
- **Rules**:
  - Invoice amount must be within 10% of PO estimated price
  - Invoices exceeding 10% variance flagged for review (see invoice_variance metric)
  - Three-way match required: PO, Receipt, Invoice

### 3.3 Invoice to Asset Matching

- **Source**: AP Invoices
- **Target**: AFS Asset records
- **Match Keys**: invoice_number, asset_id
- **Rules**:
  - Asset value in AFS must match invoice amount after currency conversion
  - FX rate tolerance: 0.5% variance allowed
  - Mismatches flagged for manual review (see asset_value_mismatch metric)

## 4. AFS to OFA Asset Reconciliation

### 4.1 Asset Create Verification

- **Process**: AFS creates assets in OFA via Veritas automation
- **Verification**: Compare AFS asset_create_count with OFA acknowledgment count
- **Rules**:
  - All AFS-created assets must appear in OFA within 2 business days
  - Failed creates tracked via failed_asset_creates metric
  - Assets in account 20999 not created by AFS tracked separately (assets_not_created_by_afs metric)

### 4.2 Asset Value Reconciliation

- **Process**: Compare AFS asset values with OFA GL balances
- **Frequency**: Monthly during close
- **Rules**:
  - Total AFS asset value by entity must match OFA GL balance for LLE categories
  - Variance tracked via afs_vs_ofa_coverage metric
  - Drill-down available by entity, asset_category, currency

### 4.3 Capitalization Reconciliation

- **Process**: Verify assets are capitalized within expected timeframes
- **Rules**:
  - Assets should be capitalized within 180 days of receipt
  - Aging assets tracked via aging_not_capitalized metric
  - Decision: 180-day threshold set per FY2024 GAAP update (previously 120 days)

## 5. ERV (Estimated Remaining Value) Reconciliation

- **Process**: Compare ERV calculations with actual invoice costs
- **Rules**:
  - ERV variance > 5% flagged for review (see erv_variance metric)
  - Variance tracked by entity and currency
  - Historical ERV accuracy tracked QTD and YTD

## 6. Period Close Procedures

### 6.1 Month-End Close

1. Run all namespace metric refreshes (veritas_po_metrics, afs_asset_metrics, lle_reconciliation)
2. Review all HIGH risk items (po_amount > $500K or aging > 120 days)
3. Clear or escalate all mismatches > $10,000
4. Generate period snapshot for audit trail
5. Submit close certification to FBI CapEx lead

### 6.2 Quarter-End Close

- All month-end procedures plus:
- Full OFA to FASL+ reconciliation across all entities
- YTD variance analysis on all metrics
- GRC control attestation

### 6.3 Year-End Close

- All quarter-end procedures plus:
- Full asset inventory reconciliation
- External audit preparation package
- Historical metric trend analysis (3-year lookback)
