"""Tool-calling turns for both supported formats over one provider-neutral transcript.

Transcript items:
  {"role": "user", "text": str}
  {"role": "assistant", "text": str, "tool_calls": [{"id", "name", "arguments": dict}]}
  {"role": "tool", "tool_call_id": str, "name": str, "content": str, "is_error": bool}
"""
import json

from app.observation.agent import AgentError, endpoint, post, read_key


def openai_messages(system, transcript):
    messages = [{"role": "system", "content": system}]
    for item in transcript:
        if item["role"] == "user":
            messages.append({"role": "user", "content": item["text"]})
        elif item["role"] == "assistant":
            message = {"role": "assistant", "content": item["text"] or None}
            if item["tool_calls"]:
                message["tool_calls"] = [{"id": call["id"], "type": "function",
                                          "function": {"name": call["name"], "arguments": json.dumps(call["arguments"], ensure_ascii=False)}}
                                         for call in item["tool_calls"]]
            messages.append(message)
        else:
            messages.append({"role": "tool", "tool_call_id": item["tool_call_id"], "content": item["content"]})
    return messages


def anthropic_messages(transcript):
    """Anthropic requires alternating roles: tool results and any following user text share one user message."""
    messages = []
    for item in transcript:
        if item["role"] == "assistant":
            blocks = ([{"type": "text", "text": item["text"]}] if item["text"] else []) + \
                [{"type": "tool_use", "id": call["id"], "name": call["name"], "input": call["arguments"]} for call in item["tool_calls"]]
            messages.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "…"}]})
            continue
        block = {"type": "text", "text": item["text"]} if item["role"] == "user" else \
            {"type": "tool_result", "tool_use_id": item["tool_call_id"], "content": item["content"], "is_error": item["is_error"]}
        if messages and messages[-1]["role"] == "user":
            messages[-1]["content"].append(block)
        else:
            messages.append({"role": "user", "content": [block]})
    return messages


def parse_arguments(raw):
    if isinstance(raw, dict):
        return raw, None
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}, "invalid_tool_arguments"
    return (value, None) if isinstance(value, dict) else ({}, "invalid_tool_arguments")


def turn(config, system, transcript, tools):
    """One model call. Returns {"text", "tool_calls", "stop", "usage", "model"}; raises AgentError."""
    key = read_key(config)
    if not (config.base_url and config.model):
        raise AgentError("agent_not_configured")
    if key is None:
        raise AgentError("agent_key_missing")
    url = endpoint(config.api_format, config.base_url)
    if config.api_format == "openai_chat":
        body = {"model": config.model, "messages": openai_messages(system, transcript),
                "tools": [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}} for t in tools]}
        data = post(url, {"Authorization": f"Bearer {key}"}, body, config.timeout_seconds)
        try:
            choice = data["choices"][0]
            message = choice["message"]
            text = message.get("content") or ""
            if isinstance(text, list):
                text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
            calls = []
            for call in message.get("tool_calls") or []:
                arguments, problem = parse_arguments(call["function"].get("arguments"))
                calls.append({"id": str(call["id"]), "name": str(call["function"]["name"]), "arguments": arguments, "problem": problem})
            stop = {"length": "max_tokens"}.get(choice.get("finish_reason"), "tool_use" if calls else "end_turn")
            usage = data.get("usage") or {}
            usage = {"input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens")}
        except (KeyError, IndexError, TypeError, AttributeError):
            raise AgentError("agent_invalid_response") from None
    else:
        body = {"model": config.model, "max_tokens": config.max_output_tokens, "system": system, "messages": anthropic_messages(transcript),
                "tools": [{"name": t["name"], "description": t["description"], "input_schema": t["parameters"]} for t in tools]}
        data = post(url, {"x-api-key": key, "anthropic-version": "2023-06-01"}, body, config.timeout_seconds)
        try:
            text = "".join(block["text"] for block in data["content"] if block.get("type") == "text")
            calls = []
            for block in data["content"]:
                if block.get("type") == "tool_use":
                    arguments, problem = parse_arguments(block.get("input"))
                    calls.append({"id": str(block["id"]), "name": str(block["name"]), "arguments": arguments, "problem": problem})
            stop = data.get("stop_reason") or ("tool_use" if calls else "end_turn")
            usage = data.get("usage") or {}
            usage = {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens")}
        except (KeyError, TypeError, AttributeError):
            raise AgentError("agent_invalid_response") from None
    if not isinstance(text, str):
        raise AgentError("agent_invalid_response")
    return {"text": text.strip(), "tool_calls": calls, "stop": stop, "usage": usage, "model": data.get("model") if isinstance(data.get("model"), str) else None}
