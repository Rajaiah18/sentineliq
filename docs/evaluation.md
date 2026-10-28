# SentinelIQ — Detection Evaluation & Ground Truth Benchmark
**Intelligent Transaction Risk & Investigation Platform**  
*Tagline: Explainable Risk. Traceable Decisions.*

---

## 1. Ground Truth Separation Principle

In strict compliance with financial crime risk modeling standards, ground-truth labels are **completely segregated** from the inference pipeline:

1. **Storage Isolation:** Ground-truth records are generated into `ground_truth/ground_truth.json` and `ground_truth/ground_truth.csv`.
2. **Zero Input Feature Leakage:** The `Transaction` schema and database documents contain **zero** target labels (no `is_suspicious`, no `ground_truth_id`, no `scenario_id`). Check `CHK-23-GT-LEAKAGE` programmatically verifies this in every validation run.
3. **Post-Inference Joining:** The Risk Engine runs completely blind to ground truth. Once detection is complete, the `RiskEvaluator` joins generated alerts to ground-truth records by `transaction_id`.

---

## 2. Evaluation Metric Formulas & Denominators

### Binary Classification Matrix
- **True Positives ($TP$):** Injected suspicious scenarios flagged by one or more risk rules.
- **False Positives ($FP$):** Legitimate transactions flagged by risk rules, or control scenarios flagged unexpectedly.
- **True Negatives ($TN$):** Legitimate baseline transactions that triggered no alerts.
- **False Negatives ($FN$):** Injected suspicious scenarios that bypassed all risk rules.

### Performance Ratios
$$\text{Precision} = \frac{TP}{TP + FP}$$
$$\text{Recall} = \frac{TP}{TP + FN}$$
$$\text{F1 Score} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$
$$\text{Specificity} = \frac{TN}{TN + FP}$$
$$\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}$$

Zero-division guards ensure all metrics cleanly resolve to `0.0` when denominators are zero without throwing runtime exceptions.

---

## 3. Actual Evaluation Baseline Results

Evaluated on fixed random seed `20261022`:

| Metric | Full Profile (100k txns) | Demo Profile (2k txns) |
|---|:---:|:---:|
| **Precision** | **68.75%** | **88.00%** |
| **Recall** | **78.94%** | **44.00%** |
| **F1 Score** | **73.49%** | **58.67%** |
| **Specificity** | **99.68%** | **99.85%** |
| **Accuracy** | **99.47%** | **99.30%** |
