# Nursing XRP Scenario – Glenda (heart failure home visit)

An immersive district-nursing scenario for the Igloo 360° room: a first home visit to Glenda, 74, with heart failure.
Students talk to her through Yes/No answers on their own phones; every answer is logged with their name.

| Folder | What's in it |
|---|---|
| `spout-test/` | **The live scene.** Three.js page sent to the Igloo via OBS → Spout, the phone remote, the server, dialogue and audio. Start here: `spout-test/README.md` |
| `blender_room/` | `Glenda_Room.blend` (room + Glenda + animations) and `build_room.py`, which builds the room to the physical room's size |
| `Characters/` | Glenda's MPFB character files and baked textures |
| `Mixamo-In/` | Mixamo animation clips (seated idle, talking, rubbing arm) |
| `FBX/` | ARUP model of the physical room (6.40 × 5.71 × 2.244 m) |
| `Nursing_Brief/` | The scenario brief |

## Getting a fresh copy working

1. Clone with Git (Git for Windows includes Git LFS, which holds the large files: .blend, .glb, images, audio).
2. Run the scene: double-click `spout-test/start-server.bat` (needs Python), then see `spout-test/README.md`.
3. Only needed to rebuild the room in Blender: `python blender_room/fetch_blender_assets.py` downloads the Poly Haven CC0 models and textures.

Not in the repo: the MakeHuman asset packs, test renders, old asset versions and `spout-test/sessions/` (answer logs contain student names).

## Credits

Models and textures: Poly Haven (CC0). Character: MakeHuman / MPFB (CC0 assets). Animation: Mixamo. Voice: ElevenLabs (placeholder lines).
