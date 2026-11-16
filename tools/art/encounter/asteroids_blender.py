"""Headless Blender: procedural asteroids for the encounter.
blender -b -P asteroids_blender.py -- <out_dir> <kind: small|big> <frames> <res> <seed>"""
import bpy, sys, math, os, random
argv = sys.argv[sys.argv.index('--') + 1:]
OUT, KIND, NF, RES, SEED = argv[0], argv[1], int(argv[2]), int(argv[3]), int(argv[4])
os.makedirs(OUT, exist_ok=True); random.seed(SEED)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=1.0)
rock = bpy.context.active_object
rock.scale = (1.0, 0.82 + random.random() * 0.15, 0.72 + random.random() * 0.2)
def disp(tex_type, strength, size, mid=0.5, **kw):
    t = bpy.data.textures.new(f't{tex_type}{size}', tex_type)
    for k, v in kw.items(): setattr(t, k, v)
    if hasattr(t, 'noise_scale'): t.noise_scale = size
    m = rock.modifiers.new(f'd{tex_type}{size}', 'DISPLACE'); m.texture = t; m.strength = strength; m.mid_level = mid
    m.texture_coords = 'LOCAL'
    return t
# big lumps, craters (voronoi pits), fine grain
disp('CLOUDS', 0.45, 0.9, noise_depth=2)
v = disp('VORONOI', -0.22, 0.45, mid=0.0, distance_metric='DISTANCE')
v.noise_intensity = 1.0
disp('CLOUDS', 0.06, 0.12, noise_depth=4)
rock.modifiers.new('sub', 'SUBSURF').levels = 1
for p in rock.data.polygons: p.use_smooth = True

mat = bpy.data.materials.new('rock'); mat.use_nodes = True
nt = mat.node_tree; b = nt.nodes['Principled BSDF']
n1 = nt.nodes.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 3.0; n1.inputs['Detail'].default_value = 8
cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = (0.10, 0.085, 0.075, 1); cr.color_ramp.elements[1].color = (0.42, 0.36, 0.30, 1)
nt.links.new(n1.outputs['Fac'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], b.inputs['Base Color'])
b.inputs['Roughness'].default_value = 0.92
n2 = nt.nodes.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 40.0; n2.inputs['Detail'].default_value = 10
bump = nt.nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.35
nt.links.new(n2.outputs['Fac'], bump.inputs['Height']); nt.links.new(bump.outputs['Normal'], b.inputs['Normal'])
rock.data.materials.append(mat)

def light(name, energy, color, rot):
    d = bpy.data.lights.new(name, 'SUN'); d.energy = energy; d.color = color
    o = bpy.data.objects.new(name, d); o.rotation_euler = [math.radians(r) for r in rot]; sc.collection.objects.link(o)
light('key', 4.0, (1.0, 0.95, 0.88), (40, -35, -30))     # from upper left, like the ship art
light('rim', 1.2, (0.55, 0.7, 1.0), (-60, 50, 150))
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs[1].default_value = 0.03

cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.9; cam.location = (0, 0, 10)
r = sc.render; r.engine = 'CYCLES'; r.film_transparent = True; r.resolution_x = r.resolution_y = RES
sc.cycles.samples = 32; sc.cycles.use_denoising = True
try:
    pr = bpy.context.preferences.addons['cycles'].preferences; pr.compute_device_type = 'OPTIX'; pr.get_devices()
    for d in pr.devices: d.use = True
    sc.cycles.device = 'GPU'
except Exception as e: print('gpu', e)

ax = (random.uniform(-1, 1), random.uniform(-1, 1), random.uniform(0.3, 1))
L = math.sqrt(sum(a * a for a in ax)); ax = tuple(a / L for a in ax)
from mathutils import Quaternion
for f in range(NF):
    rock.rotation_mode = 'QUATERNION'
    rock.rotation_quaternion = Quaternion(ax, 2 * math.pi * f / NF) @ Quaternion((1, 0, 0), 0.4)
    r.filepath = os.path.join(OUT, f'{KIND}_{f:02d}.png'); bpy.ops.render.render(write_still=True)
print('done')
