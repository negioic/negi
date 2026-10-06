"""解析済みレースの集計。"""

import csv
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from .parser import Race


def _winner(race: Race):
    return next((e for e in race.entries if e.place == 1), None)


def win_rate_by(races: list[Race], key: str) -> dict[str, dict[int, tuple[int, int]]]:
    """場ごとに、枠番（key="lane"）または進入コース（key="course"）別の1着回数を数える。

    戻り値: {場名: {枠/コース: (1着回数, レース数)}}。"全場" に合計も入る。
    """
    wins: dict[str, Counter] = defaultdict(Counter)
    totals: Counter = Counter()
    for race in races:
        winner = _winner(race)
        if winner is None:
            continue
        value = getattr(winner, key)
        if value is None:
            continue
        for name in (race.venue, "全場"):
            wins[name][value] += 1
            totals[name] += 1
    return {
        name: {v: (wins[name][v], totals[name]) for v in range(1, 7)}
        for name in sorted(wins, key=lambda n: (n == "全場", n))
    }


def backtest(races: list[Race], bet_type: str, combo: str, stake: int = 100) -> dict:
    """毎レース同じ買い目を stake 円ずつ買い続けた場合の成績。

    払戻金は100円あたりの金額なので stake/100 倍する。
    払戻データのないレース（中止・不成立など）は除外する。
    """
    bets = hits = returned = 0
    for race in races:
        payouts = [p for p in race.payouts if p[0] == bet_type]
        if not payouts:
            continue
        bets += 1
        for _, c, amount in payouts:
            if c == combo:
                hits += 1
                returned += amount * stake // 100
    spent = bets * stake
    return {
        "券種": bet_type,
        "買い目": combo,
        "レース数": bets,
        "的中数": hits,
        "的中率": hits / bets if bets else 0.0,
        "投資額": spent,
        "払戻額": returned,
        "回収率": returned / spent if spent else 0.0,
    }


def payout_stats(races: list[Race], bet_type: str, top: int = 10) -> dict:
    """券種ごとの払戻金の分布と、よく出る組番。"""
    amounts = [a for r in races for b, _, a in r.payouts if b == bet_type]
    combos = Counter(c for r in races for b, c, _ in r.payouts if b == bet_type)
    if not amounts:
        return {"券種": bet_type, "件数": 0}
    return {
        "券種": bet_type,
        "件数": len(amounts),
        "平均": statistics.mean(amounts),
        "中央値": statistics.median(amounts),
        "最大": max(amounts),
        "頻出組番": combos.most_common(top),
    }


def export_csv(races: list[Race], out_dir: Path) -> None:
    """races.csv / entries.csv / payouts.csv に書き出す（Excel で開けるよう BOM 付き UTF-8）。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    race_cols = ["date", "venue_code", "venue", "race_no", "race_name", "distance"]
    with open(out_dir / "races.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(race_cols)
        for r in races:
            w.writerow([r.date, r.venue_code, r.venue, r.race_no, r.race_name, r.distance])

    entry_cols = None
    with open(out_dir / "entries.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        for r in races:
            for e in r.entries:
                row = asdict(e)
                if entry_cols is None:
                    entry_cols = list(row)
                    w.writerow(["date", "venue", "race_no", *entry_cols])
                w.writerow([r.date, r.venue, r.race_no, *row.values()])

    with open(out_dir / "payouts.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["date", "venue", "race_no", "bet_type", "combination", "payout"])
        for r in races:
            for bet, combo, amount in r.payouts:
                w.writerow([r.date, r.venue, r.race_no, bet, combo, amount])
