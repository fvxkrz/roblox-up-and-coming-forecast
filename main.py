#!/usr/bin/env python3
"""Improved Up-and-Coming forecaster for roblox-up-and-coming-forecast-01.
Standard library only. Recent rank occupancy + smoothed transitions.
"""
import json
import os
from pathlib import Path

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

def main():
    task = json.loads((INPUT_DIR / "task.json").read_text())
    places = task["places"]
    lines = (INPUT_DIR / "history.ndjson").read_text().splitlines()
    snaps = [json.loads(l) for l in lines if l.strip()]

    # Recent regime
    N = min(12, len(snaps))
    recent = snaps[-N:]

    # Collect ranks for games in top 30
    game_ranks = {}
    for s in recent:
        for r in s.get("up_and_coming", []):
            if r["rank"] > 30:
                continue
            uid = r["universe_id"]
            game_ranks.setdefault(uid, []).append(r["rank"])

    # Score by average rank (lower better) then frequency
    scored = []
    for uid, ranks in game_ranks.items():
        avg = sum(ranks) / len(ranks)
        scored.append((avg, -len(ranks), uid))
    scored.sort()
    candidates = [uid for _, _, uid in scored[:25]]

    last = snaps[-1]
    last_chart = [r["universe_id"] for r in sorted(last.get("up_and_coming", []), key=lambda x: x["rank"])]

    probabilities = []
    top10 = []

    for place in range(1, places + 1):
        primary = last_chart[place - 1] if place - 1 < len(last_chart) else (candidates[place - 1] if place - 1 < len(candidates) else last_chart[0])
        # Prefer candidate whose avg is close to this place
        for avg, _, uid in scored:
            if abs(avg - place) < 3 and uid in candidates:
                primary = uid
                break

        top10.append(primary)
        probabilities.append({"universe_id": primary, "place": place, "p": 0.42})

        neigh = set()
        if place > 1 and place - 2 < len(last_chart):
            neigh.add(last_chart[place - 2])
        if place < len(last_chart):
            neigh.add(last_chart[place])
        if place < len(candidates):
            neigh.add(candidates[place])

        for uid in list(neigh)[:2]:
            if uid != primary:
                probabilities.append({"universe_id": uid, "place": place, "p": 0.16})

    # Unique top10
    seen = set()
    unique = []
    for uid in top10:
        if uid not in seen:
            seen.add(uid)
            unique.append(uid)
    for uid in last_chart:
        if len(unique) >= places:
            break
        if uid not in seen:
            seen.add(uid)
            unique.append(uid)

    out = {"probabilities": probabilities, "top10": unique[:places]}
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / task["output"]).write_text(json.dumps(out) + "\n")
    print(f"Wrote forecast using {N} recent snapshots", file=os.sys.stderr)

if __name__ == "__main__":
    main()
