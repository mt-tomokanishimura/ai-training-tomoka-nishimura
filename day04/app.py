from __future__ import annotations

import argparse
import logging
import sys
from typing import List
import os

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
load_dotenv()


def build_parser() -> argparse.ArgumentParser:
    """Day04のCLI引数を定義します（ユーザー入力テキスト）。"""
    p = argparse.ArgumentParser(prog="day04")
    p.add_argument("--text", required=True)
    return p


def _validate_args(args: argparse.Namespace) -> None:
    """引数の簡易バリデーションを行います（入力不備は exit code=2）。"""
    if not args.text:
        raise ValueError("--text is required")

@tool
def add(a: int, b: int) -> int:
    """2つの整数を足し算します。"""
    if type(a) is not int or type(b) is not int:
        raise ValueError("a and b must be integers")

    logging.info("tool=add called a=%s b=%s", a, b)
    return a + b

def run_chain(text: str) -> str:
    """LangChain + Tool calling を使って回答（文字列）を返します。

    この関数を実装すると、`python -m day04.app --text ...` が動くようになります。

    要件（READMEの受け入れ基準）：
    - `today` または `add` のツールを1つ実装し、LLMから1回以上呼び出す
    - ツール引数のバリデーションを入れる（不正なら実行しない）
    - ツール失敗時は安全に失敗する（例外でOK。mainがexit code=1にする）

    ヒント：
    - まずはツールをPython関数として作り、ログで「呼ばれた」ことを確認
    - 次にLLM側のプロンプトで「必要ならツールを使う」よう誘導
    """
    region = os.getenv("AWS_REGION")
    model_id = os.getenv("BEDROCK_MODEL_ID")
    profile = os.getenv("AWS_PROFILE")

    if not region or not model_id:
        raise ValueError("AWS region or model ID is not configured")

    llm = ChatBedrockConverse(
        model=model_id,
        region_name=region,
        credentials_profile_name=profile,
        temperature=0.2,
        max_tokens=512,
    )

    llm_with_tools = llm.bind_tools([add])
    question = HumanMessage(
        content=f"{text}\n必要な計算には必ずaddツールを使用してください。"
    )

    first_response = llm_with_tools.invoke([question])

    if not first_response.tool_calls:
        raise ValueError("LLM did not call the add tool")

    messages = [question, first_response]

    for tool_call in first_response.tool_calls:
        if tool_call["name"] != "add":
            raise ValueError("Unapproved tool was requested")

        result = add.invoke(tool_call["args"])
        messages.append(
            ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"],
            )
        )

    final_response = llm_with_tools.invoke(messages)

    if not isinstance(final_response.content, str):
        raise ValueError("LLM response is not text")

    return final_response.content

def main(argv: List[str] | None = None) -> int:
    """CLIのエントリポイントです。

    受講者は `run_chain()` の実装に集中し、ここは原則編集しません。
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
        out = run_chain(args.text)
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
