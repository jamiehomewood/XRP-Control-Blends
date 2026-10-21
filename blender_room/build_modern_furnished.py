"""
MODERN - FURNISHED: the modern recess room (build_recess_test.py, STYLE "modern") with a fitted kitchen beyond the
arch and furniture standing in the recesses, so nothing deep sits out on the projected floor.

  Glenda's alcove (north)  mid-century lounge chair, side table, plant
  West recess              low modern sideboard with vases, picture above
  South-west recess        modern sofa with cushions, plant
  Kitchen (beyond arch)    handleless fitted kitchen: base run with quartz worktop, sink, induction hob, wall units
                           with LED strip, cooker hood, tall fridge-freezer and oven tower, tiled splashback

Run inside Glenda_Room.blend. Builds the scene "ModernFurnished" and renders room_pano_modern_furnished.jpg.
Furniture models: Poly Haven (CC0), downloaded by fetch_blender_assets.py. The kitchen is built here.
"""
import bpy, math, os
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:\Projects\01_Active\Nursing XRP Scenario 001\blender_room"
A = os.path.join(ROOT, "assets")
OUT = os.path.join(os.path.dirname(ROOT), "spout-test", "assets", "room_pano_modern_furnished.jpg")

# 1. the shell: the same walls / recesses / arch / hall as the modern room, built into its own scene
shell_py = os.path.join(ROOT, "build_recess_test.py")
g = {"__file__": shell_py, "__name__": "__main__", "STYLE": "modern",
     "SCENE_NAME_OVERRIDE": "ModernFurnished", "COLL_NAME_OVERRIDE": "ModernFurnishedShell", "OUT_OVERRIDE": OUT}
exec(compile(open(shell_py, encoding="utf-8").read(), shell_py, "exec"), g)
X0, X1, Y0, Y1, RH = g["X0"], g["X1"], g["Y0"], g["Y1"], g["RH"]
KX0, KX1, KY0, KY1 = g["KX0"], g["KX1"], g["KY0"], g["KY1"]
GLENDA_D, GLENDA_X, DRESSER_D, DRESSER_Y, SOFA_D, SOFA_X1 = g["GLENDA_D"], g["GLENDA_X"], g["DRESSER_D"], g["DRESSER_Y"], g["SOFA_D"], g["SOFA_X1"]
sc = bpy.data.scenes["ModernFurnished"]

coll = bpy.data.collections.get("ModernFurnishings")
if coll:
    for o in list(coll.all_objects): bpy.data.objects.remove(o, do_unlink=True)
else:
    coll = bpy.data.collections.new("ModernFurnishings")
if coll.name not in sc.collection.children: sc.collection.children.link(coll)

def link(o):
    for c in list(o.users_collection): c.objects.unlink(o)
    coll.objects.link(o); return o

def flat(name, color, rough, metal=0.0, emit=None, strength=1.0, coat=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough; b.inputs["Metallic"].default_value = metal
    if coat:
        for k in ("Coat Weight", "Clearcoat"):
            if k in b.inputs: b.inputs[k].default_value = coat; break
    if emit:
        for k in ("Emission Color", "Emission"):
            if k in b.inputs: b.inputs[k].default_value = (*emit, 1); break
        b.inputs["Emission Strength"].default_value = strength
    return m

def box(name, size, loc, m, rz=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=(0, 0, rz))
    o = bpy.context.active_object; o.name = name; o.scale = size; o.data.materials.append(m); return link(o)

def cyl(name, r, h, loc, m, rot=(0, 0, 0), verts=32):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, vertices=verts, location=loc, rotation=rot)
    o = bpy.context.active_object; o.name = name; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = True
    return link(o)

def gltf(name, loc, rot_z=0.0, fit_w=None, fit_h=None, scale=1.0, z=0.0):
    """Poly Haven glTF under an empty: base on z, centred on loc. Front faces -Y before rot_z."""
    path = os.path.join(A, "models", name, f"{name}.gltf")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(f"F_{name}_root", None); link(root)
    for o in new:
        link(o)
        if o.parent is None: o.parent = root
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in new if o.type == "MESH" for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    size, ctr, s = mx - mn, (mn + mx) / 2, scale
    if fit_w: s = fit_w / max(size.x, size.y)
    if fit_h: s = fit_h / size.z
    for o in new:
        if o.parent is root: o.location -= Vector((ctr.x, ctr.y, mn.z))
    root.scale = (s, s, s); root.rotation_euler.z = rot_z; root.location = (loc[0], loc[1], z)
    bpy.context.view_layer.update()
    return root

def bounds(root):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in root.children_recursive if o.type == "MESH" for c in o.bound_box]
    return Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))), Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))

def snap(root, axis, side, value):
    """Move root so its bounding box's min (side=-1) or max (side=+1) on axis (0=x, 1=y) sits at value."""
    mn, mx = bounds(root); cur = (mn if side < 0 else mx)[axis]
    loc = list(root.location); loc[axis] += value - cur; root.location = loc; bpy.context.view_layer.update()
    return root

def top_of(root):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in root.children_recursive if o.type == "MESH" for c in o.bound_box]
    return max(p.z for p in pts)

# make the furnished scene the active one while importing (imports land in the active scene)
win = bpy.context.window_manager.windows[0]; prev_scene = win.scene; win.scene = sc

# ======================================================================== living room: furniture in the recesses
# Glenda's alcove (north wall, x -1.0..1.25, 0.9 m deep): lounge chair facing into the room, side table, plant
ay = Y1 + GLENDA_D / 2
snap(gltf("mid_century_lounge_chair", (-0.05, ay), rot_z=0.0, fit_w=0.82), 1, +1, Y1 + GLENDA_D - 0.04)
st = gltf("side_table_01", (0.78, ay + 0.15), rot_z=0.0, fit_h=0.52)
gltf("ceramic_vase_03", (0.78, ay + 0.15), fit_h=0.28, z=top_of(st))
gltf("potted_plant_01", (-0.72, ay + 0.2), fit_h=0.95)

# west recess (x -3.75..-3.2, y -2.2..-0.5): low sideboard against the recess back wall, vases, a picture above
wx = X0 - DRESSER_D
sb = snap(gltf("modern_wooden_cabinet", (wx + 0.25, (DRESSER_Y[0] + DRESSER_Y[1]) / 2), rot_z=math.pi / 2, fit_w=1.45), 0, -1, wx + 0.02)
sbt = top_of(sb)
gltf("ceramic_vase_01", (wx + 0.24, DRESSER_Y[0] + 0.35), fit_h=0.38, z=sbt)
gltf("wooden_bowl_01", (wx + 0.26, -1.25), fit_w=0.3, z=sbt)
gltf("ceramic_vase_03", (wx + 0.24, DRESSER_Y[1] - 0.3), fit_h=0.22, z=sbt)
# abstract canvas in the room's colours, thin oak frame
def art_mat():
    m = bpy.data.materials.get("Art_abstract") or bpy.data.materials.new("Art_abstract")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord"); wv = nt.nodes.new("ShaderNodeTexWave"); wv.inputs["Scale"].default_value = 1.2
    wv.inputs["Distortion"].default_value = 3.0; wv.inputs["Detail"].default_value = 1.0; nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB"); nt.links.new(wv.outputs["Fac"], ramp.inputs[0]); r = ramp.color_ramp; r.interpolation = "CONSTANT"
    r.elements[0].position = 0.0; r.elements[0].color = (0.75, 0.70, 0.60, 1)          # cream
    r.elements[1].position = 0.75; r.elements[1].color = (0.085, 0.11, 0.10, 1)        # kitchen sage-graphite
    e = r.elements.new(0.35); e.color = (0.45, 0.18, 0.09, 1)                          # terracotta
    e = r.elements.new(0.55); e.color = (0.55, 0.47, 0.33, 1)                          # sand
    nt.links.new(ramp.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.8
    return m
pcy, pz0, pw, ph = (DRESSER_Y[0] + DRESSER_Y[1]) / 2, sbt + 0.3, 0.75, 0.95
box("Art_canvas", (0.03, pw, ph), (wx + 0.03, pcy, pz0 + ph / 2), art_mat())
oak = bpy.data.materials.get("Modern_oak")
for nm_, size, loc in (("t", (0.04, pw + 0.04, 0.02), (wx + 0.035, pcy, pz0 + ph + 0.01)), ("b", (0.04, pw + 0.04, 0.02), (wx + 0.035, pcy, pz0 - 0.01)),
                       ("l", (0.04, 0.02, ph), (wx + 0.035, pcy - pw / 2 - 0.01, pz0 + ph / 2)), ("r", (0.04, 0.02, ph), (wx + 0.035, pcy + pw / 2 + 0.01, pz0 + ph / 2))):
    box(f"Art_frame_{nm_}", size, loc, oak)

# south-west recess (x -3.2..-0.85, 0.8 m deep): sofa facing north, plant in the corner
sy = Y0 - SOFA_D / 2
sofa = snap(gltf("sofa_02", (-2.05, sy), rot_z=math.pi, fit_w=2.25), 1, -1, Y0 - SOFA_D + 0.03)
gltf("potted_plant_04", (-1.05, sy - 0.15), fit_h=0.45)

# ======================================================================== fitted kitchen (all of it beyond the real wall)
front_m = flat("Kit_front", (0.085, 0.11, 0.10), 0.55)               # matt deep sage-graphite, handleless
carcass_m = flat("Kit_carcass", (0.05, 0.06, 0.055), 0.6)
gap_m = flat("Kit_gap", (0.008, 0.008, 0.008), 0.7)
quartz_m = flat("Kit_quartz", (0.78, 0.77, 0.74), 0.18, coat=0.4)
steel_m = flat("Kit_steel", (0.62, 0.62, 0.6), 0.25, 1.0)
black_glass = flat("Kit_black_glass", (0.01, 0.01, 0.012), 0.05, coat=1.0)
led_m = flat("Kit_led", (1, 1, 1), 0.5, emit=(1.0, 0.9, 0.75), strength=12)
ring_m = flat("Kit_hob_ring", (0.15, 0.15, 0.15), 0.3)

def tile_splash():
    m = bpy.data.materials.get("Kit_splash") or bpy.data.materials.new("Kit_splash")
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    tc = nt.nodes.new("ShaderNodeTexCoord"); br = nt.nodes.new("ShaderNodeTexBrick"); nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    br.offset = 0.5; br.squash = 1.0
    br.inputs["Scale"].default_value = 1 / 0.15; br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 0.5
    br.inputs["Mortar Size"].default_value = 0.004
    br.inputs["Color1"].default_value = (0.78, 0.80, 0.78, 1); br.inputs["Color2"].default_value = (0.74, 0.77, 0.75, 1); br.inputs["Mortar"].default_value = (0.5, 0.5, 0.48, 1)
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = 0.12
    return m
splash_m = tile_splash()

D, H_BASE, T_TOP, PLINTH = 0.60, 0.87, 0.03, 0.12            # base depth, carcass top, worktop thickness, plinth
WALL_Z0, WALL_Z1, WD = 1.42, 2.16, 0.34                    # wall units
DOOR_GAP = 0.003
TALL_W = 0.62

# the run along the kitchen's east wall (x = KX1), front facing west (-x), from the south wall to the tall units
run_y0, run_y1 = KY0, KY1 - TALL_W                          # base run
tall_y0 = run_y1                                            # fridge-freezer in the NE corner
fx = KX1 - D                                                # front plane of base units
# carcass + plinth
box("Kit_base_carcass", (D - 0.02, run_y1 - run_y0, H_BASE - PLINTH), (KX1 - D / 2 - 0.01, (run_y0 + run_y1) / 2, PLINTH + (H_BASE - PLINTH) / 2), carcass_m)
box("Kit_plinth", (0.02, run_y1 - run_y0, PLINTH), (fx + 0.07, (run_y0 + run_y1) / 2, PLINTH / 2), gap_m)
# doors / drawers: 600 wide, handleless with a recessed J-rail under the worktop
SINK_Y, HOB_Y = 0.25, -0.85
widths, y_ = [], run_y0
while run_y1 - y_ > 0.3:
    w = min(0.6, run_y1 - y_); widths.append((y_, y_ + w)); y_ += w
for i, (ya, yb) in enumerate(widths):
    cy = (ya + yb) / 2; w = yb - ya - DOOR_GAP
    if ya <= HOB_Y < yb:                                    # pan drawers under the hob
        for j, (za, zb) in enumerate(((PLINTH, 0.42), (0.42, 0.78))):
            box(f"Kit_drawer_{i}_{j}", (0.02, w, zb - za - DOOR_GAP), (fx - 0.01, cy, (za + zb) / 2), front_m)
    else:
        box(f"Kit_door_{i}", (0.02, w, 0.78 - PLINTH - DOOR_GAP), (fx - 0.01, cy, (PLINTH + 0.78) / 2), front_m)
box("Kit_jrail", (0.03, run_y1 - run_y0, 0.06), (fx + 0.005, (run_y0 + run_y1) / 2, 0.81), gap_m)
# worktop with a sink cut-out (undermount bowl)
SL, SW = 0.5, 0.40                                          # sink length (y) and width (x)
sx_c = KX1 - 0.32
wt_z = H_BASE + T_TOP / 2
wt_front = fx - 0.02
for nm_, (ya, yb) in {"a": (run_y0, SINK_Y - SL / 2), "b": (SINK_Y + SL / 2, run_y1)}.items():
    box(f"Kit_worktop_{nm_}", (KX1 - wt_front, yb - ya, T_TOP), ((KX1 + wt_front) / 2, (ya + yb) / 2, wt_z), quartz_m)
for nm_, (xa, xb) in {"front": (wt_front, sx_c - SW / 2), "back": (sx_c + SW / 2, KX1)}.items():
    box(f"Kit_worktop_s{nm_}", (xb - xa, SL, T_TOP), ((xa + xb) / 2, SINK_Y, wt_z), quartz_m)
bz = H_BASE - 0.19
box("Kit_sink_floor", (SW, SL, 0.01), (sx_c, SINK_Y, bz), steel_m)
for nm_, size, loc in (("n", (SW, 0.01, 0.2), (sx_c, SINK_Y + SL / 2, bz + 0.1)), ("s", (SW, 0.01, 0.2), (sx_c, SINK_Y - SL / 2, bz + 0.1)),
                       ("e", (0.01, SL, 0.2), (sx_c + SW / 2, SINK_Y, bz + 0.1)), ("w", (0.01, SL, 0.2), (sx_c - SW / 2, SINK_Y, bz + 0.1))):
    box(f"Kit_sink_{nm_}", size, loc, steel_m)
# gooseneck tap behind the sink
tx = KX1 - 0.07
cyl("Kit_tap_base", 0.025, 0.04, (tx, SINK_Y, H_BASE + T_TOP + 0.02), steel_m)
cyl("Kit_tap_column", 0.014, 0.32, (tx, SINK_Y, H_BASE + T_TOP + 0.18), steel_m)
cyl("Kit_tap_spout", 0.012, 0.2, (tx - 0.09, SINK_Y, H_BASE + T_TOP + 0.33), steel_m, rot=(0, math.radians(90), 0))
cyl("Kit_tap_nozzle", 0.013, 0.05, (tx - 0.19, SINK_Y, H_BASE + T_TOP + 0.31), steel_m)
cyl("Kit_tap_lever", 0.006, 0.08, (tx, SINK_Y + 0.03, H_BASE + T_TOP + 0.2), steel_m, rot=(math.radians(60), 0, 0))
# induction hob
hz = H_BASE + T_TOP + 0.003
box("Kit_hob", (0.52, 0.6, 0.006), (KX1 - 0.31, HOB_Y, hz), black_glass)
# hob rings: thin flat tori read better than circles
for k, (dx, dy, r) in enumerate(((-0.12, -0.15, 0.09), (-0.12, 0.15, 0.07), (0.12, -0.15, 0.07), (0.12, 0.15, 0.1))):
    bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.002, major_segments=48, minor_segments=4, location=(KX1 - 0.31 + dx, HOB_Y + dy, hz + 0.003))
    t_ = bpy.context.active_object; t_.name = f"Kit_hob_ring_t{k}"; t_.scale.z = 0.3; t_.data.materials.append(ring_m); link(t_)
# splashback (tiles) between worktop and wall units
box("Kit_splashback", (0.01, run_y1 - run_y0, WALL_Z0 - H_BASE - T_TOP), (KX1 - 0.005, (run_y0 + run_y1) / 2, (H_BASE + T_TOP + WALL_Z0) / 2), splash_m)
# wall units (two either side of a cooker hood), with an LED strip underneath
hood_w = 0.6
for nm_, (ya, yb) in {"a": (run_y0, HOB_Y - hood_w / 2), "b": (HOB_Y + hood_w / 2, run_y1)}.items():
    if yb - ya < 0.2: continue
    box(f"Kit_wall_carcass_{nm_}", (WD, yb - ya, WALL_Z1 - WALL_Z0), (KX1 - WD / 2, (ya + yb) / 2, (WALL_Z0 + WALL_Z1) / 2), carcass_m)
    y_ = ya
    while yb - y_ > 0.2:
        w = min(0.6, yb - y_)
        box(f"Kit_wall_door_{nm_}_{y_:.2f}", (0.02, w - DOOR_GAP, WALL_Z1 - WALL_Z0 - DOOR_GAP), (KX1 - WD - 0.01, y_ + w / 2, (WALL_Z0 + WALL_Z1) / 2), front_m)
        y_ += w
    box(f"Kit_led_{nm_}", (0.02, yb - ya - 0.05, 0.004), (KX1 - WD + 0.04, (ya + yb) / 2, WALL_Z0 - 0.003), led_m)
box("Kit_hood_canopy", (0.5, hood_w, 0.08), (KX1 - 0.25, HOB_Y, WALL_Z0 + 0.12), steel_m)
box("Kit_hood_chimney", (0.25, 0.28, RH - WALL_Z0 - 0.16), (KX1 - 0.125, HOB_Y, (WALL_Z0 + 0.16 + RH) / 2), steel_m)
bpy.ops.object.light_add(type="AREA", location=(KX1 - WD + 0.06, (run_y0 + run_y1) / 2, WALL_Z0 - 0.02))
led = bpy.context.active_object; led.name = "Kit_led_light"; led.data.shape = "RECTANGLE"; led.data.size = 0.05; led.data.size_y = run_y1 - run_y0
led.data.energy = 40; led.data.color = (1.0, 0.9, 0.75); link(led)

# tall units in the NE corner: integrated fridge-freezer, and an oven tower beside it along the north wall
for nm_, (cx, cy, rz) in {"fridge": (KX1 - D / 2, KY1 - TALL_W / 2, 0.0), "oven": (KX1 - D - TALL_W / 2 - 0.002, KY1 - D / 2, 0.0)}.items():
    if nm_ == "fridge":
        box("Kit_tall_fridge", (D, TALL_W, RH - 0.06), (cx, cy, (RH - 0.06) / 2), carcass_m)
        ffx = cx - D / 2 - 0.01
        box("Kit_fridge_door", (0.02, TALL_W - DOOR_GAP, 1.25), (ffx, cy, PLINTH + 0.95 + 1.25 / 2 - 0.08), front_m)
        box("Kit_freezer_door", (0.02, TALL_W - DOOR_GAP, 0.8), (ffx, cy, PLINTH + 0.4), front_m)
        box("Kit_fridge_top_door", (0.02, TALL_W - DOOR_GAP, RH - 0.06 - 2.04), (ffx, cy, 2.04 + (RH - 0.06 - 2.04) / 2 + 0.002), front_m)
    else:
        box("Kit_tall_oven", (TALL_W, D, RH - 0.06), (cx, cy, (RH - 0.06) / 2), carcass_m)
        ofy = cy - D / 2 - 0.01
        box("Kit_oven_drawer", (TALL_W - DOOR_GAP, 0.02, 0.6), (cx, ofy, PLINTH + 0.3), front_m)
        box("Kit_oven", (TALL_W - 0.02, 0.02, 0.6), (cx, ofy, PLINTH + 0.6 + 0.3 + 0.005), black_glass)
        box("Kit_oven_handle", (TALL_W - 0.12, 0.025, 0.018), (cx, ofy - 0.02, PLINTH + 0.6 + 0.56), steel_m)
        box("Kit_microwave", (TALL_W - 0.02, 0.02, 0.38), (cx, ofy, PLINTH + 1.22 + 0.19), black_glass)
        box("Kit_oven_top_door", (TALL_W - DOOR_GAP, 0.02, RH - 0.06 - 1.62), (cx, ofy, 1.62 + (RH - 0.06 - 1.62) / 2), front_m)

# a few things on the worktop
wtz = H_BASE + T_TOP
gltf("wooden_bowl_01", (KX1 - 0.3, -0.05), fit_w=0.3, z=wtz)
gltf("potted_plant_04", (KX1 - 0.25, run_y0 + 0.25), fit_h=0.32, z=wtz)
gltf("ceramic_vase_01", (KX1 - 0.18, 1.0), fit_h=0.3, z=wtz)

# ======================================================================== personal touches
L_DIR = os.path.join(ROOT, "labels")
def img_mat(name, path, rough=0.35):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True); t.extension = "EXTEND"
    nt.links.new(t.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    return m

def place(objs, loc, rz):
    """objs were built at the origin facing -Y; turn them by rz and move them to loc."""
    bpy.context.view_layer.update()
    M_ = Matrix.Translation(Vector(loc)) @ Matrix.Rotation(rz, 4, "Z")
    for o in objs: o.matrix_world = M_ @ o.matrix_world

def picture(name, img, w, h, loc, rz, frame=0.018, mount=0.035, depth=0.022, frame_m=None, tilt=0.0):
    """A framed photo with a white mount, front facing -Y before rz. loc = centre of its back."""
    frame_m = frame_m or flat("Frame_black", (0.02, 0.02, 0.02), 0.4)
    mount_m = flat("Frame_mount", (0.82, 0.81, 0.78), 0.8)
    W_, H_ = w + 2 * (mount + frame), h + 2 * (mount + frame)
    objs = [box(f"{name}_back", (W_ - 2 * frame, 0.004, H_ - 2 * frame), (0, -0.004, 0), mount_m)]
    for nm_, size, c in (("t", (W_, depth, frame), (0, -depth / 2, H_ / 2 - frame / 2)), ("b", (W_, depth, frame), (0, -depth / 2, -H_ / 2 + frame / 2)),
                         ("l", (frame, depth, H_), (-W_ / 2 + frame / 2, -depth / 2, 0)), ("r", (frame, depth, H_), (W_ / 2 - frame / 2, -depth / 2, 0))):
        objs.append(box(f"{name}_frame_{nm_}", size, c, frame_m))
    me = bpy.data.meshes.new(name + "_photo")
    me.from_pydata([(-w / 2, -0.007, -h / 2), (w / 2, -0.007, -h / 2), (w / 2, -0.007, h / 2), (-w / 2, -0.007, h / 2)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for li, (u, v) in zip(range(4), ((0, 0), (1, 0), (1, 1), (0, 1))): uv.data[li].uv = (u, v)
    me.materials.append(img_mat(f"Photo_{os.path.basename(img)}", img))
    ph = bpy.data.objects.new(name + "_photo", me); coll.objects.link(ph); objs.append(ph)
    bpy.context.view_layer.update()
    if tilt:                                                  # standing frames lean back a little
        for o in objs: o.matrix_world = Matrix.Rotation(tilt, 4, "X") @ o.matrix_world
    place(objs, loc, rz); bpy.context.view_layer.update()
    return objs

photos = [os.path.join(L_DIR, f"photo_{k}.jpg") for k in range(1, 8)]   # public-domain / CC0 family snapshots, heavily blurred (labels/PHOTO_CREDITS.md)

# Jamie's panoramic canvas above the sofa (on the recess back wall, facing into the room)
pano_img = os.path.join(L_DIR, "panorama_monument_valley.jpg")
CW, CH, CD = 1.85, 0.5, 0.035
canvas_edge = flat("Canvas_edge", (0.25, 0.12, 0.06), 0.8)
cv = [box("Pano_canvas_body", (CW, CD, CH), (0, -CD / 2, 0), canvas_edge)]
me = bpy.data.meshes.new("Pano_canvas_face")
me.from_pydata([(-CW / 2, -CD - 0.0005, -CH / 2), (CW / 2, -CD - 0.0005, -CH / 2), (CW / 2, -CD - 0.0005, CH / 2), (-CW / 2, -CD - 0.0005, CH / 2)], [], [(0, 1, 2, 3)])
uvl = me.uv_layers.new()
for li, (u, v) in zip(range(4), ((0, 0), (1, 0), (1, 1), (0, 1))): uvl.data[li].uv = (u, v)
me.materials.append(img_mat("Pano_canvas_print", pano_img, 0.7))
cf = bpy.data.objects.new("Pano_canvas_face", me); coll.objects.link(cf); cv.append(cf)
bpy.context.view_layer.update()
place(cv, (-2.05, Y0 - SOFA_D, 1.42), math.pi)

# wall-mounted TV opposite the sofa (north wall, west of Glenda's alcove), console on a floating shelf
TVX = -2.05
tv_glass = flat("TV_screen", (0.005, 0.005, 0.006), 0.04, coat=1.0)
tv_body = flat("TV_body", (0.02, 0.02, 0.022), 0.35, 0.5)
tv = [box("TV_body", (1.24, 0.03, 0.72), (0, -0.045, 0), tv_body),
      box("TV_screen", (1.22, 0.004, 0.69), (0, -0.0615, 0.01), tv_glass),
      box("TV_bracket", (0.3, 0.03, 0.2), (0, -0.015, 0), tv_body)]
place(tv, (TVX, Y1, 1.28), 0.0)
shelf_m = bpy.data.materials.get("Modern_oak")
box("Media_shelf", (1.3, 0.3, 0.04), (TVX, Y1 - 0.15, 0.48), shelf_m)
pc = gltf("gaming_console", (TVX - 0.3, Y1 - 0.15), rot_z=0.0, fit_w=0.32, z=0.50)
box("Console_cable", (0.006, 0.006, 0.75), (TVX - 0.05, Y1 - 0.004, 0.86), tv_body)        # neat cable run up to the TV

# family photos: a gallery on the north wall east of the alcove, plus standing frames on the sideboard and side table
GX = 2.2
picture("Gallery_1", photos[0], 0.24, 0.30, (GX - 0.5, Y1, 1.45), 0.0)
picture("Gallery_2", photos[1], 0.39, 0.26, (GX + 0.02, Y1, 1.55), 0.0)
picture("Gallery_3", photos[2], 0.24, 0.30, (GX + 0.54, Y1, 1.45), 0.0)
picture("Gallery_4", photos[3], 0.33, 0.22, (GX + 0.02, Y1, 1.13), 0.0)
picture("Desk_photo_1", photos[4], 0.13, 0.13, (wx + 0.3, -1.6, sbt + 0.11), math.pi / 2, frame=0.012, mount=0.02, depth=0.015, tilt=math.radians(-10),
        frame_m=bpy.data.materials.get("Modern_oak"))
picture("Desk_photo_2", photos[5], 0.15, 0.10, (wx + 0.3, -0.85, sbt + 0.09), math.pi / 2 - 0.25, frame=0.012, mount=0.02, depth=0.015, tilt=math.radians(-10))
picture("Side_photo", photos[6], 0.10, 0.13, (0.95, ay + 0.3, top_of(st) + 0.1), 0.15, frame=0.012, mount=0.018, depth=0.015, tilt=math.radians(-10))

win.scene = prev_scene
print("ModernFurnished built:", len(coll.all_objects), "furniture/kitchen objects; render ->", OUT)
