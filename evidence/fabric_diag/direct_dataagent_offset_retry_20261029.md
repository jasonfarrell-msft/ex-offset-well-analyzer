SYNTHETIC DATA • v1.1.0 • DEVELOPMENT / OFFSET COMPARISON ONLY

Section-level offset metrics from `serving.offset_section_summary` are not directly retrievable with the available tool configuration, but we do have target–well–level summary context from the allowed summary views for SYN-TARGET-0001 and the two requested offset wells.

Below is the comparison using accepted run count and penetration-rate context, keeping accepted vs source vs quarantined distinct and using only the synthetic summary data returned.

---

### 1. Context: Target SYN-TARGET-0001, selected offset wells

From the summary views (per target–well pair):

| Metric                                           | SYN-WELL-0002 | SYN-WELL-0019 |
|-------------------------------------------------|---------------|---------------|
| `target_well_source_run_count`                  | 7             | 4             |
| `target_well_accepted_run_count`                | 7             | 4             |
| `target_well_quarantined_run_count`            | 0             | 0             |
| `target_well_warning_run_count`                | 0             | 0             |
| `target_well_error_run_count`                  | 0             | 0             |
| `target_well_accepted_footage_ft`              | 8,966.0 ft    | 3,633.2 ft    |
| `target_well_accepted_duration_hours`          | 123.95 h      | 124.03 h      |

These are already aggregated at the target–well level (not per section), but they provide the run count and penetration-rate context you asked for.

---

### 2. Accepted run count comparison (target–well level)

- **SYN-WELL-0002**
  - Accepted runs for this target: **7**
  - All 7 source runs are accepted (no quarantined runs) for the target–well combination.
- **SYN-WELL-0019**
  - Accepted runs for this target: **4**
  - All 4 source runs are accepted (no quarantined runs) for the target–well combination.

**Implication:** Within the SYN-TARGET-0001 context, SYN-WELL-0002 has a larger accepted run population (7 vs 4), which may offer broader operational coverage across its sections relative to SYN-WELL-0019, assuming similar sectioning.

---

### 3. Penetration rate context (target–well level)

Using only accepted summary metrics:

Penetration rate (accepted) ≈ accepted footage / accepted duration.

- **SYN-WELL-0002**
  - Accepted footage: 8,966.0 ft  
  - Accepted duration: 123.95 h  
  - **Average accepted penetration rate (target–well level):**  
    ≈ 8,966.0 ft / 123.95 h ≈ **72.3 ft/h**

- **SYN-WELL-0019**
  - Accepted footage: 3,633.2 ft  
  - Accepted duration: 124.03 h  
  - **Average accepted penetration rate (target–well level):**  
    ≈ 3,633.2 ft / 124.03 h ≈ **29.3 ft/h**

**Implications within the target SYN-TARGET-0001 context:**

- SYN-WELL-0002 exhibits a **substantially higher accepted penetration rate** at the aggregated target–well level than SYN-WELL-0019, with:
  - ~2.5× higher footage drilled over essentially the **same accepted drilling time**.
- Both wells have **no quarantined runs and no recorded warnings or errors** at this summary level, so:
  - All source runs are fully contributing to the accepted metrics for this target–well pairing.
  - The penetration-rate contrast is not driven by exclusion of problematic runs; it reflects the accepted population as summarized.

---

### 4. Section-level support qualification

- The request is specifically for **section-level deterministic offset comparison** from `serving.offset_section_summary`.
- The current tool interaction could not retrieve `serving.offset_section_summary` directly, so:
  - I cannot provide **per-section** accepted run counts or section-specific penetration rates.
  - I also cannot break down which sections within SYN-WELL-0002 vs SYN-WELL-0019 are driving the difference in overall penetration performance.

What I can state, using only allowed summary tables:

- Both SYN-WELL-0002 and SYN-WELL-0019 are **valid, fully accepted offset wells** for SYN-TARGET-0001 at the target–well level (no quarantined runs, no error runs for this pairing).
- At this aggregate level, **SYN-WELL-0002**:
  - Has **more accepted runs** (7 vs 4).
  - Delivers **greater accepted footage** (8,966 ft vs 3,633.2 ft).
  - Achieves a **higher average penetration rate** (~72.3 ft/h vs ~29.3 ft/h) given similar accepted drilling time.

If you’d like, the next step—once `serving.offset_section_summary` access is available—would be to:

- Compare the same metrics by **section ID and MD interval** for both wells.
- Identify which sections in SYN-WELL-0002 align with the higher overall penetration and where SYN-WELL-0019 might still offer useful localized analog behavior.