#!/usr/bin/env python3
"""
Tiny analytics server for the Flames of Foe redirect page.
Appends each event as a JSON line to analytics.ndjson.

Usage:
    python3 analytics_server.py
    python3 analytics_server.py --port 5555 --log analytics.ndjson
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

DEFAULT_PORT = 5555
DEFAULT_LOG  = os.path.join(os.path.dirname(__file__), "analytics.ndjson")


class AnalyticsHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Suppress default Apache-style access log; we write our own
        pass

    def _cors_headers(self):
        # Allow the static page (any origin) to POST here.
        # Tighten this to your actual domain in production.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path != "/analytics":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self._cors_headers()
            self.end_headers()
            return

        # Enrich with server-side IP
        data["ip"] = self.client_address[0]
        if not data.get("ts"):
            data["ts"] = datetime.now(timezone.utc).isoformat()

        line = json.dumps(data, ensure_ascii=False)
        with open(self.server.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

        print(f"[{data['ts']}] {data.get('event','?'):10s}  {data.get('label') or data.get('utm',{}).get('source','') or ''}")

        self.send_response(204)
        self._cors_headers()
        self.end_headers()


def main():
    parser = argparse.ArgumentParser(description="Flames of Foe analytics server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--log",  default=DEFAULT_LOG)
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), AnalyticsHandler)
    server.log_path = args.log

    print(f"Analytics server listening on :{args.port}")
    print(f"Logging to: {args.log}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
