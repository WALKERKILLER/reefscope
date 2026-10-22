"""Bounded track pages and shared query semantics for scientific outputs."""
import json
import math

from django.core import signing

from .storage import artifact


def parameters(query):
    if set(query) - {"start_ms", "end_ms", "track_id", "class_id", "roi", "limit", "cursor", "width", "height", "export"}:
        raise ValueError("unknown_parameter")
    result = {}
    try:
        for key in ("start_ms", "end_ms"):
            result[key] = float(query[key]) if key in query else (0 if key == "start_ms" else None)
        for key in ("track_id", "class_id"):
            result[key] = int(query[key]) if key in query else None
            if result[key] is not None and result[key] < 0:
                raise ValueError("invalid_filter")
        result["roi"] = json.loads(query["roi"]) if "roi" in query else None
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("invalid_query") from exc
    for value in (result["start_ms"], result["end_ms"]):
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError("invalid_time_window")
    if result["end_ms"] is not None and result["end_ms"] <= result["start_ms"]:
        raise ValueError("invalid_time_window")
    return result


def records(run):
    with artifact(run,"tracks.jsonl").open("r",encoding="utf-8") as stream:
        while True:
            line = stream.readline(65537)
            if not line:
                break
            if len(line) > 65536:
                raise ValueError("invalid_track_record")
            yield json.loads(line)


def page(run, query):
    if set(query) - {"start_ms", "end_ms", "track_id", "class_id", "limit", "cursor"}:
        raise ValueError("unknown_parameter")
    options = parameters(query)
    if options["roi"] is not None:
        raise ValueError("roi_not_supported_for_track_pages")
    try:
        limit = int(query.get("limit", 500))
    except ValueError as exc:
        raise ValueError("invalid_page_size") from exc
    if not 1 <= limit <= 2000:
        raise ValueError("invalid_page_size")
    binding = {"run":str(run.pk), "attempt":str(run.attempt_token), "options":options}
    offset = 0
    if query.get("cursor"):
        try:
            decoded = signing.loads(query["cursor"], salt="fish-track-page", max_age=86400)
            if decoded["binding"] != binding or type(decoded["offset"]) is not int or decoded["offset"] < 0:
                raise ValueError("invalid_cursor")
            offset = decoded["offset"]
        except (signing.BadSignature, KeyError, TypeError) as exc:
            raise ValueError("invalid_cursor") from exc
    items, next_cursor = [], None
    with artifact(run,"tracks.jsonl").open("rb") as stream:
        stream.seek(offset)
        while True:
            position = stream.tell()
            line = stream.readline(65537)
            if not line:
                break
            if len(line) > 65536:
                raise ValueError("invalid_track_record")
            point = json.loads(line)
            timestamp = point["timestamp_ms"]
            if options["end_ms"] is not None and timestamp >= options["end_ms"]:
                break
            if timestamp < options["start_ms"] or any(options[k] is not None and point[k] != options[k] for k in ("track_id","class_id")):
                continue
            if len(items) == limit:
                next_cursor = signing.dumps({"binding":binding,"offset":position},salt="fish-track-page",compress=True)
                break
            items.append(point)
    return {"items":items,"next_cursor":next_cursor, "query":options}
