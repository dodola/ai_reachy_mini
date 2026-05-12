#!/usr/bin/env python3
"""
Update URDF file to use optimized GLB meshes instead of STL files.

Usage: python scripts/update_urdf.py
"""

import re
from pathlib import Path

URDF_PATH = Path("assets/reachy-mini.urdf")
OUTPUT_PATH = Path("assets/reachy-mini-optimized.urdf")

def update_urdf():
    if not URDF_PATH.exists():
        print(f"ERROR: URDF file not found: {URDF_PATH}")
        return False

    content = URDF_PATH.read_text()

    # Replace mesh references from meshes/*.stl to meshes_optimized/*.glb
    # Handles both package:// and relative paths
    def replace_mesh(match):
        original = match.group(0)
        # Replace directory and extension
        updated = re.sub(r'/meshes/', '/meshes_optimized/', original)
        updated = re.sub(r'\.stl"', '.glb"', updated, flags=re.IGNORECASE)
        return updated

    # Match filename="...meshes/...stl"
    pattern = r'filename="[^"]*meshes/[^"]*\.stl"'
    new_content, count = re.subn(pattern, replace_mesh, content, flags=re.IGNORECASE)

    if count == 0:
        print("No mesh references found to update!")
        return False

    # Write updated URDF
    OUTPUT_PATH.write_text(new_content)

    print(f"Updated {count} mesh references")
    print(f"Original: {URDF_PATH}")
    print(f"Updated:  {OUTPUT_PATH}")
    print()
    print("To use the optimized URDF, update your app URL:")
    print("  ?urdf=assets/reachy-mini-optimized.urdf")

    return True

if __name__ == "__main__":
    update_urdf()
