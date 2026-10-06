"""コマンドライン入口。

  python -m boatrace download 2024-09-01 2024-09-30
  python -m boatrace summary
  python -m boatrace backtest 3連単 1-2-3
  python -m boatrace export
"""

import argparse
import datetime as dt
import sys
import unicodedata
from pathlib import Path

from . import analyze
from .parser import BET_TYPES, parse_file

DEFAULT_RAW = Path("data/raw")


def load(raw_dir: Path, venue: str | None):
    races = []
    for path in sorted(raw_dir.glob("K*.TXT")):
        races.extend(parse_file(path))
    if venue:
        races = [r for r in races if r.venue == venue or r.venue_code == venue]
    if not races:
        sys.exit(f"{raw_dir} にレースデータがありません。先に download を実行してください。")
    return races


def ljust_width(text: str, width: int) -> str:
    """全角文字を幅2として左寄せする。"""
    w = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)
    return text + " " * max(width - w, 0)


def print_win_rates(title: str, table: dict) -> None:
    print(f"\n■ {title}別 1着率")
    print(ljust_width("場", 8) + "".join(f"{i:>8}" for i in range(1, 7)) + "  " + "レース数")
    for name, row in table.items():
        total = next(iter(row.values()))[1]
        cells = "".join(f"{w / t:>8.1%}" if t else f"{'-':>8}" for w, t in row.values())
        print(f"{ljust_width(name, 8)}{cells}{total:>10}")


def cmd_download(args):
    from .download import download_range

    start = dt.date.fromisoformat(args.start)
    end = dt.date.fromisoformat(args.end or args.start)
    download_range(start, end, args.raw)


def cmd_summary(args):
    races = load(args.raw, args.venue)
    dates = sorted({r.date for r in races})
    print(f"期間: {dates[0]} ～ {dates[-1]}  レース数: {len(races)}")
    print_win_rates("枠番", analyze.win_rate_by(races, "lane"))
    print_win_rates("進入コース", analyze.win_rate_by(races, "course"))
    for bet in ("単勝", "2連単", "3連単"):
        s = analyze.payout_stats(races, bet, top=5)
        if not s["件数"]:
            continue
        print(f"\n■ {bet} 払戻金  平均 {s['平均']:,.0f}円 / 中央値 {s['中央値']:,.0f}円 / 最大 {s['最大']:,}円")
        print("  頻出組番: " + ", ".join(f"{c}({n}回)" for c, n in s["頻出組番"]))


def cmd_backtest(args):
    races = load(args.raw, args.venue)
    bet_type = unicodedata.normalize("NFKC", args.bet_type)
    if bet_type not in BET_TYPES:
        sys.exit(f"券種は {', '.join(BET_TYPES)} のいずれかを指定してください。")
    r = analyze.backtest(races, bet_type, args.combo, args.stake)
    print(f"{r['券種']} {r['買い目']} を毎レース {args.stake}円ずつ購入した場合")
    print(f"  レース数 {r['レース数']} / 的中 {r['的中数']} ({r['的中率']:.1%})")
    print(f"  投資 {r['投資額']:,}円 → 払戻 {r['払戻額']:,}円  回収率 {r['回収率']:.1%}")


def cmd_export(args):
    races = load(args.raw, args.venue)
    analyze.export_csv(races, args.out)
    print(f"{args.out} に races.csv / entries.csv / payouts.csv を出力しました。")


def main(argv=None):
    p = argparse.ArgumentParser(prog="boatrace", description="ボートレース競走成績の集計・分析")
    p.add_argument("--raw", type=Path, default=DEFAULT_RAW, help="成績ファイル(TXT)の置き場所")
    sub = p.add_subparsers(required=True)

    d = sub.add_parser("download", help="公式サイトから成績ファイルを取得")
    d.add_argument("start", help="開始日 YYYY-MM-DD")
    d.add_argument("end", nargs="?", help="終了日 YYYY-MM-DD（省略時は開始日のみ）")
    d.set_defaults(func=cmd_download)

    s = sub.add_parser("summary", help="枠番・コース別1着率と払戻金の傾向")
    s.add_argument("--venue", help="場名または場コード（例: 住之江, 12）")
    s.set_defaults(func=cmd_summary)

    b = sub.add_parser("backtest", help="同じ買い目を買い続けた場合の回収率")
    b.add_argument("bet_type", help="券種（単勝, 複勝, 2連単, 2連複, 拡連複, 3連単, 3連複）")
    b.add_argument("combo", help="組番（例: 1, 1-2, 1-2-3）")
    b.add_argument("--stake", type=int, default=100, help="1レースあたりの購入額（円）")
    b.add_argument("--venue", help="場名または場コード")
    b.set_defaults(func=cmd_backtest)

    e = sub.add_parser("export", help="CSV に書き出し")
    e.add_argument("--out", type=Path, default=Path("data/csv"))
    e.add_argument("--venue", help="場名または場コード")
    e.set_defaults(func=cmd_export)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
