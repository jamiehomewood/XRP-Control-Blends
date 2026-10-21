"""
Builds Glenda's living room inside the physical Igloo room dimensions (ARUP_RoomModel: 6.40 x 5.71 x 2.244 m).

Blender axes:  +X = east, +Y = north (the front of the room, image centre), +Z = up.
The 360 camera sits at (0, 0, EYE) - the middle of the physical room.

Run inside Blender (Scripting tab, or exec(open(path).read())). Re-running rebuilds the "Room" collection
and leaves Glenda alone.
"""
import bpy, bmesh, math, os
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:\Projects\01_Active\Nursing XRP Scenario 001\blender_room"
A = os.path.join(ROOT, "assets")
L = os.path.join(ROOT, "labels")
X0, X1, Y0, Y1, RH = -3.2, 3.2, -2.855, 2.855, 2.244
EYE = 1.12                                  # viewer height: the Igloo maps the 360 image from half the wall height
WIN_Y, WIN_W, WIN_SILL, WIN_H = 0.5, 1.3, 0.9, 1.15        # west window (centre y, width, sill height, height)
DOOR_X, DOOR_W, DOOR_H = 1.0, 0.86, 2.0                    # south door
CHAIR = Vector((0.0, 2.50, 0.0))      # chair backed up to the north wall: the Igloo floor is projected too, so
                                       # anything standing out from a wall would be smeared across the real floor

# ------------------------------------------------------------------ helpers
def fresh_mat(name):
    """Rebuild-safe material: a material that already went through the ageing pass is replaced."""
    m = bpy.data.materials.get(name)
    if m and m.get("grubby"): bpy.data.materials.remove(m); m = None
    return m or bpy.data.materials.new(name)

def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c:
        for o in list(c.all_objects): bpy.data.objects.remove(o, do_unlink=True)
        for ch in list(c.children): bpy.data.collections.remove(ch)
    else:
        c = bpy.data.collections.new(name); (parent or bpy.context.scene.collection).children.link(c)
    return c

ROOM = coll("Room")

def link(o, c=None):
    for uc in list(o.users_collection): uc.objects.unlink(o)
    (c or ROOM).objects.link(o); return o

def img(path, non_color=False):
    im = bpy.data.images.load(path, check_existing=True)
    if non_color: im.colorspace_settings.name = "Non-Color"
    return im

def pbr_mat(name, tex, scale=1.0, tint=None, rough_mul=1.0, normal=1.0):
    """Poly Haven texture set as a Principled material using object-space-independent UVs (metres)."""
    m = fresh_mat(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (scale, scale, scale); nt.links.new(tc.outputs["UV"], mp.inputs[0])
    def t(suffix, nc):
        p = os.path.join(A, "tex", f"{tex}_{suffix}.jpg")
        if not os.path.exists(p): return None
        n = nt.nodes.new("ShaderNodeTexImage"); n.image = img(p, nc); nt.links.new(mp.outputs[0], n.inputs[0]); return n
    d = t("diff", False); r = t("rough", True); nm = t("nor", True)
    if d:
        if tint:
            mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
            mix.inputs[0].default_value = 1.0; nt.links.new(d.outputs[0], mix.inputs[6]); mix.inputs[7].default_value = (*tint, 1)
            nt.links.new(mix.outputs[2], b.inputs["Base Color"])
        else: nt.links.new(d.outputs[0], b.inputs["Base Color"])
    if r:
        mth = nt.nodes.new("ShaderNodeMath"); mth.operation = "MULTIPLY"; mth.inputs[1].default_value = rough_mul
        nt.links.new(r.outputs[0], mth.inputs[0]); nt.links.new(mth.outputs[0], b.inputs["Roughness"])
    if nm:
        nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.inputs[0].default_value = normal
        nt.links.new(nm.outputs[0], nmap.inputs[1]); nt.links.new(nmap.outputs[0], b.inputs["Normal"])
    return m

def flat_mat(name, color, rough=0.6, metal=0.0, emit=None, emit_strength=0.0, alpha=1.0, transmission=0.0):
    m = fresh_mat(name)
    m.use_nodes = True; b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal; b.inputs["Alpha"].default_value = alpha
    b.inputs["Transmission Weight"].default_value = transmission
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1); b.inputs["Emission Strength"].default_value = emit_strength
    return m

def label_mat(name, png, rough=0.5, base=None):
    m = fresh_mat(name)
    m.use_nodes = True; nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = img(os.path.join(L, png))
    nt.links.new(t.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    return m

def quad(name, corners, mat, uv_scale=1.0):
    """Quad from 4 corners (counter-clockwise seen from the front). UVs in metres."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    vs = [bm.verts.new(c) for c in corners]; f = bm.faces.new(vs)
    uv = bm.loops.layers.uv.new()
    w = (Vector(corners[1]) - Vector(corners[0])).length; h = (Vector(corners[3]) - Vector(corners[0])).length
    for loop, (u, v) in zip(f.loops, [(0, 0), (w, 0), (w, h), (0, h)]): loop[uv].uv = (u * uv_scale, v * uv_scale)
    bm.to_mesh(me); bm.free(); o = bpy.data.objects.new(name, me); me.materials.append(mat); return link(o)

def box(name, size, loc, mat, rot_z=0.0, bevel=0.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:   # simple box projection UVs in metres
        n = f.normal
        for l in f.loops:
            c = l.vert.co
            l[uv].uv = (c.y, c.z) if abs(n.x) > 0.5 else ((c.x, c.z) if abs(n.y) > 0.5 else (c.x, c.y))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; o.rotation_euler.z = rot_z; me.materials.append(mat)
    if bevel:
        bv = o.modifiers.new("bevel", "BEVEL"); bv.width = bevel; bv.segments = 2
    return link(o)

def label_box(name, size, loc, png, rot_z=0.0, rough=0.5):
    """Box whose every face shows the whole label image (good enough for small packets)."""
    o = box(name, size, loc, label_mat(f"lbl_{png}", png, rough), rot_z)
    uv = o.data.uv_layers.active.data
    for p in o.data.polygons:
        for i, li in enumerate(p.loop_indices): uv[li].uv = [(0, 0), (1, 0), (1, 1), (0, 1)][i % 4]
    return o

def cylinder(name, r, h, loc, mat, verts=32, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.data.materials.append(mat); bpy.ops.object.shade_smooth()
    return link(o)

def gltf(name, loc, rot_z=0.0, scale=1.0, fit_h=None, fit_w=None, z=None, tint=None):
    """Import a Poly Haven glTF, parent under an empty, put its base on the floor (or z) at loc."""
    path = os.path.join(A, "models", name, f"{name}.gltf")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(f"{name}_root", None); link(root)
    for o in new:
        link(o)
        if o.parent is None: o.parent = root
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    size = mx - mn
    s = scale
    if fit_h: s = fit_h / size.z
    if fit_w: s = fit_w / max(size.x, size.y)
    ctr = (mn + mx) / 2
    for o in new:
        if o.parent is root: o.location -= Vector((ctr.x, ctr.y, mn.z))
    root.scale = (s, s, s); root.rotation_euler.z = rot_z
    root.location = (loc[0], loc[1], loc[2] if z is None else z) if len(loc) == 3 else (loc[0], loc[1], z or 0.0)
    if tint:
        for o in new:
            for sl in getattr(o, "material_slots", []):
                if sl.material and sl.material.use_nodes:
                    b = sl.material.node_tree.nodes.get("Principled BSDF")
                    if b and not b.inputs["Base Color"].links:
                        c = b.inputs["Base Color"].default_value; b.inputs["Base Color"].default_value = (c[0]*tint[0], c[1]*tint[1], c[2]*tint[2], 1)
    return root

def surface_z(x, y, z_from=2.2, below=None):
    """Height of the first surface under (x, y), ignoring Glenda. below: only accept hits lower than this."""
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    o = Vector((x, y, z_from))
    for _ in range(12):
        hit, loc, n, i, ob, m = bpy.context.scene.ray_cast(dg, o, Vector((0, 0, -1)))
        if not hit: return 0.0
        if ob.name.startswith("Glenda") or (below is not None and loc.z >= below):
            o = loc - Vector((0, 0, 0.002)); continue
        return loc.z
    return 0.0

def lathe(name, profile, loc, mat, steps=48):
    """Turned object from a list of (radius, height) points, e.g. bowls and bins."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    rings = []
    for k in range(steps):
        a = 2 * math.pi * k / steps
        rings.append([bm.verts.new((r * math.cos(a), r * math.sin(a), h)) for r, h in profile])
    for k in range(steps):
        r0, r1 = rings[k], rings[(k + 1) % steps]
        for j in range(len(profile) - 1):
            bm.faces.new([r0[j], r1[j], r1[j + 1], r0[j + 1]])
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = loc; me.materials.append(mat)
    for p_ in me.polygons: p_.use_smooth = True
    return link(o)

def face_room(root, wall_normal):
    """Rotate an imported wall frame so its thin axis lines up with the wall normal."""
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in root.children_recursive if o.type == "MESH" for c in o.bound_box]
    size = Vector([max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3)])
    thin = min(range(3), key=lambda i: size[i])
    if thin == 0 and abs(wall_normal.y) > 0.5: root.rotation_euler.z += math.pi / 2
    if thin == 1 and abs(wall_normal.x) > 0.5: root.rotation_euler.z += math.pi / 2
    return root

# ------------------------------------------------------------------ materials
wood_floor = pbr_mat("Floor_wood", "wood_floor_worn", scale=0.45, tint=(0.5, 0.43, 0.37), rough_mul=1.5)
rug_m = pbr_mat("Rug", "quatrefoil_jacquard_fabric", scale=1.2, tint=(0.5, 0.36, 0.32), normal=0.8, rough_mul=1.5)
def age_rug(m):
    """Fade, grime and a worn path: desaturate, darken in blotches, lighter where it's walked on."""
    nt = m.node_tree; b = nt.nodes.get("Principled BSDF")
    src = b.inputs["Base Color"].links[0].from_socket
    hsv = nt.nodes.new("ShaderNodeHueSaturation"); hsv.inputs["Saturation"].default_value = 0.6; hsv.inputs["Value"].default_value = 0.95
    nt.links.new(src, hsv.inputs["Color"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    grime = nt.nodes.new("ShaderNodeTexNoise"); grime.inputs["Scale"].default_value = 2.5; grime.inputs["Detail"].default_value = 8
    nt.links.new(tc.outputs["Object"], grime.inputs[0])
    gr = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(grime.outputs[0], gr.inputs[0])
    gr.color_ramp.elements[0].position = 0.35; gr.color_ramp.elements[0].color = (0.45, 0.4, 0.33, 1)
    gr.color_ramp.elements[1].position = 0.65; gr.color_ramp.elements[1].color = (1, 1, 1, 1)
    spots = nt.nodes.new("ShaderNodeTexVoronoi"); spots.inputs["Scale"].default_value = 6
    nt.links.new(tc.outputs["Object"], spots.inputs[0])
    sp = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(spots.outputs["Distance"], sp.inputs[0])
    sp.color_ramp.elements[0].position = 0.06; sp.color_ramp.elements[0].color = (0.55, 0.45, 0.3, 1)   # old stains
    sp.color_ramp.elements[1].position = 0.12; sp.color_ramp.elements[1].color = (1, 1, 1, 1)
    m1 = nt.nodes.new("ShaderNodeMix"); m1.data_type = "RGBA"; m1.blend_type = "MULTIPLY"; m1.inputs[0].default_value = 1.0
    nt.links.new(hsv.outputs[0], m1.inputs[6]); nt.links.new(gr.outputs[0], m1.inputs[7])
    m2 = nt.nodes.new("ShaderNodeMix"); m2.data_type = "RGBA"; m2.blend_type = "MULTIPLY"; m2.inputs[0].default_value = 1.0
    nt.links.new(m1.outputs[2], m2.inputs[6]); nt.links.new(sp.outputs[0], m2.inputs[7])
    nt.links.new(m2.outputs[2], b.inputs["Base Color"])
    return m
age_rug(rug_m)
lino = pbr_mat("Lino", "old_linoleum_flooring_01", scale=0.8)
ceiling_m = flat_mat("Ceiling_paint", (0.84, 0.8, 0.68), 0.95)        # nicotine-yellowed
gloss_white = flat_mat("Gloss_white", (0.78, 0.74, 0.62), 0.45)     # old yellowed gloss
upvc = flat_mat("uPVC", (0.92, 0.92, 0.9), 0.3)

def wallpaper_mat():
    """Regency-stripe wallpaper with grime from the decrepit_wallpaper texture."""
    m = fresh_mat("Wallpaper")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(b.outputs[0], out.inputs[0]); b.inputs["Roughness"].default_value = 0.75
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["UV"], sep.inputs[0])
    # stripes: period 0.18 m, wide cream band + narrow sage pin stripes
    m1 = nt.nodes.new("ShaderNodeMath"); m1.operation = "MULTIPLY"; m1.inputs[1].default_value = 1 / 0.18
    nt.links.new(sep.outputs[0], m1.inputs[0])
    fr = nt.nodes.new("ShaderNodeMath"); fr.operation = "FRACT"; nt.links.new(m1.outputs[0], fr.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(fr.outputs[0], ramp.inputs[0])
    r = ramp.color_ramp; r.interpolation = "CONSTANT"
    r.elements[0].position = 0.0; r.elements[0].color = (0.62, 0.66, 0.52, 1)   # sage
    r.elements[1].position = 0.5; r.elements[1].color = (0.80, 0.76, 0.62, 1)   # cream
    e = r.elements.new(0.92); e.color = (0.55, 0.6, 0.47, 1)
    e = r.elements.new(0.95); e.color = (0.80, 0.76, 0.62, 1)
    grime = nt.nodes.new("ShaderNodeTexImage"); grime.image = img(os.path.join(A, "tex", "decrepit_wallpaper_diff.jpg"))
    mp = nt.nodes.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.5, 0.5, 0.5); nt.links.new(tc.outputs["UV"], mp.inputs[0]); nt.links.new(mp.outputs[0], grime.inputs[0])
    bw = nt.nodes.new("ShaderNodeRGBToBW"); nt.links.new(grime.outputs[0], bw.inputs[0])
    lev = nt.nodes.new("ShaderNodeMapRange"); lev.inputs[1].default_value = 0.15; lev.inputs[2].default_value = 0.6
    lev.inputs[3].default_value = 0.72; lev.inputs[4].default_value = 1.05; nt.links.new(bw.outputs[0], lev.inputs[0])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs[0].default_value = 1.0
    nt.links.new(ramp.outputs[0], mix.inputs[6])
    comb = nt.nodes.new("ShaderNodeCombineColor"); [nt.links.new(lev.outputs[0], comb.inputs[i]) for i in range(3)]
    nt.links.new(comb.outputs[0], mix.inputs[7]); nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    nm = nt.nodes.new("ShaderNodeTexImage"); nm.image = img(os.path.join(A, "tex", "decrepit_wallpaper_nor.jpg"), True)
    nt.links.new(mp.outputs[0], nm.inputs[0]); nmap = nt.nodes.new("ShaderNodeNormalMap"); nmap.inputs[0].default_value = 0.25
    nt.links.new(nm.outputs[0], nmap.inputs[1]); nt.links.new(nmap.outputs[0], b.inputs["Normal"])
    return m
wallpaper = wallpaper_mat()

# ------------------------------------------------------------------ shell
quad("Floor", [(X0, Y0, 0), (X1, Y0, 0), (X1, Y1, 0), (X0, Y1, 0)], wood_floor)
quad("Ceiling", [(X0, Y1, RH), (X1, Y1, RH), (X1, Y0, RH), (X0, Y0, RH)], ceiling_m)
quad("Wall_N", [(X1, Y1, 0), (X0, Y1, 0), (X0, Y1, RH), (X1, Y1, RH)], wallpaper)
quad("Wall_E", [(X1, Y0, 0), (X1, Y1, 0), (X1, Y1, RH), (X1, Y0, RH)], wallpaper)
# south wall with door opening
dx0, dx1 = DOOR_X - DOOR_W / 2 - 0.07, DOOR_X + DOOR_W / 2 + 0.07
quad("Wall_S_a", [(X0, Y0, 0), (dx0, Y0, 0), (dx0, Y0, RH), (X0, Y0, RH)], wallpaper)
quad("Wall_S_b", [(dx1, Y0, 0), (X1, Y0, 0), (X1, Y0, RH), (dx1, Y0, RH)], wallpaper)
quad("Wall_S_c", [(dx0, Y0, DOOR_H + 0.07), (dx1, Y0, DOOR_H + 0.07), (dx1, Y0, RH), (dx0, Y0, RH)], wallpaper)
# west wall with window opening
wy0, wy1 = WIN_Y - WIN_W / 2, WIN_Y + WIN_W / 2
quad("Wall_W_a", [(X0, Y1, 0), (X0, wy1, 0), (X0, wy1, RH), (X0, Y1, RH)], wallpaper)
quad("Wall_W_b", [(X0, wy0, 0), (X0, Y0, 0), (X0, Y0, RH), (X0, wy0, RH)], wallpaper)
quad("Wall_W_c", [(X0, wy1, 0), (X0, wy0, 0), (X0, wy0, WIN_SILL), (X0, wy1, WIN_SILL)], wallpaper)
quad("Wall_W_d", [(X0, wy1, WIN_SILL + WIN_H), (X0, wy0, WIN_SILL + WIN_H), (X0, wy0, RH), (X0, wy1, RH)], wallpaper)
# window reveal (wall thickness 0.25 m)
reveal = flat_mat("Reveal", (0.85, 0.83, 0.78), 0.8)
T = 0.25
quad("Reveal_bottom", [(X0 - T, wy1, WIN_SILL), (X0, wy1, WIN_SILL), (X0, wy0, WIN_SILL), (X0 - T, wy0, WIN_SILL)], reveal)
quad("Reveal_top", [(X0, wy1, WIN_SILL + WIN_H), (X0 - T, wy1, WIN_SILL + WIN_H), (X0 - T, wy0, WIN_SILL + WIN_H), (X0, wy0, WIN_SILL + WIN_H)], reveal)
quad("Reveal_n", [(X0, wy1, WIN_SILL), (X0 - T, wy1, WIN_SILL), (X0 - T, wy1, WIN_SILL + WIN_H), (X0, wy1, WIN_SILL + WIN_H)], reveal)
quad("Reveal_s", [(X0 - T, wy0, WIN_SILL), (X0, wy0, WIN_SILL), (X0, wy0, WIN_SILL + WIN_H), (X0 - T, wy0, WIN_SILL + WIN_H)], reveal)
# door reveal + hall beyond (dim)
quad("Door_reveal_top", [(dx0, Y0 - T, DOOR_H + 0.07), (dx1, Y0 - T, DOOR_H + 0.07), (dx1, Y0, DOOR_H + 0.07), (dx0, Y0, DOOR_H + 0.07)], reveal)

# skirting, dado rail, coving
for nm_, a, b_ in [("N", (X0, Y1 - 0.01), (X1, Y1 - 0.01)), ("E", (X1 - 0.01, Y0), (X1 - 0.01, Y1))]:
    L_ = (Vector(b_) - Vector(a)).length; c = (Vector(a) + Vector(b_)) / 2; rz = 0 if nm_ == "N" else math.pi / 2
    box(f"Skirting_{nm_}", (L_, 0.02, 0.14), (c.x, c.y, 0.07), gloss_white, rz)
    box(f"Dado_{nm_}", (L_, 0.025, 0.05), (c.x, c.y, 0.92), gloss_white, rz, 0.004)
    box(f"Coving_{nm_}", (L_, 0.06, 0.06), (c.x, c.y, RH - 0.03), gloss_white, rz)
for nm_, y in [("W", None)]:
    for seg, (ya, yb) in enumerate([(Y0, wy0), (wy1, Y1)]):
        box(f"Skirting_W{seg}", (0.02, yb - ya, 0.14), (X0 + 0.01, (ya + yb) / 2, 0.07), gloss_white)
        box(f"Dado_W{seg}", (0.025, yb - ya, 0.05), (X0 + 0.01, (ya + yb) / 2, 0.92), gloss_white, 0, 0.004)
    box("Coving_W", (0.06, Y1 - Y0, 0.06), (X0 + 0.03, 0, RH - 0.03), gloss_white)
for seg, (xa, xb) in enumerate([(X0, dx0), (dx1, X1)]):
    box(f"Skirting_S{seg}", (xb - xa, 0.02, 0.14), ((xa + xb) / 2, Y0 + 0.01, 0.07), gloss_white)
    box(f"Dado_S{seg}", (xb - xa, 0.025, 0.05), ((xa + xb) / 2, Y0 + 0.01, 0.92), gloss_white, 0, 0.004)
box("Coving_S", (X1 - X0, 0.06, 0.06), (0, Y0 + 0.03, RH - 0.03), gloss_white)

# ------------------------------------------------------------------ floor coverings
rug = quad("Rug", [(-1.25, 0.8, 0.0095), (1.25, 0.8, 0.0095), (1.25, 2.7, 0.0095), (-1.25, 2.7, 0.0095)], rug_m)
box("Rug_edge", (2.58, 1.98, 0.009), (0, 1.75, 0.0045), flat_mat("Rug_edge", (0.22, 0.07, 0.06), 0.95))
quad("Kitchen_lino", [(2.0, Y0, 0.003), (X1, Y0, 0.003), (X1, Y1, 0.003), (2.0, Y1, 0.003)], lino)

# ------------------------------------------------------------------ window (west)
cy = WIN_SILL + WIN_H / 2
box("Win_sill", (0.2, WIN_W + 0.16, 0.04), (X0 + 0.04, WIN_Y, WIN_SILL - 0.02), upvc, 0, 0.005)
for i, yy in enumerate([wy0 + 0.035, wy1 - 0.035, WIN_Y]):
    box(f"Win_jamb{i}", (0.07, 0.07 if i < 2 else 0.05, WIN_H), (X0 - 0.12, yy, cy), upvc)
box("Win_head", (0.07, WIN_W, 0.07), (X0 - 0.12, WIN_Y, WIN_SILL + WIN_H - 0.035), upvc)
box("Win_bottom", (0.07, WIN_W, 0.07), (X0 - 0.12, WIN_Y, WIN_SILL + 0.035), upvc)
glass = bpy.data.materials.new("Glass"); glass.use_nodes = True
gn = glass.node_tree; gn.nodes.clear(); go = gn.nodes.new("ShaderNodeOutputMaterial"); gt = gn.nodes.new("ShaderNodeBsdfTransparent")
gt.inputs[0].default_value = (0.95, 0.97, 0.97, 1); gn.links.new(gt.outputs[0], go.inputs[0])
quad("Win_glass", [(X0 - 0.12, wy1, WIN_SILL), (X0 - 0.12, wy0, WIN_SILL), (X0 - 0.12, wy0, WIN_SILL + WIN_H), (X0 - 0.12, wy1, WIN_SILL + WIN_H)], glass)
# outside: garden fence and lawn so the window isn't just white
quad("Outside_lawn", [(X0 - 8, -6, -0.3), (X0 - 0.3, -6, -0.3), (X0 - 0.3, 7, -0.3), (X0 - 8, 7, -0.3)], flat_mat("Lawn", (0.16, 0.24, 0.1), 0.95))
quad("Outside_fence", [(X0 - 6, 7, -0.3), (X0 - 6, -6, -0.3), (X0 - 6, -6, 1.6), (X0 - 6, 7, 1.6)], flat_mat("Fence", (0.25, 0.17, 0.11), 0.9))
quad("Outside_house", [(X0 - 14, 9, -0.3), (X0 - 14, -9, -0.3), (X0 - 14, -9, 7), (X0 - 14, 9, 7)], flat_mat("Brick_far", (0.35, 0.2, 0.15), 0.95))

def curtain(name, y_center, width, height, top_z, mat, gathered=1.0, sheer=False):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    nx, nz = 60, 20
    verts = [[bm.verts.new((0, -width / 2 + width * i / nx, -height * j / nz)) for i in range(nx + 1)] for j in range(nz + 1)]
    for j in range(nz):
        for i in range(nx):
            bm.faces.new([verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]])
    for row in verts:
        for k, v in enumerate(row):
            t = k / nx
            v.co.x = math.sin(t * math.pi * 2 * (width / 0.11) * gathered) * (0.035 if not sheer else 0.012) * (1 + 0.3 * math.sin(v.co.z * 3))
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for l in f.loops: l[uv].uv = (l.vert.co.y + width / 2, -l.vert.co.z)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = (X0 + (0.06 if sheer else 0.12), y_center, top_z); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return link(o)
velvet = flat_mat("Curtain_velvet", (0.35, 0.12, 0.13), 0.85)
net = flat_mat("Net_curtain", (0.95, 0.94, 0.9), 0.9, alpha=1.0, transmission=0.0)
net.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.55
net.blend_method = "BLEND" if hasattr(net, "blend_method") else None
curtain("Curtain_L", wy0 - 0.34, 0.45, RH - 0.1, RH - 0.08, velvet)
curtain("Curtain_R", wy1 + 0.34, 0.45, RH - 0.1, RH - 0.08, velvet)
curtain("Net_curtain", WIN_Y, WIN_W, WIN_H * 0.62, WIN_SILL + WIN_H - 0.02, net, sheer=True)
cylinder("Curtain_pole", 0.015, WIN_W + 1.55, (X0 + 0.13, WIN_Y, RH - 0.06), flat_mat("Brass", (0.6, 0.45, 0.2), 0.35, 1.0), 16, (math.pi / 2, 0, 0))
# radiator under the window
rad_m = flat_mat("Radiator", (0.9, 0.89, 0.85), 0.3)
for i in range(24):
    box(f"Radiator_fin{i}", (0.08, 0.035, 0.55), (X0 + 0.07, wy0 + 0.08 + i * 0.047, 0.42), rad_m, 0, 0.008)
box("Radiator_pipe", (0.02, 0.02, 0.2), (X0 + 0.07, wy0 + 0.05, 0.1), rad_m)

# ------------------------------------------------------------------ door (south)
door_m = flat_mat("Door_paint", (0.86, 0.84, 0.77), 0.35)
box("Door", (DOOR_W, 0.045, DOOR_H), (DOOR_X, Y0 - 0.03, DOOR_H / 2), door_m, 0, 0.003)
for zc, hh in [(0.5, 0.65), (1.42, 0.85)]:
    for sx in (-0.19, 0.19):
        box(f"Door_panel_{zc}_{sx}", (0.3, 0.012, hh), (DOOR_X + sx, Y0 - 0.002, zc), door_m, 0, 0.006)
for side in (-1, 1):
    box(f"Architrave_{side}", (0.07, 0.025, DOOR_H + 0.07), (DOOR_X + side * (DOOR_W / 2 + 0.035), Y0 + 0.012, (DOOR_H + 0.07) / 2), gloss_white, 0, 0.004)
box("Architrave_top", (DOOR_W + 0.14, 0.025, 0.07), (DOOR_X, Y0 + 0.012, DOOR_H + 0.035), gloss_white, 0, 0.004)
brass = flat_mat("Brass_handle", (0.75, 0.58, 0.25), 0.3, 1.0)
box("Door_handle_plate", (0.035, 0.012, 0.2), (DOOR_X - 0.33, Y0 + 0.0, 1.0), brass)
box("Door_handle", (0.12, 0.05, 0.02), (DOOR_X - 0.3, Y0 + 0.03, 1.04), brass, 0, 0.005)
# post piled up behind the door
import random; random.seed(7)
paper_env = [flat_mat("Envelope_white", (0.9, 0.88, 0.82), 0.8), flat_mat("Envelope_brown", (0.62, 0.48, 0.3), 0.85)]
for i in range(10):
    box(f"Post{i}", (0.22, 0.11, 0.003), (DOOR_X + random.uniform(-0.25, 0.25), Y0 + 0.35 + random.uniform(0, 0.3), 0.002 + i * 0.003), paper_env[i % 3 == 0], random.uniform(0, 3))
lbl = label_box("Takeaway_menu", (0.15, 0.21, 0.002), (DOOR_X + 0.15, Y0 + 0.5, 0.035), "newspaper.png", 0.4)

# ------------------------------------------------------------------ NORTH: Glenda's corner
chair = gltf("GreenChair_01", (CHAIR.x, CHAIR.y), rot_z=0.0)
chair.name = "Glenda_chair"
gltf("throw_pillows_01", (CHAIR.x + 0.02, CHAIR.y + 0.2), rot_z=0.05, scale=0.6, z=0.47)
TY = 0.26                                                              # side table pushed back to the wall
side = gltf("side_table_01", (0.78, 2.35 + TY))
ST = surface_z(0.86, 2.3 + TY, 1.2)                                         # actual tabletop height
gltf("round_spectacles", (0.72, 2.2 + TY), rot_z=0.4, z=ST, fit_w=0.14)
for i in range(7):
    label_box(f"Med_side_{i}", (0.135, 0.075, 0.05), (0.82 + (i % 2) * 0.1, 2.4 + TY + ((i * 37) % 5 - 2) * 0.012, ST + 0.025 + (i // 2) * 0.05), f"med_{i % 6}.png", (i * 0.7) % 0.6 - 0.3)
gav = cylinder("Gaviscon", 0.035, 0.19, (1.0, 2.22 + TY, ST + 0.095), label_mat("lbl_gav", "gaviscon.png", 0.35))
cylinder("Gaviscon_cap", 0.02, 0.03, (1.0, 2.22 + TY, ST + 0.205), flat_mat("Cap_green", (0.1, 0.45, 0.2), 0.4))
label_box("Rennie", (0.1, 0.06, 0.03), (0.86, 2.2 + TY, ST + 0.015), "rennie.png", 0.5)
gltf("standing_picture_frame_01", (1.0, 2.53 + TY), rot_z=-0.6, z=ST)
# table lamp on the side table
cylinder("Lamp_base", 0.06, 0.28, (0.6, 2.68, ST + 0.14), flat_mat("Lamp_ceramic", (0.55, 0.42, 0.3), 0.25))
shade_m = flat_mat("Lamp_shade", (0.9, 0.82, 0.62), 0.9, emit=(1.0, 0.75, 0.45), emit_strength=2.0)
bpy.ops.mesh.primitive_cone_add(radius1=0.17, radius2=0.11, depth=0.2, vertices=40, end_fill_type="NOTHING", location=(0.6, 2.68, ST + 0.38))
sh = bpy.context.active_object; sh.name = "Lamp_shade"; sh.data.materials.append(shade_m); link(sh)
bpy.ops.object.light_add(type="POINT", location=(0.6, 2.68, ST + 0.36)); lp = bpy.context.active_object
lp.name = "Lamp_bulb"; lp.data.energy = 25; lp.data.color = (1.0, 0.72, 0.42); lp.data.shadow_soft_size = 0.05; link(lp)
# wall decoration above the chair
gltf("fancy_picture_frame_01", (-0.15, Y1 - 0.03), z=1.35, fit_w=0.75)
pf = face_room(gltf("hanging_picture_frame_01", (1.3, Y1 - 0.03), z=1.4, fit_w=0.42), Vector((0, -1, 0)))
# the frame ships with black glass: put a picture behind it (a crop of the landscape canvas)
bpy.context.view_layer.update()
_pts = [o.matrix_world @ Vector(c) for o in pf.children_recursive if o.type == "MESH" for c in o.bound_box]
_mn = Vector([min(q[i] for q in _pts) for i in range(3)]); _mx = Vector([max(q[i] for q in _pts) for i in range(3)])
_pw, _ph = (_mx.x - _mn.x) * 0.78, (_mx.z - _mn.z) * 0.82; _cx, _cz = (_mn.x + _mx.x) / 2, (_mn.z + _mx.z) / 2
pic_m = fresh_mat("Small_picture"); pic_m.use_nodes = True
_t = pic_m.node_tree.nodes.new("ShaderNodeTexImage")
_t.image = img(os.path.join(A, "models", "fancy_picture_frame_01", "textures", "fancy_picture_frame_01_canvas_diff_2k.jpg"))
pic_m.node_tree.links.new(_t.outputs[0], pic_m.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
pic_m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.6
_q = quad("Small_picture", [(_cx + _pw / 2, _mn.y - 0.002, _cz - _ph / 2), (_cx - _pw / 2, _mn.y - 0.002, _cz - _ph / 2),
                            (_cx - _pw / 2, _mn.y - 0.002, _cz + _ph / 2), (_cx + _pw / 2, _mn.y - 0.002, _cz + _ph / 2)], pic_m)
_uv = _q.data.uv_layers.active.data
for _i, _li in enumerate(_q.data.polygons[0].loop_indices): _uv[_li].uv = [(0.35, 0.2), (0.62, 0.2), (0.62, 0.75), (0.35, 0.75)][_i]
gltf("wall_clock", (-1.2, Y1 - 0.03), z=1.7)
# towel under the feet - a crumpled bath towel, damp where her legs have been weeping
towel_m = fresh_mat("Towel_terry")
towel_m.use_nodes = True; tb = towel_m.node_tree; tb.nodes.clear()
to = tb.nodes.new("ShaderNodeOutputMaterial"); tbn = tb.nodes.new("ShaderNodeBsdfPrincipled"); tb.links.new(tbn.outputs[0], to.inputs[0])
tbn.inputs["Roughness"].default_value = 1.0; tbn.inputs["Sheen Weight"].default_value = 0.6
tco = tb.nodes.new("ShaderNodeTexCoord")
terry = tb.nodes.new("ShaderNodeTexNoise"); terry.inputs["Scale"].default_value = 900; terry.inputs["Detail"].default_value = 2
tb.links.new(tco.outputs["Object"], terry.inputs[0])
bump = tb.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6; bump.inputs["Distance"].default_value = 0.002
tb.links.new(terry.outputs[0], bump.inputs["Height"]); tb.links.new(bump.outputs[0], tbn.inputs["Normal"])
wet = tb.nodes.new("ShaderNodeTexNoise"); wet.inputs["Scale"].default_value = 3.0; wet.inputs["Detail"].default_value = 4
tb.links.new(tco.outputs["Object"], wet.inputs[0])
wr = tb.nodes.new("ShaderNodeValToRGB"); tb.links.new(wet.outputs[0], wr.inputs[0])
wr.color_ramp.elements[0].position = 0.45; wr.color_ramp.elements[0].color = (0.42, 0.5, 0.58, 1)     # damp, darker blue
wr.color_ramp.elements[1].position = 0.6; wr.color_ramp.elements[1].color = (0.58, 0.68, 0.76, 1)     # dry pale blue
stain = tb.nodes.new("ShaderNodeTexNoise"); stain.inputs["Scale"].default_value = 6.0
tb.links.new(tco.outputs["Object"], stain.inputs[0])
sr = tb.nodes.new("ShaderNodeValToRGB"); tb.links.new(stain.outputs[0], sr.inputs[0])
sr.color_ramp.elements[0].position = 0.62; sr.color_ramp.elements[0].color = (1, 1, 1, 1)
sr.color_ramp.elements[1].position = 0.72; sr.color_ramp.elements[1].color = (0.85, 0.78, 0.55, 1)   # yellowish exudate staining
mixc = tb.nodes.new("ShaderNodeMix"); mixc.data_type = "RGBA"; mixc.blend_type = "MULTIPLY"; mixc.inputs[0].default_value = 1.0
tb.links.new(wr.outputs[0], mixc.inputs[6]); tb.links.new(sr.outputs[0], mixc.inputs[7]); tb.links.new(mixc.outputs[2], tbn.inputs["Base Color"])
bpy.ops.mesh.primitive_plane_add(size=1, location=(CHAIR.x - 0.03, CHAIR.y - 0.42, 0.02))
tw = bpy.context.active_object; tw.name = "Towel"; tw.scale = (0.72, 0.48, 1); tw.rotation_euler.z = 0.12
tw.data.materials.append(towel_m); link(tw)
sub = tw.modifiers.new("sub", "SUBSURF"); sub.levels = 5; sub.render_levels = 5; sub.subdivision_type = "SIMPLE"
tex = bpy.data.textures.get("towel_folds") or bpy.data.textures.new("towel_folds", "CLOUDS"); tex.noise_scale = 0.09; tex.noise_depth = 3
dp = tw.modifiers.new("folds", "DISPLACE"); dp.texture = tex; dp.texture_coords = "GLOBAL"; dp.strength = 0.05; dp.mid_level = 0.35
so = tw.modifiers.new("thick", "SOLIDIFY"); so.thickness = 0.012
sm_ = tw.modifiers.new("smooth", "SMOOTH"); sm_.iterations = 6
for p_ in tw.data.polygons: p_.use_smooth = True
# walking stick leaning on the chair arm
# walking stick leaning against the left arm of the chair (as you face her)
TILT = 0.39; SB = Vector((CHAIR.x - 0.62, CHAIR.y - 0.17, 0.0))          # foot of the stick on the floor
SD = Vector((math.sin(TILT), 0, math.cos(TILT)))
stick = cylinder("Walking_stick", 0.011, 0.88, SB + SD * 0.44, flat_mat("Stick", (0.18, 0.11, 0.06), 0.4), 12, (0, TILT, 0))
top = SB + SD * 0.88
handle = cylinder("Walking_stick_handle", 0.014, 0.13, (top.x + 0.035, top.y, top.z + 0.012), bpy.data.materials["Stick"], 16, (0, math.radians(80), 0))
cylinder("Walking_stick_ferrule", 0.013, 0.03, SB + SD * 0.015, flat_mat("Rubber", (0.05, 0.05, 0.05), 0.8), 12, (0, TILT, 0))

# ------------------------------------------------------------------ WEST: window side - clutter, dresser, Dizzy
gltf("potted_plant_02", (X0 + 0.07, WIN_Y + 0.35), z=WIN_SILL, fit_h=0.32, tint=(0.75, 0.65, 0.4))
gltf("vintage_cabinet_01", (X0 + 0.3, -1.38), rot_z=math.pi / 2, fit_h=1.8)
# the old CRT telly sits on the dresser worktop, facing into the room
DRESSER_TOP = surface_z(X0 + 0.42, -1.38, 1.2)
gltf("television_02", (X0 + 0.42, -1.38), rot_z=math.pi / 2, z=DRESSER_TOP, scale=1.25)
# hoarding: newspaper piles and carrier bags in the north-west corner
news = label_mat("lbl_news", "newspaper.png", 0.9)
for (x, y, n) in [(X0 + 0.3, 2.6, 16), (X0 + 0.78, 2.55, 9), (X0 + 1.2, Y1 - 0.2, 11), (X0 + 0.55, -0.45, 7)]:
    for i in range(n):
        o = box(f"News_{x}_{y}_{i}", (0.42, 0.3, 0.025), (x + random.uniform(-0.03, 0.03), y + random.uniform(-0.02, 0.02), 0.0125 + i * 0.025), news, random.uniform(-0.25, 0.25))
gltf("wooden_bookshelf_worn", (X0 + 0.2, 2.05), rot_z=-math.pi / 2, fit_h=1.2)
SHELF = surface_z(X0 + 0.2, 2.05, 0.75)                          # top of the shelf just below 0.75 m
gltf("book_encyclopedia_set_01", (X0 + 0.2, 2.05), rot_z=-math.pi / 2, z=SHELF + 0.002, fit_w=0.5)
# Dizzy's basket and bowls
DOG = (-0.42, Y0 + 0.42)                                               # basket against the south wall, west of the door
gltf("wicker_basket_01", DOG, rot_z=0.1, scale=1.9)
dog_cushion = gltf("throw_pillows_01", DOG, rot_z=0.1 + math.pi / 2, z=0.035, fit_w=0.62)   # a flattened cushion inside the basket
dog_cushion.scale.z *= 0.45
BOWL = [(0.0, 0.004), (0.07, 0.004), (0.085, 0.0), (0.095, 0.0), (0.105, 0.055), (0.11, 0.062), (0.1, 0.062), (0.088, 0.052), (0.06, 0.012), (0.0, 0.012)]
BF, BW = (2.42, -0.35), (2.45, -0.1)                                   # bowls are only 6 cm tall, so they can sit out on the lino
lathe("Dog_bowl_food", BOWL, (*BF, 0), flat_mat("Bowl_red", (0.55, 0.1, 0.08), 0.35))
lathe("Dog_bowl_water", BOWL, (*BW, 0), flat_mat("Steel", (0.75, 0.75, 0.75), 0.22, 1.0))
lathe("Dog_water", [(0.0, 0.035), (0.094, 0.035)], (*BW, 0), flat_mat("Water", (0.6, 0.62, 0.6), 0.05, transmission=0.9))
kib = flat_mat("Kibble", (0.32, 0.18, 0.08), 0.7)
for k in range(26):
    a_ = random.uniform(0, 6.28); r_ = random.uniform(0, 0.06)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.009, segments=8, ring_count=6, location=(BF[0] + r_ * math.cos(a_), BF[1] + r_ * math.sin(a_), 0.02 + random.uniform(0, 0.012)))
    kb = bpy.context.active_object; kb.name = f"Kibble{k}"; kb.data.materials.append(kib); link(kb)

# ------------------------------------------------------------------ SOUTH: pad deliveries by the door
card = flat_mat("Cardboard", (0.55, 0.42, 0.26), 0.85)
pad_label = label_mat("lbl_pad", "pad_label.png", 0.6)
pack = label_mat("lbl_pad_pack", "pad_pack.png", 0.4)
def pad_box(name, loc, rz, opened=False):
    o = box(name, (0.6, 0.4, 0.35), (loc[0], loc[1], loc[2] + 0.175), card, rz, 0.01)
    lb = quad(name + "_label", [(-0.15, 0.2011, -0.1), (0.15, 0.2011, -0.1), (0.15, 0.2011, 0.12), (-0.15, 0.2011, 0.12)], pad_label)
    lb.parent = o; lb.rotation_euler.z = math.pi
    lb2 = quad(name + "_label2", [(0.15, -0.2011, -0.1), (-0.15, -0.2011, -0.1), (-0.15, -0.2011, 0.12), (0.15, -0.2011, 0.12)], pad_label); lb2.parent = o
    if opened:
        o.scale.z = 0.98
        for k in range(3):
            p_ = label_box(f"{name}_pack{k}", (0.17, 0.32, 0.12), (loc[0] - 0.18 + k * 0.18, loc[1], loc[2] + 0.38), "pad_pack.png", rz)
    return o
pad_box("Pads_box_1", (1.95, Y0 + 0.3, 0), 0.05)
pad_box("Pads_box_2", (1.97, Y0 + 0.31, 0.35), -0.08)
pad_box("Pads_box_3", (1.93, Y0 + 0.31, 0.70), 0.1, opened=True)
# sofa along the south wall (behind the viewer), second armchair in the north-east corner
gltf("sofa_03", (-1.98, Y0 + 0.39), rot_z=math.pi, scale=0.8, tint=(0.85, 0.8, 0.72))          # ~2.2 m three-seater
gltf("throw_pillows_01", (-2.55, Y0 + 0.45), rot_z=math.pi + 0.2, z=0.42, scale=0.6)
gltf("ArmChair_01", (1.65, 2.33), rot_z=-0.35, tint=(0.75, 0.7, 0.6))

# ------------------------------------------------------------------ EAST: kitchenette
unit_m = flat_mat("Kitchen_unit", (0.86, 0.83, 0.74), 0.4)
door_k = flat_mat("Kitchen_door", (0.82, 0.78, 0.66), 0.35)
top_m = flat_mat("Worktop", (0.28, 0.25, 0.22), 0.3)
kx = X1 - 0.3; ky0, ky1 = -1.2, 1.2
box("Kitchen_base", (0.6, ky1 - ky0, 0.86), (kx, (ky0 + ky1) / 2, 0.43), unit_m)
SY, SL, SW_ = 0.75, 0.42, 0.36                  # sink centre (y), bowl length (y) and width (x)
sx0, sx1, sy0, sy1 = kx - 0.02 - SW_ / 2, kx - 0.02 + SW_ / 2, SY - SL / 2, SY + SL / 2
wx0, wx1 = kx - 0.34, kx + 0.30
box("Worktop_a", (0.64, sy0 - (ky0 - 0.02), 0.04), (kx - 0.02, (ky0 - 0.02 + sy0) / 2, 0.88), top_m, 0, 0.004)
box("Worktop_b", (0.64, (ky1 + 0.02) - sy1, 0.04), (kx - 0.02, (sy1 + ky1 + 0.02) / 2, 0.88), top_m, 0, 0.004)
box("Worktop_c", (sx0 - wx0, SL, 0.04), ((wx0 + sx0) / 2, SY, 0.88), top_m)
box("Worktop_d", (wx1 - sx1, SL, 0.04), ((sx1 + wx1) / 2, SY, 0.88), top_m)
steel = flat_mat("Steel_sink", (0.72, 0.73, 0.75), 0.22, 1.0)
D = 0.16
box("Sink_floor", (SW_, SL, 0.008), (kx - 0.02, SY, 0.9 - D), steel)
box("Sink_wall_w", (0.008, SL, D), (sx0, SY, 0.9 - D / 2), steel); box("Sink_wall_e", (0.008, SL, D), (sx1, SY, 0.9 - D / 2), steel)
box("Sink_wall_s", (SW_, 0.008, D), (kx - 0.02, sy0, 0.9 - D / 2), steel); box("Sink_wall_n", (SW_, 0.008, D), (kx - 0.02, sy1, 0.9 - D / 2), steel)
for e_, (w_, d_, x_, y_) in enumerate([(SW_ + 0.06, 0.03, kx - 0.02, sy0 - 0.015), (SW_ + 0.06, 0.03, kx - 0.02, sy1 + 0.015), (0.03, SL, sx0 - 0.015, SY), (0.03, SL, sx1 + 0.015, SY)]):
    box(f"Sink_rim{e_}", (w_, d_, 0.006), (x_, y_, 0.903), steel)
lathe("Sink_plug", [(0.0, 0.0), (0.025, 0.0), (0.025, 0.004), (0.0, 0.004)], (kx - 0.02, SY, 0.9 - D + 0.004), flat_mat("Plug", (0.15, 0.15, 0.15), 0.6))
for k in range(9):                                  # drainer ridges beside the sink
    box(f"Drainer{k}", (0.3, 0.01, 0.006), (kx - 0.02, sy0 - 0.08 - k * 0.035, 0.903), steel)
TAPX = kx + 0.2
cylinder("Tap_body", 0.016, 0.2, (TAPX, SY, 1.0), steel, 20)
cylinder("Tap_spout", 0.011, 0.17, (TAPX - 0.085, SY, 1.1), steel, 16, (0, math.pi / 2, 0))
for k_, dy in enumerate((-0.07, 0.07)):
    cylinder(f"Tap_handle{k_}", 0.02, 0.05, (TAPX, SY + dy, 0.925), flat_mat("Tap_head", (0.85, 0.85, 0.85), 0.2, 1.0), 12)
# washing-up liquid and a dirty plate in the sink
cylinder("Washing_up", 0.028, 0.2, (kx + 0.15, SY + 0.28, 1.0), flat_mat("WashUp", (0.2, 0.6, 0.25), 0.2), 16)
lathe("Plate_in_sink", [(0, 0.0), (0.1, 0.0), (0.12, 0.015), (0.13, 0.018)], (kx - 0.03, SY + 0.03, 0.9 - D + 0.012), flat_mat("China", (0.93, 0.92, 0.88), 0.2))
for i in range(4):
    yy = ky0 + 0.3 + i * 0.6
    box(f"Kitchen_door{i}", (0.02, 0.58, 0.7), (kx - 0.31, yy, 0.45), door_k, 0, 0.004)
    box(f"Kitchen_handle{i}", (0.02, 0.015, 0.12), (kx - 0.33, yy - 0.22, 0.68), flat_mat("Chrome", (0.8, 0.8, 0.8), 0.2, 1.0))
box("Kitchen_plinth", (0.02, ky1 - ky0, 0.1), (kx - 0.27, (ky0 + ky1) / 2, 0.05), flat_mat("Plinth", (0.2, 0.18, 0.16), 0.6))

box("Wall_units", (0.33, 1.8, 0.65), (X1 - 0.17, 0.0, 1.75), unit_m, 0, 0.005)
for i in range(3):
    box(f"Wall_unit_door{i}", (0.015, 0.58, 0.62), (X1 - 0.34, -0.6 + i * 0.6, 1.75), door_k, 0, 0.004)
box("Splashback", (0.01, ky1 - ky0, 0.55), (X1 - 0.005, (ky0 + ky1) / 2, 1.17), flat_mat("Tiles", (0.9, 0.9, 0.86), 0.15))
gltf("vintage_electric_kettle", (kx, -0.85), rot_z=-math.pi / 2, z=0.9, scale=0.75)
gltf("vintage_microwave", (kx + 0.03, -0.1), rot_z=-math.pi / 2, z=0.9, fit_w=0.5)
gltf("bananas", (kx - 0.1, 0.25), rot_z=0.6, z=0.9, tint=(0.35, 0.28, 0.15))
for i, (y, c) in enumerate([(0.38, (0.9, 0.88, 0.82)), (1.1, (0.18, 0.35, 0.55)), (-0.45, (0.6, 0.2, 0.15))]):
    cylinder(f"Mug{i}", 0.04, 0.09, (kx - 0.12, y, 0.945), flat_mat(f"Mug{i}", c, 0.25))
for i in range(6):
    label_box(f"Med_kitchen_{i}", (0.135, 0.075, 0.05), (kx - 0.05 + (i % 2) * 0.02, -0.55 + (i % 3) * 0.08, 0.925 + (i // 2) * 0.05), f"med_{(i + 2) % 6}.png", i * 0.4)
cylinder("Gaviscon_2", 0.035, 0.19, (kx - 0.15, -0.7, 0.995), bpy.data.materials["lbl_gav"])
# fridge with a note
fr = box("Fridge", (0.6, 0.62, 1.45), (X1 - 0.31, Y1 - 0.35, 0.725), flat_mat("Fridge_white", (0.9, 0.9, 0.87), 0.25), 0, 0.02)
box("Fridge_handle", (0.02, 0.03, 0.3), (X1 - 0.62, Y1 - 0.62, 1.1), flat_mat("Fridge_handle", (0.7, 0.7, 0.7), 0.3))
q = quad("Fridge_note", [(X1 - 0.612, Y1 - 0.15, 1.0), (X1 - 0.612, Y1 - 0.45, 1.0), (X1 - 0.612, Y1 - 0.45, 1.3), (X1 - 0.612, Y1 - 0.15, 1.3)], label_mat("lbl_note", "fridge_note.png", 0.7))
for p_ in q.data.uv_layers.active.data: pass
uvq = q.data.uv_layers.active.data
for i, li in enumerate(q.data.polygons[0].loop_indices): uvq[li].uv = [(0, 0), (1, 0), (1, 1), (0, 1)][i]
gltf("painted_wooden_cabinet", (X1 - 0.35, -2.2), rot_z=-math.pi / 2, fit_h=1.3, tint=(0.85, 0.82, 0.75))
BIN = Vector((X1 - 0.3, -1.45, 0))
bin_m = flat_mat("Pedal_bin", (0.75, 0.75, 0.76), 0.25, 1.0)
lathe("Pedal_bin", [(0.0, 0.0), (0.13, 0.0), (0.135, 0.01), (0.14, 0.42), (0.14, 0.43), (0.0, 0.43)], BIN, bin_m)
lathe("Pedal_bin_lid", [(0.0, 0.47), (0.08, 0.465), (0.13, 0.445), (0.145, 0.43), (0.145, 0.425)], BIN + Vector((0, 0, 0.0)), bin_m)
box("Pedal_bin_pedal", (0.07, 0.05, 0.012), (BIN.x - 0.15, BIN.y, 0.03), flat_mat("Pedal", (0.1, 0.1, 0.1), 0.5))
box("Pedal_bin_bagedge", (0.01, 0.06, 0.04), (BIN.x - 0.14, BIN.y + 0.04, 0.44), flat_mat("Binbag", (0.03, 0.03, 0.035), 0.3))
gltf("trashbag", (0.3, Y0 + 0.3), rot_z=0.8, scale=0.85)
gltf("trashbag", (0.22, Y0 + 0.26), rot_z=2.4, scale=0.6, z=0.3)
gltf("trashbag", (0.12, Y0 + 0.3), rot_z=4.0, scale=0.7)

# ------------------------------------------------------------------ outer shell: blocks stray daylight everywhere except the window
shell = flat_mat("Shell_black", (0.02, 0.02, 0.02), 1.0)
O_ = 0.3
SX0, SX1, SY0, SY1, SZ0, SZ1 = X0 - O_, X1 + O_, Y0 - O_, Y1 + O_, -O_, RH + O_
quad("Shell_top", [(SX0, SY0, SZ1), (SX1, SY0, SZ1), (SX1, SY1, SZ1), (SX0, SY1, SZ1)], shell)
quad("Shell_bottom", [(SX0, SY1, SZ0), (SX1, SY1, SZ0), (SX1, SY0, SZ0), (SX0, SY0, SZ0)], shell)
quad("Shell_n", [(SX1, SY1, SZ0), (SX0, SY1, SZ0), (SX0, SY1, SZ1), (SX1, SY1, SZ1)], shell)
quad("Shell_s", [(SX0, SY0, SZ0), (SX1, SY0, SZ0), (SX1, SY0, SZ1), (SX0, SY0, SZ1)], shell)
quad("Shell_e", [(SX1, SY0, SZ0), (SX1, SY1, SZ0), (SX1, SY1, SZ1), (SX1, SY0, SZ1)], shell)
for nm_, (ya, yb, za, zb) in {"a": (SY0, wy0, SZ0, SZ1), "b": (wy1, SY1, SZ0, SZ1), "c": (wy0, wy1, SZ0, WIN_SILL), "d": (wy0, wy1, WIN_SILL + WIN_H, SZ1)}.items():
    quad(f"Shell_w_{nm_}", [(SX0, yb, za), (SX0, ya, za), (SX0, ya, zb), (SX0, yb, zb)], shell)
# window tunnel through the shell so the opening stays clean
for nm_, pts_ in {"t": [(SX0, wy1, WIN_SILL + WIN_H), (X0 - T, wy1, WIN_SILL + WIN_H), (X0 - T, wy0, WIN_SILL + WIN_H), (SX0, wy0, WIN_SILL + WIN_H)],
                  "b": [(X0 - T, wy1, WIN_SILL), (SX0, wy1, WIN_SILL), (SX0, wy0, WIN_SILL), (X0 - T, wy0, WIN_SILL)],
                  "n": [(X0 - T, wy1, WIN_SILL), (X0 - T, wy1, WIN_SILL + WIN_H), (SX0, wy1, WIN_SILL + WIN_H), (SX0, wy1, WIN_SILL)],
                  "s": [(SX0, wy0, WIN_SILL), (SX0, wy0, WIN_SILL + WIN_H), (X0 - T, wy0, WIN_SILL + WIN_H), (X0 - T, wy0, WIN_SILL)]}.items():
    quad(f"Shell_win_{nm_}", pts_, reveal)
# behind the door: a dim hallway wall so the door gap isn't a light source
quad("Hall_back", [(dx0 - 0.3, Y0 - 0.28, 0), (dx1 + 0.3, Y0 - 0.28, 0), (dx1 + 0.3, Y0 - 0.28, DOOR_H + 0.3), (dx0 - 0.3, Y0 - 0.28, DOOR_H + 0.3)], flat_mat("Hall", (0.3, 0.27, 0.22), 0.9))

# ------------------------------------------------------------------ ceiling light
cylinder("Ceiling_light", 0.19, 0.06, (0, 0.3, RH - 0.03), flat_mat("Ceiling_light", (0.95, 0.92, 0.85), 0.5, emit=(1.0, 0.85, 0.65), emit_strength=0.8), 48)
bpy.ops.object.light_add(type="AREA", location=(0, 0.3, RH - 0.07)); cl = bpy.context.active_object
cl.name = "Ceiling_light_lamp"; cl.data.shape = "DISK"; cl.data.size = 0.35; cl.data.energy = 60; cl.data.color = (1.0, 0.82, 0.6); link(cl)

# ------------------------------------------------------------------ daylight: sky + sun + window portal
sc = bpy.context.scene
w = sc.world or bpy.data.worlds.new("World"); sc.world = w; w.use_nodes = True; wn = w.node_tree; wn.nodes.clear()
wo = wn.nodes.new("ShaderNodeOutputWorld"); bg = wn.nodes.new("ShaderNodeBackground"); sky = wn.nodes.new("ShaderNodeTexSky")
try: sky.sky_type = "NISHITA"
except Exception: pass
try:
    sky.sun_elevation = math.radians(22); sky.sun_rotation = math.radians(250); sky.air_density = 1.5; sky.dust_density = 4.0
except Exception: pass
wn.links.new(sky.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 0.35; wn.links.new(bg.outputs[0], wo.inputs[0])
bpy.ops.object.light_add(type="SUN", rotation=(math.radians(68), 0, math.radians(-110))); sun = bpy.context.active_object
sun.name = "Sun"; sun.data.energy = 2.5; sun.data.angle = math.radians(2); sun.data.color = (1.0, 0.93, 0.82); link(sun)
bpy.ops.object.light_add(type="AREA", location=(X0 - 0.13, WIN_Y, cy), rotation=(0, math.radians(90), 0)); po = bpy.context.active_object
po.name = "Window_portal"; po.data.shape = "RECTANGLE"; po.data.size = WIN_H; po.data.size_y = WIN_W
po.rotation_euler = (0, math.radians(-90), 0)
try: po.data.cycles.is_portal = True
except Exception: pass
link(po)

# ------------------------------------------------------------------ 360 camera
cam = bpy.data.objects.get("Cam360")
if not cam:
    cam = bpy.data.objects.new("Cam360", bpy.data.cameras.new("Cam360")); sc.collection.objects.link(cam)
cam.location = (0, 0, EYE); cam.rotation_euler = (math.radians(90), 0, 0)      # looking north (+Y)
cam.data.type = "PANO"
try: cam.data.panorama_type = "EQUIRECTANGULAR"
except Exception: cam.data.cycles.panorama_type = "EQUIRECTANGULAR"
cam.data.clip_start = 0.05
sc.camera = cam
sc.render.engine = "CYCLES"
sc.cycles.samples = 256; sc.cycles.use_denoising = True
sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Base Contrast" if "AgX - Base Contrast" in [l for l in []] else "None"
sc.view_settings.exposure = 0.6
sc.render.resolution_x, sc.render.resolution_y = 2048, 1024

# ------------------------------------------------------------------ age everything: grime, fading, less shine
SKIP = ("Lamp_shade", "Ceiling_light", "Glass", "Water", "Shell", "Hall", "Lawn", "Fence", "Brick_far", "Net_curtain", "Rug")
def grubby(m, amount=1.0):
    if not m or not m.use_nodes or any(k in m.name for k in SKIP) or m.get("grubby"): return
    nt = m.node_tree; b = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if not b: return
    tc = nt.nodes.new("ShaderNodeTexCoord")
    dirt = nt.nodes.new("ShaderNodeTexNoise"); dirt.inputs["Scale"].default_value = 3.5; dirt.inputs["Detail"].default_value = 10; dirt.inputs["Roughness"].default_value = 0.65
    nt.links.new(tc.outputs["Object"], dirt.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(dirt.outputs[0], ramp.inputs[0])
    ramp.color_ramp.elements[0].position = 0.38; ramp.color_ramp.elements[0].color = (0.62 + 0.38 * (1 - amount), 0.57 + 0.43 * (1 - amount), 0.47 + 0.53 * (1 - amount), 1)
    ramp.color_ramp.elements[1].position = 0.62; ramp.color_ramp.elements[1].color = (0.97, 0.95, 0.9, 1)
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs[0].default_value = 1.0
    bc = b.inputs["Base Color"]
    if bc.links: nt.links.new(bc.links[0].from_socket, mix.inputs[6])
    else: mix.inputs[6].default_value = bc.default_value
    hs = nt.nodes.new("ShaderNodeHueSaturation"); hs.inputs["Saturation"].default_value = 0.85
    nt.links.new(ramp.outputs[0], mix.inputs[7]); nt.links.new(mix.outputs[2], hs.inputs["Color"]); nt.links.new(hs.outputs[0], b.inputs["Base Color"])
    r = b.inputs["Roughness"]
    if not r.links: r.default_value = min(1.0, r.default_value + 0.25 * amount)
    m["grubby"] = 1
seen = set()
for o in ROOM.all_objects:
    for sl in getattr(o, "material_slots", []):
        if sl.material and sl.material.name not in seen:
            seen.add(sl.material.name)
            grubby(sl.material, 0.6 if sl.material.name.startswith("lbl_") else (0.35 if sl.material.name.startswith("Ceiling") else 1.0))
print("Room built:", len(ROOM.all_objects), "objects")
