# Art masters

High resolution source art for the remaster. Game files under `bin/data` are
generated from these masters; edit the master, then regenerate.

## Ships (`ships/`)

`<name>_8x.png`: 8x the original sprite size, transparent background.
Player ships: `military`, `science`, `freelance`. Alien ships: `barzhon`,
`coalition`, `elowan`, `minex`, `nyssian`, `pirate`, `spemin`, `tafel`, `thrynn`.

How they were made (`tools/art/batch_ships.py`, run on a CUDA machine with
ComfyUI and Hunyuan3D):

1. Real-ESRGAN (`realesrgan-x4plus-anime`, two passes) upscales the original sprite.
2. Hunyuan3D-2 builds a mesh from the upscaled sprite; the mesh is matched to
   the sprite's silhouette and rendered straight down.
3. Lighting: the mesh supplies the large forms (hull volume), the original
   sprite supplies color, outline and fine panel relief; light from the upper
   left, metal highlights, glowing pink panels.

Every in-game copy is regenerated from the masters with
`tools/art/derive_ships.py`: the engineering and auxiliary screens, the 32x64
auxiliary icons, the ship configuration screen (rotated), the 128 px space
flight sprites, the planet surface animation strips (original thruster flames
kept) and the encounter sprites. Each copy keeps its original size, format,
rotation and position.

## Datafiles

The original Allegro `.dat` archives were unpacked once with
`tools/art/dat_extract.py`. Each `<module>.assets` file lists, in order, the
images the code indexes for that module; images that existed only inside an
archive are in that module's `from_dat/` folder.
