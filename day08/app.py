from __future__ import annotations

import argparse
import logging
import sys
from typing import List

import json
from typing import TypedDict

from langgraph.graph import END, StateGraph


def build_parser() -> argparse.ArgumentParser:
    """Day08のCLI引数を定義します（入力と上限設定）。"""
    p = argparse.ArgumentParser(prog="day08")
    p.add_argument("--text", required=True)
    p.add_argument("--max-steps", type=int, default=10)
    p.add_argument("--max-retry", type=int, default=1)
    return p


def _validate_args(args: argparse.Namespace) -> None:
    """引数の簡易バリデーションを行います（入力不備は exit code=2）。"""
    if not args.text:
        raise ValueError("--text is required")
    if not (1 <= args.max_steps <= 50):
        raise ValueError("--max-steps must be between 1 and 50")
    if not (0 <= args.max_retry <= 5):
        raise ValueError("--max-retry must be between 0 and 5")

class GraphState(TypedDict):
    input: str
    candidate: str
    output: str
    error: str
    status: str
    retry_count: int
    max_retry: int
    step_count: int
    max_steps: int

def run_graph(*, text: str, max_steps: int, max_retry: int) -> str:
    """失敗時復帰（リトライ/フォールバック）付きのフローを実行します。

    実装ガイド：
    - 失敗パターンを1つ以上作り、復帰パスへ入ることを確認する
      - 例：JSONが壊れる→再生成
      - 例：検索ヒットなし→聞き返し
    - `max_steps` / `max_retry` を上限として必ず反映し、無限ループを防ぐ
    - 上限到達時は明示的に失敗（例外）してよい（mainがexit code=1にする）
    """
    def use_step(state: GraphState, node_name: str) -> int:
        next_step = state["step_count"] + 1

        if next_step > state["max_steps"]:
            raise RuntimeError(
                f"maximum steps reached: {state['max_steps']}"
            )

        logging.info(
            "node=%s step=%s/%s retry=%s/%s",
            node_name,
            next_step,
            state["max_steps"],
            state["retry_count"],
            state["max_retry"],
        )
        return next_step

    def generate(state: GraphState) -> dict:
        step_count = use_step(state, "generate")

        if "存在しない情報" in state["input"]:
            return {
                "candidate": "",
                "status": "fallback",
                "step_count": step_count,
            }

        if (
            "不完全なJSON" in state["input"]
            and state["retry_count"] == 0
        ):
            candidate = '{"answer":'
        else:
            candidate = json.dumps(
                {"answer": f"処理結果: {state['input']}"},
                ensure_ascii=False,
            )

        return {
            "candidate": candidate,
            "status": "generated",
            "step_count": step_count,
        }

    def validate(state: GraphState) -> dict:
        step_count = use_step(state, "validate")

        if state["status"] == "fallback":
            return {"step_count": step_count}

        try:
            parsed = json.loads(state["candidate"])
        except json.JSONDecodeError as error:
            status = (
                "retry"
                if state["retry_count"] < state["max_retry"]
                else "failed"
            )
            logging.warning("JSON validation failed: %s", error)
            return {
                "status": status,
                "error": str(error),
                "step_count": step_count,
            }

        return {
            "status": "success",
            "output": parsed["answer"],
            "error": "",
            "step_count": step_count,
        }

    def retry_node(state: GraphState) -> dict:
        step_count = use_step(state, "retry")
        retry_count = state["retry_count"] + 1
        logging.info("retrying attempt=%s", retry_count)

        return {
            "retry_count": retry_count,
            "step_count": step_count,
        }

    def fallback_node(state: GraphState) -> dict:
        step_count = use_step(state, "fallback")
        logging.info("fallback=ask_user_to_rephrase")

        return {
            "status": "success",
            "output": "該当情報が見つかりません。質問を具体的にしてください。",
            "step_count": step_count,
        }

    def fail_node(state: GraphState) -> dict:
        use_step(state, "fail")
        raise RuntimeError(
            f"recovery failed after {state['retry_count']} retries: "
            f"{state['error']}"
        )

    graph = StateGraph(GraphState)
    graph.add_node("generate", generate)
    graph.add_node("validate", validate)
    graph.add_node("retry", retry_node)
    graph.add_node("fallback", fallback_node)
    graph.add_node("fail", fail_node)

    graph.set_entry_point("generate")
    graph.add_edge("generate", "validate")
    graph.add_conditional_edges(
        "validate",
        lambda state: state["status"],
        {
            "success": END,
            "retry": "retry",
            "fallback": "fallback",
            "failed": "fail",
        },
    )
    graph.add_edge("retry", "generate")
    graph.add_edge("fallback", END)
    graph.add_edge("fail", END)

    app = graph.compile()
    result = app.invoke(
        {
            "input": text,
            "candidate": "",
            "output": "",
            "error": "",
            "status": "",
            "retry_count": 0,
            "max_retry": max_retry,
            "step_count": 0,
            "max_steps": max_steps,
        },
        {"recursion_limit": max_steps + 5},
    )

    return result["output"]


def main(argv: List[str] | None = None) -> int:
    """CLIのエントリポイントです。

    受講者は `run_graph()` を実装します。ここは引数解析/検証/上限の適用/終了コードを担当します。
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)

    try:
        _validate_args(args)
    except Exception as e:
        logging.error(str(e))
        print(str(e), file=sys.stderr)
        return 2

    logging.info("max-steps=%s max-retry=%s", args.max_steps, args.max_retry)

    try:
        out = run_graph(text=args.text, max_steps=args.max_steps, max_retry=args.max_retry)
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
