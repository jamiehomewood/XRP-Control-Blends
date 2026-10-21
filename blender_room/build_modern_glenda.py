"""
MODERN - GLENDA'S THINGS: the modern flat (same walls, recesses, fitted kitchen, blinds, radiator, garden) furnished
with Glenda's own dated belongings, as if she has moved her old furniture into a refurbished 2026 flat.

Deep pieces stand in the recesses so they stay off the projected floor; only flat things (rug, towel) are on the
floor; her clutter (dog basket and bowls, pad deliveries, bin bags) is beyond the real walls in the kitchen and hall.

  Glenda's alcove     her old chintz sofa (where she will sit), walking stick, towel at her feet, Jamie's panorama above
  Beside the alcove   her side table: tablets, Gaviscon, Rennie, glasses, table lamp
  South-west recess   her CRT telly on a wooden stand, facing the sofa, and the wingback chair
  West recess         the tall dark dresser with a mantel clock and tea set
  North wall          worn bookshelf with encyclopaedias, newspaper piles, wall clock; the family photo gallery
  Kitchen             older cream shaker-style units; her kettle, microwave, bananas, tablets, fridge note; Dizzy's basket
  Hall                incontinence-pad delivery boxes and bin bags waiting to go out

Run inside Glenda_Room.blend. Builds the scene "ModernGlenda" and renders room_pano_modern_glenda.jpg.
"""
import bpy, math, os, random
from mathutils import Vector, Matrix

ROOT = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else r"D:\Projects\01_Active\Nursing XRP Scenario 001\blender_room"
L_DIR = os.path.join(ROOT, "labels")
OUT = os.path.join(os.path.dirname(ROOT), "spout-test", "assets", "room_pano_modern_glenda.jpg")
random.seed(7)

# 1. shell + fitted kitchen, without the modern living-room furniture
fp = os.path.join(ROOT, "build_modern_furnished.py")
g = {"__file__": fp, "__name__": "__main__", "FURN_SCENE": "ModernGlenda", "FURN_SHELL_COLL": "ModernGlendaShell",
     "FURN_COLL": "ModernGlendaThings", "FURN_LIVING": False, "FURN_KITCHEN": "traditional", "FURN_OUT": OUT,
     # a wider alcove (sofa + side table both inside it) and a bookshelf recess, so nothing deep stands out on the floor
     "FURN_SHELL_EXTRA": {"GLENDA_X_OVERRIDE": (-1.3, 2.0), "BOOK_RECESS": (-2.95, -1.75, 0.40),
                          "GARDEN_PHOTO": "garden_backdrop.jpg"}}
exec(compile(open(fp, encoding="utf-8").read(), fp, "exec"), g)
gltf, snap, bounds, top_of, box, cyl, flat, link, picture, pano_canvas, PHOTOS = (g[k] for k in ("gltf", "snap", "bounds", "top_of", "box", "cyl", "flat", "link", "picture", "pano_canvas", "PHOTOS"))
SH = g["g"]                                                   # the shell script's names (WIN_SILL, WALL_T, ...)
X0, X1, Y0, Y1, RH = g["X0"], g["X1"], g["Y0"], g["Y1"], g["RH"]
KX0, KX1, KY0, KY1 = g["KX0"], g["KX1"], g["KY0"], g["KY1"]
GLENDA_D, DRESSER_D, DRESSER_Y, SOFA_D = g["GLENDA_D"], g["DRESSER_D"], g["DRESSER_Y"], g["SOFA_D"]
H_BASE, T_TOP, D = g["H_BASE"], g["T_TOP"], g["D"]
sc = bpy.data.scenes["ModernGlenda"]
win = bpy.context.window_manager.windows[0]; prev = win.scene; win.scene = sc

def surface_z(x, y, z_from=2.2):
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, n, i, ob, m = sc.ray_cast(dg, Vector((x, y, z_from)), Vector((0, 0, -1)))
    return loc.z if hit else 0.0

def img_mat(name, path, rough=0.5):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial"); b = nt.nodes.new("ShaderNodeBsdfPrincipled"); nt.links.new(b.outputs[0], out.inputs[0])
    t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(path, check_existing=True)
    nt.links.new(t.outputs[0], b.inputs["Base Color"]); b.inputs["Roughness"].default_value = rough
    return m

def label_box(name, size, loc, img, rz=0.0):
    o = box(name, size, loc, img_mat("GL_" + img, os.path.join(L_DIR, img)), rz)
    return o

def quad(name, pts, m, uv=((0, 0), (1, 0), (1, 1), (0, 1))):
    me = bpy.data.meshes.new(name); me.from_pydata(pts, [], [(0, 1, 2, 3)]); uvl = me.uv_layers.new()
    for li in range(4): uvl.data[li].uv = uv[li]
    me.materials.append(m); o = bpy.data.objects.new(name, me); return link(o)

# ======================================================================== Glenda's alcove: her sofa (she will sit here)
ay0, ay1 = Y1, Y1 + GLENDA_D
sofa = snap(gltf("sofa_03", (0.0, ay0 + 0.45), rot_z=0.0, scale=0.8), 1, +1, ay1 - 0.03)
smn, smx = bounds(sofa)
# her orange throw cushions on the seat, one at each end, in front of the sofa's own cushions.
# Each cushion is settled on its own: rays down over its footprint (cushions hidden) find the highest point under it,
# so neither cushion of a pair sinks into the seat or the sofa arm.
def settle(root):
    meshes = [o for o in root.children_recursive if o.type == "MESH"]
    for o in meshes: o.hide_viewport = True
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    hits = {}
    for o in meshes:
        pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
        x0, x1 = min(p.x for p in pts), max(p.x for p in pts); y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
        zs = []
        for fx in (0.15, 0.5, 0.85):
            for fy in (0.2, 0.5, 0.8):
                h = sc.ray_cast(dg, Vector((x0 + (x1 - x0) * fx, y0 + (y1 - y0) * fy, 1.0)), Vector((0, 0, -1)))
                if h[0]: zs.append(h[1].z)
        hits[o] = (max(zs) if zs else None, min(p.z for p in pts))
    for o in meshes: o.hide_viewport = False
    for o, (top, bottom) in hits.items():
        if top is not None: o.matrix_world = Matrix.Translation((0, 0, top - 0.015 - bottom)) @ o.matrix_world
    bpy.context.view_layer.update()
    # the model is a pair; the back one ends up perched on the sofa's own cushions, so keep only the one on the seat
    low = min(hits, key=lambda o: min((o.matrix_world @ Vector(c)).z for c in o.bound_box))
    for o in meshes:
        if o is not low: bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
for px_, rz_ in ((smn.x + 0.5, 0.2), (smx.x - 0.5, -0.15)):
    settle(gltf("throw_pillows_01", (px_, smx.y - 0.56), rot_z=rz_, scale=0.6, z=0.45))
pano_canvas(0.0, ay1, 1.45, 0.0)                             # Jamie's panorama on the alcove's back wall, above her
# walking stick in the gap between the sofa's left arm and the alcove wall, leaning on the wall (clear of the arm);
# towel on the floor where her feet will be (flat, fine on the real floor)
SB = Vector(((smn.x + SH["GLENDA_X"][0]) / 2 + 0.03, smn.y + 0.2, 0.0))
TILT = -math.asin(min(0.3, (SB.x - SH["GLENDA_X"][0] - 0.012) / 0.88)); SD = Vector((math.sin(TILT), 0, math.cos(TILT)))
stick_m = flat("GL_stick", (0.18, 0.11, 0.06), 0.4)
cyl("GL_stick", 0.011, 0.88, SB + SD * 0.44, stick_m, rot=(0, TILT, 0), verts=12)
top = SB + SD * 0.88
cyl("GL_stick_handle", 0.014, 0.13, (top.x + 0.01, top.y - 0.05, top.z + 0.012), stick_m, rot=(math.radians(80), 0, 0))
box("GL_towel", (0.72, 0.48, 0.012), (0.0, smn.y - 0.22, 0.006), flat("GL_towel", (0.78, 0.76, 0.7), 0.95), 0.08)

# her side table inside the (widened) alcove, beside the sofa: tablets, Gaviscon, Rennie, glasses, lamp
TX = 1.55
side = snap(gltf("side_table_01", (TX, ay0 + 0.5)), 1, +1, ay1 - 0.04)
ST = top_of(side); tmn, tmx = bounds(side); ty = (tmn.y + tmx.y) / 2
gltf("round_spectacles", (TX - 0.12, ty - 0.1), rot_z=0.4, fit_w=0.14, z=ST)
for i in range(7):
    label_box(f"GL_med_side_{i}", (0.135, 0.075, 0.05), (TX + 0.05 + (i % 2) * 0.1, ty + ((i * 37) % 5 - 2) * 0.012, ST + 0.025 + (i // 2) * 0.05),
              f"med_{i % 6}.png", (i * 0.7) % 0.6 - 0.3)
cyl("GL_gaviscon", 0.035, 0.19, (TX + 0.2, ty - 0.12, ST + 0.095), img_mat("GL_gav", os.path.join(L_DIR, "gaviscon.png"), 0.35))
cyl("GL_gaviscon_cap", 0.02, 0.03, (TX + 0.2, ty - 0.12, ST + 0.205), flat("GL_cap_green", (0.1, 0.45, 0.2), 0.4))
label_box("GL_rennie", (0.1, 0.06, 0.03), (TX - 0.05, ty - 0.14, ST + 0.015), "rennie.png", 0.5)
cyl("GL_lamp_base", 0.06, 0.28, (TX - 0.16, ty + 0.08, ST + 0.14), flat("GL_lamp_ceramic", (0.55, 0.42, 0.3), 0.25))
bpy.ops.mesh.primitive_cone_add(radius1=0.17, radius2=0.11, depth=0.2, vertices=40, end_fill_type="NOTHING", location=(TX - 0.16, ty + 0.08, ST + 0.38))
sh = bpy.context.active_object; sh.name = "GL_lamp_shade"
sh.data.materials.append(flat("GL_lamp_shade", (0.9, 0.82, 0.62), 0.9, emit=(1.0, 0.75, 0.45), strength=2.0)); link(sh)
bpy.ops.object.light_add(type="POINT", location=(TX - 0.16, ty + 0.08, ST + 0.36)); lp = bpy.context.active_object
lp.name = "GL_lamp_bulb"; lp.data.energy = 25; lp.data.color = (1.0, 0.72, 0.42); lp.data.shadow_soft_size = 0.05; link(lp)

# her old rug, flat in front of the alcove
rug_m = bpy.data.materials.get("Rug") or flat("GL_rug", (0.4, 0.15, 0.12), 0.95)
quad("GL_rug", [(-1.15, 0.7, 0.004), (1.4, 0.7, 0.004), (1.4, 2.6, 0.004), (-1.15, 2.6, 0.004)], rug_m,
     uv=((0, 0), (2.55, 0), (2.55, 1.9), (0, 1.9)))
box("GL_rug_edge", (2.63, 1.98, 0.003), (0.125, 1.65, 0.0015), flat("GL_rug_edge", (0.22, 0.07, 0.06), 0.95))

# ======================================================================== south-west recess: the CRT telly facing her sofa, and the wingback
sw_y = Y0 - SOFA_D
stand = snap(gltf("ClassicNightstand_01", (-1.55, sw_y + 0.3), rot_z=math.pi, fit_w=0.75), 1, -1, sw_y + 0.03)
nmn, nmx = bounds(stand)
gltf("television_02", ((nmn.x + nmx.x) / 2, (nmn.y + nmx.y) / 2 + 0.02), rot_z=math.pi - 0.25, scale=1.25, z=top_of(stand))   # turned to face the sofa
wing = snap(gltf("ArmChair_01", (-2.55, sw_y + 0.5), rot_z=math.pi - 0.45), 1, -1, sw_y + 0.03)

# ======================================================================== west recess: the tall dresser with her ornaments
wx = X0 - DRESSER_D
dresser = snap(gltf("vintage_cabinet_01", (wx + 0.3, (DRESSER_Y[0] + DRESSER_Y[1]) / 2), rot_z=math.pi / 2, fit_h=1.8), 0, -1, wx + 0.02)
dmn, dmx = bounds(dresser)
dtop = surface_z(dmn.x + 0.4 * (dmx.x - dmn.x) + 0.12, (dmn.y + dmx.y) / 2, 1.2)
dcy = (dmn.y + dmx.y) / 2
gltf("mantel_clock_01", (dmn.x + 0.32, dcy), rot_z=math.pi / 2, fit_h=0.26, z=dtop)
gltf("tea_set_01", (dmn.x + 0.34, dcy - 0.45), rot_z=math.pi / 2 + 0.3, fit_w=0.35, z=dtop)
gltf("standing_picture_frame_01", (dmn.x + 0.3, dcy + 0.45), rot_z=math.pi / 2 - 0.3, fit_h=0.2, z=dtop)

# family photo gallery (blurred stand-ins) on the north wall, east of the side table
GX = 2.6                                                      # on the 1.2 m of flat wall east of the widened alcove
picture("GL_gallery_1", PHOTOS[0], 0.19, 0.24, (GX - 0.406, Y1, 1.5), 0.0)
picture("GL_gallery_2", PHOTOS[1], 0.31, 0.21, (GX, Y1, 1.6), 0.0)
picture("GL_gallery_3", PHOTOS[2], 0.19, 0.24, (GX + 0.406, Y1, 1.5), 0.0)
picture("GL_gallery_4", PHOTOS[3], 0.26, 0.18, (GX, Y1, 1.27), 0.0)

# ======================================================================== bookshelf recess (north wall, west of the alcove): shelf, papers, clock
BR = (-2.95, -1.75, 0.40)
shelf = snap(gltf("wooden_bookshelf_worn", ((BR[0] + BR[1]) / 2 - 0.12, Y1 + 0.2), rot_z=0.0, fit_h=1.2), 1, +1, Y1 + BR[2] - 0.02)
bmn, bmx = bounds(shelf)
SHELF = surface_z((bmn.x + bmx.x) / 2, (bmn.y + bmx.y) / 2, 0.75)
gltf("book_encyclopedia_set_01", ((bmn.x + bmx.x) / 2, (bmn.y + bmx.y) / 2), z=SHELF + 0.002, fit_w=0.5)
news = img_mat("GL_news", os.path.join(L_DIR, "newspaper.png"), 0.9)
piles = [((BR[1] - 0.17, Y1 + BR[2] - 0.22), 10, math.pi / 2)]            # beside the shelf, inside the recess
hy1_ = Y0 - SH["WALL_T"]
piles += [((-0.35, hy1_ - 0.3), 14, 0.0), ((2.55, hy1_ - 0.3), 9, 0.0)]  # more in the hall
for (x, y), n, base in piles:
    for i in range(n):
        box(f"GL_news_{x:.2f}_{i}", (0.42, 0.3, 0.025), (x + random.uniform(-0.02, 0.02), y + random.uniform(-0.015, 0.015), 0.0125 + i * 0.025), news,
            base + random.uniform(-0.15, 0.15))
gltf("wall_clock", ((BR[0] + BR[1]) / 2, Y1 + BR[2] - 0.03), z=1.75)                 # above the bookshelf
gltf("potted_plant_02", (X0 + 0.07, 0.85), fit_h=0.32, z=SH["WIN_SILL"])

# ======================================================================== kitchen (beyond the real wall): her things on the fitted units
wtz = H_BASE + T_TOP
gltf("vintage_electric_kettle", (KX1 - 0.3, -0.25), rot_z=-math.pi / 2, scale=0.75, z=wtz)
gltf("vintage_microwave", (KX1 - 0.32, 1.3), rot_z=-math.pi / 2, fit_w=0.5, z=wtz)
gltf("bananas", (KX1 - 0.35, 0.75), rot_z=0.6, z=wtz)
for i in range(6):
    label_box(f"GL_med_kitchen_{i}", (0.14, 0.08, 0.05), (KX1 - 0.45 + (i % 3) * 0.02, -1.2 + (i % 3) * 0.09, wtz + 0.025 + (i // 3) * 0.05),
              f"med_{i}.png", random.uniform(-0.3, 0.3))
quad("GL_fridge_note", [(KX1 - 0.6 - 0.032, KY1 - 0.55, 1.3), (KX1 - 0.6 - 0.032, KY1 - 0.25, 1.3), (KX1 - 0.6 - 0.032, KY1 - 0.25, 1.62), (KX1 - 0.6 - 0.032, KY1 - 0.55, 1.62)],
     img_mat("GL_fridge_note", os.path.join(L_DIR, "fridge_note.png"), 0.8))
# Dizzy's basket and bowls on the kitchen floor
gltf("wicker_basket_01", (KX0 + 0.55, KY0 + 0.5), rot_z=0.3, scale=1.9)
gltf("throw_pillows_01", (KX0 + 0.55, KY0 + 0.5), rot_z=0.3 + math.pi / 2, fit_w=0.62, z=0.035).scale.z *= 0.45
bowl_red = flat("GL_bowl_red", (0.55, 0.1, 0.08), 0.35); steel = flat("GL_bowl_steel", (0.75, 0.75, 0.75), 0.22, 1.0)
for nm_, (x, y), m_ in (("food", (KX0 + 0.5, 1.4), bowl_red), ("water", (KX0 + 0.75, 1.5), steel)):
    cyl(f"GL_bowl_{nm_}", 0.1, 0.06, (x, y, 0.03), m_)
kib = flat("GL_kibble", (0.32, 0.18, 0.08), 0.7)
for k in range(20):
    a_, r_ = random.uniform(0, 6.28), random.uniform(0, 0.06)
    cyl(f"GL_kibble_{k}", 0.009, 0.012, (KX0 + 0.5 + r_ * math.cos(a_), 1.4 + r_ * math.sin(a_), 0.065), kib, verts=8)

# ======================================================================== hall (beyond the open door): deliveries and bin bags
hy1 = Y0 - SH["WALL_T"]
card = flat("GL_cardboard", (0.55, 0.42, 0.26), 0.85)
for k, (x, z, rz) in enumerate(((1.95, 0.0, 0.05), (1.97, 0.35, -0.08), (2.0, 0.70, 0.1))):
    b_ = box(f"GL_pads_box_{k}", (0.6, 0.4, 0.35), (x, hy1 - 0.3, z + 0.175), card, rz)
    label_box(f"GL_pads_label_{k}", (0.3, 0.004, 0.2), (x, hy1 - 0.098, z + 0.175), "pad_label.png", rz)
for k, (x, y, s_) in enumerate(((-0.2, hy1 - 0.35, 0.85), (0.05, hy1 - 0.3, 0.7), (-0.1, hy1 - 0.4, 0.6))):
    gltf("trashbag", (x, y), rot_z=k * 1.7, scale=s_, z=0.0 if k < 2 else 0.3)

win.scene = prev
print("ModernGlenda built ->", OUT)
