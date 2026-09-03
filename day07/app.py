from __future__ import annotations

import argparse
import logging
import sys
from typing import List
import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse
from langgraph.graph import END, StateGraph
load_dotenv()


def build_parser() -> argparse.ArgumentParser:
    """Day07のCLI引数を定義します（入力と分類モード）。"""
    p = argparse.ArgumentParser(prog="day07")
    p.add_argument("--text", required=True)
    p.add_argument("--mode", choices=["llm", "rule"], default="rule")
    return p


def _validate_args(args: argparse.Namespace) -> None:
    """引数の簡易バリデーションを行います（入力不備は exit code=2）。"""
    if not args.text:
        raise ValueError("--text is required")

class GraphState(TypedDict):
    input: str
    intent: str
    output: str
    errors: list[str]
    mode: str

def run_graph(*, text: str, mode: str) -> str:
    """LangGraphで「分類→分岐→処理」を実行し、最終出力（文字列）を返します。

    mode:
    - `rule`：ルール（キーワード等）でintentを決めて分岐
    - `llm`：LLMでintentを分類して分岐

    受け入れ基準（README）：
    - 分岐が最低2パターンある
    - どの分岐に入ったかがログで分かる
    - 分類不能時のフォールバックがある
    """

    def classify(state: GraphState) -> dict:
        input_text = state["input"]

        if state["mode"] == "rule":
            if "要約" in input_text:
                intent = "summarize"
                reason = "「要約」を検出"
            elif any(word in input_text for word in ("手順", "実装", "計画")):
                intent = "plan"
                reason = "手順・実装・計画に関する語を検出"
            elif any(word in input_text for word in ("教えて", "調べて", "検索")):
                intent = "rag"
                reason = "検索・質問に関する語を検出"
            else:
                intent = "default"
                reason = "分類用キーワードなし"
        else:
            region = os.getenv("AWS_REGION")
            model_id = os.getenv("BEDROCK_MODEL_ID")
            profile = os.getenv("AWS_PROFILE")

            if not region or not model_id:
                raise ValueError("AWS region or model ID is not configured")

            llm = ChatBedrockConverse(
                model=model_id,
                region_name=region,
                credentials_profile_name=profile,
                temperature=0,
                max_tokens=20,
            )
            response = llm.invoke(
                "次の入力を rag、summarize、plan、default の"
                f"いずれか1語だけで分類してください。\n入力: {input_text}"
            )

            if not isinstance(response.content, str):
                raise ValueError("LLM classification response is not text")

            candidate = response.content.strip().lower()
            intent = (
                candidate
                if candidate in {"rag", "summarize", "plan", "default"}
                else "default"
            )
            reason = f"LLM分類結果: {candidate}"

        logging.info("node=classify intent=%s reason=%s", intent, reason)
        return {"intent": intent}

    def rag_node(state: GraphState) -> dict:
        logging.info("branch=rag")
        return {
            "output": f"RAG分岐: 「{state['input']}」の情報を検索します。"
        }

    def summarize_node(state: GraphState) -> dict:
        logging.info("branch=summarize")
        return {
            "output": f"要約分岐: 「{state['input']}」を要約します。"
        }

    def plan_node(state: GraphState) -> dict:
        logging.info("branch=plan")
        return {
            "output": f"タスク分解分岐: 「{state['input']}」の手順を作成します。"
        }

    def default_node(state: GraphState) -> dict:
        logging.info("branch=default")
        return {
            "output": f"デフォルト分岐: 「{state['input']}」を通常処理します。"
        }

    graph = StateGraph(GraphState)
    graph.add_node("classify", classify)
    graph.add_node("rag", rag_node)
    graph.add_node("summarize", summarize_node)
    graph.add_node("plan", plan_node)
    graph.add_node("default", default_node)

    graph.set_entry_point("classify")
    graph.add_conditional_edges(
        "classify",
        lambda state: state["intent"],
        {
            "rag": "rag",
            "summarize": "summarize",
            "plan": "plan",
            "default": "default",
        },
    )

    for node_name in ("rag", "summarize", "plan", "default"):
        graph.add_edge(node_name, END)

    app = graph.compile()
    result = app.invoke(
        {
            "input": text,
            "intent": "",
            "output": "",
            "errors": [],
            "mode": mode,
        }
    )

    return result["output"]


def main(argv: List[str] | None = None) -> int:
    """CLIのエントリポイントです。

    受講者は `run_graph()` を実装します。ここは引数解析/検証/終了コードを担当します。
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)

    try:
        _validate_args(args)
    except Exception as e:
        logging.error(str(e))
        print(str(e), file=sys.stderr)
        return 2

    logging.info("mode=%s", args.mode)

    try:
        out = run_graph(text=args.text, mode=args.mode)
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
