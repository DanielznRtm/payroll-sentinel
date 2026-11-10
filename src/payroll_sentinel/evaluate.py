"""Score the validator against the planted ground truth."""

from __future__ import annotations

import pandas as pd

from .validate import ValidationResult

STAT_ERRORS = ["annual_as_monthly", "level_salary_mismatch"]


def _prf(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return {"precision": round(p, 3), "recall": round(r, 3), "f1": round(f, 3),
            "tp": tp, "fp": fp, "fn": fn}


def score(result: ValidationResult, truth: pd.DataFrame) -> dict:
    issues = result.issues[result.issues["cause"] != "unmapped_title"]
    causes = issues.groupby("row_id")["cause"].agg(set)
    t = truth.set_index("row_id")
    flagged = set(causes.index)
    errored = set(t.index[t["error_type"] != "none"])

    overall = _prf(len(flagged & errored), len(flagged - errored), len(errored - flagged))

    per_type = []
    for err, rows in t[t["error_type"] != "none"].groupby("error_type"):
        ids = set(rows.index)
        detected = ids & flagged
        diagnosed = {i for i in detected if err in causes[i]}
        per_type.append({"error_type": err, "planted": len(ids),
                         "detected": len(detected), "recall": round(len(detected) / len(ids), 3),
                         "correct_cause": len(diagnosed),
                         "cause_accuracy": round(len(diagnosed) / len(detected), 3) if detected else 0.0})

    # Detector comparison on the statistical error types, among rows each detector saw.
    rec = result.records.set_index("row_id").join(t["error_type"])
    seen = rec[rec["flag_ensemble"].notna()]
    positive = seen["error_type"].isin(STAT_ERRORS)
    clean_seen = seen["error_type"].eq("none")
    detectors = {}
    for col in ["vote_z", "vote_iqr", "vote_iforest", "flag_ensemble"]:
        pred = seen[col].astype(bool)
        # Recall: on the statistical error types. False positives: only truly clean rows
        # (a salary flag on, say, a below-minimum-wage row is still a correct catch).
        tp, fn, fp = int((pred & positive).sum()), int((~pred & positive).sum()), int((pred & clean_seen).sum())
        detectors[col] = {**_prf(tp, fp, fn), "flagged": int(pred.sum())}
    stat_planted = int(t["error_type"].isin(STAT_ERRORS).sum())
    stat_seen = int(positive.sum())

    clean = t["error_type"] == "none"
    false_alarm_rate = len(flagged & set(t.index[clean])) / int(clean.sum())
    return {"overall": overall, "per_type": pd.DataFrame(per_type), "detectors": pd.DataFrame(detectors).T,
            "stat_coverage": f"{stat_seen}/{stat_planted}", "false_alarm_rate": round(false_alarm_rate, 4)}


def title_accuracy(norm: pd.DataFrame, truth: pd.DataFrame, titles: pd.Series) -> pd.DataFrame:
    has_title = titles.fillna("").astype(str).str.strip().ne("")
    rows = []
    for name, mask in [("all", has_title), ("common titles", has_title & ~truth["hard_title"]),
                       ("long-tail titles", has_title & truth["hard_title"])]:
        fam = norm.loc[mask, "family"] == truth.loc[mask, "true_family"]
        lvl = norm.loc[mask, "level"] == truth.loc[mask, "true_level"]
        rows.append({"subset": name, "rows": int(mask.sum()),
                     "family_acc": round(fam.mean(), 3), "level_acc": round(lvl.mean(), 3),
                     "both_acc": round((fam & lvl).mean(), 3),
                     "unmapped": round(norm.loc[mask, "family"].isna().mean(), 3)})
    return pd.DataFrame(rows)
