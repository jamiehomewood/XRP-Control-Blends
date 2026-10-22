"""
DATED ROOM - NEGLECTED: Glenda's original dated room (recess version) furnished with dated BlenderKit furniture
and showing signs of self-neglect: damp and yellowed walls, a stained ceiling and carpet, clutter, dirty dishes,
unopened post, rubbish bags and boxes.

As in the other recess rooms, everything deep stands in a recess beyond the real Igloo walls; only flat things
(rug, scattered post) are on the projected floor.

Run inside Glenda_Room.blend. The furniture comes from blender_room/assets_local/blenderkit_dated.blend, a local
library of free BlenderKit models (not in git: BlenderKit's licence doesn't allow sharing the model files).
Builds scene "DatedNeglect" and sets it to render spout-test/assets/room_pano_dated_neglect.jpg.
"""
import bpy, math, os, random
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:\Projects\01_Active\Nursing XRP Scenario 001\blender_room"
LIB = os.path.join(ROOT, "assets_local", "blenderkit_dated.blend")
OUT = os.path.join(os.path.dirname(ROOT), "spout-test", "assets", "room_pano_dated_neglect.jpg")
random.seed(7)

# ---- 1. the shell: the dated recess room, with a bookcase recess on the north wall --------------------------
fp = os.path.join(ROOT, "build_recess_test.py")
g = {"__file__": fp, "__name__": "__main__", "STYLE": "dated", "SCENE_NAME_OVERRIDE": "DatedNeglect",
     "COLL_NAME_OVERRIDE": "DatedNeglectShell", "OUT_OVERRIDE": OUT, "BOOK_RECESS": (-3.05, -1.25, 0.40)}
exec(compile(open(fp, encoding="utf-8").read(), fp, "exec"), g)
X0, X1, Y0, Y1 = g["X0"], g["X1"], g["Y0"], g["Y1"]
GX0, GX1 = g["GLENDA_X"]; GD = g["GLENDA_D"]
sc = bpy.data.scenes["DatedNeglect"]
shell = bpy.data.collections["DatedNeglectShell"]
win = bpy.context.window_manager.windows[0]; win.scene = sc

old = bpy.data.collections.get("DatedNeglectThings")
if old:
    for o in list(old.all_objects): bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(old)
coll = bpy.data.collections.new("DatedNeglectThings"); sc.collection.children.link(coll)

# ---- 2. grime: scene-only copies of the room materials with stains mixed in ----------------------------------
def grimed(mat, tag, stain=(0.22, 0.17, 0.09), scale=1.6, amount=0.55, band=None, tint=(1, 1, 1), seed=0.0):
    """Copy of mat whose colour is tinted and blotched with stains. band=(z0, z1, invert): stains fade in from
    z0 to z1 (damp creeping down from the ceiling, or scuffs up from the floor)."""
    name = f"{mat.name}_{tag}"
    m = bpy.data.materials.get(name)
    if m: return m
    m = mat.copy(); m.name = name
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    base_in = bsdf.inputs["Base Color"]
    src = base_in.links[0].from_socket if base_in.links else None
    rgb = nt.nodes.new("ShaderNodeRGB"); rgb.outputs[0].default_value = tuple(base_in.default_value)
    colour = src or rgb.outputs[0]
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    noise = nt.nodes.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = scale; noise.inputs["Detail"].default_value = 8
    noise.inputs["Roughness"].default_value = 0.62
    if "W" in noise.inputs: noise.noise_dimensions = "4D"; noise.inputs["W"].default_value = seed
    nt.links.new(geo.outputs["Position"], noise.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(noise.outputs["Fac"], ramp.inputs[0])
    ramp.color_ramp.elements[0].position = 0.52; ramp.color_ramp.elements[1].position = 0.70
    mask = ramp.outputs[0]
    if band:
        sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange"); nt.links.new(sep.outputs["Z"], mr.inputs[0])
        mr.inputs[1].default_value, mr.inputs[2].default_value = band[0], band[1]
        if band[2]: mr.inputs[3].default_value, mr.inputs[4].default_value = 1.0, 0.0
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
        mx = nt.nodes.new("ShaderNodeMath"); mx.operation = "MAXIMUM"
        nt.links.new(ramp.outputs[0], mul.inputs[0]); nt.links.new(mr.outputs[0], mul.inputs[1])
        mask = mul.outputs[0]
    amt = nt.nodes.new("ShaderNodeMath"); amt.operation = "MULTIPLY"; amt.inputs[1].default_value = amount
    nt.links.new(mask, amt.inputs[0])
    tint_n = nt.nodes.new("ShaderNodeMix"); tint_n.data_type = "RGBA"; tint_n.blend_type = "MULTIPLY"
    tint_n.inputs["Factor"].default_value = 1.0; tint_n.inputs[7].default_value = (*tint, 1)
    nt.links.new(colour, tint_n.inputs[6])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs[7].default_value = (*stain, 1)
    nt.links.new(amt.outputs[0], mix.inputs["Factor"]); nt.links.new(tint_n.outputs[2], mix.inputs[6])
    nt.links.new(mix.outputs[2], base_in)
    return m

def regrime(obj_filter, mat_name, newmat):
    for o in shell.all_objects:
        if o.type != "MESH" or not obj_filter(o): continue
        for i, s in enumerate(o.material_slots):
            if s.material and s.material.name == mat_name:
                if s.link != "OBJECT": s.link = "OBJECT"
                o.material_slots[i].material = newmat

M = bpy.data.materials
walls = grimed(M["Wallpaper"], "neglect", stain=(0.30, 0.25, 0.12), scale=1.3, amount=0.75, band=(1.25, 2.2, False), tint=(0.86, 0.82, 0.70), seed=1.0)
walls_low = grimed(M["Wallpaper"], "scuff", stain=(0.35, 0.30, 0.22), scale=2.5, amount=0.6, band=(0.0, 0.45, True), tint=(0.86, 0.82, 0.70), seed=2.0)
ceil = grimed(M["Ceiling_paint"], "nicotine", stain=(0.42, 0.30, 0.13), scale=0.9, amount=0.8, tint=(0.88, 0.80, 0.62), seed=3.0)
carpet = grimed(M["Carpet_plain"], "stained", stain=(0.30, 0.23, 0.15), scale=1.8, amount=0.6, tint=(0.82, 0.78, 0.72), seed=4.0)
kitch = grimed(M["dated_kitchen_paint"], "grease", stain=(0.32, 0.26, 0.12), scale=2.0, amount=0.8, band=(1.2, 2.2, False), tint=(0.85, 0.80, 0.68), seed=5.0)
lino = grimed(M["Lino"], "grime", stain=(0.30, 0.25, 0.18), scale=2.2, amount=0.8, tint=(0.85, 0.82, 0.75), seed=6.0)
hall = grimed(M["dated_hall_paint"], "grime", stain=(0.32, 0.26, 0.14), scale=1.5, amount=0.6, band=(1.3, 2.2, False), tint=(0.86, 0.82, 0.72), seed=7.0)
gloss = grimed(M["Gloss_white"], "yellowed", stain=(0.45, 0.38, 0.22), scale=3.0, amount=0.5, tint=(0.86, 0.82, 0.68), seed=8.0)
regrime(lambda o: True, "Wallpaper", walls)
regrime(lambda o: True, "Ceiling_paint", ceil)
regrime(lambda o: True, "Carpet_plain", carpet)
regrime(lambda o: True, "dated_kitchen_paint", kitch)
regrime(lambda o: True, "Lino", lino)
regrime(lambda o: True, "dated_hall_paint", hall)
regrime(lambda o: True, "Gloss_white", gloss)
# low scuffs on the lower wall panels (below the dado rail) as a second layer: the lower panels get the scuffed copy
for o in shell.all_objects:
    if o.type == "MESH" and o.name.startswith("RWall") and o.matrix_world.translation.z < 0.6:
        for s in o.material_slots:
            if s.material == walls: s.material = walls_low
# the bare ceiling light is dimmer and warmer (old bulb, dirty shade)
for o in shell.all_objects:
    if o.name.startswith("Ceiling_light") or "Pendant" in o.name:
        for s in o.material_slots:
            if s.material and s.material.name == "Ceiling_light":
                cm = s.material.copy(); cm.name = "Ceiling_light_dim"; s.link = "OBJECT"; s.material = cm
                for n in cm.node_tree.nodes:
                    if n.type == "EMISSION": n.inputs["Strength"].default_value *= 0.6; n.inputs["Color"].default_value = (1.0, 0.82, 0.55, 1)
                    if n.type == "BSDF_PRINCIPLED" and "Emission Strength" in n.inputs: n.inputs["Emission Strength"].default_value *= 0.6
for o in sc.objects:
    if o.type == "LIGHT" and o.data.type in ("POINT", "AREA", "SPOT"):
        o.data = o.data.copy(); o.data.energy *= 0.7; o.data.color = (1.0, 0.86, 0.66)

# ---- 3. furniture from the BlenderKit library --------------------------------------------------------------
LIBRARY = {}
_old = bpy.data.collections.get("BK_library")
if _old:                                          # drop the copies a previous build loaded (placed pieces keep their mesh data)
    for o in list(_old.objects): bpy.data.objects.remove(o, do_unlink=True)
with bpy.data.libraries.load(LIB, link=False) as (src, dst):
    dst.objects = list(src.objects)
for o in dst.objects:
    if o is None: continue
    if "bk_key" in o.keys() and o.parent is None: LIBRARY[o["bk_key"]] = o
STASH = bpy.data.collections.get("BK_library") or bpy.data.collections.new("BK_library")
for o in dst.objects:
    if o and o.name not in STASH.objects: STASH.objects.link(o)

def bounds(objs):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == "MESH" for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))

def copy_tree(root):
    """Duplicate a library object and its children into this scene (mesh data shared)."""
    mapping = {}
    for o in [root, *root.children_recursive]:
        c = o.copy(); mapping[o] = c; coll.objects.link(c)
    for o, c in mapping.items():
        if o.parent in mapping: c.parent = mapping[o.parent]; c.matrix_parent_inverse = o.matrix_parent_inverse.copy()
    return mapping[root]

def put(key, xy, rot_z=0.0, z=0.0, scale=1.0, fit=None, back=None):
    """Place a library piece: centred on xy (or with its back face at `back` = (axis, value)), standing on z,
    turned by rot_z (its front faces -Y before turning), uniformly scaled (or fit=(axis, size) in metres,
    measured along the model's own axes before it is turned)."""
    root = copy_tree(LIBRARY[key])
    root.matrix_world = Matrix.Identity(4); root.location = (0, 0, 0); root.rotation_euler = (0, 0, 0); root.scale = (1, 1, 1)
    parts = [root, *root.children_recursive]
    mn, mx = bounds(parts)
    s = scale
    if fit: s = fit[1] / (mx - mn)[fit[0]]
    ctr = (mn + mx) / 2
    root.matrix_world = Matrix.Translation((xy[0], xy[1], z)) @ Matrix.Rotation(rot_z, 4, "Z") @ Matrix.Scale(s, 4) @ Matrix.Translation((-ctr.x, -ctr.y, -mn.z))
    if back:
        bpy.context.view_layer.update(); mn, mx = bounds(parts)
        ax, val, side = back
        d = val - (mx[ax] if side > 0 else mn[ax])
        root.location[ax] += d
    bpy.context.view_layer.update()
    return root

def top_of(root):
    return bounds([root, *root.children_recursive])[1].z

# north alcove: her old sofa, the side table with the clutter of someone who no longer clears up
AB = Y1 + GD                                  # alcove back wall
sofa = put("sofa", ((GX0 + GX1) / 2 - 0.22, AB - 0.4), back=(1, AB - 0.02, +1))
st = put("side_table", (GX1 - 0.32, AB - 0.32), back=(1, AB - 0.02, +1))
tz = top_of(st)
put("coffee_cup", (GX1 - 0.42, AB - 0.40), z=tz)
put("bottle_dark", (GX1 - 0.22, AB - 0.24), z=tz)
put("teapot", (GX1 - 0.28, AB - 0.45), z=tz, fit=(0, 0.22))
smn, smx = bounds([sofa, *sofa.children_recursive])
seat_z = smn.z + (smx.z - smn.z) * 0.48
put("magazines", (smn.x + 0.35, (smn.y + smx.y) / 2 - 0.05), rot_z=0.4, z=seat_z)
put("letters", (smx.x - 0.35, (smn.y + smx.y) / 2 - 0.08), rot_z=-0.3, z=seat_z + 0.01)

# bookcase recess, north wall west of the alcove
BR = g["BOOK_RECESS"]
put("bookcase", ((BR[0] + BR[1]) / 2, Y1 + BR[2] - 0.2), rot_z=math.radians(-90), fit=(1, (BR[1] - BR[0]) - 0.08), back=(1, Y1 + BR[2] - 0.02, +1))   # the model is long along its own Y

# west recess: the big dark dresser, its counter covered in clutter (turned +90deg so its front faces into the room, +X)
DY0, DY1 = g["DRESSER_Y"]; DD = g["DRESSER_D"]
dres = put("dresser", (X0 - DD / 2, (DY0 + DY1) / 2), rot_z=math.radians(90), fit=(0, (DY1 - DY0) - 0.06), back=(0, X0 - DD + 0.02, -1))   # fit uses the model's own (unturned) axes
dmn, dmx = bounds([dres, *dres.children_recursive])
ctr_z = dmn.z + (dmx.z - dmn.z) * 0.44          # the counter between the cupboards and the glass top
put("radio", (dmx.x - 0.2, DY0 + 0.35), rot_z=math.radians(90), z=ctr_z, fit=(0, 0.3))
put("dead_plant", (dmx.x - 0.2, (DY0 + DY1) / 2), rot_z=math.radians(80), z=ctr_z)
put("bottle_glass", (dmx.x - 0.18, DY1 - 0.32), z=ctr_z)
put("bottle_dark", (dmx.x - 0.28, DY1 - 0.22), z=ctr_z)

# south-west recess: her floral armchair and the old telly, a standard lamp in the corner
SB = Y0 - g["SOFA_D"]
put("armchair_floral", (X0 + 0.75, SB + 0.42), rot_z=math.radians(170), fit=(1, g["SOFA_D"] - 0.04), back=(1, SB + 0.02, -1))
put("tv_legs", (g["SOFA_X1"] - 0.55, SB + 0.35), rot_z=math.radians(200), back=(1, SB + 0.02, -1))
lamp = put("standard_lamp", (X0 + 0.2, SB + 0.2))
for o in list(lamp.children_recursive):          # its flex is a long curve that trails across the whole floor
    if "wire" in o.name.lower(): bpy.data.objects.remove(o, do_unlink=True)

# kitchen recess beyond the arch: an old fitted kitchen along the back wall (turned -90deg so the fronts face
# back into the room, -X; a model's own X runs along the wall). Left to right as seen from the room:
# the little freestanding cooker, the sink run with its wall cupboards, the old fridge in the corner.
KX = X1 + g["KITCHEN_D"]; KY0, KY1 = g["KITCHEN_Y"]

def tree(root): return [root, *root.children_recursive]

def recolour(root, name, rgb, tag, match=None):
    """Multiply the colour of material `name` on this piece by rgb (an image-textured colour keeps its grain).
    match(mat) picks the material instead of the name (library loads can renumber names like Metal.005)."""
    for o in tree(root):
        if o.type != "MESH": continue
        for s in o.material_slots:
            if not s.material: continue
            if not (match(s.material) if match else s.material.name.split(".")[0] == name.split(".")[0] and s.material.name.startswith(name)): continue
            nm = f"{name}_{tag}"
            m = bpy.data.materials.get(nm)
            if not m:
                m = s.material.copy(); m.name = nm; nt = m.node_tree
                bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"); bi = bsdf.inputs["Base Color"]
                img = next((n for n in nt.nodes if n.type == "TEX_IMAGE" and "base" in n.image.name.lower()), None) if bi.links else None
                if img or bi.links:
                    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
                    mix.inputs["Factor"].default_value = 1.0; mix.inputs[7].default_value = (*rgb, 1)
                    nt.links.new(img.outputs["Color"] if img else bi.links[0].from_socket, mix.inputs[6]); nt.links.new(mix.outputs[2], bi)
                else:
                    bi.default_value = (*rgb, 1)
            s.link = "OBJECT"; s.material = m

kit = put("kitchen_pariz", (KX - 0.3, 0.725), rot_z=math.radians(-90), back=(0, KX - 0.02, +1))
for o in list(tree(kit)):                         # no fresh fruit or new-looking bowls in this kitchen
    if o.type == "MESH" and any(s.material and s.material.name.split(".")[0] in ("apple", "wooden bowl") for s in o.material_slots):
        bpy.data.objects.remove(o, do_unlink=True)
recolour(kit, "wood_drawers dark", (0.34, 0.19, 0.09), "oak80s")    # dark grey doors -> tired brown 'oak effect'
recolour(kit, "wood_drawers light", (0.40, 0.24, 0.12), "oak80s")
recolour(kit, "wood_cabinets", (0.36, 0.21, 0.10), "oak80s")
recolour(kit, "wood_tabletop", (0.62, 0.55, 0.42), "stained")
kmn, kmx = bounds(tree(kit))
work_z = max(bounds([o])[1].z for o in tree(kit) if o.type == "MESH" and any(s.material and "tabletop" in s.material.name for s in o.material_slots))   # top of the worktop
fr = put("fridge_retro", (KX - 0.38, KY1 - 0.38), rot_z=math.radians(-90), back=(0, KX - 0.02, +1))
def _orange(m):
    b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.use_nodes else None
    c = b.inputs["Base Color"].default_value if b else (0, 0, 0, 1)
    return c[0] > 0.6 and c[2] < 0.2
recolour(fr, "fridge_body", (0.78, 0.74, 0.62), "cream", match=_orange)   # a yellowed cream, not the shiny orange
put("cooker", (KX - 0.3, kmn.y - 0.3), rot_z=math.radians(-90), back=(0, KX - 0.02, +1))

# the worktop: dirty dishes by the sink, a takeaway bag, bottles, a mug
put("dishes", (KX - 0.32, kmn.y + 1.35), rot_z=math.radians(-90), z=work_z)
put("takeaway_bag", (KX - 0.3, kmn.y + 0.35), rot_z=0.3, z=work_z)
put("bottle_glass", (KX - 0.42, kmn.y + 2.45), z=work_z)
put("bottle_dark", (KX - 0.30, kmn.y + 2.60), z=work_z)
put("coffee_cup", (KX - 0.45, kmn.y + 2.1), z=work_z)
put("teapot", (KX - 0.35, kmn.y + 0.75), z=work_z, fit=(0, 0.22))
# on the kitchen floor: the overflowing bin and bags that never went out
put("bin_full", (KX - 0.85, kmn.y + 0.2))
put("binbag_a", (X1 + 0.55, KY0 + 0.35), rot_z=0.7)
put("binbag_b", (X1 + 0.6, KY1 - 0.35), rot_z=-0.4)
put("box_open", (KX - 1.0, KY1 - 0.3), rot_z=0.2)

# the hall door: the shell's copy of the main room's door leaf comes out misplaced in this file, so build a
# plain panelled door instead, swung open into the hall the same way (it never covers the real floor)
for o in list(sc.objects):
    if o.name.startswith("RC_Door"): bpy.data.objects.remove(o, do_unlink=True)
DX, DW, DH, DOPEN = g["DOOR_X"], g["DOOR_W"], g["DOOR_H"], g["DOOR_OPEN"]
hinge = Vector((DX - DW / 2, Y0 - 0.005, 0))
drot = Matrix.Translation(hinge) @ Matrix.Rotation(DOPEN, 4, "Z") @ Matrix.Translation(-hinge)
brass = bpy.data.materials.get("Neglect_brass") or bpy.data.materials.new("Neglect_brass")
brass.use_nodes = True; _b = brass.node_tree.nodes["Principled BSDF"]
_b.inputs["Base Color"].default_value = (0.45, 0.33, 0.14, 1); _b.inputs["Metallic"].default_value = 1.0; _b.inputs["Roughness"].default_value = 0.45
def door_box(nm, size, loc, mat):
    me = bpy.data.meshes.new(nm); import bmesh; bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
    me.materials.append(mat); o = bpy.data.objects.new(nm, me); coll.objects.link(o)
    o.matrix_world = drot @ Matrix.LocRotScale(Vector(loc), None, Vector(size)); return o
DY = Y0 - 0.025
door_box("Neglect_door_slab", (DW - 0.006, 0.04, DH - 0.008), (DX, DY, DH / 2), gloss)
for zc in (0.5, 1.42):
    for xo in (-0.19, 0.19):
        door_box(f"Neglect_door_panel_{zc}_{xo}", (0.30, 0.012, 0.70 if zc > 1 else 0.62), (DX + xo, DY + 0.024, zc), gloss)
        door_box(f"Neglect_door_panelb_{zc}_{xo}", (0.30, 0.012, 0.70 if zc > 1 else 0.62), (DX + xo, DY - 0.024, zc), gloss)
for sy in (+1, -1):
    door_box(f"Neglect_door_knob_{sy}", (0.06, 0.05, 0.06), (DX + DW / 2 - 0.07, DY + sy * 0.045, 1.0), brass)

# hall beyond the door: rubbish bags and boxes waiting to go out (they never did)
HY = Y0 - g["WALL_T"] - g["HALL_W"]           # far wall of the hall
put("binbag_a", (0.55, HY + 0.4), rot_z=-0.3)
put("binbag_b", (1.05, HY + 0.35), rot_z=0.5)
put("box_damaged", (1.6, HY + 0.32), rot_z=0.1)
put("box_open", (1.65, HY + 0.3), z=0.34, rot_z=-0.25)
put("magazines", (2.2, HY + 0.3), rot_z=0.2)

# on the projected floor only flat things: the worn rug and post pushed under the door
put("rug", (0.1, 1.2), rot_z=math.radians(90), fit=(0, 1.9))
for i in range(3):
    put("letters", (0.9 + random.uniform(-0.3, 0.3), Y0 + 0.35 + random.uniform(0, 0.3)), rot_z=random.uniform(-1, 1), z=0.004 + i * 0.002, scale=0.8)

for o in coll.all_objects: o["dated_neglect"] = True
win.scene = sc
print("DatedNeglect built ->", sc.render.filepath)
