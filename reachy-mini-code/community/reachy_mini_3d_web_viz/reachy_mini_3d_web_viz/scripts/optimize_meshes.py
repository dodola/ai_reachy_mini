# Blender mesh optimization script
# Run with: blender --background --python scripts/optimize_meshes.py
#
# This script:
# 1. Removes interior/duplicate vertices
# 2. Decimates to reduce polygon count
# 3. Exports as GLB with Draco compression

import bpy
import os
from pathlib import Path

INPUT_DIR = "assets/meshes"
OUTPUT_DIR = "assets/meshes_optimized"
DECIMATE_RATIO = 0.2  # Keep 20% of faces (adjust as needed)

# Files to skip geometry optimization (exact stem names, no extension)
SKIP_GEOMETRY_OPTIMIZATION = {"antenna_V2"}  # Use set for exact matching

def clean_scene():
    """Remove all objects from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def optimize_mesh(obj):
    """Merge vertices and apply auto-smooth shading"""
    import math
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # STL files have separate vertices per face - merge coincident ones
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.00001)  # Very small threshold
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Apply smooth shading as base
    bpy.ops.object.shade_smooth()

    # Mark sharp edges based on angle (edges > 30 degrees become sharp)
    # This preserves flat shading on sharp corners while smoothing curves
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.edges_select_sharp(sharpness=math.radians(30))
    bpy.ops.mesh.mark_sharp()
    bpy.ops.object.mode_set(mode='OBJECT')

    # Edge Split modifier splits geometry at sharp edges for proper shading
    mod = obj.modifiers.new("EdgeSplit", 'EDGE_SPLIT')
    mod.use_edge_angle = False  # Only use marked sharp edges
    mod.use_edge_sharp = True
    bpy.ops.object.modifier_apply(modifier="EdgeSplit")

def should_skip_optimization(filepath):
    """Check if file should skip geometry optimization (exact stem match)"""
    stem = Path(filepath).stem.lower()
    return stem in SKIP_GEOMETRY_OPTIMIZATION

def process_stl(stl_path, output_path):
    """Process a single STL file"""
    clean_scene()

    # Import STL (API changed in Blender 4.0+)
    try:
        bpy.ops.wm.stl_import(filepath=str(stl_path))
    except AttributeError:
        # Fallback for older Blender versions
        bpy.ops.import_mesh.stl(filepath=str(stl_path))

    if not bpy.context.selected_objects:
        print(f"  ERROR: Failed to import {stl_path.name}")
        return False

    obj = bpy.context.selected_objects[0]

    # IMPORTANT: Preserve original coordinates
    # Move object origin to world origin while keeping mesh in place
    obj.location = (0, 0, 0)
    obj.rotation_euler = (0, 0, 0)
    obj.scale = (1, 1, 1)

    # Get original face count
    original_faces = len(obj.data.polygons)

    # Optimize (unless in skip list)
    skip_optimization = should_skip_optimization(stl_path)
    if skip_optimization:
        print(f"\033[96m  *** Skipping geometry optimization (in skip list) ***\033[0m")
    else:
        optimize_mesh(obj)

    # Get new face count
    new_faces = len(obj.data.polygons)

    # Ensure object is still selected for export
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Export as GLB
    # Skip DRACO compression for files in skip list to preserve geometry exactly
    export_params = {
        'filepath': str(output_path),
        'export_format': 'GLB',
        'use_selection': True,
        'export_yup': False,  # Keep Z-up to match original STL coordinate system
    }
    if skip_optimization:
        export_params['export_draco_mesh_compression_enable'] = False
    else:
        export_params['export_draco_mesh_compression_enable'] = True
        export_params['export_draco_mesh_compression_level'] = 7

    bpy.ops.export_scene.gltf(**export_params)

    # Get file sizes
    original_size = stl_path.stat().st_size / 1024
    new_size = output_path.stat().st_size / 1024

    print(f"  Faces: {original_faces} -> {new_faces} ({100*new_faces/original_faces:.1f}%)")
    print(f"  Size: {original_size:.1f}KB -> {new_size:.1f}KB ({100*new_size/original_size:.1f}%)")

    return True

def main():
    # Get script directory (Blender sets cwd to script location)
    script_dir = Path(__file__).parent.parent
    input_dir = script_dir / INPUT_DIR
    output_dir = script_dir / OUTPUT_DIR

    print(f"\nMesh Optimization Script")
    print(f"========================")
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    print(f"Decimate ratio: {DECIMATE_RATIO}")
    print()

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process all STL files
    stl_files = list(input_dir.glob("*.stl")) + list(input_dir.glob("*.STL"))

    if not stl_files:
        print("No STL files found!")
        return

    print(f"Found {len(stl_files)} STL files\n")

    success_count = 0
    for i, stl_file in enumerate(stl_files, 1):
        output_path = output_dir / (stl_file.stem + ".glb")
        print(f"[{i}/{len(stl_files)}] {stl_file.name}")

        if process_stl(stl_file, output_path):
            success_count += 1
        print()

    print(f"Done! Processed {success_count}/{len(stl_files)} files")
    print(f"Optimized meshes saved to: {output_dir}")

if __name__ == "__main__":
    main()
