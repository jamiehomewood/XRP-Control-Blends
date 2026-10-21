# Run inside Blender with Characters/Glenda_seated.blend loaded (also stored there as a text block).

import bpy, json
from mathutils import Quaternion
rig = bpy.data.objects["Glenda.rig.001"]
base = {k: Quaternion(v) for k, v in json.loads(rig["seated_base"]).items()}
def _fcs(a):
    out = []
    for L in a.layers:
        for s in L.strips:
            for cb in s.channelbags: out += list(cb.fcurves)
    return out
def _qc(a):
    d = {}
    for c in _fcs(a):
        if c.data_path.endswith("rotation_quaternion"): d.setdefault(c.data_path.split('"')[1], [None]*4)[c.array_index] = c
    return d
def _q(curves, bn, f):
    c = curves.get(bn)
    if not c or None in c: return Quaternion()
    return Quaternion([x.evaluate(f) for x in c]).normalized()
REF = {bn: _q(_qc(bpy.data.actions["OLD_Idle"]), bn, 1) for bn in base}
# how much of each clip's motion is layered onto the seated pose. Legs and hands stay as posed; the arms only
# a little (the hands are then pinned to her thighs by the contact pass); the upper body, neck and head fully.
def weight(bn):
    if bn.startswith(("spine", "neck", "head", "breast")): return 1.0
    if bn.startswith(("clavicle", "shoulder")): return 0.6
    if bn.startswith(("upperarm", "lowerarm")): return 0.3
    return 0.0
def bake(clip):
    src = bpy.data.actions["OLD_" + clip]; cur = _qc(src)
    f0, f1 = int(src.frame_range[0]), int(src.frame_range[1]); frames = list(range(f0, f1 + 1))
    old = bpy.data.actions.get(clip)
    if old: bpy.data.actions.remove(old)
    act = bpy.data.actions.new(clip); act.use_fake_user = True
    rig.animation_data_create(); rig.animation_data.action = act
    for bn in base:
        w = weight(bn); vals = []
        anim = w > 0 or bn.startswith(("upperarm", "lowerarm", "wrist"))     # the arm chain gets a key every frame for the contact pass
        for f in (frames if anim else [f0, f1]):
            q = base[bn]
            if w > 0:
                d = REF[bn].inverted() @ _q(cur, bn, f)
                if bn.startswith(("spine", "neck")):          # keep her upright: no sideways lean, half the twist
                    d = Quaternion((d.w, d.x, d.y * 0.5, 0.0)).normalized()
                if w < 1: d = Quaternion().slerp(d, w)
                q = base[bn] @ d
            if vals and q.dot(vals[-1][1]) < 0: q = -q
            vals.append((f, q))
        for ax in range(4):
            fc = act.fcurve_ensure_for_datablock(rig, f'pose.bones["{bn}"].rotation_quaternion', index=ax)
            fc.keyframe_points.add(len(vals)); co = []
            for f, q in vals: co += [f, q[ax]]
            fc.keyframe_points.foreach_set("co", co)
            for k in fc.keyframe_points: k.interpolation = "LINEAR"
            fc.update()
    return act
