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
OUT = os.path.join(os.path.dirname(ROOT), "spout-test", "assets", "room_pano_recess.jpg")
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
GLENDA_D, GLENDA_X = 0.90, (-1.0, 1.25)  # north wall: alcove for Glenda's chair, stick and side table
HALL_W, HALL_X, WALL_T = 1.35, (-0.6, 3.0), 0.15   # hallway beyond the south door (width, extent), wall thickness
DOOR_OPEN = math.radians(-78)                    # door swings OUT into the hall, so it never covers the real floor

# room outline, walked clockwise seen from above (interior on the right). Openings are added per segment.
OUTLINE = [
    (X0, Y1),                                                        # north wall (Glenda's), with her alcove
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
sc = bpy.data.scenes.get("RecessTest")
if sc:
    for o in list(sc.collection.all_objects):
        if o.get("recess_test"): bpy.data.objects.remove(o, do_unlink=True)
    for c in list(sc.collection.children): sc.collection.children.unlink(c)
    for o in list(sc.collection.objects): sc.collection.objects.unlink(o)
else:
    sc = bpy.data.scenes.new("RecessTest")
sc.world = main.world
coll = bpy.data.collections.get("RecessShell") or bpy.data.collections.new("RecessShell")
for o in list(coll.objects): bpy.data.objects.remove(o, do_unlink=True)
if coll.name not in sc.collection.children: sc.collection.children.link(coll)

M = bpy.data.materials
wallpaper, floor_m, lino, ceiling_m = M["Wallpaper"], M["Floor_wood"], M["Lino"], M["Ceiling_paint"]
gloss, reveal, shell_m = M["Gloss_white"], M["Reveal"], M["Shell_black"]

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
carpet = carpet_mat()
ngon("RFloor", OUTLINE, 0.0, carpet, flip=True)
ngon("RCeiling", OUTLINE, RH, ceiling_m)

# ---- the kitchen beyond the arch -----------------------------------------------------------------
KX0, KX1, KY0, KY1 = X1 + ARCH_T, X1 + KITCHEN_D, KITCHEN_Y[0], KITCHEN_Y[1]
ngon("RKitchen_floor", [(X1, KY0), (KX1, KY0), (KX1, KY1), (X1, KY1)], 0.0, lino, flip=True)
ngon("RKitchen_ceiling", [(X1, KY0), (KX1, KY0), (KX1, KY1), (X1, KY1)], RH, ceiling_m)
kitchen_paint = bpy.data.materials.get("Kitchen_paint") or bpy.data.materials.new("Kitchen_paint")
kitchen_paint.use_nodes = True; kp = kitchen_paint.node_tree.nodes.get("Principled BSDF")
kp.inputs["Base Color"].default_value = (0.62, 0.58, 0.42, 1); kp.inputs["Roughness"].default_value = 0.6   # old magnolia gloss
for nm_, a, b_ in [("N", (KX0, KY1), (KX1, KY1)), ("E", (KX1, KY1), (KX1, KY0)), ("S", (KX1, KY0), (KX0, KY0))]:
    a, b_ = Vector(a), Vector(b_); L = (b_ - a).length; d = (b_ - a) / L; n_in = Vector((d.y, -d.x))
    quad(f"RKitchen_wall_{nm_}", [(a.x, a.y, 0), (b_.x, b_.y, 0), (b_.x, b_.y, RH), (a.x, a.y, RH)], kitchen_paint,
         [(0, 0), (L, 0), (L, RH), (0, RH)])
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
mo = mesh_obj("RArch_mould", verts, faces, uvs, gloss)
for poly in mo.data.polygons: poly.use_smooth = True
# kitchen light (it is its own room now)
bpy.ops.object.light_add(type="AREA", location=((KX0 + KX1) / 2, (KY0 + KY1) / 2, RH - 0.05))
kl = bpy.context.active_object; kl.name = "RKitchen_light"; kl.data.shape = "RECTANGLE"; kl.data.size = 1.2; kl.data.size_y = 0.25
kl.data.energy = 120; kl.data.color = (1.0, 0.95, 0.85); kl["recess_test"] = True
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
for nm_, (ya, yb, za, zb) in {"a": (SY0, wy0, SZ0, SZ1), "b": (wy1, SY1, SZ0, SZ1), "c": (wy0, wy1, SZ0, WIN_SILL), "d": (wy0, wy1, WIN_SILL + WIN_H, SZ1)}.items():
    quad(f"RShell_w_{nm_}", [(SX0, yb, za), (SX0, ya, za), (SX0, ya, zb), (SX0, yb, zb)], shell_m)
T = 0.25
for nm_, p in {"t": [(SX0, wy1, WIN_SILL + WIN_H), (X0 - T, wy1, WIN_SILL + WIN_H), (X0 - T, wy0, WIN_SILL + WIN_H), (SX0, wy0, WIN_SILL + WIN_H)],
               "b": [(X0 - T, wy1, WIN_SILL), (SX0, wy1, WIN_SILL), (SX0, wy0, WIN_SILL), (X0 - T, wy0, WIN_SILL)],
               "n": [(X0 - T, wy1, WIN_SILL), (X0 - T, wy1, WIN_SILL + WIN_H), (SX0, wy1, WIN_SILL + WIN_H), (SX0, wy1, WIN_SILL)],
               "s": [(SX0, wy0, WIN_SILL), (SX0, wy0, WIN_SILL + WIN_H), (X0 - T, wy0, WIN_SILL + WIN_H), (X0 - T, wy0, WIN_SILL)]}.items():
    quad(f"RShell_win_{nm_}", p, reveal)

# ---- hallway beyond the open door --------------------------------------------------------------
hall_paint = bpy.data.materials.get("Hall_paint") or bpy.data.materials.new("Hall_paint")
hall_paint.use_nodes = True; hp = hall_paint.node_tree.nodes.get("Principled BSDF")
hp.inputs["Base Color"].default_value = (0.55, 0.5, 0.38, 1); hp.inputs["Roughness"].default_value = 0.8
hx0, hx1, hy1, hy0 = HALL_X[0], HALL_X[1], Y0 - WALL_T, Y0 - WALL_T - HALL_W
d0, d1 = DOOR_X - DOOR_W / 2, DOOR_X + DOOR_W / 2
ngon("RHall_floor", [(hx0, hy0), (hx1, hy0), (hx1, hy1), (hx0, hy1)], 0.0, M["Floor_wood"], flip=True)
ngon("RHall_ceiling", [(hx0, hy0), (hx1, hy0), (hx1, hy1), (hx0, hy1)], RH, ceiling_m)
quad("RHall_wall_S", [(hx1, hy0, 0), (hx0, hy0, 0), (hx0, hy0, RH), (hx1, hy0, RH)], hall_paint, [(0, 0), (hx1 - hx0, 0), (hx1 - hx0, RH), (0, RH)])
quad("RHall_wall_W", [(hx0, hy0, 0), (hx0, hy1, 0), (hx0, hy1, RH), (hx0, hy0, RH)], hall_paint)
quad("RHall_wall_E", [(hx1, hy1, 0), (hx1, hy0, 0), (hx1, hy0, RH), (hx1, hy1, RH)], hall_paint)
for nm_, (xa, xb, za, zb) in {"a": (hx0, d0, 0, RH), "b": (d1, hx1, 0, RH), "c": (d0, d1, DOOR_H, RH)}.items():   # hall side of the room wall
    quad(f"RHall_wall_N_{nm_}", [(xa, hy1, za), (xb, hy1, za), (xb, hy1, zb), (xa, hy1, zb)], hall_paint)
for nm_, x_ in (("a", d0), ("b", d1)):                                     # door lining through the wall thickness
    quad(f"RDoor_jamb_{nm_}", [(x_, Y0, 0), (x_, hy1, 0), (x_, hy1, DOOR_H), (x_, Y0, DOOR_H)], gloss)
ngon("RDoor_threshold", [(d0, hy1), (d1, hy1), (d1, Y0), (d0, Y0)], 0.0, M["Floor_wood"], flip=True)
quad("RDoor_head", [(d0, hy1, DOOR_H), (d1, hy1, DOOR_H), (d1, Y0, DOOR_H), (d0, Y0, DOOR_H)], gloss)
# fill the gap between the architrave opening and the door lining on the room face
for nm_, (xa, xb) in {"a": (dx0, d0), "b": (d1, dx1)}.items():
    quad(f"RDoor_fill_{nm_}", [(xa, Y0, 0), (xb, Y0, 0), (xb, Y0, DOOR_H + 0.07), (xa, Y0, DOOR_H + 0.07)], gloss)
quad("RDoor_fill_top", [(dx0, Y0, DOOR_H), (dx1, Y0, DOOR_H), (dx1, Y0, DOOR_H + 0.07), (dx0, Y0, DOOR_H + 0.07)], gloss)
for nm_, (a, b_) in {"S": ((hx1, hy0), (hx0, hy0)), "Na": ((hx0, hy1), (d0, hy1)), "Nb": ((d1, hy1), (hx1, hy1))}.items():
    a, b_ = Vector(a), Vector(b_); L = (b_ - a).length; dd = (b_ - a) / L; n_in = Vector((dd.y, -dd.x)); c = (a + b_) / 2 + n_in * 0.01
    box(f"RHall_skirting_{nm_}", (L, 0.02, 0.14), (c.x, c.y, 0.07), gloss, math.atan2(dd.y, dd.x))
bpy.ops.object.light_add(type="POINT", location=((hx0 + hx1) / 2 + 0.3, (hy0 + hy1) / 2, RH - 0.25))
hl = bpy.context.active_object; hl.name = "RHall_light"; hl.data.energy = 35; hl.data.color = (1.0, 0.8, 0.55); hl.data.shadow_soft_size = 0.1
hl["recess_test"] = True
for c in list(hl.users_collection): c.objects.unlink(hl)
coll.objects.link(hl)

# ---- reuse the architecture from the main room: window, door, radiator, outside view, lights -----
KEEP = ("Architrave", "Outside_", "Sun", "Ceiling_light")
for o in bpy.data.collections["Room"].all_objects:
    if o.name.startswith(KEEP) and o.name not in sc.collection.objects:
        sc.collection.objects.link(o)
# the window, its reveal and the window light are copied 20 cm lower; the radiator is copied shorter.
# (copies share the meshes, so the main room is untouched)
for o in list(bpy.data.collections["Room"].all_objects):
    if o.name.startswith(("Win_", "Reveal_", "Window_portal")):
        c = o.copy(); c.name = "RC_" + o.name; c["recess_test"] = True; c.location.z += WIN_DZ; coll.objects.link(c)
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
