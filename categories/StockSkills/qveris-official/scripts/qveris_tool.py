#!/usr/bin/env python3
import argparse
import json
import os
import sys
from urllib import error, parse, request

BASE_URL = "https://qveris.ai/api/v1"
DEFAULT_TIMEOUT = 60


def get_api_key() -> str:
    key = os.environ.get("QVERIS_API_KEY")
    if not key:
        raise SystemExit("QVERIS_API_KEY environment variable not set")
    return key


def post_json(path: str, payload: dict, query: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> dict:
    api_key = get_api_key()
    url = f"{BASE_URL}{path}"
    if query:
        url += "?" + parse.urlencode(query)
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "qveris-official-skill/0.1",
        },
    )
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP Error {e.code}: {body}")
    except error.URLError as e:
        raise SystemExit(f"Network Error: {e}")


def search_tools(query: str, limit: int = 5, session_id: str | None = None) -> dict:
    payload = {"query": query, "limit": limit}
    if session_id:
        payload["session_id"] = session_id
    return post_json("/search", payload, timeout=30)


def get_tools_by_ids(tool_ids: list[str], session_id: str | None = None) -> dict:
    payload = {"tool_ids": tool_ids}
    if session_id:
        payload["session_id"] = session_id
    return post_json("/tools/by-ids", payload, timeout=30)


def execute_tool(tool_id: str, search_id: str, parameters: dict, max_response_size: int = 20480, session_id: str | None = None) -> dict:
    payload = {
        "search_id": search_id,
        "parameters": parameters,
        "max_response_size": max_response_size,
    }
    if session_id:
        payload["session_id"] = session_id
    return post_json("/tools/execute", payload, query={"tool_id": tool_id}, timeout=60)


def main() -> None:
    parser = argparse.ArgumentParser(description="QVeris discovery/inspect/execute helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=5)
    s.add_argument("--session-id")

    i = sub.add_parser("inspect")
    i.add_argument("tool_ids", nargs="+")
    i.add_argument("--session-id")

    e = sub.add_parser("execute")
    e.add_argument("tool_id")
    e.add_argument("--search-id", required=True)
    e.add_argument("--params", default="{}")
    e.add_argument("--max-size", type=int, default=20480)
    e.add_argument("--session-id")

    args = parser.parse_args()

    if args.cmd == "search":
        out = search_tools(args.query, args.limit, args.session_id)
    elif args.cmd == "inspect":
        out = get_tools_by_ids(args.tool_ids, args.session_id)
    else:
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSON for --params: {exc}")
        out = execute_tool(args.tool_id, args.search_id, params, args.max_size, args.session_id)

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
