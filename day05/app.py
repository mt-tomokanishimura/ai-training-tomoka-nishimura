from __future__ import annotations

import argparse
import logging
import sys
from typing import List
import re
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Day05のCLI引数を定義します（質問文）。"""
    p = argparse.ArgumentParser(prog="day05")
    p.add_argument("--question", required=True)
    return p


def _validate_args(args: argparse.Namespace) -> None:
    """引数の簡易バリデーションを行います（入力不備は exit code=2）。"""
    if not args.question:
        raise ValueError("--question is required")


def answer_with_rag(question: str) -> str:
    """RAGで質問に回答し、指定フォーマットのテキストを返します。

    この関数を実装すると、`python -m day05.app --question ...` が動くようになります。

    要件（READMEの出力フォーマット）：
    - 標準出力に次の形で出すための文字列を返す
      1) `Answer:` 行
      2) `Sources:` 行
      3) `- <URL or ファイル名> (excerpt: "...")` を最低1件（ヒットなしなら `- (none)`）

    実装ガイド：
    - `day05/data/` 配下の `.txt` を読み込み、検索対象とする
    - 最初は単純なキーワード検索でもOK（高品質でなくてよい）
    - ヒットがない場合の挙動を必ず実装する
    """
    data_dir = Path(__file__).parent / "data"
    files = sorted(data_dir.glob("*.txt"))

    if not files:
        raise FileNotFoundError("No text files found in day05/data")

    def make_terms(value: str) -> set[str]:
        compact = re.sub(r"[\s、。,.!?！？「」『』（）()]", "", value)
        return {
            compact[index : index + 2]
            for index in range(len(compact) - 1)
        }

    question_terms = make_terms(question)
    best_file: Path | None = None
    best_text = ""
    best_score = 0

    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        score = len(question_terms & make_terms(text))

        if score > best_score:
            best_file = file_path
            best_text = text
            best_score = score

    if best_file is None or best_score == 0:
        return (
            "Answer: 該当する根拠が見つかりませんでした。\n\n"
            "Sources:\n"
            "- (none)"
        )

    excerpt = " ".join(best_text.split())[:120]
    source = best_file.relative_to(Path(__file__).parent.parent)

    return (
        f"Answer: 根拠として次の記述が見つかりました。{excerpt}\n\n"
        f"Sources:\n"
        f'- {source} (excerpt: "{excerpt}")'
    )


def main(argv: List[str] | None = None) -> int:
    """CLIのエントリポイントです。

    受講者は `answer_with_rag()` を実装します。
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        _validate_args(args)
    except Exception as e:
        logging.error(str(e))
        print(str(e), file=sys.stderr)
        return 2

    try:
        out = answer_with_rag(args.question)
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
