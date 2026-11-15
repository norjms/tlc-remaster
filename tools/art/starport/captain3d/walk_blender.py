"""Headless Blender: import the generated captain, auto-rig it, key a walk cycle, render a side-view sprite strip.
blender -b -P walk_blender.py -- <in.glb> <out_dir> <mode: views|walk> [frames=16] [res=948]"""
import bpy, sys, math, os
import numpy as np
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
GLB, OUT, MODE = argv[0], argv[1], argv[2]
NF = int(argv[3]) if len(argv) > 3 else 16
RES = int(argv[4]) if len(argv) > 4 else 948
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in bpy.context.scene.objects: o.select_set(False)
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
if len(meshes) > 1: bpy.ops.object.join()
body = bpy.context.view_layer.objects.active
bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in list(bpy.context.scene.objects):
    if o.type == 'EMPTY': bpy.data.objects.remove(o)

V = np.array([v.co[:] for v in body.data.vertices])
# normalise: height 1.8 m, feet at z 0, centred on x/y
lo, hi = V.min(0), V.max(0)
s = 1.8 / (hi[2] - lo[2])
c = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
body.data.transform(Matrix.Diagonal((s, s, s, 1)) @ Matrix.Translation(Vector(-c)))
"""Inserted into walk_blender.py after normalisation: remove a backpack (geometry behind the torso) and close the back.
Character faces -Y, so the back is +Y."""
import bmesh
def cut_pack(body, H, margin=0.03):
    me = body.data
    bm = bmesh.new(); bm.from_mesh(me)
    uvl = bm.loops.layers.uv.active
    vs = np.array([v.co[:] for v in bm.verts])
    waist = vs[(vs[:, 2] > 0.44 * H) & (vs[:, 2] < 0.50 * H) & (np.abs(vs[:, 0]) < 0.15)]
    yb = np.percentile(waist[:, 1], 97) + margin
    print('pack cut at y >', yb)
    global PACK_Y; PACK_Y = yb - margin
    # a UV on the back of the waist, to texture the new back panel
    best = None
    for f in bm.faces:
        c = f.calc_center_median()
        if 0.46 * H < c.z < 0.50 * H and abs(c.x) < 0.06 and c.y > yb - margin - 0.03 and f.normal.y > 0.5:
            best = f; break
    uv0 = best.loops[0][uvl].uv.copy() if (best is not None and uvl) else None
    kill = [v for v in bm.verts if v.co.y > yb and 0.50 * H < v.co.z < 0.92 * H and abs(v.co.x) < 0.36]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    edges = [e for e in bm.edges if e.is_boundary]
    before = set(bm.faces)
    bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    new = [f for f in bm.faces if f not in before]
    if new:
        bmesh.ops.triangulate(bm, faces=new)
        new = [f for f in bm.faces if f not in before]
        for f in new:
            f.normal_update()
            if uv0 is not None:
                for l in f.loops: l[uvl].uv = uv0
    print('pack verts removed', len(kill), 'faces added', len(new))
    bm.normal_update(); bm.to_mesh(me); bm.free(); me.update()


def cut_floaters(body, H, frac=0.04):
    """Remove disconnected mesh islands smaller than frac of the vertices, and anything well in front of the chest."""
    me = body.data
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    seen = set(); islands = []
    for v in bm.verts:
        if v.index in seen: continue
        st = [v]; comp = []; seen.add(v.index)
        while st:
            x = st.pop(); comp.append(x)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen: seen.add(o.index); st.append(o)
        islands.append(comp)
    n = len(bm.verts); kill = []
    vs = np.array([v.co[:] for v in bm.verts])
    belly = vs[(vs[:, 2] > 0.52 * H) & (vs[:, 2] < 0.56 * H) & (np.abs(vs[:, 0]) < 0.12)]
    yf = np.percentile(belly[:, 1], 3) - float(os.environ.get('FRONT_MARGIN', '0.05'))
    ks = set(kill)
    kill += [v for v in bm.verts if v not in ks and v.co.y < yf and 0.55 * H < v.co.z < 0.86 * H and abs(v.co.x) < 0.2]
    print('islands', sorted(len(c) for c in islands)[-6:], 'front cut y <', yf, 'removed', len(kill))
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(me); bm.free(); me.update()

PACK_Y = None
def add_pack(body, back_y, H):
    """Model an EMU-style life support pack (tall rounded box + secondary oxygen pack under it) and join it to the body,
    weighted fully to the spine so it rides with the torso. Character faces -Y; the back is +Y."""
    import bmesh
    mat = bpy.data.materials.new('pack_fabric'); mat.use_nodes = True
    nt = mat.node_tree; bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = (0.80, 0.79, 0.76, 1)
    bsdf.inputs['Roughness'].default_value = 0.85
    tex = nt.nodes.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = 60.0
    bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.08
    nt.links.new(tex.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    dark = bpy.data.materials.new('pack_trim'); dark.use_nodes = True
    dark.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.32, 0.32, 0.33, 1)
    dark.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.5

    def box(name, cx, cy, cz, sx, sy, sz, bevel, m):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
        o = bpy.context.active_object; o.name = name; o.scale = (sx, sy, sz)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        bv = o.modifiers.new('bv', 'BEVEL'); bv.width = bevel; bv.segments = 4; bv.limit_method = 'NONE'
        bpy.ops.object.modifier_apply(modifier='bv')
        o.data.materials.append(m)
        for p in o.data.polygons: p.use_smooth = True
        return o

    d = 0.24                                   # pack depth
    y0 = back_y - float(os.environ.get('PACK_IN', '0.055'))                        # front face sits on the back
    parts = [
        box('plss', 0, y0 + d / 2, 1.275, 0.54, d, 0.70, 0.045, mat),                 # main pack: top ~1.55 m, behind the helmet
        box('sop', 0, y0 + 0.19 / 2, 0.86, 0.44, 0.19, 0.13, 0.03, mat),             # secondary oxygen pack at its base
        box('rib1', 0, y0 + d + 0.004, 1.42, 0.40, 0.012, 0.018, 0.005, dark),        # panel seams on the back face
        box('rib2', 0, y0 + d + 0.004, 1.10, 0.40, 0.012, 0.018, 0.005, dark),
        box('vent', 0.17, y0 + d * 0.5, 1.615, 0.06, 0.10, 0.035, 0.01, dark),         # top fittings
        box('vent2', -0.17, y0 + d * 0.5, 1.615, 0.06, 0.10, 0.035, 0.01, dark),
    ]
    nb = len(body.data.vertices)
    for o in bpy.context.scene.objects: o.select_set(False)
    for p in parts: p.select_set(True)
    body.select_set(True); bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    g = body.vertex_groups['spine']
    g.add(list(range(nb, len(body.data.vertices))), 1.0, 'REPLACE')
    print('pack added', len(body.data.vertices) - nb, 'verts at back y', round(back_y, 3))

V = np.array([v.co[:] for v in body.data.vertices]); H = 1.8
if os.environ.get('CUT_PACK') == '1':
    cut_pack(body, H, float(os.environ.get('PACK_MARGIN', '0.03')))
    cut_floaters(body, H)
    V = np.array([v.co[:] for v in body.data.vertices])
print('bounds', V.min(0), V.max(0), 'verts', len(V))

def band(z0, z1):
    return V[(V[:, 2] > z0 * H) & (V[:, 2] < z1 * H)]

# ---- landmarks from the mesh ----
arm = band(0.42, 0.62); ax = np.abs(arm[:, 0]).max()
hands = {sd: arm[(np.sign(arm[:, 0]) == sd) & (np.abs(arm[:, 0]) > 0.82 * ax)].mean(0) for sd in (1, -1)}
legs = band(0.10, 0.30)
legc = {sd: legs[np.sign(legs[:, 0]) == sd].mean(0) for sd in (1, -1)}
sh = band(0.78, 0.82); shx = np.percentile(np.abs(sh[:, 0]), 97) * 0.78
ymid = band(0.45, 0.6)[:, 1].mean()
print('hands', hands, 'legs', legc, 'shoulder x', shx)

arm_obj = bpy.data.armatures.new('rig'); rig = bpy.data.objects.new('rig', arm_obj)
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
eb = arm_obj.edit_bones
FWD = Vector((0, -1, 0))
def bone(name, h, t, parent=None, conn=False):
    b = eb.new(name); b.head = Vector(h); b.tail = Vector(t)
    b.align_roll(FWD if abs(Vector(t).z - Vector(h).z) > 0.3 * (Vector(t) - Vector(h)).length else Vector((0, 0, 1)))
    if parent: b.parent = eb[parent]; b.use_connect = conn
    return b
hipz = 0.52 * H
bone('hips', (0, ymid, hipz), (0, ymid, 0.62 * H))
bone('spine', (0, ymid, 0.62 * H), (0, ymid, 0.80 * H), 'hips', True)
bone('head', (0, ymid, 0.80 * H), (0, ymid, 1.0 * H), 'spine', True)
for sd, nm in ((1, 'L'), (-1, 'R')):
    lx = legc[sd][0]; ly = legc[sd][1]
    bone(f'thigh.{nm}', (lx, ly, hipz), (lx, ly, 0.28 * H), 'hips')
    bone(f'shin.{nm}', (lx, ly, 0.28 * H), (lx, ly, 0.055 * H), f'thigh.{nm}', True)
    bone(f'foot.{nm}', (lx, ly, 0.055 * H), (lx, ly - 0.12, 0.01 * H), f'shin.{nm}', True)
    shp = Vector((sd * shx, ymid, 0.79 * H)); hp = Vector(hands[sd])
    wrist = shp + (hp - shp) * 0.88; elbow = shp + (wrist - shp) * 0.5 + Vector((0, 0.015, 0))
    bone(f'upper_arm.{nm}', shp, elbow, 'spine')
    bone(f'forearm.{nm}', elbow, wrist, f'upper_arm.{nm}', True)
    bone(f'hand.{nm}', wrist, hp + (hp - shp).normalized() * 0.15, f'forearm.{nm}', True)
segs = {b.name: (np.array(b.head[:]), np.array(b.tail[:])) for b in eb}
bpy.ops.object.mode_set(mode='OBJECT')

# ---- weights: inverse distance to bone segments, with side and region gating ----
names = list(segs)
D = np.zeros((len(V), len(names)))
for j, n in enumerate(names):
    a, b = segs[n]; ab = b - a
    t = np.clip(((V - a) @ ab) / (ab @ ab), 0, 1)
    D[:, j] = np.linalg.norm(V - (a + t[:, None] * ab), axis=1)
x, z = V[:, 0], V[:, 2]
nearhand = D[:, [names.index(k) for k in ('hand.L', 'hand.R', 'forearm.L', 'forearm.R')]].min(1)
for j, n in enumerate(names):
    if n.endswith('.L'): D[x < -0.01, j] = 9
    if n.endswith('.R'): D[x > 0.01, j] = 9
    if n.startswith(('thigh', 'shin', 'foot')): D[(z > hipz + 0.04) | (nearhand < 0.10), j] = 9
    if n.startswith(('upper_arm', 'forearm', 'hand')): D[np.abs(x) < shx * 0.75, j] = 9
W = 1.0 / np.maximum(D, 1e-3) ** 6
W[D > 8] = 0
W /= W.sum(1, keepdims=True)
for j, n in enumerate(names):
    g = body.vertex_groups.new(name=n)
    idx = np.nonzero(W[:, j] > 0.02)[0]
    for i in idx: g.add([int(i)], float(W[i, j]), 'REPLACE')
if os.environ.get('ADD_PACK') == '1':
    add_pack(body, PACK_Y if PACK_Y is not None else float(np.percentile(V[:, 1], 97)), H)
body.parent = rig
md = body.modifiers.new('arm', 'ARMATURE'); md.object = rig

# ---- walk cycle ----
sc = bpy.context.scene
sc.frame_start, sc.frame_end = 0, NF - 1
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='POSE')
pb = rig.pose.bones
for p in pb: p.rotation_mode = 'XYZ'
SGN = float(os.environ.get('WALK_SIGN', '1'))  # flip if legs swing the wrong way
ARMDOWN = float(os.environ.get('ARM_DOWN', '18'))
def key(f):
    t = f / NF * 2 * math.pi
    for sd, nm, ph in ((1, 'L', 0.0), (-1, 'R', math.pi)):
        a = t + ph
        thigh = 4 + 29 * math.sin(a)
        knee = 4 + 62 * max(0.0, math.cos(a - 0.45)) ** 2.5 + 9 * max(0.0, math.sin(2 * (a - math.pi / 2))) * (math.sin(a) > 0)
        ankle = -0.85 * thigh + 0.85 * knee - 14 * max(0.0, math.cos(a + 1.3)) ** 2
        pb[f'thigh.{nm}'].rotation_euler = (math.radians(SGN * thigh), 0, 0)
        pb[f'shin.{nm}'].rotation_euler = (math.radians(-SGN * knee), 0, 0)
        pb[f'foot.{nm}'].rotation_euler = (math.radians(SGN * ankle), 0, 0)
        swing = -16 * math.sin(a)
        pb[f'upper_arm.{nm}'].rotation_euler = (math.radians(SGN * swing), 0, math.radians(sd * ARMDOWN))
        pb[f'forearm.{nm}'].rotation_euler = (math.radians(SGN * (14 + 10 * max(0.0, -math.sin(a)))), 0, 0)
        for b in ('thigh', 'shin', 'foot', 'upper_arm', 'forearm'): pb[f'{b}.{nm}'].keyframe_insert('rotation_euler', frame=f)
    pb['hips'].location = (0, 0.035 * math.cos(2 * t), 0)  # bone-local Y is world up for hips
    pb['hips'].rotation_euler = (0, math.radians(5 * math.sin(t)), 0)
    pb['spine'].rotation_euler = (math.radians(float(os.environ.get('LEAN', '-4'))), math.radians(-7 * math.sin(t)), 0)
    pb['head'].rotation_euler = (0, math.radians(4 * math.sin(t)), 0)
    for b in ('hips', 'spine', 'head'): pb[b].keyframe_insert('rotation_euler', frame=f)
    pb['hips'].keyframe_insert('location', frame=f)
for f in range(NF): key(f)
bpy.ops.object.mode_set(mode='OBJECT')

# ---- feet on the floor: per frame, lift so the lowest point sits at z 0 ----
dg = bpy.context.evaluated_depsgraph_get()
lift = []
for f in range(NF):
    sc.frame_set(f); dg = bpy.context.evaluated_depsgraph_get()
    m = body.evaluated_get(dg).to_mesh(); zs = np.array([v.co.z for v in m.vertices]); body.evaluated_get(dg).to_mesh_clear()
    lift.append(-zs.min())
for f in range(NF):
    rig.location = (0, 0, lift[f]); rig.keyframe_insert('location', frame=f)
print('lift', [round(l, 3) for l in lift])

# ---- lights and camera ----
def light(name, kind, energy, color, loc, rot, size=1.0):
    d = bpy.data.lights.new(name, kind); d.energy = energy; d.color = color
    if kind == 'AREA': d.size = size
    o = bpy.data.objects.new(name, d); o.location = loc; o.rotation_euler = [math.radians(r) for r in rot]
    sc.collection.objects.link(o)
light('key', 'AREA', float(os.environ.get('KEY', '450')), (1.0, 0.80, 0.58), (-3.0, -2.2, 3.4), (50, 0, -55), 2.5)
light('fill', 'AREA', 180, (0.55, 0.65, 0.85), (-3.0, 2.5, 1.5), (75, 0, -130), 3)
light('rim', 'AREA', 700, (1.0, 0.62, 0.28), (2.5, 0.5, 2.6), (60, 0, 80), 1.5)
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.06, 0.05, 0.045, 1); w.node_tree.nodes['Background'].inputs[1].default_value = 1.0

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; OS = float(os.environ.get('ORTHO', '1.06')); cam.data.ortho_scale = H * OS
r = sc.render; r.engine = 'CYCLES'; r.film_transparent = True
r.resolution_x = r.resolution_y = RES
sc.cycles.samples = 48; sc.cycles.use_denoising = True
try:
    pr = bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type = 'OPTIX'; pr.get_devices()
    for d in pr.devices: d.use = True
    sc.cycles.device = 'GPU'
except Exception as e: print('gpu', e)

def place(view):
    zc = H * OS / 2 - 0.025  # feet near the bottom edge
    if view == 'side':   cam.location = (-8, ymid, zc); cam.rotation_euler = (math.radians(90), 0, math.radians(-90))
    elif view == 'front': cam.location = (0, -8, zc); cam.rotation_euler = (math.radians(90), 0, 0)
    elif view == 'back':  cam.location = (0, 8, zc); cam.rotation_euler = (math.radians(90), 0, math.radians(180))

if MODE == 'views':
    rig.data.pose_position = 'REST'; sc.frame_set(0); place('side'); r.filepath = os.path.join(OUT, 'view_rest_side.png'); bpy.ops.render.render(write_still=True)
    rig.data.pose_position = 'POSE'
    for f, v in ((0, 'front'), (0, 'side'), (NF // 4, 'side'), (NF // 2, 'side'), (NF // 4, 'front')):
        sc.frame_set(f); place(v); r.filepath = os.path.join(OUT, f'view_{v}_{f:02d}.png'); bpy.ops.render.render(write_still=True)
else:
    place('side')
    for f in range(NF):
        sc.frame_set(f); r.filepath = os.path.join(OUT, f'walk_{f:02d}.png'); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'captain_rig.blend'))
print('done')
