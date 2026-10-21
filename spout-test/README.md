# Glenda's living room – 360 scene for the Igloo room

## Running it

1. Double-click **start-server.bat** and leave its window open. It needs Python (python.org; tick "Add python.exe to PATH" when installing). The window prints the address for the remote control.
2. Set up an OBS **Browser** source:
   - URL: `http://localhost:8000/index.html`
   - size 4096 × 2048 (OBS Settings → Video should match)
   - tick "Control audio via OBS" if you want her voice to go through OBS; leave it unticked to play through the PC's speakers
3. Go to **Tools → Spout Output Settings** and start sending as `GlendaScene`, then select that sender in IglooPreview or the room.

### Talking to her (Yes / No branching)

**Remote control (recommended):** everyone in the room can use their own phone. On the same Wi-Fi, open the address the server window prints, e.g. `http://192.168.1.20:8000/control.html` (on the PC itself: `http://localhost:8000/control.html`).

- Each person enters their name once (the phone remembers it; tap **change** to switch).
- **In the room** lists everyone connected.
- When she asks a question, it appears on every phone and the **Yes** / **No** buttons light up. The first answer counts, and every phone shows who gave it ("Sam answered Yes to…"), plus the list of answers for this visit.
- **Facilitator controls** (tap to open): **Start**, **Replay**, **New take**, **Stop**.
- Under the title: the scene's frame rate (green 50+, amber 30–49, red below 30).

Every answer is saved to `sessions/answers_<date>.csv` (opens in Excel) with the time, the visit's start time, the person's name, the question and their answer. Answers given with the keyboard are logged as "Keyboard".

If Windows asks whether to allow Python on the network, allow it on Private networks, or the phone can't reach it.

**Keyboard:** right-click the source in OBS → **Interact**, click inside once, then:

| Key | Action |
|---|---|
| Space / Enter | Start |
| Y / N | Answer Yes / No |
| R | Replay her last line |
| T | Different take of the same line |
| S | Stop |
| H | Show or hide the status display |

The placeholder conversation: greeting → offers tea (Y/N) → asks if you've come about her legs (Y/N) → asks if you want to see her tablets (Y/N) → closing line. Each answer has its own reply, with cues from the brief (leaking legs, skipped water tablets, "heartburn" when walking).

## How it's built

| Part | File | Made in |
|---|---|---|
| The room | `assets/room_pano.jpg` | Blender Cycles, rendered as a 6144 × 3072 360 image from the viewer's position. Glenda is invisible in this render, but her shadow is baked in. |
| Glenda | `assets/glenda.glb` | MPFB in Blender: rigged and seated. Her clothes are baked into the seated shape. |
| Occluders | `assets/room_proxies.glb` | Invisible copies of the chair, stick, side table and lamp, so they appear in front of her correctly |
| Her lines | `dialogue.json` + `audio/` | ElevenLabs (voice "Beatrice"), four takes per line |

The live page draws the room panorama and renders Glenda on top every frame. She:
- plays Mixamo clips: seated idle, talking gestures while she speaks, and an occasional arm rub
- blinks every few seconds
- opens her jaw in time with the loudness of the audio while she talks

The virtual room is the physical room's size (6.40 × 5.71 m, 2.24 m walls), with the camera in the middle at 1.12 m (half the wall height), which is where the Igloo software puts the viewer when it maps a 360 image onto the walls and floor.

### Changing the room

1. Open `blender_room/Glenda_Room.blend`. The layout comes from `blender_room/build_room.py`; re-running the script rebuilds the room and leaves Glenda alone.
2. Re-render with the **Cam360** camera, with Glenda's objects set to Visibility → Camera off.
3. Save the render over `spout-test/assets/room_pano.jpg`.

### Changing the dialogue

Everything she says is in `dialogue.json`. Each node is one line:

```json
"tea": {
  "label": "Offers tea",
  "text": "Would you like a cup of tea, love?",
  "ask": "Would you like a cup of tea?",
  "audio": ["audio/G_tea_take1.mp3", "audio/G_tea_take2.mp3"],
  "yes": "tea_yes",
  "no": "tea_no"
}
```

- `yes` / `no`: she waits for an answer, then plays that node. `ask` is the text shown on the remote.
- `next`: she carries straight on to that node after a short pause. `null` ends the conversation.
- `audio`: one or more takes (MP3 or WAV); one is picked at random each time.
- `"start"` at the top of the file names the first node.

Save the file and refresh the OBS source; no restart needed.

## URL options

| Option | What it does |
|---|---|
| `hud=1` | Status display |
| `exposure=1.2` | Brightens Glenda only (the room is fixed in the render) |
| `cube=768` | Lowers Glenda's render resolution if the frame rate is low (default 1024) |
| `eye=1.0`, `eye=1.3` | Tries a different viewer height (uses `assets/room_pano_eye100.jpg` etc.) if the room looks too high or low in the Igloo |
| `yaw=90`, `flip=1` | Rotates or mirrors the whole output to suit the room |
| `mode=cylinder&vfov=70` | Cylindrical strip output |
| `say=hello&delay=3` | Plays a dialogue node automatically after loading |
| `persp=1`, `persp=face` | Close-up camera on Glenda, for checking her (not for the room) |
| `jawtest=1`, `blinktest=1` | Hold the jaw open or the eyes closed (rig checks) |

`index_live_threejs_room.html` is the earlier all-three.js version of the room, kept for reference.
