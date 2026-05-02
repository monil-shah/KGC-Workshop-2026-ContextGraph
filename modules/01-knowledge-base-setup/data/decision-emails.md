# AFS Decision Emails Archive

**Source**: FBI CapEx / Accounting / Finance email threads
**Purpose**: Capture decisions made via email that shaped current metric configurations

---

## Email Thread: RE: PO Aging Threshold Review

**From**: Sarah Chen (FBI CapEx Lead)
**To**: AFS-Finance-Team@
**Date**: 2024-10-15
**Subject**: RE: PO Aging Threshold Review

Team,

After reviewing the Q4 audit findings, I'm approving the change to increase the PO aging threshold from 60 days to 90 days effective immediately.

**Decision**: Change po_aging_not_invoiced threshold from 60 → 90 days
**Rationale**: The 60-day threshold was generating approximately 40% false positives during the Q3 close cycle. The audit team confirmed that 90 days better reflects actual procurement timelines for infrastructure equipment.
**Impact**: Expected to reduce false positive alerts by ~35%, allowing the team to focus on genuine aging issues.
**Approved by**: Sarah Chen, FBI CapEx Lead
**Effective**: October 15, 2024

Please update the metric configuration accordingly.

---

## Email Thread: RE: GENERATOR Category Reclassification

**From**: Michael Torres (Finance Director)
**To**: AFS-Finance-Team@, Accounting-ATEAM@
**Date**: 2024-07-01
**Subject**: RE: FY2024 GAAP Update — LLE Category Changes

All,

Per the FY2024 GAAP update, generator assets must now be classified under LLE (Long-Lived Equipment) alongside AHU. This affects the veritas_po_metrics namespace — the line_category filter needs to include GENERATOR.

**Decision**: Add GENERATOR to LLE line_category filter in veritas_po_metrics
**Rationale**: FY2024 GAAP update requires reclassification of generator assets under LLE for proper capitalization treatment.
**Impact**: Increases LLE transaction volume by approximately 15%. All existing GENERATOR assets in account 20999 will now flow through LLE reconciliation.
**Approved by**: Michael Torres, Finance Director
**Effective**: July 1, 2024

Accounting team — please ensure the Alteryx workflows are also updated to reflect this change.

---

## Email Thread: RE: Capitalization Window Extension

**From**: Sarah Chen (FBI CapEx Lead)
**To**: AFS-Engineering@, Finance-Controls@
**Date**: 2024-08-01
**Subject**: RE: Asset Capitalization Aging Threshold

Engineering,

Following the GAAP update and discussion with external auditors, we're extending the capitalization aging threshold from 120 days to 180 days.

**Decision**: Extend aging_not_capitalized threshold from 120 → 180 days
**Rationale**: Complex infrastructure assets (especially generators and large AHU units) have longer installation and commissioning timelines. The 120-day window was triggering premature aging alerts for assets still in commissioning.
**Impact**: Reduces false aging alerts by approximately 25%. Aligns with updated GAAP guidance for complex infrastructure.
**Approved by**: Sarah Chen, FBI CapEx Lead; Michael Torres, Finance Director
**Effective**: August 1, 2024

---

## Email Thread: RE: DataStudio vs LakeFormation Decision

**From**: Raj Patel (AFS Engineering Lead)
**To**: AFS-Engineering@, FBI-CapEx@
**Date**: 2025-01-15
**Subject**: RE: Metrics Framework — Compute Decision

Team,

After evaluating both options, we're going with DataStudio Redshift for the metrics query compute layer.

**Decision**: Use DataStudio Redshift over LakeFormation Glue for metric query compute
**Rationale**: Key factors:
1. Customers can test queries directly in DataStudio before onboarding to metrics framework
2. Simpler implementation leveraging existing DataStudio infrastructure
3. Better query performance due to Redshift-specific optimizations
**Trade-off**: Less control over data pipeline compared to LakeFormation, and we're dependent on DataStudio team for dataset onboarding prioritization.
**Approved by**: Raj Patel, AFS Engineering Lead
**Effective**: January 15, 2025

---

## Email Thread: RE: March Close — Failed Asset Creates Investigation

**From**: Lisa Wang (FBI CapEx Analyst)
**To**: AFS-Engineering@, FBI-CapEx@
**Date**: 2025-03-18
**Subject**: RE: Spike in Failed Asset Creates — March 2025

Team,

Investigated the spike in failed asset creates this month (23 failures vs 8 last month). Root cause identified:

**Finding**: 15 of 23 failures are GENERATOR category assets that were onboarded on March 15th. The OFA interface was not updated to accept the new GENERATOR sub-category codes.
**Decision**: Hotfix deployed March 18th to add GENERATOR sub-category codes to OFA interface mapping.
**Impact**: Failures should return to baseline (~8/month) by next week. The 15 failed GENERATOR assets will be reprocessed.
**Action items**:
- AFS Engineering: Monitor reprocessing of 15 failed assets (due March 20)
- FBI CapEx: No manual intervention needed, automated reprocessing will handle
**Resolved by**: Lisa Wang, FBI CapEx Analyst; Raj Patel, AFS Engineering Lead

---

## Email Thread: RE: ERV Variance Threshold Discussion

**From**: Michael Torres (Finance Director)
**To**: FBI-CapEx@, Finance-Controls@
**Date**: 2025-02-10
**Subject**: RE: ERV Variance Threshold — Keep at 5% or Lower?

After reviewing Q4 data, I'm keeping the ERV variance threshold at 5%.

**Decision**: Maintain erv_variance threshold at 5% (no change)
**Rationale**: Analysis of Q4 2024 data shows that lowering to 3% would increase flagged items by 60% without meaningful improvement in catching genuine issues. The 5% threshold catches 94% of actual ERV problems while keeping false positives manageable.
**Data**: At 5%: 47 flagged items, 44 genuine (94% precision). At 3%: 75 flagged items, 46 genuine (61% precision).
**Approved by**: Michael Torres, Finance Director
**Effective**: Continuing existing threshold
