"""Talks to Edits for Mac through its local automation server (the same connection Claude Code uses).

Edits has to be open, with its automation setting on. The address and access token are read
from Claude Code's config (~/.claude.json, server "metapilot-native"), so nothing secret lives here.
"""
import json
import os
import urllib.request
from pathlib import Path


class EditsError(RuntimeError):
    pass


class Edits:
    def __init__(self):
        # EDITS_URL + EDITS_TOKEN (from Edits' "connect" command) work for any tool; otherwise
        # use the connection already saved for Claude Code.
        url, token = os.environ.get("EDITS_URL"), os.environ.get("EDITS_TOKEN")
        auth = {"Authorization": f"Bearer {token}"} if token else {}
        if not (url and token):
            cfg_path = Path.home() / ".claude.json"
            cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
            server = cfg.get("mcpServers", {}).get("metapilot-native")
            if not server:
                raise EditsError("No Edits connection: set EDITS_URL and EDITS_TOKEN, "
                                 "or add Edits to Claude Code from Edits' settings")
            url = url or server["url"]
            auth = auth or server.get("headers", {})
        self.url = url
        self.headers = {"Content-Type": "application/json",
                        "Accept": "application/json, text/event-stream", **auth}
        self.session = None
        self.n = 0
        self._rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "nielparle-tiktok", "version": "1"}})
        self._rpc("notifications/initialized", None, notify=True)

    def _rpc(self, method, params, notify=False):
        body = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            body["params"] = params
        if not notify:
            self.n += 1
            body["id"] = self.n
        headers = dict(self.headers)
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        req = urllib.request.Request(self.url, json.dumps(body).encode(), headers)
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                self.session = r.headers.get("Mcp-Session-Id") or self.session
                raw = r.read().decode()
        except OSError as e:
            raise EditsError(f"can't reach Edits at {self.url}: is the app open? ({e})") from e
        if notify or not raw.strip():
            return None
        if raw.lstrip().startswith("event:") or raw.lstrip().startswith("data:"):  # SSE
            raw = next(l[5:] for l in raw.splitlines() if l.startswith("data:"))
        msg = json.loads(raw)
        if "error" in msg:
            raise EditsError(f"{method}: {msg['error']}")
        return msg["result"]

    def call(self, tool, **args):
        res = self._rpc("tools/call", {"name": tool, "arguments": args})
        text = "".join(c.get("text", "") for c in res.get("content", []) if c.get("type") == "text")
        try:
            data = json.loads(text)
        except ValueError:
            data = {"text": text}
        if res.get("isError") or (isinstance(data, dict) and data.get("ok") is False):
            raise EditsError(f"{tool}({args}): {data.get('error', text) if isinstance(data, dict) else text}")
        return data


if __name__ == "__main__":
    e = Edits()
    print(json.dumps(e.call("appState").get("screen")))
    print(json.dumps(e.call("state"), indent=1)[:400])
