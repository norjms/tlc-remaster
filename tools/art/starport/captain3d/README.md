# Captain walk: image-to-3D, auto-rig, Blender render

The captain wears a plain white pressure suit (NASA-like, no logos, flags or
patches) with a gold visor and no backpack.

1. front.py: FLUX front-view references in A-pose. Do not put "NASA" in the
   prompt: FLUX then adds logos and flags. Pick a clean one (nasb_3 was used).
2. prep_cap.py: cut it out with rembg into ComfyUI/input/sf8_nasa2.png and erase
   the pack edges that show beside the helmet.
3. wf2api.py MeshWithTexturing.json trellis_overrides.json: runs the ComfyUI-Trellis2
   example workflow (TRELLIS.2 4B, sdpa/xformers) for a textured GLB.
4. blender -b -P walk_blender.py -- <captain.glb> <out dir> walk 16 948
   Normalises the mesh to 1.8 m. With CUT_PACK=1 it removes any backpack TRELLIS
   invents (geometry behind the waist line, PACK_MARGIN) and anything floating in
   front of the chest (FRONT_MARGIN), closing the back with suit fabric. Places a
   skeleton from mesh landmarks (hand bones reach the fingertips), skins by
   distance to bone segments (legs never take the hands), keys a 16-frame walk,
   keeps the feet on the floor and renders an orthographic side view with the
   concourse lighting.
   Used: CUT_PACK=1 PACK_MARGIN=0.012 FRONT_MARGIN=0.015 ARM_DOWN=-20 KEY=320.
   "views" mode renders check views.
5. install_walk.py <bin/data> <out dir>: light warm grade (0.86, 0.82, 0.75),
   contact shadow, mirrored row, writes starport_avatar.png (+@2x, @4x).
