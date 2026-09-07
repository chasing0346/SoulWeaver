#!/usr/bin/env python3
"""按有效相邻对话 turn 数计算真实短语境示例配额。"""

from __future__ import annotations

import argparse
import json
import math


def calculate_quota(eligible_turns: int) -> int:
    if eligible_turns < 0:
        raise ValueError("eligible_turns 不能为负数")
    if eligible_turns == 0:
        return 0
    rounded = math.floor(math.sqrt(eligible_turns / 100) + 0.5)
    return min(eligible_turns, min(24, max(3, rounded)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eligible-turns", type=int, required=True)
    args = parser.parse_args()
    quota = calculate_quota(args.eligible_turns)
    print(
        json.dumps(
            {
                "eligible_turns": args.eligible_turns,
                "quota": quota,
                "formula": "min(E, min(24, max(3, round(sqrt(E/100)))))",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
