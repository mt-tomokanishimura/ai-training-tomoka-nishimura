from __future__ import annotations

import argparse
import logging
import sys
from typing import List


def build_parser() -> argparse.ArgumentParser:
    """Day06のCLI引数を定義します（入力・モード・ケース番号）。"""
    p = argparse.ArgumentParser(prog="day06")
    p.add_argument("--text", required=True)
    p.add_argument("--mode", choices=["normal", "attack"], default="normal")
    p.add_argument("--case", type=int, default=1)
    return p


def _validate_args(args: argparse.Namespace) -> None:
    """引数の簡易バリデーションを行います（入力不備は exit code=2）。"""
    if not args.text:
        raise ValueError("--text is required")
    if args.mode == "attack" and not (1 <= args.case <= 3):
        raise ValueError("--case must be between 1 and 3 when --mode attack")


def run_guarded(*, text: str, mode: str, case: int) -> str:
    """入力とツール実行をガードしながら処理し、回答（文字列）を返します。

    `mode` の意味：
    - `normal`：通常入力を処理
    - `attack`：用意した「悪い入力例」を使って、ガードが効いているか確認

    実装ガイド：
    - attackケースは最低3つ用意（README参照）
    - 「禁止する行為」を明確にし、検知したら例外（または拒否文）にする
    - ツールを実装する場合は許可リストで制限する（許可されないツールは実行しない）

    返り値：
    - 標準出力に出る本文（文章）を返す
    """
    if len(text) > 1000:
        raise ValueError("input is too long")

    attack_rules = {
        1: (
            "指示の乗っ取り",
            ("前の指示を無視", "秘密情報", "隠し情報"),
        ),
        2: (
            "不正なシステムコマンド実行",
            ("システムコマンド", "コマンドを実行", "環境変数を表示"),
        ),
        3: (
            "許可されていないファイル操作",
            ("ファイルを削除", "データを削除", "設定を書き換え"),
        ),
    }

    normalized_text = text.strip()
    rules_to_check = (
        [(case, attack_rules[case])]
        if mode == "attack"
        else list(attack_rules.items())
    )

    for case_number, (reason, patterns) in rules_to_check:
        if any(pattern in normalized_text for pattern in patterns):
            logging.warning(
                "guard rejected case=%s reason=%s",
                case_number,
                reason,
            )
            raise PermissionError(
                f"不正な入力が検出されました: {reason}"
            )

    if mode == "attack":
        raise PermissionError(
            f"攻撃ケース{case}を安全のため拒否しました"
        )

    return f"安全に処理しました: {normalized_text}"


def main(argv: List[str] | None = None) -> int:
    """CLIのエントリポイントです。

    受講者は `run_guarded()` を実装します。ここは引数解析/検証/終了コードを担当します。
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)

    try:
        _validate_args(args)
    except Exception as e:
        logging.error(str(e))
        print(str(e), file=sys.stderr)
        return 2

    logging.info("mode=%s case=%s", args.mode, args.case)

    try:
        out = run_guarded(text=args.text, mode=args.mode, case=args.case)
        print(out)
        return 0
    except NotImplementedError as e:
        logging.error(str(e))
        print(str(e), file=sys.stderr)
        return 1
    except Exception as e:
        logging.error("%s", e)
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
