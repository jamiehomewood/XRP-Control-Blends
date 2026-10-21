"""
Glenda scene server: serves this folder and relays button presses from the remote control page
(control.html, on any phone/tablet/laptop on the same network) to the scene running in OBS.

Run:  python server.py        (or double-click start-server.bat)
Then: OBS Browser source  ->  http://localhost:8000/index.html
      Remote control      ->  http://<this PC's IP>:8000/control.html   (address printed below)

Only the Python standard library is used.
"""
import csv, json, os, socket, threading, time
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

PORT = int(os.environ.get("GLENDA_PORT", "8000"))
ROOT = os.path.dirname(os.path.abspath(__file__))

lock = threading.Lock()
commands = []          # [{"id": n, "cmd": "yes", "t": time}]
next_id = 1
scene_state = {"node": None, "status": "not connected", "ask": "", "text": "", "updated": 0}
people = {}            # client id -> {"name": ..., "seen": time}   (remotes check in every poll)
LOG_DIR = os.path.join(ROOT, "sessions")


def log_answer(a):
    """Append one answer to today's CSV in sessions/ (opens in Excel)."""
    os.makedirs(LOG_DIR, exist_ok=True)
    path = os.path.join(LOG_DIR, datetime.now().strftime("answers_%Y-%m-%d.csv"))
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new: w.writerow(["time", "run started", "name", "question", "answer", "node"])
        run = datetime.fromtimestamp(a.get("run", 0) / 1000).strftime("%H:%M:%S") if a.get("run") else ""
        w.writerow([datetime.now().strftime("%H:%M:%S"), run, a.get("who", ""), a.get("ask", ""), a.get("answer", ""), a.get("node", "")])


def online():
    now = time.time()
    return sorted({p["name"] for p in people.values() if now - p["seen"] < 6 and p["name"]}, key=str.lower)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):          # keep the console quiet apart from commands
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # never cache the scene files while we are editing them
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        global commands
        if self.path.startswith("/api/poll"):
            since = 0
            if "since=" in self.path:
                try: since = int(self.path.split("since=")[1].split("&")[0])
                except ValueError: since = 0
            with lock:
                out = [c for c in commands if c["id"] > since]
                latest = commands[-1]["id"] if commands else 0
            return self._json({"commands": out, "latest": latest})
        if self.path.startswith("/api/state"):
            q = parse_qs(urlparse(self.path).query)
            cid, name = q.get("client", [""])[0][:40], q.get("name", [""])[0].strip()[:30]
            with lock:
                if cid:
                    if cid not in people and name: print(f"[join] {name}")
                    people[cid] = {"name": name, "seen": time.time()}
                return self._json({**scene_state, "people": online()})
        return super().do_GET()

    def do_POST(self):
        global next_id, commands, scene_state
        length = int(self.headers.get("Content-Length", "0") or 0)
        try: data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError: data = {}
        if self.path.startswith("/api/cmd"):
            cmd = str(data.get("cmd", ""))[:32]
            name = str(data.get("name", "") or "Someone").strip()[:30]
            with lock:
                commands.append({"id": next_id, "cmd": cmd, "name": name, "arg": data.get("arg"), "t": time.time()})
                next_id += 1
                commands = commands[-200:]
            print(f"[remote] {name}: {cmd}")
            return self._json({"ok": True})
        if self.path.startswith("/api/answer"):
            print(f"[answer] {data.get('who')} said {data.get('answer')} to \"{data.get('ask')}\"")
            try: log_answer(data)
            except OSError as e: print("could not write the answer log:", e)
            return self._json({"ok": True})
        if self.path.startswith("/api/state"):
            with lock:
                scene_state = {**data, "updated": time.time()}
            return self._json({"ok": True})
        self._json({"error": "unknown"}, 404)


def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1)); return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    ip = lan_ip()
    print("Glenda scene server running.")
    print(f"  OBS Browser source:  http://localhost:{PORT}/index.html")
    print(f"  Remote control:      http://{ip}:{PORT}/control.html   (phone/tablet on the same Wi-Fi)")
    print(f"                       http://localhost:{PORT}/control.html  (on this PC)")
    print(f"Answers are logged to {LOG_DIR}")
    print("Leave this window open. Press Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
