"""Command line entry point.

    python -m payroll_sentinel.cli run            # generate + validate + evaluate (rules only, free)
    python -m payroll_sentinel.cli run --llm      # same, titles normalized by an LLM (see llm.py)
    python -m payroll_sentinel.cli validate FILE  # validate your own CSV
    python -m payroll_sentinel.cli eval-titles FILE [--llm | --no-cbo]  # score titles on a held-out file
    python -m payroll_sentinel.cli models         # model ids your LLM key can use
    python -m payroll_sentinel.cli ask "QUESTION"  # question about the benchmark (needs an LLM)
    python -m payroll_sentinel.cli eval-ask FILE   # score ask on eval/questions.csv (needs an LLM)
    python -m payroll_sentinel.cli triage FILE [--llm]  # claims of a petition (.txt) and what they are worth
    python -m payroll_sentinel.cli eval-claims [--llm] [--heldout DIR]  # score claim extraction
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .ask import QuestionsError, ask, build_benchmark, run_ask_eval
from .pipeline import annotate_submission, run_evaluation, validate_submissions
from .titles_eval import HeldoutError, evaluate_titles, load_heldout


def cmd_run(args) -> None:
    data, reports = Path(args.data), Path(args.reports)
    data.mkdir(parents=True, exist_ok=True)
    reports.mkdir(parents=True, exist_ok=True)

    if args.llm and args.no_cbo:
        raise SystemExit("--no-cbo removes CBO titles from the rules; it cannot be combined with --llm.")
    ev = run_evaluation(seed=args.seed, n_companies=args.companies, use_llm=args.llm,
                        cache_path=None if args.no_cache else data / "llm_title_cache.json",
                        cbo=not args.no_cbo)
    ev.submitted.to_csv(data / "submissions.csv", index=False)
    ev.truth.to_csv(data / "ground_truth.csv", index=False)
    ev.result.issues.to_csv(reports / "issues.csv", index=False)
    ev.result.companies.to_csv(reports / "companies.csv", index=False)

    lines = ev.report_lines()
    (reports / "evaluation.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:30]))
    print(f"\nReports written to {reports}/")


def cmd_validate(args) -> None:
    out = Path(args.reports)
    df = pd.read_csv(args.file)
    result = validate_submissions(df, use_llm=args.llm, cache_path=out / "llm_title_cache.json")
    out.mkdir(parents=True, exist_ok=True)
    result.issues.to_csv(out / "issues.csv", index=False)
    result.companies.to_csv(out / "companies.csv", index=False)
    annotated = annotate_submission(df, result)
    blocked = annotated["status"].eq("block")
    annotated[~blocked].to_csv(out / "accepted_rows.csv", index=False)
    annotated[blocked].to_csv(out / "rows_to_fix.csv", index=False)
    print(result.companies.to_string(index=False))
    print(f"\n{len(result.issues)} issues written to {out / 'issues.csv'}")
    print(f"{int((~blocked).sum())} accepted rows (ok + warn) in {out / 'accepted_rows.csv'}, "
          f"{int(blocked.sum())} rows to fix in {out / 'rows_to_fix.csv'}")


def cmd_eval_titles(args) -> None:
    try:
        gold = load_heldout(args.file)
    except HeldoutError as exc:
        raise SystemExit(f"{args.file} is not ready:\n{exc}")
    if args.llm and args.no_cbo:
        raise SystemExit("--no-cbo removes CBO titles from the rules; it cannot be combined with --llm.")
    ev = evaluate_titles(gold, use_llm=args.llm, cbo=not args.no_cbo)
    out = Path(args.reports)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"titles_heldout_{ev.slug}.md"
    text = ev.report(Path(args.file).as_posix())
    path.write_text(text, encoding="utf-8")
    print(text)
    print(f"Report written to {path}")


def cmd_models(args) -> None:
    from .llm import LLMClient
    client = LLMClient.from_env()
    print(f"Models for provider '{client.provider}' (current: {client.model}):")
    for model in client.list_models():
        print(model)


def cmd_ask(args) -> None:
    from .llm import LLMClient
    result = ask(args.question, build_benchmark(args.seed, args.companies), LLMClient.from_env())
    print(result.text)
    if result.answer is not None and result.answer.groups is not None:
        print(result.answer.groups.to_string(index=False))
    if result.query is not None:
        print(f"\nQuery: {json.dumps(result.query.to_dict(), ensure_ascii=False)}")
    if result.error:
        print(f"\nRejected LLM output: {result.error}")


def cmd_eval_ask(args) -> None:
    try:
        tag, report = run_ask_eval(args.file)
    except QuestionsError as exc:
        raise SystemExit(f"{args.file} is not ready:\n{exc}")
    out = Path(args.reports)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"ask_eval_{tag}.md"
    path.write_text(report, encoding="utf-8")
    print(report)
    print(f"Report written to {path}")


def _claim_extractor(args):
    """Keyword rules, or an LLM with a cache file per provider and model."""
    from .claims import llm_extract, rule_extract
    if not args.llm:
        return "rules", "keyword rules", rule_extract, None
    from .llm import LLMClient
    client = LLMClient.from_env()
    cache = None if args.no_cache else Path(args.data) / f"llm_claims_cache_{client.tag}.json"
    return f"llm_{client.tag}", f"LLM {client.label}", lambda text: llm_extract(text, client, cache), client


def cmd_triage(args) -> None:
    from salary_core import load_params
    from .triage import triage
    text = Path(args.file).read_text(encoding="utf-8")
    _, method, extract, _ = _claim_extractor(args)
    extraction = extract(text)
    result = triage(extraction, load_params(2026))
    print(f"Extraction ({method}):")
    for key, value in extraction.as_truth().items():
        if key != "claims":
            print(f"  {key}: {value}")
    print("\nClaims:")
    for e, c in zip(result.estimates, extraction.claims):
        amount = f"R$ {e.amount:,.2f}" if e.amount is not None else "not priced"
        print(f"  {e.type}{f' ({c.label})' if c.label else ''}: {amount} - {e.note}")
        print(f"    \"{c.quote}\"")
    print(f"\nPriced total: R$ {result.total:,.2f} (estimate, no interest or monetary correction)")
    print(f"Likely procedure: {result.procedure}")
    for flag in result.flags:
        print(f"Flag: {flag}")
    for problem in extraction.problems:
        print(f"Dropped by the checks: {problem}")


def cmd_eval_claims(args) -> None:
    from salary_core import load_params
    from .claims_eval import HeldoutError, evaluate_claims, load_heldout_petitions
    from .petitions import generate_petitions
    if args.heldout:
        try:
            petitions = load_heldout_petitions(args.heldout)
        except HeldoutError as exc:
            raise SystemExit(f"{args.heldout} is not ready:\n{exc}")
        kind, source = "heldout", f"written by hand, {Path(args.heldout).as_posix()}"
    else:
        petitions = generate_petitions(args.n, seed=args.seed)
        kind, source = "synthetic", f"synthetic, seed {args.seed}; template text, easier than real petitions"
    slug, method, extract, client = _claim_extractor(args)
    ev = evaluate_claims(petitions, extract, load_params(2026), method, source)
    if client is not None:
        ev.llm_stats = client.stats.summary()
    out = Path(args.reports)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"claims_{kind}_{slug}.md"
    text = ev.report()
    path.write_text(text, encoding="utf-8")
    print(text[:3000])
    print(f"Report written to {path}")


def main() -> None:
    p = argparse.ArgumentParser(prog="payroll_sentinel")
    sub = p.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="generate synthetic data, validate and evaluate")
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--companies", type=int, default=25)
    run.add_argument("--llm", action="store_true", help="normalize titles with an LLM")
    run.add_argument("--data", default="data")
    run.add_argument("--reports", default="reports")
    run.add_argument("--no-cache", action="store_true",
                     help="ask the LLM for every title (use it to time a model)")
    run.add_argument("--no-cbo", action="store_true",
                     help="keyword rules only, without the official CBO titles (the v1.0 rules)")
    run.set_defaults(func=cmd_run)
    val = sub.add_parser("validate", help="validate a CSV file")
    val.add_argument("file")
    val.add_argument("--llm", action="store_true")
    val.add_argument("--reports", default="reports")
    val.set_defaults(func=cmd_validate)
    ttl = sub.add_parser("eval-titles", help="score title normalization on a held-out file")
    ttl.add_argument("file", help="CSV with columns title,family,level (empty family: outside the taxonomy)")
    ttl.add_argument("--llm", action="store_true", help="normalize titles with an LLM (no cache)")
    ttl.add_argument("--no-cbo", action="store_true",
                     help="keyword rules only, without the official CBO titles (the v1.0 rules)")
    ttl.add_argument("--reports", default="reports")
    ttl.set_defaults(func=cmd_eval_titles)
    sub.add_parser("models", help="list the models your LLM key can use").set_defaults(func=cmd_models)
    q = sub.add_parser("ask", help="ask a question about the validated benchmark (needs an LLM)")
    q.add_argument("question")
    q.add_argument("--seed", type=int, default=42)
    q.add_argument("--companies", type=int, default=25)
    q.set_defaults(func=cmd_ask)
    qe = sub.add_parser("eval-ask", help="score ask on a questions file (needs an LLM)")
    qe.add_argument("file", help="CSV with columns question,expected_query")
    qe.add_argument("--reports", default="reports")
    qe.set_defaults(func=cmd_eval_ask)
    tr = sub.add_parser("triage", help="find the claims of a petition and price them")
    tr.add_argument("file", help="petition as a UTF-8 .txt file (synthetic or fictitious only)")
    tr.add_argument("--llm", action="store_true", help="extract the claims with an LLM")
    tr.add_argument("--no-cache", action="store_true", help="ask the LLM again")
    tr.add_argument("--data", default="data")
    tr.set_defaults(func=cmd_triage)
    ec = sub.add_parser("eval-claims", help="score claim extraction on synthetic or hand-written petitions")
    ec.add_argument("--heldout", help="folder of hand-written petitions (*.txt) with truth.json")
    ec.add_argument("--llm", action="store_true", help="extract the claims with an LLM")
    ec.add_argument("--no-cache", action="store_true", help="ask the LLM for every petition (use it to time a model)")
    ec.add_argument("--n", type=int, default=60)
    ec.add_argument("--seed", type=int, default=7)
    ec.add_argument("--data", default="data")
    ec.add_argument("--reports", default="reports")
    ec.set_defaults(func=cmd_eval_claims)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
