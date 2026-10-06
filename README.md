# ボートレース成績 集計・分析ツール

ボートレース公式が公開している「競走成績」ファイルをダウンロードし、
枠番・進入コース別の1着率、払戻金の傾向、買い目ごとの回収率を集計します。

## 準備

Python 3.10 以上が必要です。

```
pip install -r requirements.txt
```

## 使い方

```
# 1. 成績ファイルを取得（data/raw に保存。1日ずつ1秒間隔で取得します）
python -m boatrace download 2024-09-01 2024-09-30

# 2. 枠番・コース別1着率と払戻金の傾向
python -m boatrace summary
python -m boatrace summary --venue 住之江

# 3. 同じ買い目を毎レース買い続けた場合の回収率
python -m boatrace backtest 単勝 1
python -m boatrace backtest 3連単 1-2-3 --venue 大村

# 4. CSV に書き出し（Excel などで自由に分析できます）
python -m boatrace export --out data/csv
```

## 出力される CSV

| ファイル | 内容 |
|---|---|
| races.csv | 日付・場・レース番号・レース名・距離 |
| entries.csv | 着順・枠・登番・選手名・モーター・ボート・展示タイム・進入・ST・レースタイム |
| payouts.csv | 券種・組番・払戻金（100円あたり） |

## 注意

- 回収率が100%を下回るのが普通です（舟券の払戻率は約75%）。過去データで回収率が高く見えても、
  レース数が少ない場合は偶然の可能性が高く、将来も勝てる保証にはなりません。
- 公式サーバーに負荷をかけないよう、大量取得は控えめにしてください。

## テスト

```
python -m unittest
```
