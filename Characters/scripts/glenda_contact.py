# Run inside Blender with Characters/Glenda_seated.blend loaded (also stored there as a text block).

import bpy, json, math
from mathutils import Vector, Quaternion, Matrix
rig = bpy.data.objects["Glenda.rig.001"]; pb = rig.pose.bones
body = bpy.data.objects["Glenda.001"]; tro = bpy.data.objects["Glenda.male_casualsuit02"]
sc = bpy.data.scenes["GlendaChar"]
uvl = tro.data.uv_layers.active.data
TP = set()
for p in tro.data.polygons:
    u = sum(uvl[i].uv.x for i in p.loop_indices) / p.loop_total; v = sum(uvl[i].uv.y for i in p.loop_indices) / p.loop_total
    if v < 0.58 and u < 0.71: TP.add(p.index)
MASKS = [m for m in body.modifiers if m.type == "MASK"]
def vg(side, keys, step):
    gi = {g.index for g in body.vertex_groups if g.name.endswith("." + side) and any(k in g.name for k in keys)}
    return [v.index for v in body.data.vertices if any(g.group in gi and g.weight > 0.4 for g in v.groups)][::step]
HAND = {s: vg(s, ("metacarpal", "finger", "wrist"), 2) for s in "LR"}
PALM = {s: vg(s, ("metacarpal",), 2) for s in "LR"}
CHAIN = ["upperarm01", "upperarm02", "lowerarm01", "lowerarm02"]
KEYED = CHAIN + ["wrist"]
TGT = bpy.data.objects.get("IKT_bake") or bpy.data.objects.new("IKT_bake", None)
if TGT.name not in sc.collection.objects: sc.collection.objects.link(TGT)
def measure(side):
    """(how deep any part of the hand is inside the trousers, palm's distance above them)"""
    dg = bpy.context.evaluated_depsgraph_get()
    be = body.evaluated_get(dg); me = be.to_mesh()
    te = tro.evaluated_get(dg); inv = te.matrix_world.inverted(); nm = te.matrix_world.to_3x3()
    def sd(i):
        p = be.matrix_world @ me.vertices[i].co
        ok, loc, nrm, fi = te.closest_point_on_mesh(inv @ p, depsgraph=dg)
        if not ok or fi not in TP: return None
        return (p - te.matrix_world @ loc).dot((nm @ nrm).normalized())
    pen = max([-d for d in (sd(i) for i in HAND[side]) if d is not None] + [0.0])
    pg = sorted(d for d in (sd(i) for i in PALM[side]) if d is not None)
    be.to_mesh_clear()
    k = max(1, len(pg) // 3)
    return pen, (sum(pg[:k]) / k if pg else 1.0)
def fc_map(act):
    m = {}
    for L in act.layers:
        for s in L.strips:
            for cb in s.channelbags:
                for c in cb.fcurves: m[(c.data_path.split('"')[1], c.array_index)] = c
    return m
def ik_to(side, target):
    TGT.location = target
    c = pb[f"lowerarm02.{side}"].constraints.new("IK"); c.target = TGT; c.chain_count = 4
    bpy.context.view_layer.update()
    q = {bn: rig.convert_space(pose_bone=pb[f"{bn}.{side}"], matrix=pb[f"{bn}.{side}"].matrix, from_space="POSE", to_space="LOCAL").to_quaternion() for bn in CHAIN}
    wb = pb[f"wrist.{side}"]
    want = Matrix.LocRotScale(wb.matrix.to_translation(), BASE_WR[side], Vector((1, 1, 1)))
    qw = rig.convert_space(pose_bone=wb, matrix=want, from_space="POSE", to_space="LOCAL").to_quaternion()
    # never bend the wrist more than MAX_WRIST away from its resting bend (more than that tears the hand off the sleeve)
    rest = BASE_WL[side]; d = rest.rotation_difference(qw)
    if d.angle > MAX_WRIST: qw = rest.slerp(qw, MAX_WRIST / d.angle)
    q["wrist"] = qw
    pb[f"lowerarm02.{side}"].constraints.remove(c)
    return q
def write(F, f0, f, side, q):
    for bn, qq in q.items():
        k = f - f0
        prevq = Quaternion([F[(f"{bn}.{side}", ax)].keyframe_points[max(0, k - 1)].co.y for ax in range(4)])
        if k > 0 and qq.dot(prevq) < 0: qq = -qq
        for ax in range(4): F[(f"{bn}.{side}", ax)].keyframe_points[k].co.y = qq[ax]
    for bn in q:
        for ax in range(4): F[(f"{bn}.{side}", ax)].update()
BASE_WR = {s: Quaternion(v) for s, v in json.loads(rig.get("base_wrist_rot", "{}")).items()}
MAX_WRIST = 0.35
BASE_WL = {s: Quaternion(v) for s, v in json.loads(rig.get("base_wrist_local", "{}")).items()}
BASE_PEN = {k: v for k, v in json.loads(rig.get("base_contact", "{}")).items()}
BASE_W = {s: Vector(v) for s, v in json.loads(rig.get("base_wrist", "{}")).items()}
def contact(clip, fa, fb, reach=0.03):
    act = bpy.data.actions[clip]; rig.animation_data.action = act; F = fc_map(act)
    f0 = int(act.frame_range[0]); stats = [0, 0]
    for m in MASKS: m.show_viewport = False
    try:
        for f in range(fa, fb + 1):
            sc.frame_set(f)
            for side in "LR":
                w = rig.matrix_world @ pb[f"wrist.{side}"].head
                off = Vector((w.x, w.y, 0)) - Vector((BASE_W[side].x, BASE_W[side].y, 0))
                if off.length > reach: off *= reach / off.length
                tgt = Vector((BASE_W[side].x + off.x, BASE_W[side].y + off.y, w.z))
                LIM = BASE_PEN.get(side, 0.0) + 0.002     # sink no deeper than the resting pose does
                def at(z):
                    tgt.z = z; write(F, f0, f, side, ik_to(side, tgt)); sc.frame_set(f); return measure(side)
                pen, gap = at(tgt.z)
                if pen > LIM:
                    lo, hi = tgt.z, tgt.z + 0.06
                else:
                    lo, hi = tgt.z - max(gap, 0.01) - 0.01, tgt.z
                for it in range(7):
                    mid = (lo + hi) / 2; pm, gm = at(mid)
                    if pm > LIM: lo = mid
                    else: hi = mid
                pen, gap = at(hi)
                stats[0 if (pen <= LIM + 0.001 and gap <= 0.02) else 1] += 1
    finally:
        for m in MASKS: m.show_viewport = True
    return stats
