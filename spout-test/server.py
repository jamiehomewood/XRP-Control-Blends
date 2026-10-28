"""
Glenda scene server: serves this folder and relays button presses from the remote control page
(control.html, on any phone/tablet/laptop on the same network) to the scene running in OBS.

Run:  python server.py        (or double-click start-server.bat)
Then: OBS Browser source  ->  http://localhost:8000/index.html
      Remote control      ->  http://<this PC's IP>:8000/control.html   (address printed below)

The remote also has a scene picker (groups, search, tags - tags are edited on the tablet and saved to scenes.json),
a Reset scene button, and a panel of controls for the live scene: each scene lists its own controls with remote.js.

Only the Python standard library is used.
"""
import csv, email.utils, json, mimetypes, os, re, socket, threading, time
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
SCENES_FILE = os.path.join(ROOT, "scenes.json")
stage = {"current": None, "seen": 0, "load": 0}   # which scene stage.html (the page loaded in the Igloo) should show;
                                                  # "load" goes up on Reset scene, so stage.html reloads it
# Scene controls (effects, audio layers...). The tablet sets values here; the live scene polls them (remote.js).
# Cleared whenever the scene changes or is reset, so every scene starts from its own defaults.
controls = {"rev": 0, "reset": 0, "values": {}}
reports = {}           # scene page -> what it last said about itself: {"title", "controls", "values", "t"}


def norm(url):
    """'/dementia.html?night=dusk', './dementia.html?night=dusk' and 'dementia.html?night=dusk' are the same page."""
    u = str(url or "").split("#")[0]
    for pre in ("http://", "https://"):
        if u.startswith(pre): u = "/" + u[len(pre):].split("/", 1)[-1]
    return u.lstrip("./")


def clear_controls():
    controls["values"] = {}
    controls["reset"] += 1
    controls["rev"] += 1


def save_scenes(scenes):
    """Write scenes.json back, one scene per line so it stays easy to edit by hand."""
    body = "[\n" + ",\n".join("  " + json.dumps(x, ensure_ascii=False) for x in scenes) + "\n]\n"
    tmp = SCENES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: f.write(body)
    os.replace(tmp, SCENES_FILE)


def clean_tags(tags):
    out = []
    for t in tags if isinstance(tags, list) else []:
        t = " ".join(str(t).split())[:30]
        if t and t.lower() not in (x.lower() for x in out): out.append(t)
    return out[:12]


def live_panel():
    """The control panel of the scene that is showing now (or, with no stage.html open, the newest scene to report)."""
    now, st = time.time(), stage_info()
    fresh = {k: r for k, r in reports.items() if now - r["t"] < 5}
    if st["connected"]:
        r = fresh.get(norm(st["url"]))
    else:
        r = max(fresh.values(), key=lambda r: r["t"], default=None)
    if not r: return None
    return {"page": r["page"], "title": r.get("title", ""), "controls": r.get("controls", []), "values": r.get("values", {})}


def own_scenes():
    """scenes.json is read on every request, so it can be edited while the server runs."""
    try:
        with open(SCENES_FILE, encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError) as e:
        print("could not read scenes.json:", e); return []


# ------------------------------------------------------------------ Room Builder library
# Every finished room in the Room Builder library becomes a scene (one per rendered view), served from here so the
# Room Builder server doesn't need to be running. Where the library is: the RB_LIBRARY environment variable, else the
# first line of roombuilder_library.txt next to this file, else ..\..\RoomBuilder\library (D:\Projects\01_Active\RoomBuilder).
EXTRA_FILE = os.path.join(ROOT, "scene_extras.json")   # tags and hiding for library rooms: {"scene id": {"tags": [...], "hidden": true}}
ROOM_TYPES = {"modern": "Home", "neglected": "Home", "home": "Home", "hospital": "Hospital", "court": "Court",
              "custody": "Custody", "outdoor": "Outdoor"}
_lib_cache = {"t": 0, "dir": None, "scenes": []}


def rb_library():
    d = os.environ.get("RB_LIBRARY", "").strip()
    if not d:
        try:
            with open(os.path.join(ROOT, "roombuilder_library.txt"), encoding="utf-8") as f: d = f.readline().strip().strip('"')
        except OSError: d = ""
    return os.path.normpath(d or os.path.join(ROOT, "..", "..", "RoomBuilder", "library"))


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except (OSError, ValueError): return default


def library_scenes():
    """Room Builder library -> scenes (re-read at most every 5 s, so new renders appear without a restart)."""
    lib = rb_library()
    if time.time() - _lib_cache["t"] < 5 and _lib_cache["dir"] == lib: return _lib_cache["scenes"]
    out = []
    rooms = {r.get("id"): r.get("name", r.get("id")) for r in read_json(os.path.join(lib, "..", "presets", "rooms.json"), {}).get("rooms", [])}
    try: ids = sorted(os.listdir(lib), reverse=True)                         # newest first
    except OSError: ids = []
    for lid in ids:
        if lid.startswith("_") or not re.fullmatch(r"[\w\-]+", lid): continue
        meta = read_json(os.path.join(lib, lid, "meta.json"), None)
        if not isinstance(meta, dict): continue
        spec = read_json(os.path.join(lib, lid, "spec.json"), {})
        style = str(meta.get("style") or spec.get("style") or "")
        kind = ROOM_TYPES.get(style, style.title() or "Other")
        cond = spec.get("condition") or ("neglected" if style == "neglected" else "")
        preset = (meta.get("room") or {}).get("preset") or (spec.get("room") or {}).get("preset") or "custom"
        room = rooms.get(preset, "custom size" if preset == "custom" else preset).split(" (")[0]
        tags = ["Room Builder", kind.lower(), room]
        if cond: tags.append(cond.replace("_", " "))
        if meta.get("lighting") == "night": tags.append("night")
        if spec.get("lights_on") is False: tags.append("lights off")
        if meta.get("quality") == "draft": tags.append("draft")
        views = [v for v in (meta.get("views") or ["centre"]) if re.fullmatch(r"[\w\-]+", str(v))]
        for v in views:
            if not os.path.exists(os.path.join(lib, lid, f"view_{v}.jpg")): continue
            out.append({"id": f"rb-{lid}-{v}", "label": meta.get("name", lid) + ("" if v == "centre" else f" ({v} view)"),
                        "url": f"rbpano.html?lib={lid}&view={v}", "group": f"Room Builder – {kind}", "tags": tags[:],
                        "thumb": f"/rb/{lid}/thumb_{v}.jpg" if os.path.exists(os.path.join(lib, lid, f"thumb_{v}.jpg")) else "",
                        "note": str(meta.get("created", "")), "library": True})
    _lib_cache.update(t=time.time(), dir=lib, scenes=out)
    return out


# Tours made in Room Builder's Tour Builder (RoomBuilder\tours\*.json, next to the library): one scene each, played by
# Room Builder's builder\tour.html, which this server serves as /rbtour.html (the tablet drives it through remote.js).
_tour_cache = {"t": 0, "scenes": []}


def rb_root():
    return os.path.dirname(rb_library())


def tour_scenes():
    if time.time() - _tour_cache["t"] < 5: return _tour_cache["scenes"]
    d = os.path.join(rb_root(), "tours"); out = []
    try: names = sorted(os.listdir(d))
    except OSError: names = []
    for f in names:
        if not f.endswith(".json") or not re.fullmatch(r"[\w\-]+\.json", f): continue
        t = read_json(os.path.join(d, f), None)
        if not isinstance(t, dict): continue
        rooms = [r for r in t.get("rooms") or [] if isinstance(r, dict)]
        first = next((r for r in rooms if r.get("id") == t.get("start")), rooms[0] if rooms else {})
        lib, view = str(first.get("lib", "")), str(first.get("view", "centre"))
        thumb = f"/rb/{lib}/thumb_{view}.jpg" if lib and os.path.exists(os.path.join(rb_library(), lib, f"thumb_{view}.jpg")) else ""
        out.append({"id": "tour-" + f[:-5], "label": t.get("name", f[:-5]), "url": f"rbtour.html?tour={f[:-5]}", "group": "Tours",
                    "tags": ["Tour", "Room Builder"], "thumb": thumb, "note": f"{len(rooms)} rooms", "library": True})
    _tour_cache.update(t=time.time(), scenes=out)
    return out


def load_scenes():
    """Your own scenes (scenes.json), Tour Builder tours, then the Room Builder rooms, with tags/hiding from scene_extras.json applied."""
    extras = read_json(EXTRA_FILE, {})
    out = []
    for sc in own_scenes() + [dict(x, tags=list(x["tags"])) for x in tour_scenes() + library_scenes()]:
        ex = extras.get(sc.get("id")) or {}
        if sc.get("library") and isinstance(ex.get("tags"), list): sc["tags"] = ex["tags"]
        if ex.get("hidden"): sc["hidden"] = True
        out.append(sc)
    return out


def save_extra(sid, **kw):
    extras = read_json(EXTRA_FILE, {})
    e = extras.setdefault(sid, {})
    e.update(kw)
    if not e.get("hidden"): e.pop("hidden", None)
    if not e: extras.pop(sid, None)
    tmp = EXTRA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(extras, f, ensure_ascii=False, indent=1)
    os.replace(tmp, EXTRA_FILE)


def stage_info():
    scenes = load_scenes()
    cur = stage["current"] or (scenes[0]["id"] if scenes else None)
    sc = next((x for x in scenes if x["id"] == cur), None)
    return {"current": cur, "label": sc["label"] if sc else "", "url": sc["url"] if sc else "",
            "load": stage["load"], "connected": time.time() - stage["seen"] < 5}
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
        # never cache the scene files while we are editing them (Room Builder renders don't change, so those can be)
        # renders can be turned in place in Room Builder, so they are checked each time (unchanged ones answer 304: cheap)
        self.send_header("Cache-Control", "no-cache" if self.path.startswith("/rb/") else "no-store")
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
        if self.path.startswith("/api/scenes"):
            with lock:
                if "stage=1" in self.path: stage["seen"] = time.time()      # stage.html checking in
                return self._json({"scenes": load_scenes(), **stage_info()})
        if self.path.startswith("/api/state"):
            q = parse_qs(urlparse(self.path).query)
            cid, name = q.get("client", [""])[0][:40], q.get("name", [""])[0].strip()[:30]
            with lock:
                if cid:
                    if cid not in people and name: print(f"[join] {name}")
                    people[cid] = {"name": name, "seen": time.time()}
                return self._json({**scene_state, "people": online(), "stage": stage_info(), "panel": live_panel()})
        m = re.fullmatch(r"/rb/([\w\-]+)/((?:view|thumb)_[\w\-]+\.jpg)", urlparse(self.path).path)
        if m:                                                        # a Room Builder render (read straight from its library)
            fp = os.path.join(rb_library(), m.group(1), m.group(2))
            try:
                mtime = int(os.path.getmtime(fp))
                with open(fp, "rb") as f: body = f.read()
            except OSError: return self._json({"error": "not found"}, 404)
            stamp = email.utils.formatdate(mtime, usegmt=True)
            if self.headers.get("If-Modified-Since") == stamp:         # the browser's copy is current
                self.send_response(304); self.end_headers(); return
            self.send_response(200)
            self.send_header("Last-Modified", stamp)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        upath = urlparse(self.path).path
        if upath == "/rbtour.html":                                  # the tour player lives in Room Builder (builder/tour.html)
            try:
                with open(os.path.join(rb_root(), "builder", "tour.html"), "rb") as f: body = f.read()
            except OSError: return self._json({"error": "tour.html not found in Room Builder's builder folder"}, 404)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if upath.startswith("/rb-static/"):                          # Room Builder files a tour needs: three.js, the 3D layer, catalogue models
            rel = upath[len("/rb-static/"):]
            ok = rel.startswith(("vendor/", "catalogue/models/")) or rel == "builder/tour3d.js"
            fp = os.path.normpath(os.path.join(rb_root(), *rel.split("/")))
            if not ok or ".." in rel.split("/") or not fp.startswith(os.path.normpath(rb_root()) + os.sep) or not os.path.isfile(fp):
                return self._json({"error": "not found"}, 404)
            typ = {".js": "text/javascript", ".mjs": "text/javascript", ".glb": "model/gltf-binary", ".gltf": "model/gltf+json", ".json": "application/json",
                   ".bin": "application/octet-stream"}.get(os.path.splitext(fp)[1].lower()) or mimetypes.guess_type(fp)[0] or "application/octet-stream"
            with open(fp, "rb") as f: body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", typ)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        m = re.fullmatch(r"/api/rbtour/([\w\-]+)", upath)
        if m:                                                        # a tour's JSON
            t = read_json(os.path.join(rb_root(), "tours", m.group(1) + ".json"), None)
            return self._json(t) if isinstance(t, dict) else self._json({"error": "tour not found"}, 404)
        if self.path.startswith("/api/control"):                     # a scene (remote.js) asking for its settings
            page = norm(parse_qs(urlparse(self.path).query).get("page", [""])[0])
            with lock:
                st = stage_info()
                live = not st["connected"] or page == norm(st["url"])   # the old scene fading out must not react
                return self._json({**controls, "live": live})
        return super().do_GET()

    def do_POST(self):
        global next_id, commands, scene_state
        length = int(self.headers.get("Content-Length", "0") or 0)
        try: data = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError: data = {}
        path = urlparse(self.path).path
        if path == "/api/control":                                   # tablet (or a key on the room PC) changing a setting
            cid = str(data.get("id", ""))[:40]
            if not cid: return self._json({"error": "no id"}, 400)
            with lock:
                if data.get("press"): controls["values"][cid] = (controls["values"].get(cid) or 0) + 1
                else: controls["values"][cid] = data.get("value")
                controls["rev"] += 1
            if data.get("name"): print(f"[control] {data.get('name')}: {cid} = {'press' if data.get('press') else data.get('value')}")
            return self._json({"ok": True, "rev": controls["rev"]})
        if path == "/api/reset":                                     # Reset scene: reload it with its defaults
            with lock:
                clear_controls()
                stage["load"] += 1
            print(f"[scene] {data.get('name') or 'Someone'} reset the scene")
            return self._json({"ok": True})
        if path == "/api/scenestate":                                # a scene describing its controls and their real values
            page = norm(data.get("page", ""))
            with lock:
                reports[page] = {"page": page, "title": str(data.get("title", ""))[:80], "controls": data.get("controls") or [],
                                 "values": data.get("values") or {}, "t": time.time()}
            return self._json({"ok": True})
        if path == "/api/scenetags":                                 # tablet editing a scene's tags (saved to scenes.json)
            sid = str(data.get("id", ""))
            tags = clean_tags(data.get("tags"))
            with lock:
                scenes = own_scenes()
                sc = next((x for x in scenes if x.get("id") == sid), None)
                try:
                    if sc:                                               # your own scene: the tags live in scenes.json
                        sc["tags"] = tags; save_scenes(scenes)
                    elif any(x["id"] == sid for x in library_scenes() + tour_scenes()): save_extra(sid, tags=tags)   # a Room Builder room or tour
                    else: return self._json({"error": "unknown scene"}, 400)
                except OSError as e: return self._json({"error": f"could not save the tags: {e}"}, 500)
            print(f"[tags] {data.get('name') or 'Someone'} set {sid}: {', '.join(tags) or '(none)'}")
            return self._json({"ok": True, "tags": tags})
        if path == "/api/scenehide":                                 # tablet hiding a scene from the list (kept, not deleted)
            sid = str(data.get("id", ""))
            with lock:
                if not any(x["id"] == sid for x in load_scenes()): return self._json({"error": "unknown scene"}, 400)
                try: save_extra(sid, hidden=bool(data.get("hidden")))
                except OSError as e: return self._json({"error": f"could not save: {e}"}, 500)
            print(f"[scenes] {data.get('name') or 'Someone'} {'hid' if data.get('hidden') else 'unhid'} {sid}")
            return self._json({"ok": True})
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
        if self.path.startswith("/api/shutdown"):                     # used by stop-room.bat (this PC only)
            if self.client_address[0] not in ("127.0.0.1", "::1"): return self._json({"error": "local only"}, 403)
            print("[server] shutting down (stop-room.bat)")
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return self._json({"ok": True})
        if self.path.startswith("/api/scene"):
            sid = str(data.get("id", ""))
            if not any(x["id"] == sid for x in load_scenes()): return self._json({"error": "unknown scene"}, 400)
            with lock:
                if stage["current"] != sid: clear_controls()           # a new scene always starts from its defaults
                stage["current"] = sid
            print(f"[scene] {data.get('name') or 'Someone'} switched to {sid}")
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
    srv = None
    for port in range(PORT, PORT + 10):              # if 8000 is taken (common on work PCs), try the next ones
        try:
            srv = ThreadingHTTPServer(("0.0.0.0", port), Handler); break
        except OSError as e:
            print(f"Port {port} is not available ({e.strerror or e}); trying {port + 1}...")
    if srv is None:
        raise SystemExit(f"Could not open any port from {PORT} to {PORT + 9}. Close other servers or set GLENDA_PORT.")
    PORT = port
    if PORT != 8000:
        print(f"NOTE: using port {PORT}, so change the OBS Browser source URL to match.")
    ip = lan_ip()
    print("Glenda scene server running.")
    print(f"  Igloo web layer:     http://localhost:{PORT}/stage.html   (shows the scene picked on the remote)")
    print(f"  OBS Browser source:  http://localhost:{PORT}/index.html")
    print(f"  Remote control:      http://{ip}:{PORT}/control.html   (phone/tablet on the same Wi-Fi)")
    print(f"                       http://localhost:{PORT}/control.html  (on this PC)")
    print(f"  Student tablet:      http://{ip}:{PORT}/play.html   (tours: bag, inspect, give, answer)")
    print(f"Answers are logged to {LOG_DIR}")
    print(f"Tours (Room Builder Tour Builder): {len(tour_scenes())}")
    n = len(library_scenes())
    print(f"Room Builder library: {rb_library()}  ({n} room views)" if n else
          f"Room Builder library not found at {rb_library()} - put its path in roombuilder_library.txt to add those rooms.")
    print("Leave this window open. Press Ctrl+C to stop.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
