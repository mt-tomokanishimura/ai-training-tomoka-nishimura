from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

def run_agent(message: str, history: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
    """チャットUI（`final/chat_ui.py`）から呼び出されるエージェントの入口です。

    受講者が実装する場所は基本的にこの関数（またはこの関数が呼ぶ下位関数）です。

    実装の方針（例）：
    - LangGraphでstateを持つフローを構築
    - ツール（RAG検索、計算、日付取得など）をTool callingで呼び出す
    - 失敗時フォールバック（検索ヒットなし、JSON破損など）を入れる

    引数：
    - message: ユーザーの最新発話
    - history: これまでの会話履歴（role/contentの配列）

    戻り値（辞書）：
    - reply: str（ユーザーに見せる本文）
    - meta: dict（任意。デバッグ用情報や構造化出力を入れてよい）

    注意：
    - APIキーや認証情報をコードに直書きしない
    - 例外は握りつぶさず、UI側で原因が分かるよう meta に入れるか適切にエラー化する
    """
    history = history or []
    text = message.strip()

    if not text:
        raise ValueError("message is required")

    logging.info("agent started history_len=%s", len(history))

    if "猫" in text:
        source = {
            "title": "吾輩は猫である",
            "url": "day05/data/wagahai.txt",
            "excerpt": "吾輩は猫である。名前はまだ無い。",
        }
        answer = "猫に関する根拠が見つかりました。"
        confidence = "high"
    else:
        source = None
        answer = "該当する根拠が見つかりませんでした。質問を具体的にしてください。"
        confidence = "low"

    structured = {
        "answer_summary": answer,
        "citations": [source] if source else [],
        "confidence": confidence,
        "next_actions": ["質問を具体化する", "別のキーワードで再検索する"],
    }

    citations_text = (
        f'- {source["url"]} (excerpt: "{source["excerpt"]}")'
        if source
        else "- (none)"
    )

    reply = (
        f"【回答】\n{answer}\n\n"
        f"【根拠】\n{citations_text}\n\n"
        f"【構造化出力】\n"
        f"{json.dumps(structured, ensure_ascii=False, indent=2)}"
    )

    logging.info(
        "agent completed confidence=%s source_found=%s",
        confidence,
        source is not None,
    )

    return {
        "reply": reply,
        "meta": {
            "history_len": len(history),
            "source_found": source is not None,
            "structured": structured,
        },
    }
