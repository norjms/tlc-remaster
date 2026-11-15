# Captain walk: image-to-3D, auto-rig, Blender render

1. front.py: FLUX front-view references of the captain (A-pose). Pick one.
2. prep_cap.py: cut it out with rembg into ComfyUI/input/sf8_cap.png.
3. wf2api.py MeshWithTexturing.json trellis_overrides.json: runs the ComfyUI-Trellis2
   example workflow (TRELLIS.2 4B, sdpa/xformers) for a textured GLB.
4. blender -b -P walk_blender.py -- <captain.glb> <out dir> walk 16 948
   Normalises the mesh to 1.8 m, places a skeleton from mesh landmarks, skins it
   by distance to bone segments, keys a 16-frame walk, keeps the feet on the
   floor and renders an orthographic side view with the concourse lighting.
   Env: ARM_DOWN=-20 KEY=320 ORTHO=1.06. "views" mode renders check views.
5. install_walk.py <bin/data> <out dir>: light warm grade (0.86, 0.82, 0.75), contact shadow, mirrored
   row, writes starport_avatar.png (+@2x, @4x).
