cat << 'EOF' > notebooks/README.md
# JET3 Canonical Notebooks

This directory contains the primary reproducible notebooks supporting published presentations, validation analyses, and model coefficients in `JET3`. Historical and exploratory drafts are preserved in [`archive/`](archive/).

## Active Notebooks Index

| Notebook | Purpose & Key Findings | Associated Output / Reference |
| :--- | :--- | :--- |
| **`ECOv003_JET_Accuracy_Sensitivity_Consolidated_Fixed_3.ipynb`** | End-to-end Cal-Val accuracy ($N = 999$, $\text{NDVI} \ge 0.05$) and side-by-side Monte Carlo vs. Sobol sensitivity analysis ($S_1, S_T$) for Verma vs. BESS $R_n$ and all four $LE$ models (`BESS-JPL`, `PM-JPL`, `PT-JPL-SM`, `STIC-JPL`). | 2026 ECOSTRESS SATM Presentation |
| **`ECOv003 JET Accuracy with ECOv002 Cal-Val with SOBOL Sensitivity 2.ipynb`** | Sobol main-effect scatter grids with LOWESS trendlines characterizing non-linear $R_n$ and $LE$ responses across `ST_C`. | 2026 ECOSTRESS SATM Presentation |
| **`ECOv003 JET Accuracy with ECOv002 Cal-Val with SOBOL Sensitivity with Collinearity Fixes.ipynb`** | Sobol global sensitivity analysis mitigating predictor collinearity among meteorological and surface inputs. | Post-SATM Sensitivity Analysis |
| **`ECOv003 JET Accuracy with ECOv002 Cal-Val with SOBOL Sensitivity with Meteorology Error Propagation.ipynb`** | Propagates empirical meteorological forcing errors into Sobol variance attribution. | Post-SATM UQ & Sensitivity Analysis |
| **`Shapley.ipynb`** | Game-theoretic Shapley value attribution for correlated environmental predictors. | Post-SATM Attribution Analysis |
| **`ECOv003 JET Accuracy with ECOv002 Cal-Val with Calibration.ipynb`** | Side-by-side Cal-Val benchmark ($n = 270$) quantifying $R^2$ and RMSE improvements when `use_calibration=True` is enabled for $T_a$, $RH$, and $SM$. | `JET3` Calibration Validation |
| **`Meteorology Calibration.ipynb`** | Trains the OLS bias-correction regressions for $T_a$, $RH$, and $SM$. | `JET3/*_calibration_coefficients.csv` |
| **`Meteorology UQ Pruned.ipynb`** | Trains the pruned $\pm 1\sigma$ uncertainty quantification models for uncalibrated and calibrated $T_a$, $RH$, and $SM$. | `JET3/*_UQ_coefficients.csv` |
| **`Biosphere Step 1 figure.ipynb`** | Generates spatial comparisons of coarse GEOS-5 FP vs. 70 m downscaled ECOSTRESS $RH$ and multi-model daily ET uncertainty time series (`US-Wkg`). | Biosphere / Downscaling Figures |
| **`Input Dataset.ipynb`** | Documents assembly and filtering of the 63-tower, 1,065-observation ECOv002 Cal-Val dataset. | `JET3/ECOv002-cal-val-JET-inputs.csv` |
EOF
git add notebooks/README.md