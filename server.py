#!/usr/bin/env python3
"""Chelsea Matchday server: stdlib only, binds 127.0.0.1:4276. Serves web/ + /api/match + /api/research."""
import http.server, json, os, socketserver, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "4276"))
WEB = os.path.join(HERE, "web")


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=WEB, **k)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.log_date_time_string(), fmt % args))

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/match":
            try:
                with open(os.path.join(HERE, "data", "match.json"), "rb") as f:
                    body = f.read()
                json.loads(body)
                self._send(200, body, "application/json")
            except Exception as e:
                self._send(503, json.dumps({"error": f"data unavailable: {e}"}).encode(), "application/json")
            return
        if path == "/api/research":
            try:
                with open(os.path.join(HERE, "data", "research_notes.json"), "rb") as f:
                    body = f.read()
                json.loads(body)
                self._send(200, body, "application/json")
            except Exception as e:
                self._send(200, json.dumps({"label": "research unavailable", "sections": [], "error": str(e)}).encode(), "application/json")
            return
        if path in ("/healthz", "/api/health"):
            self._send(200, b'{"ok":true}', "application/json"); return
        return super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


if __name__ == "__main__":
    with S(("127.0.0.1", PORT), H) as srv:
        print(f"Chelsea Matchday on http://127.0.0.1:{PORT}", flush=True)
        srv.serve_forever()
