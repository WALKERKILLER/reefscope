"""Optional narrative from an OpenAI-compatible or Anthropic Messages endpoint, via stdlib HTTP only.

The agent never supplies numbers: it writes `{{metric_id}}` placeholders that the server replaces with
deterministic values, and cites only the provided source IDs. Its output is audited and stored as segments.
"""
import hashlib
import json
import os
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings

from app.models import ReportAgentConfig
from .sources import SOURCES

PROMPT_VERSION = "reefscope-observation-agent/v1"
FORMATS = ("openai_chat", "anthropic_messages")
MAX_RESPONSE_BYTES = 1024 * 1024
API_KEY = re.compile(r"[\x21-\x7e]{8,400}")
PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")
CITATION = re.compile(r"\[([A-Z0-9][A-Z0-9-]{1,30})\]")
NUMBER = re.compile(r"\d+(?:[.,]\d+)*(?:\s*%)?")
SECTIONS = ("observations", "interpretation", "limitations", "next_steps")

SYSTEM_PROMPT = """你是珊瑚礁视频观测报告的撰写助手。平台已经用确定性程序算好了全部指标；你只用简体中文解释这些结果，不计算、不估计、不补全任何数值。

规则：
1. 引用数值时只写占位符 {{指标ID}}，例如 {{v1.fish.mean_count}}，平台会替换成核对过的数值和单位。正文不要直接写阿拉伯数字。指代视频时写 {{v1.label}} 这样的占位符。
2. 只使用 metrics 中给出的指标 ID。状态为 unavailable 的指标，说明缺少什么，不推测数值。
3. 引用资料时只用 sources 中的 ID，写成 [CRW-BAA] 的形式，放在相应句子末尾。
4. 解释边界：
   - 珊瑚像素占比是画面平面统计，不等于活珊瑚覆盖率；珊瑚像素中的白化比例不等于群体白化发生率。
   - 平均可见鱼数（MeanCount）和画面峰值是相对丰度指标，不是个体数量或密度；追踪 ID 数不等于鱼的个体数。
   - 单次观测不能推断趋势、原因或整片海域的状况；鱼类与珊瑚同时出现不代表因果。
   - 环境数据由用户录入，只作背景，不用来解释白化原因。
   - 没有独立真值时，不评价模型精度。
   - comparison 不可比（comparable 为 false）时，不描述变化方向，只说明不可比的原因。
5. 不给健康等级或评分，不用"良好""健康"等缺少依据的判断。
6. 只输出一个 JSON 对象，不加 Markdown 代码块：
{"summary": "两三句总体结论", "observations": ["观察到的事实"], "interpretation": ["结合资料的解释"], "limitations": ["本次结论的限制"], "next_steps": ["建议补充的数据或复核"]}
每个数组 1–5 条，每条不超过 200 字。"""


ERRORS = {
    "agent_disabled": "AI 解读未启用。", "agent_not_configured": "请先填写接口地址和模型。", "agent_key_missing": "请先保存 API Key。",
    "agent_auth_failed": "服务拒绝了这个 API Key。检查 Key 是否有效、是否有该模型的权限。",
    "agent_endpoint_not_found": "接口地址不存在。检查 Base URL 和接口格式是否匹配。",
    "agent_rate_limited": "请求过于频繁或额度不足，稍后再试。", "agent_request_rejected": "服务拒绝了请求。检查模型名称是否正确。",
    "agent_upstream_error": "服务端出错，稍后再试。", "agent_http_error": "服务返回了意外的 HTTP 状态。",
    "agent_redirect_refused": "接口发生了重定向，平台不跟随重定向。请填写最终地址。",
    "agent_timeout": "请求超时。可以调大超时时间，或换用响应更快的模型。", "agent_unreachable": "无法连接到接口地址。检查网络和地址。",
    "agent_tls_error": "TLS 证书校验失败。", "agent_response_too_large": "响应超过 1 MB，已停止读取。",
    "agent_invalid_response": "返回内容不是约定的 JSON 格式。", "agent_output_truncated": "输出达到长度上限被截断。可以调大最大输出 tokens。",
}


class AgentError(Exception):
    def __init__(self, code, http_status=None):
        super().__init__(code)
        self.code, self.http_status = code, http_status


def config():
    return ReportAgentConfig.objects.get_or_create(pk=1)[0]


def key_path():
    return Path(settings.REPORT_AGENT_KEY_PATH)


def read_key(item):
    path = key_path()
    if not item.key_bound_url or item.key_bound_url != item.base_url or not path.is_file():
        return None
    return path.read_text(encoding="ascii").strip() or None


def write_key(value):
    path = key_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="ascii") as stream:
        stream.write(value)
    os.replace(temporary, path)


def clear_key(item):
    key_path().unlink(missing_ok=True)
    item.key_hint, item.key_bound_url = "", ""


def normalize_url(value):
    if not isinstance(value, str) or len(value) > 500:
        raise ValueError("invalid_base_url")
    value = value.strip().rstrip("/")
    if not value:
        return ""
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("invalid_base_url")
    return value


def endpoint(api_format, base_url):
    if not base_url:
        return ""
    if api_format == "openai_chat":
        return base_url if base_url.endswith("/chat/completions") else base_url + "/chat/completions"
    if base_url.endswith("/messages"):
        return base_url
    return base_url + ("/messages" if base_url.endswith("/v1") else "/v1/messages")


def serialize(item):
    return {"api_format": item.api_format, "base_url": item.base_url, "model": item.model, "timeout_seconds": item.timeout_seconds,
            "max_output_tokens": item.max_output_tokens, "enabled": item.enabled, "key_configured": read_key(item) is not None,
            "key_hint": item.key_hint if read_key(item) else "", "endpoint": endpoint(item.api_format, item.base_url),
            "prompt_version": PROMPT_VERSION, "updated_at": item.updated_at}


def update(item, data):
    """Apply a validated PUT. The key is write-only and cleared whenever the base URL changes."""
    allowed = {"api_format", "base_url", "model", "timeout_seconds", "max_output_tokens", "enabled", "api_key", "clear_api_key"}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError("invalid_agent_config")
    api_format = data.get("api_format", item.api_format)
    if api_format not in FORMATS:
        raise ValueError("invalid_api_format")
    base_url = normalize_url(data["base_url"]) if "base_url" in data else item.base_url
    model = data.get("model", item.model)
    # Gateways name models freely (spaces, brackets, CJK aliases). The ID only travels inside a JSON
    # body, so the only rules are the column length and no control or line-break characters.
    if not isinstance(model, str) or len(model.strip()) > 120 or not model.strip().isprintable():
        raise ValueError("invalid_model")
    timeout = data.get("timeout_seconds", item.timeout_seconds)
    if type(timeout) is not int or not 5 <= timeout <= 100:
        raise ValueError("invalid_timeout")
    tokens = data.get("max_output_tokens", item.max_output_tokens)
    if type(tokens) is not int or not 256 <= tokens <= 32000:
        raise ValueError("invalid_max_output_tokens")
    enabled = data.get("enabled", item.enabled)
    key = data.get("api_key")
    if type(enabled) is not bool or type(data.get("clear_api_key", False)) is not bool:
        raise ValueError("invalid_agent_config")
    if key is not None and (not isinstance(key, str) or not API_KEY.fullmatch(key.strip())):
        raise ValueError("invalid_api_key")
    url_changed = base_url != item.base_url
    item.api_format, item.base_url, item.model = api_format, base_url, model.strip()
    item.timeout_seconds, item.max_output_tokens = timeout, tokens
    if data.get("clear_api_key") or (url_changed and key is None):
        clear_key(item)
    if key is not None:
        key = key.strip()
        write_key(key)
        item.key_hint, item.key_bound_url = (key[-4:] if len(key) >= 16 else ""), base_url
    if enabled and not (item.base_url and item.model and read_key(item)):
        raise ValueError("agent_config_incomplete")
    item.enabled = enabled
    item.save()
    return item


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def post(url, headers, body, timeout):
    """POST JSON with no redirects, an overall deadline and a response size cap."""
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"), method="POST",
                                     headers={"Content-Type": "application/json", "Accept": "application/json", **headers})
    deadline = time.monotonic() + timeout
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=timeout) as response:
            chunks, size = [], 0
            while chunk := response.read(65536):
                size += len(chunk)
                if size > MAX_RESPONSE_BYTES:
                    raise AgentError("agent_response_too_large")
                if time.monotonic() > deadline:
                    raise AgentError("agent_timeout")
                chunks.append(chunk)
    except urllib.error.HTTPError as exc:
        status = exc.code
        code = {401: "agent_auth_failed", 403: "agent_auth_failed", 404: "agent_endpoint_not_found", 429: "agent_rate_limited"}.get(status)
        if code is None:
            code = "agent_redirect_refused" if 300 <= status < 400 else "agent_request_rejected" if status in (400, 413, 422) else \
                "agent_upstream_error" if status >= 500 else "agent_http_error"
        raise AgentError(code, status) from None
    except (socket.timeout, TimeoutError):
        raise AgentError("agent_timeout") from None
    except urllib.error.URLError as exc:
        reason = exc.reason
        raise AgentError("agent_timeout" if isinstance(reason, (socket.timeout, TimeoutError)) else
                         "agent_tls_error" if isinstance(reason, ssl.SSLError) else "agent_unreachable") from None
    except (ssl.SSLError, ConnectionError, OSError):
        raise AgentError("agent_unreachable") from None
    try:
        return json.loads(b"".join(chunks).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AgentError("agent_invalid_response") from None


def complete(item, system, user, max_tokens=None):
    """One chat turn; returns text, stop flag and usage in a format-neutral shape."""
    key = read_key(item)
    if not (item.base_url and item.model):
        raise AgentError("agent_not_configured")
    if key is None:
        raise AgentError("agent_key_missing")
    url = endpoint(item.api_format, item.base_url)
    if item.api_format == "openai_chat":
        # Reasoning models reject max_tokens and temperature, so neither is sent.
        body = {"model": item.model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        data = post(url, {"Authorization": f"Bearer {key}"}, body, item.timeout_seconds)
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            if isinstance(content, list):
                content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
            truncated = choice.get("finish_reason") == "length"
            usage = data.get("usage") or {}
            usage = {"input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens")}
        except (KeyError, IndexError, TypeError, AttributeError):
            raise AgentError("agent_invalid_response") from None
    else:
        body = {"model": item.model, "max_tokens": max_tokens or item.max_output_tokens, "system": system,
                "messages": [{"role": "user", "content": user}]}
        data = post(url, {"x-api-key": key, "anthropic-version": "2023-06-01"}, body, item.timeout_seconds)
        try:
            content = "".join(block["text"] for block in data["content"] if block.get("type") == "text")
            truncated = data.get("stop_reason") == "max_tokens"
            usage = data.get("usage") or {}
            usage = {"input_tokens": usage.get("input_tokens"), "output_tokens": usage.get("output_tokens")}
        except (KeyError, TypeError, AttributeError):
            raise AgentError("agent_invalid_response") from None
    if not isinstance(content, str):
        raise AgentError("agent_invalid_response")
    return {"text": content, "truncated": truncated, "usage": usage, "model": data.get("model") if isinstance(data.get("model"), str) else None}


def test_connection(item):
    started = time.monotonic()
    try:
        result = complete(item, "Reply with the single word OK.", "Connection test.", max_tokens=16)
        return {"ok": True, "latency_ms": round((time.monotonic() - started) * 1000), "model": result["model"], "error_code": None, "http_status": None}
    except AgentError as exc:
        return {"ok": False, "latency_ms": round((time.monotonic() - started) * 1000), "model": None, "error_code": exc.code,
                "error_text": ERRORS.get(exc.code), "http_status": exc.http_status}


def agent_input(facts):
    """The data sent to the endpoint: statistics and labels only; no coordinates, file names or run IDs."""
    keep = ("label", "unit", "status", "reason", "display", "source")
    return {
        "site": facts["site"]["name"], "observed_on": facts["observed_on"],
        "videos": [{"label": f"{{{{v{video['index']}.label}}}}", "analyses": sorted(video["runs"]),
                    "camera_motion": sorted({run["camera_motion"] for run in video["runs"].values()})} for video in facts["videos"]],
        "metrics": {key: {name: item[name] for name in keep} for key, item in facts["metrics"].items()},
        "comparison": None if facts["comparison"] is None else {key: facts["comparison"][key] for key in ("previous_observed_on", "comparable", "reasons")},
        "model_quality": facts["model_quality"],
        "limitations": facts["limitations"],
        "sources": {key: {name: card[name] for name in ("title", "year", "supports", "limits")} for key, card in SOURCES.items()},
    }


def parse(text):
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1].rsplit("```", 1)[0]
    start, end = stripped.find("{"), stripped.rfind("}")
    try:
        data = json.loads(stripped[start:end + 1]) if start >= 0 < end else None
    except json.JSONDecodeError:
        data = None
    if not isinstance(data, dict) or not isinstance(data.get("summary"), str) or len(data["summary"]) > 1200:
        raise AgentError("agent_invalid_response")
    result = {"summary": data["summary"].strip()}
    for name in SECTIONS:
        items = data.get(name, [])
        if not isinstance(items, list) or len(items) > 10 or not all(isinstance(entry, str) and len(entry) <= 800 for entry in items):
            raise AgentError("agent_invalid_response")
        result[name] = [entry.strip() for entry in items if entry.strip()]
    return result


def segments(text, metrics, audit):
    """Split text into plain, verified-metric, citation and unverified-number segments."""
    output, cursor = [], 0
    tokens = sorted([(m.start(), m.end(), "metric", m.group(1)) for m in PLACEHOLDER.finditer(text)] +
                    [(m.start(), m.end(), "citation", m.group(1)) for m in CITATION.finditer(text)])

    def plain(fragment):
        position = 0
        for match in NUMBER.finditer(fragment):
            if match.start() > position:
                output.append({"text": fragment[position:match.start()]})
            output.append({"text": match.group(0), "unverified": True})
            audit["unverified_numbers"].append(match.group(0).strip())
            position = match.end()
        if position < len(fragment):
            output.append({"text": fragment[position:]})

    for start, end, kind, value in tokens:
        if start < cursor:
            continue
        plain(text[cursor:start])
        if kind == "metric" and value in metrics:
            output.append({"text": metrics[value]["display"], "metric": value})
        elif kind == "metric":
            audit["unknown_metrics"].append(value)
            output.append({"text": "〔未知指标〕", "unknown": True})
        elif value in SOURCES:
            output.append({"text": f"[{value}]", "citation": value})
            audit["citations"].append(value)
        else:
            audit["unknown_citations"].append(value)
            if output and set(output[-1]) == {"text"}:
                output[-1]["text"] = output[-1]["text"].rstrip()
        cursor = end
    plain(text[cursor:])
    return output


def narrate(item, facts):
    """Returns the stored agent record: status, metadata, audited segments; never raises AgentError."""
    user = json.dumps(agent_input(facts), ensure_ascii=False, sort_keys=True, allow_nan=False)
    record = {"status": "failed", "prompt_version": PROMPT_VERSION, "api_format": item.api_format, "model": item.model,
              "host": urllib.parse.urlsplit(item.base_url).hostname or "", "request_sha256": hashlib.sha256((SYSTEM_PROMPT + user).encode()).hexdigest(),
              "latency_ms": None, "usage": None, "error_code": None, "http_status": None, "narrative": None, "audit": None}
    started = time.monotonic()
    try:
        result = complete(item, SYSTEM_PROMPT, user)
        record["usage"], record["response_model"] = result["usage"], result["model"]
        if result["truncated"]:
            raise AgentError("agent_output_truncated")
        narrative = parse(result["text"])
    except AgentError as exc:
        record.update(error_code=exc.code, error_text=ERRORS.get(exc.code), http_status=exc.http_status,
                      latency_ms=round((time.monotonic() - started) * 1000))
        return record
    audit = {"unverified_numbers": [], "unknown_metrics": [], "unknown_citations": [], "citations": []}
    record["narrative"] = {"summary": segments(narrative["summary"], facts["metrics"], audit),
                           **{name: [segments(entry, facts["metrics"], audit) for entry in narrative[name]] for name in SECTIONS}}
    record["audit"] = {key: sorted(set(values)) for key, values in audit.items()}
    record.update(status="generated", latency_ms=round((time.monotonic() - started) * 1000))
    return record
