"""競走成績ファイル（K??????.TXT, Shift_JIS）を解析する。

ファイルは固定書式のテキストで、場ごとに "NNKBGN" ～ "NNKEND" で区切られ、
その中に各レースの「レース見出し → 着順表 → 払戻金」が並ぶ。
桁位置の細かな揺れに耐えられるよう、固定幅ではなく正規表現で読み取る。
"""

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from . import VENUES

VENUE_BEGIN = re.compile(r"^(\d{2})KBGN")
VENUE_END = re.compile(r"^(\d{2})KEND")
RACE_HEADER = re.compile(r"^\s*(?:第\s*)?(\d{1,2})R\s+(.*?)\s+H(\d{3,4})m")
# 着 艇 登番 選手名 モーター ボート 展示 進入 スタート レースタイム
ENTRY_ROW = re.compile(
    r"^\s*(\d{2}|[A-Z]\d?)\s+([1-6])\s+(\d{4})\s+(.+?)\s+(\d{1,3})\s+(\d{1,3})\s+(.*)$"
)
BET_TYPES = ("単勝", "複勝", "2連単", "2連複", "拡連複", "3連単", "3連複")
PAYOUT_LINE = re.compile(r"^\s*(" + "|".join(BET_TYPES) + r")\s+(.*)$")
COMBO_AMOUNT = re.compile(r"([1-6](?:-[1-6]){0,2})\s+(\d+)")
WIDE_CONT = re.compile(r"^\s+([1-6]-[1-6])\s+(\d+)")


@dataclass
class Entry:
    place: int | None  # 着順。失格・欠場などは None
    status: str  # 着順欄の元の文字列（"01", "F", "K0" など）
    lane: int
    racer_id: str
    racer_name: str
    motor: int
    boat: int
    exhibit_time: str = ""
    course: int | None = None
    start_timing: str = ""
    race_time: str = ""


@dataclass
class Race:
    date: str
    venue_code: str
    race_no: int
    race_name: str
    distance: int
    entries: list[Entry] = field(default_factory=list)
    payouts: list[tuple[str, str, int]] = field(default_factory=list)  # (券種, 組番, 払戻金)

    @property
    def venue(self) -> str:
        return VENUES.get(self.venue_code, self.venue_code)


def _normalize(line: str) -> str:
    # 全角数字・半角カナなどを統一（"３連単" → "3連単"）。全角スペースも半角になる。
    return unicodedata.normalize("NFKC", line).rstrip("\r\n")


def _parse_entry(m: re.Match) -> Entry:
    status = m.group(1)
    rest = m.group(7).split()
    entry = Entry(
        place=int(status) if status.isdigit() else None,
        status=status,
        lane=int(m.group(2)),
        racer_id=m.group(3),
        racer_name=re.sub(r"\s+", "", m.group(4)),
        motor=int(m.group(5)),
        boat=int(m.group(6)),
    )
    if rest:
        entry.exhibit_time = rest[0]
    if len(rest) >= 2 and rest[1].isdigit():
        entry.course = int(rest[1])
    if len(rest) >= 3:
        entry.start_timing = rest[2]
    if len(rest) >= 4:
        entry.race_time = rest[3]
    return entry


def parse_text(text: str, date: str) -> list[Race]:
    races: list[Race] = []
    venue = None
    race = None
    last_bet = None

    for raw in text.splitlines():
        line = _normalize(raw)

        if m := VENUE_BEGIN.match(line):
            venue, race = m.group(1), None
            continue
        if VENUE_END.match(line):
            venue, race = None, None
            continue
        if venue is None:
            continue

        if m := RACE_HEADER.match(line):
            race = Race(date, venue, int(m.group(1)), m.group(2).strip(), int(m.group(3)))
            races.append(race)
            last_bet = None
            continue
        if race is None:
            continue

        if m := PAYOUT_LINE.match(line):
            last_bet = m.group(1)
            pairs = COMBO_AMOUNT.findall(m.group(2))
            # 複勝は1行に2組並ぶ。それ以外は先頭の組番だけ（後ろは「人気」）
            for combo, amount in pairs if last_bet == "複勝" else pairs[:1]:
                race.payouts.append((last_bet, combo, int(amount)))
            continue
        if last_bet == "拡連複" and (m := WIDE_CONT.match(line)):
            race.payouts.append(("拡連複", m.group(1), int(m.group(2))))
            continue

        if m := ENTRY_ROW.match(line):
            race.entries.append(_parse_entry(m))
            continue

    return races


def parse_file(path: Path) -> list[Race]:
    # ファイル名 K240901.TXT → 2024-09-01
    m = re.search(r"(\d{2})(\d{2})(\d{2})", path.stem)
    date = f"20{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""
    text = path.read_bytes().decode("cp932", errors="replace")
    return parse_text(text, date)
