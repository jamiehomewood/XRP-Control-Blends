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
GARDEN = "garden_backdrop.jpg"                    # a garden photo outside the window (labels/)
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
def paint_above(mat, z0, paint):
    """copy of the wallpaper that is plain paint above height z0 (the dado rail), wallpaper below"""
    for old in (mat.name + "_paintabove", mat.name + "_paintabove_neglect"):   # rebuilt every run (grimed() would reuse a stale copy)
        if bpy.data.materials.get(old): bpy.data.materials.get(old).name = old + "_old"
    m = mat.copy(); m.name = mat.name + "_paintabove"; nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"); bi = b.inputs["Base Color"]
    paper = bi.links[0].from_socket if bi.links else None
    geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(geo.outputs["Position"], sep.inputs[0])
    gt = nt.nodes.new("ShaderNodeMath"); gt.operation = "GREATER_THAN"; gt.inputs[1].default_value = z0; nt.links.new(sep.outputs["Z"], gt.inputs[0])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 6; nt.links.new(geo.outputs["Position"], nz.inputs["Vector"])
    rp = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(nz.outputs["Fac"], rp.inputs[0])
    rp.color_ramp.elements[0].position = 0.35; rp.color_ramp.elements[0].color = (*paint, 1)
    rp.color_ramp.elements[1].position = 0.75; rp.color_ramp.elements[1].color = (paint[0] * 0.82, paint[1] * 0.78, paint[2] * 0.66, 1)   # patchy, grubby emulsion
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.inputs[6].default_value = (*bi.default_value[:3], 1)
    if paper: nt.links.new(paper, mx.inputs[6])
    nt.links.new(rp.outputs[0], mx.inputs[7]); nt.links.new(gt.outputs[0], mx.inputs["Factor"]); nt.links.new(mx.outputs[2], bi)
    if b.inputs["Normal"].links:                  # no wallpaper emboss on the painted part
        nsrc = b.inputs["Normal"].links[0].from_socket
        nm = nt.nodes.new("ShaderNodeMix"); nm.data_type = "VECTOR"; nt.links.new(gt.outputs[0], nm.inputs["Factor"])
        nt.links.new(nsrc, nm.inputs[4]); nt.links.new(geo.outputs["Normal"], nm.inputs[5]); nt.links.new(nm.outputs[1], b.inputs["Normal"])
    return m
walls = grimed(paint_above(M["Wallpaper"], 0.92, (0.80, 0.74, 0.58)), "neglect", stain=(0.30, 0.25, 0.12), scale=1.3, amount=0.75, band=(1.25, 2.2, False), tint=(0.86, 0.82, 0.70), seed=1.0)
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
    if o.type == "MESH" and o.name.startswith("RWall") and max((o.matrix_world @ Vector(c)).z for c in o.bound_box) < 1.0:   # (origins are all at 0: use the mesh's height)
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
bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)   # rebuilds otherwise pile up copies until the GPU runs out of memory
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
    for c in mapping.values():                    # mirror modifiers must mirror about the copied frame, not the library original
        for m in getattr(c, "modifiers", []):
            if getattr(m, "mirror_object", None) in mapping: m.mirror_object = mapping[m.mirror_object]
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

def tree(root): return [root, *root.children_recursive]

def top_of(root):
    return bounds([root, *root.children_recursive])[1].z

def drop(root, above=0.25):
    """Let a placed piece fall straight down onto whatever is under it (worktop, sink, table), so nothing floats
    or sinks: rays from just above its bottom over its footprint, and its lowest point goes to the highest hit."""
    parts = [o for o in [root, *root.children_recursive] if o.type == "MESH"]
    mn, mx = bounds(parts)
    for o in parts: o.hide_viewport = True
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    zs = []
    for fx in (0.2, 0.5, 0.8):
        for fy in (0.2, 0.5, 0.8):
            h = sc.ray_cast(dg, Vector((mn.x + (mx.x - mn.x) * fx, mn.y + (mx.y - mn.y) * fy, mn.z + above)), Vector((0, 0, -1)), distance=above + 1.5)
            if h[0]: zs.append(h[1].z)
    for o in parts: o.hide_viewport = False
    if zs: root.location.z += max(zs) - mn.z
    bpy.context.view_layer.update()
    return root

def place(key, xy, z, **kw):
    """put() then drop() onto the surface below."""
    return drop(put(key, xy, z=z + 0.02, **kw))

def plate_with_cutlery(xy, z, rot=0.0):
    """A dirty dinner plate with the knife and fork left lying across it (cutlery from the worn tableware set)."""
    pl = place("plate_dirty", xy, z, rot_z=rot)
    pmn, pmx = bounds(tree(pl)); top = pmx.z
    tray = LIBRARY["tray_dirty"]
    for i, nm in enumerate(("fork", "Knife")):
        src = next(c for c in tray.children if c.name.split(".")[0] == nm)
        c = copy_tree(src); c.parent = None
        c.matrix_world = src.matrix_world.copy()
        cmn, cmx = bounds(tree(c)); ctr = (cmn + cmx) / 2
        ang = rot + 0.5 + i * 0.25
        off = Vector((math.cos(rot) * (0.03 - i * 0.05), math.sin(rot) * (0.03 - i * 0.05), 0))
        c.matrix_world = (Matrix.Translation((xy[0] + off.x, xy[1] + off.y, top - 0.012 - cmn.z + ctr.z))
                          @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Translation(-ctr) @ c.matrix_world)
    bpy.context.view_layer.update()
    return pl

# north alcove: her old sofa, the side table with the clutter of someone who no longer clears up
AB = Y1 + GD                                  # alcove back wall
# her old, sagging, stained couch fills the whole alcove; what she needs is piled on the seat around where she sits
sofa = put("sofa_old", ((GX0 + GX1) / 2, AB - 0.45), fit=(0, (GX1 - GX0) - 0.04), back=(1, AB - 0.02, +1))
smn, smx = bounds([sofa, *sofa.children_recursive])
SEAT_Y = smn.y + 0.28                             # over the front of the seat cushions
def on_seat(key, x, rot=0.0, **kw): return drop(put(key, (x, SEAT_Y + kw.pop("dy", 0.0)), rot_z=rot, z=smx.z, **kw), above=0.05)
on_seat("magazines", smn.x + 0.40, 0.4)
on_seat("letters", smx.x - 0.42, -0.3)
pl_ = plate_with_cutlery((smn.x + 0.95, SEAT_Y), smx.z, rot=0.3)

# the two shelf recesses get cheap modern flat-pack shelving, crammed and grubby, instead of antique cabinets
def shelf_levels(x, y, ztop):
    """heights of the surfaces under (x, y), top down: shelves found by casting a ray down again and again"""
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); zs = []; z = ztop
    while z > 0.05:
        h = sc.ray_cast(dg, Vector((x, y, z)), Vector((0, 0, -1)), distance=z + 0.1)
        if not h[0]: break
        zs.append(h[1].z); z = h[1].z - 0.03
    return zs

def grubby(root, seed):
    """dust and grime over every material of a piece"""
    for o in tree(root):
        if o.type != "MESH": continue
        for sl in o.material_slots:
            m = sl.material
            if not m or not m.use_nodes or m.name.endswith("_grubby") or not any(n.type == "BSDF_PRINCIPLED" for n in m.node_tree.nodes): continue
            sl.link = "OBJECT"; sl.material = grimed(m, "grubby", stain=(0.33, 0.28, 0.20), scale=4.0, amount=0.65, tint=(0.88, 0.85, 0.78), seed=seed)

# bookcase recess, north wall west of the alcove: two pine IVAR units side by side
BR = g["BOOK_RECESS"]; BWID = (BR[1] - BR[0]) - 0.06; RYB = Y1 + BR[2] - 0.02
ivars = []
for k_ in (0, 1):
    xc_ = BR[0] + 0.03 + BWID / 4 + k_ * BWID / 2
    iv = put("ivar", (xc_, RYB - 0.15), fit=(2, min(2.0, g["RH"] - 0.12)), back=(1, RYB, +1))
    grubby(iv, 12.0 + k_); ivars.append(iv)
IVAR_FILL = [[("books_old", -0.22), ("magazines", 0.12), ("coffee_cup", 0.30)],
             [("basket", -0.18), ("letters", 0.10), ("beer_can", 0.28)],
             [("book_stack", -0.12), ("bottle_dark", 0.15), ("pill_bottle", 0.27)],
             [("clothes", -0.10), ("books", 0.22)],
             [("books", -0.22), ("beer_can", 0.02), ("pill_sheets", 0.20), ("lighter", 0.30)],
             [("toy_train", -0.25), ("box_open", 0.08)],
             [("books_old", 0.15), ("letters", -0.18), ("coffee_cup", -0.30)],
             [("basket", 0.15), ("beer_bottle", -0.12), ("beer_bottle", -0.25)],
             [("book_stack", 0.12), ("magazines", -0.18)],
             [("clothes", 0.12), ("beer_can", -0.20), ("box_damaged", -0.05)]]
fi = 0
for iv in ivars:
    imn, imx = bounds(tree(iv)); ixc = (imn.x + imx.x) / 2; iyc = (imn.y + imx.y) / 2
    for lz in shelf_levels(ixc, iyc - 0.02, imx.z - 0.25):
        if lz < 0.02 or lz > 1.75: continue
        for key, dx in IVAR_FILL[fi % len(IVAR_FILL)]:
            w_ = {"clothes": 0.30, "book_stack": 0.26, "basket": 0.28, "magazines": 0.24, "box_open": 0.28, "box_damaged": 0.22, "books_old": 0.26, "letters": 0.2}.get(key)
            kw = {"fit": (0, w_)} if w_ else {}
            place(key, (ixc + dx * (imx.x - imn.x) / 0.79, iyc - 0.01), lz, rot_z=random.uniform(-0.25, 0.25), **kw)
        fi += 1

# west recess: a 4x4 KALLAX cube unit (front turned into the room, +X); its top two open rows are where she
# keeps things, the bottom row is junk. KCELL(col, row) gives a cube's centre line and its floor height.
DY0, DY1 = g["DRESSER_Y"]; DD = g["DRESSER_D"]
kal = put("kallax", (X0 - DD / 2, (DY0 + DY1) / 2), rot_z=math.radians(90), back=(0, X0 - DD + 0.02, -1))
grubby(kal, 14.0)
kmn_, kmx_ = bounds(tree(kal))
KX_ = kmx_.x - 0.18
KCOLS = [kmn_.y + (i + 0.5) * (kmx_.y - kmn_.y) / 4 for i in range(4)]
_kl = shelf_levels(KX_, KCOLS[0], kmx_.z - 0.05)
def _near(z): return min(_kl, key=lambda v: abs(v - z))
KROWS = {"top": _near(kmn_.z + 0.75 * (kmx_.z - kmn_.z)), "mid": _near(kmn_.z + 0.5 * (kmx_.z - kmn_.z)), "low": _near(kmn_.z)}
def KCELL(col, row): return KX_, KCOLS[col], KROWS[row]
x_, y_, z_ = KCELL(2, "top"); drop(put("radio", (x_, y_), rot_z=math.radians(90), z=z_ + 0.02, fit=(0, 0.26)))
x_, y_, z_ = KCELL(3, "top"); place("beer_bottle", (x_, y_ - 0.07), z_); place("bottle_dark", (x_ - 0.05, y_ + 0.08), z_)
x_, y_, z_ = KCELL(0, "mid"); place("books_old", (x_, y_), z_, rot_z=math.radians(90), fit=(0, 0.28))
x_, y_, z_ = KCELL(1, "mid"); drop(put("dead_plant", (x_, y_), rot_z=math.radians(80), z=z_ + 0.02, fit=(2, 0.30)))
x_, y_, z_ = KCELL(2, "mid"); place("magazines", (x_, y_), z_, rot_z=math.radians(90), fit=(0, 0.28))
x_, y_, z_ = KCELL(3, "mid"); place("basket", (x_, y_), z_, rot_z=math.radians(90), fit=(0, 0.29))
x_, y_, z_ = KCELL(0, "low"); place("clothes", (x_, y_), z_, rot_z=math.radians(90), fit=(0, 0.29))
x_, y_, z_ = KCELL(1, "low"); place("toy_train", (x_ + 0.05, y_), z_, rot_z=1.2)
x_, y_, z_ = KCELL(2, "low"); place("beer_can", (x_, y_ - 0.06), z_); place("beer_can", (x_ - 0.06, y_ + 0.07), z_)
x_, y_, z_ = KCELL(3, "low"); place("book_stack", (x_, y_), z_, rot_z=math.radians(90), fit=(0, 0.28))

# south-west recess: her floral armchair and the old telly, a standard lamp in the corner
SB = Y0 - g["SOFA_D"]
put("armchair_floral", (X0 + 0.75, SB + 0.42), rot_z=math.radians(170), fit=(1, g["SOFA_D"] - 0.04), back=(1, SB + 0.02, -1))
put("tv_legs", (g["SOFA_X1"] - 0.55, SB + 0.35), rot_z=math.radians(200), back=(1, SB + 0.02, -1))
lamp = put("standard_lamp", (X0 + 0.2, SB + 0.2))
for o in list(lamp.children_recursive):          # its flex is a long curve that trails across the whole floor
    if "wire" in o.name.lower():
        for c in list(o.children):                # the lamp's bulb hangs off the flex: keep it where it is
            mw = c.matrix_world.copy(); c.parent = lamp; c.matrix_world = mw
        bpy.data.objects.remove(o, do_unlink=True)

# kitchen recess beyond the arch: an old fitted kitchen along the back wall (turned -90deg so the fronts face
# back into the room, -X; a model's own X runs along the wall). Left to right as seen from the room:
# the little freestanding cooker, the sink run with its wall cupboards, the old fridge in the corner.
KX = X1 + g["KITCHEN_D"]; KY0, KY1 = g["KITCHEN_Y"]

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
            if m and m.get("rgb") != list(rgb) and s.material != m:      # left over from an earlier build with another colour
                m.name = nm + "_old"; m = None
            if not m:
                m = s.material.copy(); m.name = nm; m["rgb"] = list(rgb); nt = m.node_tree
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
# one drawer handle has come loose at one end and hangs skew
hd = [o for o in tree(kit) if o.type == "MESH" and o.name.startswith("handle") and len(o.data.vertices) > 0]
if hd:
    h = min(hd, key=lambda o: bounds([o])[0].z)
    bpy.context.view_layer.update()
    hmn, hmx = bounds([h]); pivot = Vector(((hmn.x + hmx.x) / 2, hmx.y, (hmn.z + hmx.z) / 2))   # the screw still holding it
    h.matrix_world = Matrix.Translation(pivot) @ Matrix.Rotation(-0.12, 4, "X") @ Matrix.Translation(-pivot) @ h.matrix_world
# the model leaves some fronts without handles: the bottom drawers of the middle units and the two doors under
# the right-hand drawers. Copy the matching (mirrored-pair) handles down onto them.
bpy.context.view_layer.update()
for o in [o for o in tree(kit) if o.type == "CURVE" and o.name.startswith("handle") and any(m.type == "MIRROR" for m in o.modifiers)]:
    pn = o.parent.name if o.parent else ""
    dz = -0.295 if pn.startswith("large drawer") else (-0.135 if pn.startswith("small drawer") else None)
    if dz is None: continue
    c = o.copy(); coll.objects.link(c); c.parent = o.parent; c.matrix_parent_inverse = o.matrix_parent_inverse.copy()
    c.matrix_world = Matrix.Translation((0, 0, dz)) @ o.matrix_world
bpy.context.view_layer.update()
recolour(kit, "wood_drawers dark", (0.30, 0.16, 0.07), "oak80s")    # dark grey doors -> tired brown 'oak effect'
recolour(kit, "wood_drawers light", (0.30, 0.16, 0.07), "oak80s")
recolour(kit, "wood_cabinets", (0.30, 0.16, 0.07), "oak80s")
recolour(kit, "wood_tabletop", (0.62, 0.55, 0.42), "stained")
kmn, kmx = bounds(tree(kit))
work_z = max(bounds([o])[1].z for o in tree(kit) if o.type == "MESH" and any(s.material and "tabletop" in s.material.name for s in o.material_slots))   # top of the worktop
fr = put("fridge_retro", (KX - 0.38, KY1 - 0.38), rot_z=math.radians(-90), back=(0, KX - 0.02, +1))
def _orange(m):
    b = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m.use_nodes else None
    c = b.inputs["Base Color"].default_value if b else (0, 0, 0, 1)
    return c[0] > 0.6 and c[2] < 0.2
recolour(fr, "fridge_body", (0.78, 0.74, 0.62), "cream", match=_orange)   # a yellowed cream, not the shiny orange
stove = put("stove_white", (KX - 0.33, kmn.y - 0.32), rot_z=math.radians(-90), back=(0, KX - 0.02, +1))   # tall white old-fashioned cooker
smn_, smx_ = bounds(tree(stove))

# the sink, so things can go in it or be kept out of it
sink = [o for o in tree(kit) if o.type == "MESH" and any(sl.material and sl.material.name.split(".")[0] == "sink" for sl in o.material_slots)]
sy0, sy1 = (bounds(sink)[0].y, bounds(sink)[1].y) if sink else (kmx.y - 1.1, kmx.y - 0.6)
WX = KX - 0.30                                    # a line along the worktop, clear of the wall cupboards
# in and by the sink: dirty plates, the pile of washing-up on the drainer
plate_with_cutlery((WX - 0.02, (sy0 + sy1) / 2), work_z, rot=0.2)
_front = min(bounds([o])[0].x for o in tree(kit) if o.type == "MESH" and any(sl.material and "tabletop" in sl.material.name for sl in o.material_slots))
def keep_on_top(root, margin=0.04):
    """slide a piece back so nothing overhangs the front edge of the worktop (and not into the wall)"""
    mn_, mx_ = bounds(tree(root))
    if mn_.x < _front + margin: root.location.x += _front + margin - mn_.x
    mn_, mx_ = bounds(tree(root))
    if mx_.x > KX - 0.03: root.location.x -= mx_.x - (KX - 0.03)
    bpy.context.view_layer.update(); return drop(root)
keep_on_top(place("dishes", (KX - 0.22, sy0 - 0.34), work_z, rot_z=math.radians(-90)))
# along the rest of the worktop (south of the sink, towards the cooker): the tray from last night's dinner,
# the takeaway, the teapot; north of the sink: empties and a mug
place("tray_dirty", (WX - 0.02, kmn.y + 0.32), work_z, rot_z=math.radians(-80))
place("takeaway_bag", (WX + 0.05, kmn.y + 0.85), work_z, rot_z=0.3)
for i, (k, dy, dx) in enumerate((("beer_bottle", 0.12, -0.12), ("beer_can", 0.24, 0.02), ("beer_bottle", 0.33, -0.05),
                                 ("bottle_glass", 0.47, 0.05), ("beer_can", 0.60, -0.15), ("coffee_cup", 0.72, -0.05))):
    y_ = sy1 + dy
    if y_ < kmx.y - 0.06: place(k, (WX + dx, y_), work_z, rot_z=i * 0.9)
put("beer_can", (KX - 0.95, kmn.y + 0.55))                        # one dropped on the floor

# the overflowing bin, tucked into the corner beside the cooker if it fits there, else the front corner by the arch
binr = put("bin_full", (0, 0)); bmn, bmx = bounds(tree(binr)); bw = max(bmx.x - bmn.x, bmx.y - bmn.y)
if smn_.y - KY0 >= bw + 0.02:
    binr.location += Vector((KX - 0.02 - bw / 2 - (bmn.x + bmx.x) / 2, KY0 + 0.01 + bw / 2 - (bmn.y + bmx.y) / 2, 0))
else:
    binr.location += Vector((X1 + g["ARCH_T"] + 0.02 + bw / 2 - (bmn.x + bmx.x) / 2, KY0 + 0.01 + bw / 2 - (bmn.y + bmx.y) / 2, 0))
bpy.context.view_layer.update()
put("binbag_b", (X1 + 0.5, KY0 + 0.75), rot_z=2.2)          # by the bin (binbag_a has a long tie that pokes into the room here)
put("binbag_b", (X1 + 0.6, KY1 - 0.35), rot_z=-0.4)
put("box_open", (KX - 1.0, KY1 - 0.3), rot_z=0.2)

# children's magnetic letters on the fridge door, low down where a grandchild could reach: NANA and a scatter
fmn, fmx = bounds(tree(fr))
mags = {c.name.split(".")[0].replace("Letter_", ""): c for c in LIBRARY["magnets"].children}
R = Matrix(((0, 0, -1, 0), (-1, 0, 0, 0), (0, 1, 0, 0), (0, 0, 0, 1)))   # set's +X -> world -Y, +Y -> up, +Z -> out of the door (-X)
def magnet(ch, y, z, tilt=0.0, scale=1.45):
    src = mags[ch]; c = copy_tree(src); c.parent = None; c.matrix_world = src.matrix_world.copy()
    cmn, cmx = bounds(tree(c)); ctr = (cmn + cmx) / 2; th = cmx.z - cmn.z
    dg = bpy.context.evaluated_depsgraph_get()
    hit = sc.ray_cast(dg, Vector((fmn.x - 0.3, y, z)), Vector((1, 0, 0)), distance=1.0)
    door_x = hit[1].x if hit[0] else fmn.x
    c.matrix_world = (Matrix.Translation((door_x - th * scale / 2 - 0.0005, y, z)) @ Matrix.Rotation(tilt, 4, "X")
                      @ R @ Matrix.Scale(scale, 4) @ Matrix.Translation(-ctr) @ c.matrix_world)
random.seed(11)
for i, ch in enumerate("NANA"):
    magnet(ch, fmx.y - 0.16 - i * 0.052, 0.92 + random.uniform(-0.012, 0.012), random.uniform(-0.15, 0.15))
for ch in "BOJ7S3RT":
    if ch in mags:
        magnet(ch, random.uniform(fmn.y + 0.1, fmx.y - 0.12), random.uniform(0.38, 0.80), random.uniform(-0.6, 0.6))

# crayon drawings low on the walls (a grandchild was here): image planes just off the wall surface
def crayon_art(img, ctr, normal, width):
    path = os.path.join(ROOT, "labels", f"crayon_{img}.png")
    im = bpy.data.images.load(path, check_existing=True)
    m = bpy.data.materials.get(f"Crayon_{img}")
    if not m:
        m = bpy.data.materials.new(f"Crayon_{img}"); m.use_nodes = True; nt = m.node_tree
        b = nt.nodes["Principled BSDF"]; t = nt.nodes.new("ShaderNodeTexImage"); t.image = im
        nt.links.new(t.outputs["Color"], b.inputs["Base Color"]); nt.links.new(t.outputs["Alpha"], b.inputs["Alpha"])
        b.inputs["Roughness"].default_value = 0.7
        try: m.surface_render_method = "DITHERED"
        except Exception: pass
    n = Vector(normal); r = Vector((0, 0, 1)).cross(n); up = Vector((0, 0, 1))
    h = width * im.size[1] / im.size[0]; c = Vector(ctr) + n * 0.003
    vs = [c - r * width / 2 - up * h / 2, c + r * width / 2 - up * h / 2, c + r * width / 2 + up * h / 2, c - r * width / 2 + up * h / 2]
    me = bpy.data.meshes.new(f"Crayon_{img}"); me.from_pydata([tuple(v) for v in vs], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(); [setattr(uv.data[i], "uv", xy_) for i, xy_ in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)])]
    me.materials.append(m); o = bpy.data.objects.new(f"Crayon_{img}", me); coll.objects.link(o)
    o.visible_shadow = False
    return o
crayon_art("house", (X1, -1.95, 0.50), (-1, 0, 0), 0.72)          # east wall, beside the kitchen arch
crayon_art("rainbow", (-0.2, Y0, 0.48), (0, 1, 0), 0.75)           # south wall, between the door and the telly
if X1 - GX1 > 0.8:
    crayon_art("flowers", ((GX1 + X1) / 2, Y1, 0.46), (0, -1, 0), min(0.62, X1 - GX1 - 0.25))   # north wall, past the alcove
crayon_art("scribble", (1.05, Y0 - g["WALL_T"] - g["HALL_W"], 0.62), (0, 1, 0), 0.55)          # the hall, seen through the door

# hall beyond the door: rubbish bags and boxes waiting to go out (they never did)
HY = Y0 - g["WALL_T"] - g["HALL_W"]           # far wall of the hall
put("binbag_a", (0.55, HY + 0.4), rot_z=-0.3)
put("binbag_b", (1.05, HY + 0.35), rot_z=0.5)
put("box_damaged", (1.6, HY + 0.32), rot_z=0.1)
put("box_open", (1.65, HY + 0.3), z=0.34, rot_z=-0.25)
put("magazines", (2.2, HY + 0.3), rot_z=0.2)

# on the projected floor only flat things: the worn rug and post pushed under the door
put("rug", (0.0, 0.0), rot_z=math.radians(90), fit=(1, 3.6))   # model is long along its own Y: 3.6 x 2.3 m, long way across the room
for i in range(3):
    put("letters", (0.9 + random.uniform(-0.3, 0.3), Y0 + 0.35 + random.uniform(0, 0.3)), rot_z=random.uniform(-1, 1), z=0.004 + i * 0.002, scale=0.8)

for o in coll.all_objects: o["dated_neglect"] = True
win.scene = sc
print("DatedNeglect built ->", sc.render.filepath)
