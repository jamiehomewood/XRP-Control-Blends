/* remote.js – lets a scene page be controlled from the tablet (control.html).

   A scene lists its controls once; the tablet builds its panel from that list, so a new scene needs no
   change to the tablet page. Add to a scene:

     <script src="remote.js"></script>
     Remote.init({
       title: 'Dementia triggers',
       controls: [
         { id: 'tiles',  type: 'toggle', label: 'Patterned tiles', group: 'Effects', key: '1' },
         { id: 'vol',    type: 'slider', label: 'Volume', group: 'Sound', min: 0, max: 1, step: 0.05 },
         { id: 'mode',   type: 'select', label: 'Hole', group: 'Effects', options: [['sink', 'Drops away'], ['dark', 'Dark rug only']] },
         { id: 'dusk',   type: 'button', label: 'Start dusk', group: 'Effects' },
       ],
       get: (id) => current value,                 // what the scene is actually doing now
       set: (id, value) => { ... },                // apply a value (buttons get called with no value)
     });

   Controls:  toggle (true/false)  slider (number)  select (one of options)  button (an action, no value)
              text (shown only: label + hint)  code (a typed answer: set() gets {v, n})  pano (a tap on a 360 picture:
              src = image, markers = [{yaw, pitch, label, kind}]; set() gets {yaw, pitch, n}). n is new on every press.
   The controls list can change while the scene runs (e.g. one button per marker in the current room): change the
   array in place and call Remote.report().
   Defaults are whatever get() returns when init() runs (so URL options like ?audio=0 still set the start).
   A keyboard key on a control (key: '1') toggles it / presses it, and tells the tablet.
   Reset scene and changing scene put everything back to the defaults.
   Works on its own too: with no scene server, init() just wires up the keys. */
(function () {
  const page = location.pathname.replace(/^\/+/, '') + location.search;
  let cfg = null, defaults = {}, rev = -1, resetSeen = null, lastPress = {}, ok = false;

  const post = (url, body) => fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const values = () => { const v = {}; for (const c of cfg.controls) if (c.type !== 'button') v[c.id] = cfg.get(c.id); return v; };
  const find = (id) => cfg.controls.find((c) => c.id === id);
  const same = (a, b) => a === b || (typeof a === 'number' && typeof b === 'number' && Math.abs(a - b) < 1e-6);

  function report() {
    if (!ok) return;
    post('/api/scenestate', { page, title: cfg.title || document.title,
      controls: cfg.controls.map((c) => Object.fromEntries(Object.entries(c).filter(([, v]) => typeof v !== 'function'))),   // extra fields (src, markers...) go too
      values: values() }).catch(() => {});
  }

  function apply(id, value) {
    const c = find(id); if (!c) return;
    if (c.type === 'button') cfg.set(id);
    else if (!same(cfg.get(id), value)) cfg.set(id, value);
  }

  function toDefaults() {
    for (const c of cfg.controls) if (c.type !== 'button') apply(c.id, defaults[c.id]);
    for (const c of cfg.controls) if (c.type === 'button') lastPress[c.id] = 0;   // the server's press counts restart at 0
  }

  async function poll() {
    try {
      const d = await (await fetch('/api/control?page=' + encodeURIComponent(page), { cache: 'no-store' })).json();
      ok = true;
      if (d.live) {
        if (resetSeen === null) resetSeen = d.reset;                         // first look: nothing to reset
        else if (d.reset !== resetSeen) { resetSeen = d.reset; toDefaults(); report(); }
        if (d.rev !== rev) {
          const first = rev === -1; rev = d.rev;
          for (const [id, v] of Object.entries(d.values || {})) {
            const c = find(id);
            if (!c) { if (typeof v === 'number') lastPress[id] = v; continue; }   // a press for a button not shown now (e.g. another room's): never replay it later
            if (c.type === 'button') { if (!first && v > (lastPress[id] || 0)) cfg.set(id); lastPress[id] = v; }   // presses made before we loaded don't count
            else apply(id, v);
          }
          report();
        }
      }
    } catch (e) { ok = false; }
    setTimeout(poll, ok ? 250 : 3000);
  }

  // a change made on the room PC (keyboard): tell the server so the tablet and the scene agree
  function changed(id) {
    const c = find(id); if (!c || !ok) return;
    if (c.type === 'button') lastPress[id] = (lastPress[id] || 0) + 1;       // our own press: don't fire it again when it comes back
    const body = c.type === 'button' ? { id, press: true } : { id, value: cfg.get(id) };
    post('/api/control', body).then(report).catch(() => {});
  }

  window.Remote = {
    init(c) {
      cfg = c;
      for (const k of cfg.controls) {
        if (k.type !== 'button') defaults[k.id] = cfg.get(k.id);
        if (k.type === 'button') lastPress[k.id] = 0;
      }
      addEventListener('keydown', (ev) => {
        const k = cfg.controls.find((x) => x.key && x.key.toLowerCase() === ev.key.toLowerCase());
        if (!k) return;
        if (k.type === 'toggle') cfg.set(k.id, !cfg.get(k.id));
        else if (k.type === 'button') cfg.set(k.id);
        else return;
        changed(k.id);
      });
      poll();
      setInterval(report, 1000);
    },
    changed,                   // call after the scene changes a control itself
    report,                    // call after the scene changes its list of controls (the tablet redraws within a poll)
    defaults: () => ({ ...defaults }),
  };
})();
