import tempfile
import unittest
from pathlib import Path

from boatrace import analyze
from boatrace.__main__ import main
from boatrace.parser import parse_file, parse_text

# 公式の成績ファイルを模したサンプル（全角数字・全角スペース・半角カナを含む）
SAMPLE = """\
STARTK
12KBGN
ボートレース住之江   　   9月 1日  住之江ＳＧ　　　　　 第　１日

   1R       予選　　　　         H1800m  晴　  風  北　 1m  波　   1cm
  着 艇 登番 　選　手　名　　ﾓｰﾀｰ ﾎﾞｰﾄ 展示 進入 ｽﾀｰﾄﾀｲﾐﾝｸﾞ ﾚｰｽﾀｲﾑ
-------------------------------------------------------------------------------
  01  1 4444 山田　　太郎　 12   34  6.78   1    0.12     1.49.8
  02  3 4321 佐藤　次郎　　 45   21  6.80   3    0.15     1.51.2
  03  2 3999 鈴木　　花子　 33   56  6.75   2    0.18     1.52.0
  04  4 5011 高橋　一郎　　 21   11  6.82   4    0.20     1.53.4
  05  6 4888 田中　　健　　 18   40  6.85   6    0.22     1.55.1
  F   5 4777 伊藤　　誠　　 27   19  6.79   5   F0.01      .  .

        単勝     1          150
        複勝     1          100  3          210
        ２連単   1-3        560  人気     2
        ２連複   1-3        400  人気     1
        拡連複   1-3        160  人気     1
                 1-2        130  人気     2
                 2-3        300  人気     5
        ３連単   1-3-2     1230  人気     3
        ３連複   1-2-3      450  人気     1

   2R       一般　　　　         H1800m  曇り  風  南　 2m  波　   2cm
  着 艇 登番 　選　手　名　　ﾓｰﾀｰ ﾎﾞｰﾄ 展示 進入 ｽﾀｰﾄﾀｲﾐﾝｸﾞ ﾚｰｽﾀｲﾑ
-------------------------------------------------------------------------------
  01  2 3999 鈴木　　花子　 33   56  6.75   1    0.11     1.50.1
  02  1 4444 山田　　太郎　 12   34  6.78   2    0.14     1.51.0
  03  3 4321 佐藤　次郎　　 45   21  6.80   3    0.16     1.52.3

        単勝     2          480
        ３連単   2-1-3     3450  人気    12
12KEND
FINALK
"""


class ParserTest(unittest.TestCase):
    def setUp(self):
        self.races = parse_text(SAMPLE, "2024-09-01")

    def test_races(self):
        self.assertEqual([r.race_no for r in self.races], [1, 2])
        r = self.races[0]
        self.assertEqual((r.venue, r.distance, r.race_name), ("住之江", 1800, "予選"))

    def test_entries(self):
        entries = self.races[0].entries
        self.assertEqual(len(entries), 6)
        first = entries[0]
        self.assertEqual((first.place, first.lane, first.racer_id), (1, 1, "4444"))
        self.assertEqual(first.racer_name, "山田太郎")
        self.assertEqual((first.motor, first.boat, first.course), (12, 34, 1))
        self.assertEqual(first.start_timing, "0.12")
        flying = entries[5]
        self.assertIsNone(flying.place)
        self.assertEqual((flying.status, flying.lane), ("F", 5))

    def test_payouts(self):
        p = self.races[0].payouts
        self.assertIn(("単勝", "1", 150), p)
        self.assertIn(("複勝", "3", 210), p)
        self.assertIn(("2連単", "1-3", 560), p)
        self.assertIn(("3連単", "1-3-2", 1230), p)
        self.assertEqual([x for x in p if x[0] == "拡連複"],
                         [("拡連複", "1-3", 160), ("拡連複", "1-2", 130), ("拡連複", "2-3", 300)])

    def test_file_is_cp932(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "K240901.TXT"
            path.write_bytes(SAMPLE.encode("cp932"))
            races = parse_file(path)
        self.assertEqual(races[0].date, "2024-09-01")
        self.assertEqual(len(races[0].entries), 6)


class AnalyzeTest(unittest.TestCase):
    def setUp(self):
        self.races = parse_text(SAMPLE, "2024-09-01")

    def test_win_rate(self):
        table = analyze.win_rate_by(self.races, "lane")
        self.assertEqual(table["住之江"][1], (1, 2))
        self.assertEqual(table["全場"][2], (1, 2))

    def test_backtest(self):
        r = analyze.backtest(self.races, "単勝", "1")
        self.assertEqual((r["レース数"], r["的中数"], r["投資額"], r["払戻額"]), (2, 1, 200, 150))
        self.assertAlmostEqual(r["回収率"], 0.75)
        # 拡連複は1レースに3つの当たりがある
        self.assertEqual(analyze.backtest(self.races, "拡連複", "1-2")["払戻額"], 130)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "K240901.TXT").write_bytes(SAMPLE.encode("cp932"))
            main(["--raw", d, "summary"])
            main(["--raw", d, "backtest", "３連単", "1-3-2"])
            main(["--raw", d, "export", "--out", str(Path(d) / "csv")])
            self.assertTrue((Path(d) / "csv" / "payouts.csv").exists())


if __name__ == "__main__":
    unittest.main()
