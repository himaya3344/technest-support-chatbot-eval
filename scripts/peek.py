import glob, json, os

files = sorted(glob.glob("results/raw/*.jsonl"), key=os.path.getmtime)
if not files:
    raise SystemExit("No files in results/raw/. Run scripts/run_eval.py first.")
latest = files[-1]
print("File:", latest, "\n")

ok = bad = 0
for line in open(latest, encoding="utf-8"):
    r = json.loads(line)
    out = r.get("parsed_output") or {}
    valid = r.get("json_valid")
    ok += bool(valid)
    bad += not valid
    print(f"{r.get('case_id'):<10} run {r.get('run_index')}  valid={valid}  "
          f"action={out.get('action')}  latency={r.get('latency_s')}s")
    print("   reply:", (out.get("reply") or r.get("raw_text") or "")[:150])
    if r.get("error"):
        print("   ERROR:", r["error"])
print(f"\nvalid JSON: {ok}   invalid: {bad}")