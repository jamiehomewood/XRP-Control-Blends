# Run inside Blender with Characters/Glenda_seated.blend loaded (also stored there as a text block).

import bpy, json
from mathutils import Vector, Quaternion, Matrix
g0 = {}; exec(bpy.data.texts["glenda_contact.py"].as_string(), g0)
rig, pb, body, tro, sc, TP, MASKS = g0["rig"], g0["pb"], g0["body"], g0["tro"], g0["sc"], g0["TP"], g0["MASKS"]
HAND, PALM = g0["HAND"], g0["PALM"]
FING = {s: g0["vg"](s, ("finger",), 2) for s in "LR"}
def measure2(side):
    dg = bpy.context.evaluated_depsgraph_get()
    be = body.evaluated_get(dg); me = be.to_mesh()
    te = tro.evaluated_get(dg); inv = te.matrix_world.inverted()
    def up(i):
        p = be.matrix_world @ me.vertices[i].co
        ok, loc, nrm, fi = te.ray_cast(inv @ p, Vector((0, 0, 1)), depsgraph=dg)
        if ok and fi in TP and nrm.z > 0.2:
            d = (te.matrix_world @ loc - p).z
            if d < 0.25: return d
        return 0.0
    def down(i):
        p = be.matrix_world @ me.vertices[i].co
        ok, loc, nrm, fi = te.ray_cast(inv @ p, Vector((0, 0, -1)), depsgraph=dg)
        if ok and fi in TP and nrm.z > 0.2: return (p - te.matrix_world @ loc).z
        return None
    pen = max([up(i) for i in HAND[side]] + [0])
    gaps = [x for x in (down(i) for i in PALM[side]) if x is not None]
    be.to_mesh_clear()
    if not gaps: return pen, 1.0, 1.0
    gaps.sort()
    return pen, gaps[0], sum(gaps[:max(1, len(gaps)//3)]) / max(1, len(gaps)//3)
CHAIN = ["upperarm01", "upperarm02", "lowerarm01", "lowerarm02"]
TGT = g0["TGT"]
def pose_hand(side, target, wrot):
    """IK the arm so the wrist is at target, then give the wrist the pose-space rotation wrot."""
    TGT.location = target
    c = pb[f"lowerarm02.{side}"].constraints.new("IK"); c.target = TGT; c.chain_count = 4
    bpy.context.view_layer.update()
    mats = {bn: pb[f"{bn}.{side}"].matrix.copy() for bn in CHAIN}
    pb[f"lowerarm02.{side}"].constraints.remove(c)
    for bn in CHAIN: pb[f"{bn}.{side}"].matrix = mats[bn]; bpy.context.view_layer.update()
    wb = pb[f"wrist.{side}"]
    wb.matrix = Matrix.LocRotScale(wb.matrix.to_translation(), wrot, Vector((1, 1, 1))); bpy.context.view_layer.update()
