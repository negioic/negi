"""公式サイトから競走成績ファイル（LZH）をダウンロードして展開する。"""

import datetime as dt
import io
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://www1.mbrace.or.jp/od2/K/{yyyymm}/k{yymmdd}.lzh"


def daterange(start: dt.date, end: dt.date):
    d = start
    while d <= end:
        yield d
        d += dt.timedelta(days=1)


def download_day(day: dt.date, out_dir: Path, wait: float = 1.0) -> Path | None:
    """1日分の成績ファイルを取得して TXT を out_dir に保存する。既にあればスキップ。"""
    import lhafile  # pip install lhafile

    out_dir.mkdir(parents=True, exist_ok=True)
    txt_path = out_dir / f"K{day:%y%m%d}.TXT"
    if txt_path.exists():
        return txt_path

    url = BASE_URL.format(yyyymm=f"{day:%Y%m}", yymmdd=f"{day:%y%m%d}")
    try:
        with urllib.request.urlopen(url, timeout=30) as res:
            data = res.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:  # 開催なし、または未公開
            return None
        raise
    finally:
        time.sleep(wait)  # 公式サーバーに負荷をかけないよう間隔をあける

    archive = lhafile.Lhafile(io.BytesIO(data))
    for name in archive.namelist():
        if name.upper().endswith(".TXT"):
            txt_path.write_bytes(archive.read(name))
            return txt_path
    return None


def download_range(start: dt.date, end: dt.date, out_dir: Path) -> list[Path]:
    paths = []
    for day in daterange(start, end):
        path = download_day(day, out_dir)
        print(f"{day}: {'OK' if path else 'データなし'}")
        if path:
            paths.append(path)
    return paths
