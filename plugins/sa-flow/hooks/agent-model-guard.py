#!/usr/bin/env python3
"""PreToolUse hook for the Agent tool（sa-flow plugin 層）：通用型 subagent 沒填 model 就補預設 sonnet。

通用型 subagent（general-purpose / Explore / Plan / claude / 未指定）沒帶 `model` 時會繼承
主 session 的模型。主 session 跑最貴的模型時，一次派十幾個通用 agent、各跑數百次工具呼叫，
曾單日吃掉近四分之一的週配額。
本 hook 不擋：沒填 model 就以 updatedInput 補 `model: "sonnet"` 放行；有明確填（含 opus）
照原樣；專用 agent（frontmatter 已定 model）與 fork 不動。解析不到 stdin 時 fail-open。
"""
import json
import sys

GENERIC = {"general-purpose", "Explore", "Plan", "claude", ""}
DEFAULT_MODEL = "sonnet"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if payload.get("tool_name") != "Agent":
        return 0
    inp = payload.get("tool_input") or {}
    sub = inp.get("subagent_type") or ""
    if sub == "fork" or sub not in GENERIC or inp.get("model"):
        return 0
    updated = dict(inp)
    updated["model"] = DEFAULT_MODEL
    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "agent-model-guard：%s 未指定 model，補預設 %s（要用其他模型請明確帶 model）"
                                        % (sub or "general-purpose", DEFAULT_MODEL),
            "updatedInput": updated,
        }
    }, sys.stdout, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
