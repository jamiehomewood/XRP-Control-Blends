"""
RECESS TEST: an empty version of Glenda's room (walls, door, window only - no furniture) where some wall
sections are set back BEYOND the physical Igloo walls. Deep furniture (kitchen run + fridge, the dresser,
the sofa) can then stand in a recess with its front flush with the real wall, so it never spills onto the
projected floor. Glenda's north wall is left where it is.

Run inside Glenda_Room.blend after build_room.py (it reuses that scene's materials, window, door, lights and
world). It builds a separate scene "RecessTest" and renders spout-test/assets/room_pano_recess.jpg.
Nothing in the main scene is changed.
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:\Projects\01_Active\Nursing XRP Scenario 001\blender_room"
# STYLE "dated" = Glenda's worn-out home; "modern" = the same rooms and recesses with a clean contemporary finish.
# Set STYLE before running (exec(..., {"STYLE": "modern"})), default dated.
STYLE = globals().get("STYLE", "dated")
MODERN = STYLE == "modern"
SCENE_NAME, COLL_NAME = ("ModernRoom", "ModernShell") if MODERN else ("RecessTest", "RecessShell")
OUT = os.path.join(os.path.dirname(ROOT), "spout-test", "assets", "room_pano_modern.jpg" if MODERN else "room_pano_recess.jpg")
# another script can build a copy under its own names (e.g. build_modern_furnished.py)
SCENE_NAME = globals().get("SCENE_NAME_OVERRIDE", SCENE_NAME)
COLL_NAME = globals().get("COLL_NAME_OVERRIDE", COLL_NAME)
OUT = globals().get("OUT_OVERRIDE", OUT)
X0, X1, Y0, Y1, RH = -3.2, 3.2, -2.855, 2.855, 2.244
EYE = 1.12
WIN_DZ = -0.20                                  # window lowered 20 cm from the main room (top now 1.85 m)
WIN_Y, WIN_W, WIN_SILL, WIN_H = 0.5, 1.3, 0.9 + WIN_DZ, 1.15
RAD_TOP = 0.60                                  # radiator shortened to fit under the lower sill (was 0.695)
DOOR_X, DOOR_W, DOOR_H = 1.0, 0.86, 2.0
wy0, wy1 = WIN_Y - WIN_W / 2, WIN_Y + WIN_W / 2
dx0, dx1 = DOOR_X - DOOR_W / 2 - 0.07, DOOR_X + DOOR_W / 2 + 0.07

# ---- the recesses (metres beyond the physical wall) --------------------------------------------
# east wall: the kitchen is a separate little room BEYOND the real wall, reached through an old arch.
# Its opening sits exactly on the real wall line, with a short wall nib either side.
KITCHEN_D, KITCHEN_Y = 2.2, (-1.65, Y1)  # kitchen depth beyond the real wall, and its extent along it
ARCH_Y, ARCH_SPRING, ARCH_TOP, ARCH_T = (-1.1, 2.15), 1.55, 1.88, 0.15   # opening, where the curve starts, its top, wall thickness
DRESSER_D, DRESSER_Y = 0.55, (-2.2, -0.5)  # west wall: the tall dresser with the TV
SOFA_D, SOFA_X1 = 0.80, -0.85            # south wall, SW corner: the sofa
GLENDA_D, GLENDA_X = 0.90, globals().get("GLENDA_X_OVERRIDE", (-1.0, 1.25))   # north wall: alcove for Glenda (wider in some scenes)
BOOK_RECESS = globals().get("BOOK_RECESS")      # optional (x0, x1, depth): a shallow north-wall recess for a bookshelf
GARDEN_PHOTO = globals().get("GARDEN_PHOTO")    # optional labels/<file>: a garden photo outside the window instead of modelled plants
GARDEN_GLOW = globals().get("GARDEN_GLOW", 1.0) # brightness of that photo
HALL_W, HALL_X, WALL_T = 1.35, (-0.6, 3.0), 0.15   # hallway beyond the south door (width, extent), wall thickness
DOOR_OPEN = math.radians(-78)                    # door swings OUT into the hall, so it never covers the real floor

# room outline, walked clockwise seen from above (interior on the right). Openings are added per segment.
OUTLINE = [
    (X0, Y1),                                                        # north wall (Glenda's), with her alcove
    *([(BOOK_RECESS[0], Y1), (BOOK_RECESS[0], Y1 + BOOK_RECESS[2]), (BOOK_RECESS[1], Y1 + BOOK_RECESS[2]), (BOOK_RECESS[1], Y1)] if BOOK_RECESS else []),
    (GLENDA_X[0], Y1), (GLENDA_X[0], Y1 + GLENDA_D), (GLENDA_X[1], Y1 + GLENDA_D), (GLENDA_X[1], Y1),
    (X1, Y1),
    (X1, Y0),                                                        # east wall: real wall line, with the kitchen arch
    (SOFA_X1, Y0),                                                   # south wall with the door
    (SOFA_X1, Y0 - SOFA_D), (X0, Y0 - SOFA_D),                       # sofa recess
    (X0, DRESSER_Y[0]), (X0 - DRESSER_D, DRESSER_Y[0]),              # west wall into the dresser recess
    (X0 - DRESSER_D, DRESSER_Y[1]), (X0, DRESSER_Y[1]),
]                                                                    # ... and back up the west wall (window) to the start

# ---- scene -------------------------------------------------------------------------------------
main = bpy.data.scenes.get("Scene") or bpy.context.scene
sc = bpy.data.scenes.get(SCENE_NAME)
if sc:
    for o in list(sc.collection.all_objects):
        if o.get("recess_test"): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(sc.collection.children): sc.collection.children.unlink(c)
    for o in list(sc.collection.objects): sc.collection.objects.unlink(o)
else:
    sc = bpy.data.scenes.new(SCENE_NAME)
sc.world = main.world
coll = bpy.data.collections.get(COLL_NAME) or bpy.data.collections.new(COLL_NAME)
for o in list(coll.objects): bpy.data.objects.remove(o, do_unlink=True)
if coll.name not in sc.collection.children: sc.collection.children.link(coll)

M = bpy.data.materials
wallpaper, floor_m, lino, ceiling_m = M["Wallpaper"], M["Floor_wood"], M["Lino"], M["Ceiling_paint"]
gloss, reveal, shell_m = M["Gloss_white"], M["Reveal"], M["Shell_black"]
hall_floor = M["Floor_wood"]

def flat(name, color, rough, metal=0.0, emit=None, strength=1.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if emit:
        for k in ("Emission Color", "Emission"):
            if k in b.inputs: b.inputs[k].default_value = (*emit, 1); break
        b.inputs["Emission Strength"].default_value = strength
    return m

def oak_mat():
    """Pale oak planks: the Poly Haven wood texture lightened and desaturated."""
    m = bpy.data.materials.get("Modern_oak") or bpy.data.materials.new("Modern_oak")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.6, 0.6, 0.6)
    nt.links.new(tc.outputs["UV"], mp.inputs[0])
    tex = os.path.join(ROOT, "assets", "tex", "wood_floor_worn_{}.jpg")
    diff = nt.nodes.new("ShaderNodeTexImage"); diff.image = bpy.data.images.load(tex.format("diff"), check_existing=True); nt.links.new(mp.outputs[0], diff.inputs[0])
    hsv = nt.nodes.new("ShaderNodeHueSaturation"); hsv.inputs["Saturation"].default_value = 0.45
    nt.links.new(diff.outputs[0], hsv.inputs["Color"])
    lift = nt.nodes.new("ShaderNodeMix"); lift.data_type = "RGBA"; lift.blend_type = "SCREEN"; lift.inputs[0].default_value = 0.55
    nt.links.new(hsv.outputs[0], lift.inputs[6]); lift.inputs[7].default_value = (0.72, 0.6, 0.45, 1)
    nt.links.new(lift.outputs[2], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.42
    nor_p = tex.format("nor")
    if os.path.exists(nor_p):
        nor = nt.nodes.new("ShaderNodeTexImage"); nor.image = bpy.data.images.load(nor_p, check_existing=True); nor.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mp.outputs[0], nor.inputs[0]); nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs[0].default_value = 0.35
        nt.links.new(nor.outputs[0], nm.inputs[1]); nt.links.new(nm.outputs[0], b.inputs["Normal"])
    return m

def tile_mat():
    """Large-format pale grey porcelain tiles (60 x 60 cm) with fine grout."""
    m = bpy.data.materials.get("Modern_tile") or bpy.data.materials.new("Modern_tile")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord"); br = nt.nodes.new("ShaderNodeTexBrick"); nt.links.new(tc.outputs["UV"], br.inputs["Vector"])
    br.offset = 0.0; br.squash = 1.0
    br.inputs["Scale"].default_value = 1 / 0.6; br.inputs["Mortar Size"].default_value = 0.003; br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0
    br.inputs["Color1"].default_value = (0.30, 0.30, 0.29, 1); br.inputs["Color2"].default_value = (0.28, 0.28, 0.275, 1); br.inputs["Mortar"].default_value = (0.12, 0.12, 0.115, 1)
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.3
    return m

if MODERN:
    wallpaper = flat("Modern_wall", (0.80, 0.80, 0.78), 0.85)          # warm white matt emulsion everywhere
    ceiling_m = flat("Modern_ceiling", (0.85, 0.85, 0.84), 0.9)
    gloss = flat("Modern_trim", (0.82, 0.82, 0.81), 0.35)             # satin white skirting, linings, door
    reveal = wallpaper
    lino = tile_mat()
    hall_floor = oak_mat()

def mesh_obj(name, verts, faces, uvs, mat):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices): uvl.data[li].uv = uvs[vi]
    me.materials.append(mat)
    o = bpy.data.objects.new(name, me); o["recess_test"] = True; coll.objects.link(o); return o

def quad(name, pts, mat, uv=None):
    uv = uv or [(0, 0), (1, 0), (1, 1), (0, 1)]
    return mesh_obj(name, pts, [(0, 1, 2, 3)], uv, mat)

def box(name, size, loc, mat, rz=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=(0, 0, rz))
    o = bpy.context.active_object; o.name = name; o.scale = size; o.data.materials.append(mat)
    for c in list(o.users_collection): c.objects.unlink(o)
    coll.objects.link(o); o["recess_test"] = True; return o

# openings on a segment: (t0, t1, z0, z1) in metres along it
def openings_for(a, b):
    a, b = Vector(a), Vector(b)
    ops = []
    if abs(a.x - X0) < 1e-6 and abs(b.x - X0) < 1e-6 and min(a.y, b.y) <= wy0 and max(a.y, b.y) >= wy1:   # west window
        L = (b - a).length; d = (b - a) / L
        t0, t1 = sorted([(Vector((X0, wy0)) - a).dot(d), (Vector((X0, wy1)) - a).dot(d)])
        ops.append((t0, t1, WIN_SILL, WIN_SILL + WIN_H, "window"))
    if abs(a.y - Y0) < 1e-6 and abs(b.y - Y0) < 1e-6 and min(a.x, b.x) <= dx0 and max(a.x, b.x) >= dx1:   # south door
        L = (b - a).length; d = (b - a) / L
        t0, t1 = sorted([(Vector((dx0, Y0)) - a).dot(d), (Vector((dx1, Y0)) - a).dot(d)])
        ops.append((t0, t1, 0.0, DOOR_H + 0.07, "door"))
    if abs(a.x - X1) < 1e-6 and abs(b.x - X1) < 1e-6:                                                 # kitchen arch
        L = (b - a).length; d = (b - a) / L
        t0, t1 = sorted([(Vector((X1, ARCH_Y[0])) - a).dot(d), (Vector((X1, ARCH_Y[1])) - a).dot(d)])
        ops.append((t0, t1, 0.0, RH, "arch"))
    return ops

# ---- swept mouldings (skirting / coving) with mitred corners -------------------------------------
# profile: list of (o, z) - o = distance out from the wall into the room, z = height.
# corner ends: +1 outside corner (mitre extends the run), -1 inside corner (mitre shortens it), 0 flat cut with an end cap
MOD_SKIRT = [(0.0, 0.0), (0.018, 0.0), (0.018, 0.108), (0.016, 0.115), (0.011, 0.119), (0.0, 0.12)]
_cr, _n = 0.075, 10
MOD_COVE = [(0.0, RH - _cr)] + [(_cr + _cr * math.cos(math.radians(180 - 90 * k / _n)), RH - _cr + _cr * math.sin(math.radians(180 - 90 * k / _n))) for k in range(1, _n + 1)] + [(0.0, RH)]

def sweep(name, a, b, profile, s0, s1, mat, t0=0.0, t1=None, smooth=True):
    a, b = Vector(a), Vector(b); L = (b - a).length; d = (b - a) / L; n_in = Vector((d.y, -d.x))
    t1 = L if t1 is None else t1
    verts, faces, uvs = [], [], []
    for (o, z) in profile:
        for t in (t0 - s0 * o, t1 + s1 * o):
            p_ = a + d * t + n_in * o; verts.append((p_.x, p_.y, z)); uvs.append((t, z))
    k = len(profile)
    for j in range(k - 1):
        faces.append((2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2))
    if s0 == 0: faces.append(tuple(2 * j for j in range(k)))
    if s1 == 0: faces.append(tuple(2 * j + 1 for j in reversed(range(k))))
    o_ = mesh_obj(name, verts, faces, uvs, mat)
    if smooth:
        for poly in o_.data.polygons[:k - 1]: poly.use_smooth = True
    return o_

def corner(p_prev, p, p_next):
    d1 = (Vector(p) - Vector(p_prev)).normalized(); d2 = (Vector(p_next) - Vector(p)).normalized()
    c = d1.x * d2.y - d1.y * d2.x
    return 1 if c > 1e-6 else -1 if c < -1e-6 else 0

s_total = 0.0
pts = OUTLINE + [OUTLINE[0]]
for i in range(len(OUTLINE)):
    a, b = Vector(pts[i]), Vector(pts[i + 1]); L = (b - a).length; d = (b - a) / L
    n_in = Vector((d.y, -d.x))                                   # interior side (right of the walking direction)
    ops = openings_for(pts[i], pts[i + 1])
    # wall pieces around the openings
    cuts = sorted({0.0, L, *[t for o in ops for t in o[:2]]})
    for k in range(len(cuts) - 1):
        t0, t1 = cuts[k], cuts[k + 1]
        if t1 - t0 < 1e-4: continue
        spans = [(0.0, RH)]
        for o in ops:
            if o[0] <= t0 + 1e-6 and o[1] >= t1 - 1e-6: spans = [(0.0, o[2]), (o[3], RH)]
        for z0, z1 in spans:
            if z1 - z0 < 1e-4: continue
            p0, p1 = a + d * t0, a + d * t1
            quad(f"RWall_{i}_{k}_{z0:.2f}", [(p0.x, p0.y, z0), (p1.x, p1.y, z0), (p1.x, p1.y, z1), (p0.x, p0.y, z1)], wallpaper,
                 [(s_total + t0, z0), (s_total + t1, z0), (s_total + t1, z1), (s_total + t0, z1)])
    # skirting / dado / coving, inset into the room; skirting + dado skip the door and the window
    def run(tag, h, z, depth, skip):
        segs = [(0.0, L)]
        for o in ops:
            if o[4] in skip:
                segs = [s for (s0, s1) in segs for s in ((s0, min(s1, o[0])), (max(s0, o[1]), s1)) if s[1] - s[0] > 0.02]
        for j, (s0, s1) in enumerate(segs):
            c = a + d * ((s0 + s1) / 2) + n_in * (depth / 2)
            box(f"R{tag}_{i}_{j}", (s1 - s0, depth, h), (c.x, c.y, z), gloss, math.atan2(d.y, d.x))
    if MODERN:                                                    # swept skirting + cove, mitred at every corner
        nO = len(OUTLINE)
        c_start = corner(OUTLINE[(i - 1) % nO], OUTLINE[i], OUTLINE[(i + 1) % nO])
        c_end = corner(OUTLINE[i], OUTLINE[(i + 1) % nO], OUTLINE[(i + 2) % nO])
        for tag, prof, skip in (("Skirting", MOD_SKIRT, ("door", "arch")), ("Coving", MOD_COVE, ())):
            spans_ = [(0.0, L, c_start, c_end)]
            for o in ops:
                if o[4] in skip:
                    new = []
                    for (s0_, s1_, k0, k1) in spans_:
                        if o[0] > s0_ + 0.02: new.append((s0_, min(s1_, o[0]), k0, 0))
                        if o[1] < s1_ - 0.02: new.append((max(s0_, o[1]), s1_, 0, k1))
                    spans_ = new
            for j, (s0_, s1_, k0, k1) in enumerate(spans_):
                sweep(f"R{tag}_{i}_{j}", a, b, prof, k0, k1, gloss if tag == "Skirting" else ceiling_m, s0_, s1_)
    else:
        run("Skirting", 0.14, 0.07, 0.02, ("door", "arch"))
        run("Dado", 0.05, 0.92, 0.025, ("door", "window", "arch"))
        run("Coving", 0.06, RH - 0.03, 0.06, ())
    s_total += L

# floor, ceiling and kitchen lino follow the outline
def ngon(name, poly, z, mat, flip=False):
    poly = list(reversed(poly)) if flip else poly
    return mesh_obj(name, [(x, y, z) for x, y in poly], [tuple(range(len(poly)))], [(x - X0, y - Y0) for x, y in poly], mat)
# plain carpet: procedural, so it never shows a repeat
def carpet_mat():
    m = bpy.data.materials.get("Carpet_plain") or bpy.data.materials.new("Carpet_plain")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    b.inputs["Roughness"].default_value = 0.95
    for k in ("Sheen Weight", "Sheen"):
        if k in b.inputs: b.inputs[k].default_value = 0.4; break
    tc = nt.nodes.new("ShaderNodeTexCoord")
    fine = nt.nodes.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 900; fine.inputs["Detail"].default_value = 2
    blot = nt.nodes.new("ShaderNodeTexNoise"); blot.inputs["Scale"].default_value = 1.2; blot.inputs["Detail"].default_value = 3
    for n in (fine, blot): nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(fine.outputs["Fac"], ramp.inputs[0])
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.20, 0.155, 0.11, 1)   # oatmeal / mushroom
    ramp.color_ramp.elements[1].position = 0.65; ramp.color_ramp.elements[1].color = (0.27, 0.215, 0.16, 1)
    wear = nt.nodes.new("ShaderNodeMapRange"); nt.links.new(blot.outputs["Fac"], wear.inputs[0])
    wear.inputs[1].default_value = 0.35; wear.inputs[2].default_value = 0.7; wear.inputs[3].default_value = 0.82; wear.inputs[4].default_value = 1.08
    mul = nt.nodes.new("ShaderNodeMix"); mul.data_type = "RGBA"; mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1.0
    nt.links.new(ramp.outputs[0], mul.inputs[6])
    comb = nt.nodes.new("ShaderNodeCombineColor"); [nt.links.new(wear.outputs[0], comb.inputs[i]) for i in range(3)]
    nt.links.new(comb.outputs[0], mul.inputs[7]); nt.links.new(mul.outputs[2], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35; bump.inputs["Distance"].default_value = 0.002
    nt.links.new(fine.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs[0], b.inputs["Normal"])
    return m
carpet = oak_mat() if MODERN else carpet_mat()
ngon("RFloor", OUTLINE, 0.0, carpet, flip=True)
ngon("RCeiling", OUTLINE, RH, ceiling_m)

# ---- the kitchen beyond the arch -----------------------------------------------------------------
KX0, KX1, KY0, KY1 = X1 + ARCH_T, X1 + KITCHEN_D, KITCHEN_Y[0], KITCHEN_Y[1]
ngon("RKitchen_floor", [(X1, KY0), (KX1, KY0), (KX1, KY1), (X1, KY1)], 0.0, lino, flip=True)
ngon("RKitchen_ceiling", [(X1, KY0), (KX1, KY0), (KX1, KY1), (X1, KY1)], RH, ceiling_m)
kitchen_paint = bpy.data.materials.get(STYLE + "_kitchen_paint") or bpy.data.materials.new(STYLE + "_kitchen_paint")
kitchen_paint.use_nodes = True; kp = kitchen_paint.node_tree.nodes.get("Principled BSDF")
kp.inputs["Base Color"].default_value = (0.80, 0.80, 0.78, 1) if MODERN else (0.62, 0.58, 0.42, 1)   # white / old magnolia gloss
kp.inputs["Roughness"].default_value = 0.8 if MODERN else 0.6
for nm_, a, b_ in [("N", (KX0, KY1), (KX1, KY1)), ("E", (KX1, KY1), (KX1, KY0)), ("S", (KX1, KY0), (KX0, KY0))]:
    a, b_ = Vector(a), Vector(b_); L = (b_ - a).length; d = (b_ - a) / L; n_in = Vector((d.y, -d.x))
    quad(f"RKitchen_wall_{nm_}", [(a.x, a.y, 0), (b_.x, b_.y, 0), (b_.x, b_.y, RH), (a.x, a.y, RH)], kitchen_paint,
         [(0, 0), (L, 0), (L, RH), (0, RH)])
    if MODERN:
        sweep(f"RKitchen_Skirting_{nm_}", a, b_, MOD_SKIRT, -1, -1, gloss)
        sweep(f"RKitchen_Coving_{nm_}", a, b_, MOD_COVE, -1, -1, ceiling_m)
        continue
    for tag, h, z, dep in (("Skirting", 0.12, 0.06, 0.02), ("Coving", 0.06, RH - 0.03, 0.06)):
        c = (a + b_) / 2 + n_in * (dep / 2)
        box(f"RKitchen_{tag}_{nm_}", (L, dep, h), (c.x, c.y, z), gloss, math.atan2(d.y, d.x))

# the dividing wall seen from the kitchen side (the living-room side is the east wall above), its nibs' ends,
# and the old arch: a semi-elliptical head over the opening, with a painted soffit
ya, yb = ARCH_Y
def arch_z(y):                       # underside of the arch at y
    c, r = (ya + yb) / 2, (yb - ya) / 2
    u = max(-1.0, min(1.0, (y - c) / r))
    return ARCH_SPRING + (ARCH_TOP - ARCH_SPRING) * math.sqrt(1 - u * u)
for nm_, (y0_, y1_) in {"a": (KY0, ya), "b": (yb, KY1)}.items():
    quad(f"RDivide_back_{nm_}", [(KX0, y1_, 0), (KX0, y0_, 0), (KX0, y0_, RH), (KX0, y1_, RH)], kitchen_paint, [(0, 0), (1, 0), (1, RH), (0, RH)])
for nm_, y_ in (("a", ya), ("b", yb)):                      # jambs: the wall thickness either side of the opening
    quad(f"RArch_jamb_{nm_}", [(X1, y_, 0), (KX0, y_, 0), (KX0, y_, ARCH_SPRING), (X1, y_, ARCH_SPRING)], reveal)
N_ = 120
ys = [ya + (yb - ya) * i / N_ for i in range(N_ + 1)]
for side, x_, mat_ in (("front", X1, wallpaper), ("back", KX0, kitchen_paint)):
    verts, faces, uvs = [], [], []
    for i, y_ in enumerate(ys):
        verts += [(x_, y_, arch_z(y_)), (x_, y_, RH)]; uvs += [(y_ - KY0, arch_z(y_)), (y_ - KY0, RH)]
        if i: faces.append((2 * i - 2, 2 * i, 2 * i + 1, 2 * i - 1))
    mesh_obj(f"RArch_head_{side}", verts, faces, uvs, mat_)
verts, faces, uvs = [], [], []
for i, y_ in enumerate(ys):                                  # soffit: the underside of the arch through the wall
    z_ = arch_z(y_); verts += [(X1, y_, z_), (KX0, y_, z_)]; uvs += [(0, y_), (1, y_)]
    if i: faces.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
so = mesh_obj("RArch_soffit", verts, faces, uvs, reveal)
for poly in so.data.polygons: poly.use_smooth = True
# moulded edge round the arch on the living-room side: one continuous swept half-round, smooth shaded
def arch_curve(n):                   # points up the left jamb, round the arch, down the right jamb (y, z)
    pts_ = [(ya, 0.0), (ya, ARCH_SPRING * 0.5)]
    pts_ += [(ya + (yb - ya) * i / n, arch_z(ya + (yb - ya) * i / n)) for i in range(n + 1)]
    return pts_ + [(yb, ARCH_SPRING * 0.5), (yb, 0.0)]
cp = [Vector(p_) for p_ in arch_curve(N_)]
PROF = [(0.0, 0.0), (-0.012, 0.004), (-0.022, 0.015), (-0.026, 0.03), (-0.022, 0.045), (-0.012, 0.056), (0.0, 0.06)]  # (x out from wall, distance from opening edge)
verts, faces, uvs = [], [], []
for i, p_ in enumerate(cp):
    t = (cp[min(i + 1, len(cp) - 1)] - cp[max(i - 1, 0)]).normalized()
    n_out = Vector((-t.y, t.x))                         # away from the opening, in the wall plane
    if n_out.dot(Vector(((ya + yb) / 2, ARCH_SPRING * 0.6)) - p_) > 0: n_out = -n_out
    for px, pd in PROF:
        q = p_ + n_out * pd; verts.append((X1 + px, q.x, q.y)); uvs.append((i / len(cp), pd))
    if i:
        k = len(PROF)
        for j in range(k - 1):
            a_ = (i - 1) * k + j; faces.append((a_, a_ + 1, a_ + k + 1, a_ + k))
if not MODERN:                       # the modern version keeps a clean plastered edge
    mo = mesh_obj("RArch_mould", verts, faces, uvs, gloss)
    for poly in mo.data.polygons: poly.use_smooth = True
# kitchen light (it is its own room now)
bpy.ops.object.light_add(type="AREA", location=((KX0 + KX1) / 2, (KY0 + KY1) / 2, RH - 0.05))
kl = bpy.context.active_object; kl.name = "RKitchen_light"; kl.data.shape = "RECTANGLE"; kl.data.size = 1.2; kl.data.size_y = 0.25
kl.data.energy = 55 if MODERN else 120; kl.data.color = (1.0, 0.95, 0.85); kl["recess_test"] = True
for c in list(kl.users_collection): c.objects.unlink(kl)
coll.objects.link(kl)

# black outer shell (blocks stray daylight), big enough for the recesses, with a tunnel for the window
G = 0.4
SX0, SX1, SY0, SY1, SZ0, SZ1 = X0 - DRESSER_D - G, X1 + KITCHEN_D + G, min(Y0 - SOFA_D, Y0 - WALL_T - HALL_W) - G, Y1 + GLENDA_D + G, -0.8, RH + G
quad("RShell_top", [(SX0, SY0, SZ1), (SX1, SY0, SZ1), (SX1, SY1, SZ1), (SX0, SY1, SZ1)], shell_m)
quad("RShell_bottom", [(SX0, SY1, SZ0), (SX1, SY1, SZ0), (SX1, SY0, SZ0), (SX0, SY0, SZ0)], shell_m)
quad("RShell_n", [(SX1, SY1, SZ0), (SX0, SY1, SZ0), (SX0, SY1, SZ1), (SX1, SY1, SZ1)], shell_m)
quad("RShell_s", [(SX0, SY0, SZ0), (SX1, SY0, SZ0), (SX1, SY0, SZ1), (SX0, SY0, SZ1)], shell_m)
quad("RShell_e", [(SX1, SY0, SZ0), (SX1, SY1, SZ0), (SX1, SY1, SZ1), (SX1, SY0, SZ1)], shell_m)
T = 0.25
# the modern rooms look out on a garden, so their shell is left open to the west (the room walls are closed)
for nm_, (ya, yb, za, zb) in ({} if MODERN else {"a": (SY0, wy0, SZ0, SZ1), "b": (wy1, SY1, SZ0, SZ1), "c": (wy0, wy1, SZ0, WIN_SILL), "d": (wy0, wy1, WIN_SILL + WIN_H, SZ1)}).items():
    quad(f"RShell_w_{nm_}", [(SX0, yb, za), (SX0, ya, za), (SX0, ya, zb), (SX0, yb, zb)], shell_m)
for nm_, p in {"t": [(SX0, wy1, WIN_SILL + WIN_H), (X0 - T, wy1, WIN_SILL + WIN_H), (X0 - T, wy0, WIN_SILL + WIN_H), (SX0, wy0, WIN_SILL + WIN_H)],
               "b": [(X0 - T, wy1, WIN_SILL), (SX0, wy1, WIN_SILL), (SX0, wy0, WIN_SILL), (X0 - T, wy0, WIN_SILL)],
               "n": [(X0 - T, wy1, WIN_SILL), (X0 - T, wy1, WIN_SILL + WIN_H), (SX0, wy1, WIN_SILL + WIN_H), (SX0, wy1, WIN_SILL)],
               "s": [(SX0, wy0, WIN_SILL), (SX0, wy0, WIN_SILL + WIN_H), (X0 - T, wy0, WIN_SILL + WIN_H), (X0 - T, wy0, WIN_SILL)]}.items():
    if not MODERN: quad(f"RShell_win_{nm_}", p, reveal)

# ---- hallway beyond the open door --------------------------------------------------------------
hall_paint = bpy.data.materials.get(STYLE + "_hall_paint") or bpy.data.materials.new(STYLE + "_hall_paint")
hall_paint.use_nodes = True; hp = hall_paint.node_tree.nodes.get("Principled BSDF")
hp.inputs["Base Color"].default_value = (0.70, 0.71, 0.70, 1) if MODERN else (0.55, 0.5, 0.38, 1); hp.inputs["Roughness"].default_value = 0.8
hx0, hx1, hy1, hy0 = HALL_X[0], HALL_X[1], Y0 - WALL_T, Y0 - WALL_T - HALL_W
d0, d1 = DOOR_X - DOOR_W / 2, DOOR_X + DOOR_W / 2
ngon("RHall_floor", [(hx0, hy0), (hx1, hy0), (hx1, hy1), (hx0, hy1)], 0.0, hall_floor, flip=True)
ngon("RHall_ceiling", [(hx0, hy0), (hx1, hy0), (hx1, hy1), (hx0, hy1)], RH, ceiling_m)
quad("RHall_wall_S", [(hx1, hy0, 0), (hx0, hy0, 0), (hx0, hy0, RH), (hx1, hy0, RH)], hall_paint, [(0, 0), (hx1 - hx0, 0), (hx1 - hx0, RH), (0, RH)])
quad("RHall_wall_W", [(hx0, hy0, 0), (hx0, hy1, 0), (hx0, hy1, RH), (hx0, hy0, RH)], hall_paint)
quad("RHall_wall_E", [(hx1, hy1, 0), (hx1, hy0, 0), (hx1, hy0, RH), (hx1, hy1, RH)], hall_paint)
for nm_, (xa, xb, za, zb) in {"a": (hx0, d0, 0, RH), "b": (d1, hx1, 0, RH), "c": (d0, d1, DOOR_H, RH)}.items():   # hall side of the room wall
    quad(f"RHall_wall_N_{nm_}", [(xa, hy1, za), (xb, hy1, za), (xb, hy1, zb), (xa, hy1, zb)], hall_paint)
for nm_, x_ in (("a", d0), ("b", d1)):                                     # door lining through the wall thickness
    quad(f"RDoor_jamb_{nm_}", [(x_, Y0, 0), (x_, hy1, 0), (x_, hy1, DOOR_H), (x_, Y0, DOOR_H)], gloss)
ngon("RDoor_threshold", [(d0, hy1), (d1, hy1), (d1, Y0), (d0, Y0)], 0.0, hall_floor, flip=True)
quad("RDoor_head", [(d0, hy1, DOOR_H), (d1, hy1, DOOR_H), (d1, Y0, DOOR_H), (d0, Y0, DOOR_H)], gloss)
# fill the gap between the architrave opening and the door lining on the room face
for nm_, (xa, xb) in {"a": (dx0, d0), "b": (d1, dx1)}.items():
    quad(f"RDoor_fill_{nm_}", [(xa, Y0, 0), (xb, Y0, 0), (xb, Y0, DOOR_H + 0.07), (xa, Y0, DOOR_H + 0.07)], gloss)
quad("RDoor_fill_top", [(dx0, Y0, DOOR_H), (dx1, Y0, DOOR_H), (dx1, Y0, DOOR_H + 0.07), (dx0, Y0, DOOR_H + 0.07)], gloss)
if MODERN:                           # flat square-edged architraves, both faces, standing proud of the skirting
    AW, AT = 0.07, 0.022
    for side, yface, sgn in (("room", Y0, 1), ("hall", hy1, -1)):
        yc = yface + sgn * AT / 2
        for nm_, xc in (("l", d0 - AW / 2), ("r", d1 + AW / 2)):
            box(f"RArchitrave_{side}_{nm_}", (AW, AT, DOOR_H + AW), (xc, yc, (DOOR_H + AW) / 2), gloss)
        box(f"RArchitrave_{side}_head", (DOOR_W + 2 * AW, AT, AW), (DOOR_X, yc, DOOR_H + AW / 2), gloss)
for nm_, (a, b_) in {"S": ((hx1, hy0), (hx0, hy0)), "Na": ((hx0, hy1), (d0, hy1)), "Nb": ((d1, hy1), (hx1, hy1))}.items():
    a, b_ = Vector(a), Vector(b_); L = (b_ - a).length; dd = (b_ - a) / L; n_in = Vector((dd.y, -dd.x)); c = (a + b_) / 2 + n_in * 0.01
    box(f"RHall_skirting_{nm_}", (L, 0.02, 0.14), (c.x, c.y, 0.07), gloss, math.atan2(dd.y, dd.x))
bpy.ops.object.light_add(type="POINT", location=((hx0 + hx1) / 2 + 0.3, (hy0 + hy1) / 2, RH - 0.25))
hl = bpy.context.active_object; hl.name = "RHall_light"; hl.data.energy = 35; hl.data.color = (1.0, 0.8, 0.55); hl.data.shadow_soft_size = 0.1
hl["recess_test"] = True
for c in list(hl.users_collection): c.objects.unlink(hl)
coll.objects.link(hl)

# ---- reuse the architecture from the main room: window, door, radiator, outside view, lights -----
KEEP = ("Outside_", "Sun") if MODERN else ("Architrave", "Outside_", "Sun", "Ceiling_light")
for o in bpy.data.collections["Room"].all_objects:
    if o.name.startswith(KEEP) and o.name not in sc.collection.objects:
        sc.collection.objects.link(o)
# the window, its reveal and the window light are copied 20 cm lower; the radiator is copied shorter.
# (copies share the meshes, so the main room is untouched)
for o in list(bpy.data.collections["Room"].all_objects):
    if o.name.startswith(("Win_", "Reveal_", "Window_portal")):
        c = o.copy(); c.name = "RC_" + o.name; c["recess_test"] = True; c.location.z += WIN_DZ; coll.objects.link(c)
    elif MODERN and o.name.startswith(("Radiator", "Door")):
        continue                                                  # no radiator (underfloor heating); flush door below
    elif o.name.startswith("Radiator_fin"):
        c = o.copy(); c.name = "RC_" + o.name; c["recess_test"] = True
        bottom, top = 0.145, 0.695; k = (RAD_TOP - bottom) / (top - bottom)
        c.scale.z *= k; c.location.z = bottom + (o.location.z - bottom) * k; coll.objects.link(c)
    elif o.name in ("Door", "Door_handle", "Door_handle_plate") or o.name.startswith("Door_panel"):
        c = o.copy(); c.name = "RC_" + o.name; c["recess_test"] = True; c.parent = None
        hinge = Vector((DOOR_X - DOOR_W / 2, Y0 - 0.005, 0))
        c.matrix_world = Matrix.Translation(hinge) @ Matrix.Rotation(DOOR_OPEN, 4, "Z") @ Matrix.Translation(-hinge) @ o.matrix_world
        coll.objects.link(c)
    elif o.name.startswith("Radiator_pipe"):
        c = o.copy(); c.name = "RC_" + o.name; c["recess_test"] = True; coll.objects.link(c)

# ---- modern: radiator, venetian blinds and a little garden outside the window ------------------
if MODERN:
    white = flat("Modern_radiator", (0.8, 0.8, 0.79), 0.3)
    groove = flat("Modern_radiator_groove", (0.55, 0.55, 0.54), 0.5)
    chrome = flat("Modern_chrome", (0.8, 0.8, 0.8), 0.08, 1.0)
    # short flat-panel radiator, wall-mounted under the window
    RX, RW, RZ0, RZ1 = X0 + 0.055, 1.0, 0.14, 0.55
    box("RRad_panel", (0.05, RW, RZ1 - RZ0), (RX, WIN_Y, (RZ0 + RZ1) / 2), white)
    for k in range(1, 7):
        box(f"RRad_groove_{k}", (0.002, RW - 0.04, 0.004), (RX + 0.0255, WIN_Y, RZ0 + (RZ1 - RZ0) * k / 7), groove)
    for nm_, yv in (("l", WIN_Y - RW / 2 + 0.04), ("r", WIN_Y + RW / 2 - 0.04)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.12, location=(RX, yv, RZ0 - 0.06))
        v = bpy.context.active_object; v.name = f"RRad_valve_{nm_}"; v.data.materials.append(chrome); v["recess_test"] = True
        for c in list(v.users_collection): c.objects.unlink(v)
        coll.objects.link(v)

    # white venetian blind (50 mm slats), part lowered, slats tilted open
    blind_m = flat("Modern_blind", (0.82, 0.82, 0.8), 0.45)
    BX = X0 - 0.03
    WTOP = WIN_SILL + WIN_H
    box("RBlind_headrail", (0.05, WIN_W - 0.02, 0.035), (BX, WIN_Y, WTOP - 0.02), blind_m)
    z_ = WTOP - 0.06; k = 0
    while z_ > WIN_SILL + WIN_H * 0.45:
        sl = box(f"RBlind_slat_{k}", (0.05, WIN_W - 0.03, 0.002), (BX, WIN_Y, z_), blind_m)
        sl.rotation_euler = (0, math.radians(35), 0); z_ -= 0.042; k += 1
    box("RBlind_bottomrail", (0.05, WIN_W - 0.03, 0.012), (BX, WIN_Y, z_), blind_m)
    for nm_, yv in (("l", WIN_Y - WIN_W / 2 + 0.12), ("r", WIN_Y + WIN_W / 2 - 0.12)):
        box(f"RBlind_cord_{nm_}", (0.002, 0.002, WTOP - z_), (BX, yv, (WTOP + z_) / 2), blind_m)

    if GARDEN_PHOTO:
        # a big photo of a garden on a backdrop beyond the window instead of modelled plants. Seen from the fixed
        # 360 camera only the band through the window shows, so a flat board 2.5 m out is enough. It glows with
        # its own light (looks like the photo whatever the room lighting) and casts no shadow, so the sun still
        # comes in through the window.
        img = bpy.data.images.load(os.path.join(ROOT, "labels", GARDEN_PHOTO), check_existing=True)
        gm = bpy.data.materials.get("Garden_photo") or bpy.data.materials.new("Garden_photo")
        gm.use_nodes = True; nt = gm.node_tree; nt.nodes.clear()
        out_ = nt.nodes.new("ShaderNodeOutputMaterial"); em_ = nt.nodes.new("ShaderNodeEmission"); tx_ = nt.nodes.new("ShaderNodeTexImage")
        tx_.image = img; tx_.extension = "EXTEND"; em_.inputs["Strength"].default_value = GARDEN_GLOW
        nt.links.new(tx_.outputs["Color"], em_.inputs["Color"]); nt.links.new(em_.outputs[0], out_.inputs[0])
        GW = 7.5; GH = GW * img.size[1] / img.size[0]; GX = X0 - T - 2.5; GZ = EYE + 0.35   # photo centre a little above eye level
        me = bpy.data.meshes.new("RGarden_photo")
        me.from_pydata([(GX, WIN_Y - GW / 2, GZ - GH / 2), (GX, WIN_Y + GW / 2, GZ - GH / 2), (GX, WIN_Y + GW / 2, GZ + GH / 2), (GX, WIN_Y - GW / 2, GZ + GH / 2)], [], [(0, 1, 2, 3)])
        uv = me.uv_layers.new(); [setattr(uv.data[k], "uv", c) for k, c in enumerate(((0, 0), (1, 0), (1, 1), (0, 1)))]
        me.materials.append(gm)
        gp = bpy.data.objects.new("RGarden_photo", me); gp["recess_test"] = True; coll.objects.link(gp)
        gp.visible_shadow = False; gp.visible_diffuse = False; gp.visible_glossy = False
    else:
        # garden: stone patio, timber planters with plants, a bistro set (the lawn, fence and houses are the main scene's)
        slab = bpy.data.materials.get("Garden_slab") or bpy.data.materials.new("Garden_slab")
        slab.use_nodes = True; nt = slab.node_tree; nt.nodes.clear()
        out_ = nt.nodes.new("ShaderNodeOutputMaterial"); b_ = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b_.outputs[0], out_.inputs[0])
        tc_ = nt.nodes.new("ShaderNodeTexCoord"); br_ = nt.nodes.new("ShaderNodeTexBrick"); nt.links.new(tc_.outputs["Object"], br_.inputs["Vector"])
        br_.offset = 0.5; br_.inputs["Scale"].default_value = 1 / 0.6; br_.inputs["Brick Width"].default_value = 1.0; br_.inputs["Row Height"].default_value = 1.0
        br_.inputs["Mortar Size"].default_value = 0.01
        br_.inputs["Color1"].default_value = (0.42, 0.40, 0.36, 1); br_.inputs["Color2"].default_value = (0.36, 0.35, 0.32, 1); br_.inputs["Mortar"].default_value = (0.2, 0.2, 0.19, 1)
        nt.links.new(br_.outputs["Color"], b_.inputs["Base Color"]); b_.inputs["Roughness"].default_value = 0.85
        timber = flat("Garden_timber", (0.16, 0.10, 0.06), 0.8)
        soil = flat("Garden_soil", (0.05, 0.035, 0.025), 1.0)
        metal = flat("Garden_metal", (0.02, 0.02, 0.02), 0.45, 0.6)
        PX0, PX1, PY0, PY1, PZ = X0 - T - 2.4, X0 - T, -2.2, 3.2, -0.14
        box("RGarden_patio", (PX1 - PX0, PY1 - PY0, 0.16), ((PX0 + PX1) / 2, (PY0 + PY1) / 2, PZ - 0.08), slab)
        grass = bpy.data.materials.get("Garden_grass") or bpy.data.materials.new("Garden_grass")
        grass.use_nodes = True; nt = grass.node_tree; nt.nodes.clear()
        out_ = nt.nodes.new("ShaderNodeOutputMaterial"); b_ = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b_.outputs[0], out_.inputs[0])
        tc_ = nt.nodes.new("ShaderNodeTexCoord")
        n1 = nt.nodes.new("ShaderNodeTexNoise"); n1.inputs["Scale"].default_value = 60; n1.inputs["Detail"].default_value = 6
        n2 = nt.nodes.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 0.6; n2.inputs["Detail"].default_value = 2
        for n_ in (n1, n2): nt.links.new(tc_.outputs["Object"], n_.inputs["Vector"])
        mix_ = nt.nodes.new("ShaderNodeMath"); mix_.operation = "MULTIPLY"; nt.links.new(n1.outputs["Fac"], mix_.inputs[0]); nt.links.new(n2.outputs["Fac"], mix_.inputs[1])
        ramp_ = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(mix_.outputs[0], ramp_.inputs[0])
        ramp_.color_ramp.elements[0].position = 0.1; ramp_.color_ramp.elements[0].color = (0.03, 0.07, 0.015, 1)
        ramp_.color_ramp.elements[1].position = 0.45; ramp_.color_ramp.elements[1].color = (0.12, 0.2, 0.04, 1)
        nt.links.new(ramp_.outputs[0], b_.inputs["Base Color"]); b_.inputs["Roughness"].default_value = 0.9
        bump_ = nt.nodes.new("ShaderNodeBump"); bump_.inputs["Strength"].default_value = 0.6; nt.links.new(n1.outputs["Fac"], bump_.inputs["Height"]); nt.links.new(bump_.outputs[0], b_.inputs["Normal"])
        box("RGarden_lawn", (5.6, 13.0, 0.02), ((X0 - T - 9.0) / 2 - 0.15, 0.5, -0.29), grass)
        def planter(nm, x, y, w, d, h):
            box(f"RGarden_{nm}", (w, d, h), (x, y, PZ + h / 2), timber)
            box(f"RGarden_{nm}_soil", (w - 0.06, d - 0.06, 0.02), (x, y, PZ + h - 0.02), soil)
            return PZ + h - 0.01
        def plant(name, x, y, z, h):
            path = os.path.join(ROOT, "assets", "models", name, f"{name}.gltf")
            if not os.path.exists(path): return
            before = set(bpy.data.objects); bpy.ops.import_scene.gltf(filepath=path)
            new = [o for o in bpy.data.objects if o not in before]
            root = bpy.data.objects.new(f"RGarden_{name}_root", None); root["recess_test"] = True; coll.objects.link(root)
            for o in new:
                for c in list(o.users_collection): c.objects.unlink(o)
                coll.objects.link(o); o["recess_test"] = True
                if o.parent is None: o.parent = root
            bpy.context.view_layer.update()
            pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
            mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
            ctr = (mn + mx) / 2
            for o in new:
                if o.parent is root: o.location -= Vector((ctr.x, ctr.y, mn.z))
            s_ = h / (mx.z - mn.z); root.scale = (s_, s_, s_); root.location = (x, y, z)
        zt = planter("planter_a", PX0 + 0.35, -0.6, 0.5, 1.4, 0.45)
        plant("potted_plant_02", PX0 + 0.35, -1.0, zt, 0.55); plant("potted_plant_01", PX0 + 0.35, -0.2, zt, 0.75)
        zt = planter("planter_b", PX0 + 0.35, 2.0, 0.5, 1.4, 0.45)
        plant("potted_plant_01", PX0 + 0.35, 1.6, zt, 0.8); plant("potted_plant_04", PX0 + 0.35, 2.4, zt, 0.35)
        plant("potted_plant_04", PX1 - 0.25, 2.75, PZ, 0.4)   # (the pot that stood at y -1.7 landed inside the west recess)
        # bistro table and two chairs
        TXc, TYc = PX0 + 1.3, 0.55
        for o_ in (("RGarden_table_top", 0.32, 0.02, (TXc, TYc, PZ + 0.72)), ("RGarden_table_stem", 0.025, 0.7, (TXc, TYc, PZ + 0.36)), ("RGarden_table_foot", 0.22, 0.015, (TXc, TYc, PZ + 0.008))):
            bpy.ops.mesh.primitive_cylinder_add(radius=o_[1], depth=o_[2], location=o_[3], vertices=40)
            c_ = bpy.context.active_object; c_.name = o_[0]; c_.data.materials.append(metal); c_["recess_test"] = True
            for c in list(c_.users_collection): c.objects.unlink(c_)
            coll.objects.link(c_)
        for k, dy in enumerate((-0.55, 0.55)):
            cy = TYc + dy; sgn = 1 if dy > 0 else -1
            box(f"RGarden_chair_seat_{k}", (0.4, 0.4, 0.025), (TXc, cy, PZ + 0.45), metal)
            box(f"RGarden_chair_back_{k}", (0.4, 0.025, 0.42), (TXc, cy + sgn * 0.19, PZ + 0.66), metal)
            for j, (ex, ey) in enumerate(((-0.18, -0.18), (0.18, -0.18), (-0.18, 0.18), (0.18, 0.18))):
                box(f"RGarden_chair_leg_{k}_{j}", (0.02, 0.02, 0.45), (TXc + ex, cy + ey, PZ + 0.225), metal)

# ---- modern finish: flush white door (open into the hall) and recessed downlights instead of the pendant ---
if MODERN:
    hinge = Vector((DOOR_X - DOOR_W / 2, Y0 - 0.005, 0))
    rot = Matrix.Translation(hinge) @ Matrix.Rotation(DOOR_OPEN, 4, "Z") @ Matrix.Translation(-hinge)
    handle_m = flat("Modern_handle", (0.02, 0.02, 0.02), 0.3, 0.8)
    for nm_, size, loc, m_ in (("slab", (DOOR_W - 0.006, 0.04, DOOR_H - 0.008), (DOOR_X, Y0 - 0.025, DOOR_H / 2), gloss),
                               ("handle", (0.15, 0.02, 0.02), (DOOR_X + DOOR_W / 2 - 0.14, Y0 + 0.02, 1.0), handle_m),
                               ("rose", (0.05, 0.012, 0.05), (DOOR_X + DOOR_W / 2 - 0.07, Y0 + 0.001, 1.0), handle_m)):
        o = box(f"RModern_door_{nm_}", (1, 1, 1), (0, 0, 0), m_)
        o.matrix_world = rot @ Matrix.LocRotScale(Vector(loc), None, Vector(size))
    glow = flat("Modern_downlight", (1, 1, 1), 0.2, emit=(1.0, 0.92, 0.82), strength=25)
    spots = [(x_, y_) for x_ in (-1.8, 0.0, 1.8) for y_ in (-1.3, 1.2)] + [(0.1, Y1 + GLENDA_D / 2)]
    for i, (x_, y_) in enumerate(spots):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.045, depth=0.004, location=(x_, y_, RH - 0.002))
        dl = bpy.context.active_object; dl.name = f"RModern_downlight_{i}"; dl.data.materials.append(glow); dl["recess_test"] = True
        for c in list(dl.users_collection): c.objects.unlink(dl)
        coll.objects.link(dl)
        bpy.ops.object.light_add(type="SPOT", location=(x_, y_, RH - 0.01))
        sp = bpy.context.active_object; sp.name = f"RModern_spot_{i}"; sp["recess_test"] = True
        sp.data.energy = 70; sp.data.spot_size = math.radians(110); sp.data.spot_blend = 0.6; sp.data.shadow_soft_size = 0.04; sp.data.color = (1.0, 0.92, 0.82)
        for c in list(sp.users_collection): c.objects.unlink(sp)
        coll.objects.link(sp)

# ---- camera + render settings (same as the main 360 render) -------------------------------------
cam = bpy.data.objects.get("Cam360_recess")
if not cam:
    cam = bpy.data.objects.new("Cam360_recess", bpy.data.objects["Cam360"].data.copy())
if cam.name not in sc.collection.objects: sc.collection.objects.link(cam)
cam.location = (0, 0, EYE); cam.rotation_euler = (math.radians(90), 0, 0)
sc.camera = cam
for attr in ("engine",): setattr(sc.render, attr, main.render.engine)
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 6144, 3072, 100
sc.cycles.samples = main.cycles.samples; sc.cycles.use_denoising = True; sc.cycles.device = main.cycles.device
sc.view_settings.view_transform = main.view_settings.view_transform
sc.view_settings.look = main.view_settings.look; sc.view_settings.exposure = main.view_settings.exposure
sc.render.image_settings.file_format = "JPEG"; sc.render.image_settings.quality = 92
sc.render.filepath = OUT
print("RecessTest scene built:", len(coll.objects), "shell objects; render ->", OUT)
