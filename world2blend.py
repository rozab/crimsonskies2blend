try:    
    import bpy
    import bmesh
except ImportError:
    print("This scripts are supposed to be run inside blender! It's much easier to just run everything2blend.py, which will handle that tricky stuff for you.")
    exit(1)

import json
import os.path
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from PIL import Image

TEXTURE_SUBSTITUTIONS = {
    # higher res textures
    "agyro_taillogo.png": "12its_logo1.png",
    "agyro_winglogo.png": "12its_logo1.png",
    "bal_taillogo.png": "british_tail.png",
    "bal_winglogo.png": "04british_logo1.png",
    "blo_taillogo.png": "blake_logo1.png",
    "blo_winglogo.png": "blake_logo1.png",
    "bri_taillogo.png": "14medusa_logo1.png",
    "bri_winglogo.png": "14medusa_logo1.png",
    "dev_taillogo.png": "fhunter_logo2.png",
    "dev_winglogo.png": "fhunter_logo4_1.png",
    "fir_taillogo.png": "10hknights_logo2.png",
    "fir_winglogo.png": "hollywoodlogo.png",
    "fur_taillogo.png": "bswan_logo1.png",
    "fur_winglogo.png": "bswan_logo1.png",
    "hel_taillogo.png": "sacredtrust_logo1.png",
    "hel_winglogo.png": "sacredtrust_logo1.png",
    "kes_taillogo.png": "14medusa_logo1.png",
    "kes_winglogo.png": "14medusa_logo1.png",
    "pea_taillogo.png": "blake_logo1.png",
    "pea_winglogo.png": "blake_logo1.png",
    "war_taillogo.png": "blackhat_logo1.png",
    "war_winglogo.png": "blackhat_logo1.png",
    # these are different textures, but match what's in-game
    "bal_noselogo.png": "21ace_star.png",
    "blo_noselogo.png": "21ace_star.png",
    "bri_noselogo.png": "21ace_star.png",
    "dev_noselogo.png": "40ohsoblue.png",
    "fur_noselogo.png": "21ace_star.png",
    "hel_noselogo.png": "21ace_star.png",
    "kes_noselogo.png": "21ace_star.png",
    "pea_noselogo.png": "21ace_star.png",
    "war_noselogo.png": "21ace_star.png",
}


class MeshFactory:
    def __init__(self, meshes_json, material_factory):
        self.meshes_json = meshes_json
        self.material_factory = material_factory

    @staticmethod
    def _get_name(mesh_index):
        return f"mesh{mesh_index:04}"

    def _create_mesh(self, mesh_index):
        if mesh_index == -1: return None
        if not (m := meshes_json[mesh_index]): print(f"WARNING: no such mesh {mesh_index}")
        if not m["polygons"]: return None # don't bother with those lights-only meshes

        # initialize mesh object with materials
        mesh_data = bpy.data.meshes.new(name=self._get_name(mesh_index))
        mat_indices = set([p["materials"][0]["material_index"] for p in m["polygons"]])
        local_mat_indices = {}
        for local_mat_index, mat_index in enumerate(mat_indices):
            mat = material_factory(mat_index)
            local_mat_indices[mat_index] = local_mat_index
            mesh_data.materials.append(mat)

        bm = bmesh.new(use_operators=True)
        uv_layer = bm.loops.layers.uv.new()
        color_layer = bm.loops.layers.color.new("color")

        for v in m["vertices"]:
            bm.verts.new((v["x"], -v["z"], v["y"]))
        bm.verts.ensure_lookup_table()
        bm.verts.index_update()

        for poly in m["polygons"]:
            self._process_poly(bm, poly, uv_layer, color_layer, local_mat_indices)

        assert(len(bm.faces))
        
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(mesh_data)
        bm.free()
        mesh_data.attributes.active_color_index = 0
        return mesh_data
    
    @staticmethod
    def _process_poly(bm, poly, uv_layer, color_layer, local_mat_indices):
        verts = poly["vertex_indices"]
        colors = poly["vertex_colors"]
        mat_index = poly["materials"][0]["material_index"]
        uvs = poly["materials"][0]["uv_coords"]

        if "triangle_strip" in poly["flags"]:
            # Create series of triangular faces
            for i in range(len(poly["vertex_indices"]) - 3 + 1):
                window = verts[i : i + 3]
                if len(set(window)) != len(window):
                    # ignore tris with duplicate verts
                    continue
                try:
                    face = bm.faces.new(bm.verts[i] for i in window)
                    face.smooth = True
                    face.material_index = local_mat_indices[mat_index]
                except ValueError:
                    # print("WARNING: couldn't create face in triangle strip for some unknown reason")
                    # yeah this happens a lot but the meshes look good so whatever
                    continue

                colors_window = colors[i : i + 3]
                for index_in_mesh, loop, color in zip(window, face.loops, colors_window):
                    loop[color_layer] = (color["r"] / 255, color["g"] / 255, color["b"] / 255, 1)

                uvs_window = uvs[i : i + 3]
                for index_in_mesh, loop, uv in zip(window, face.loops, uvs_window):
                    loop[uv_layer].uv = (uv["u"], 1 - uv["v"])
        else:
            # Create a single N-gon face
            try:
                face = bm.faces.new(bm.verts[i] for i in verts)
                face.smooth = True
                face.material_index = local_mat_indices[mat_index]
            except ValueError:
                # print("WARNING: couldn't create face in N-gon for some unknown reason")
                return

            for index_in_mesh, loop, color in zip(verts, face.loops, colors):
                loop[color_layer] = (color["r"] / 255, color["g"] / 255, color["b"] / 255, 1)

            for index_in_mesh, loop, uv in zip(verts, face.loops, uvs):
                loop[uv_layer].uv = (uv["u"], 1 - uv["v"])
    
    def __call__(self, mesh_index):
        if mesh_index == -1: return None
        name = self._get_name(mesh_index)
        if name in bpy.data.meshes:
            return bpy.data.meshes[name]
        else:
            return self._create_mesh(mesh_index)


class MaterialFactory:
    @classmethod
    @contextmanager
    def with_tempdir(
        cls,
        textures,
        materials_json,
    ):
        with TemporaryDirectory() as tempdir:
            yield cls(textures, materials_json, Path(tempdir))

    def __init__(
        self,
        textures_zip,
        materials_json,
        tempdir,
    ):
        self.tempdir = Path(tempdir)
        self.textures_zip = ZipFile(textures_zip)
        self.materials_json = materials_json

    @staticmethod
    def has_alpha(fname):
        if os.path.isfile(fname):
            with Image.open(fname) as im:
                return im.mode == "RGBA" and im.getextrema()[3][0] < 255
    
    def _get_image(self, texture_name):
        if texture_name in bpy.data.images:
            return bpy.data.images[texture_name]
        try:
            self.textures_zip.extract(texture_name, path=str(self.tempdir))
            return bpy.data.images.load(str(self.tempdir / texture_name))
        except KeyError:
            print("WARNING: did not find", texture_name)
        
    def _get_name(self, i):
        m = self.materials_json[i]
        if "Colored" in m: return f"material_{i}"
        
        tif_name = m["Textured"]["texture"]

        # some textures have spurious segments like bldhwk_cowling.5.tif which can be ignored
        if len(parts := tif_name.split(".")) > 2:
            tif_name = parts[0] + "." + parts[-1]

        png_name = os.path.splitext(tif_name.lower())[0] + ".png"

        # get a better texture if we have one
        return TEXTURE_SUBSTITUTIONS.get(png_name, png_name)

    def _create_material(self, mat_index):
        name = self._get_name(mat_index)
        m = materials_json[mat_index]
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        bsdf = material.node_tree.nodes["Principled BSDF"]

        if "Colored" in m:
            # create a simple colored material
            color = m["Colored"]["color"]
            bsdf.inputs["Base Color"].default_value = (color["r"] / 255, color["g"] / 255, color["b"] / 255, 1)
        else:
            # create a textured material
            image = self._get_image(name)
            if image is None:
                bsdf.inputs["Base Color"].default_value = (1, 0, 0.5, 1)
                return material
        
            tex = material.node_tree.nodes.new("ShaderNodeTexImage")
            tex.image = image
            material.node_tree.links.new(bsdf.inputs["Base Color"], tex.outputs["Color"])

            if self.has_alpha(str(self.tempdir / name)):
                material.node_tree.links.new(bsdf.inputs["Alpha"], tex.outputs["Alpha"])
                material.blend_method = "BLEND"
                material.shadow_method = "CLIP"
                material.alpha_threshold = 0.8

        material.roughness = 0.9
        material.specular_intensity = 0.1
        return material

    def __call__(self, mat_index):
        name = self._get_name(mat_index)
        if name in bpy.data.materials:
            return bpy.data.materials[name]
        else:
            return self._create_material(mat_index)
        

def hide_recursive(obj, except_condition = lambda c: False):
    obj.hide_set(True)
    for c in obj.children:
        if not except_condition(c):
            hide_recursive(c, except_condition)

def create_object_tree(i, mesh_factory, col):
    n = nodes_json[i]
    v = next(iter(n.values()))
    node_type = v["type"]
    mesh = mesh_factory(v.get("mesh_index")) if "mesh_index" in v else None

    if node_type == "World":
        v["name"] = "world"
        col = bpy.data.collections["world"]
    elif node_type == "Terrain":
        col = bpy.data.collections["terrain"]
    elif v.get("parent") is None and node_type in ["Object3d", "Lod"]:
        col = bpy.data.collections["misc"]
    elif node_type in ["Window", "Display", "Camera", "Light"]:
        return None
    
    obj = bpy.data.objects.new(v["name"], mesh)

    if "transformation" in v and v["transformation"]:
        trans = v["transformation"]["translation"]
        obj.location = (trans["x"], -trans["z"], trans["y"])
        rot = v["transformation"]["rotation"]
        obj.rotation_euler = (rot["x"], -rot["z"], rot["y"])
    
    for ci in v["children"]:
        create_object_tree(ci, mesh_factory, col).parent = obj
    
    col.objects.link(obj)

    if node_type == "World": obj.scale = (0.03, 0.03, 0.03)

    return obj

print("====================================================")

# & "C:\Program Files\Blender Foundation\Blender 3.5\blender.exe" --background --factory-startup --python-use-system-env --python world2blend.py -- "C:/Users/roz/Documents/crimson/extracted" "C:/Users/roz/Documents/crimson/planetoblend/world_out"

args = sys.argv[sys.argv.index("--") + 1:]

data_folder = Path(args[0])
out_folder = Path(args[1])
cname = args[2]

with ZipFile(str(data_folder / f"{cname}.zip")) as gamez:
    with gamez.open("meshes.json") as f:
        meshes_json = json.load(f)
    with gamez.open("materials.json") as f:
        materials_json = json.load(f)
    with gamez.open("nodes.json") as f:
        nodes_json = json.load(f)

for obj in bpy.data.objects:
    bpy.data.objects.remove(obj)

roots = []
for i, n in enumerate(nodes_json):
    node_type = next(iter(n.keys()))
    v = n[node_type]
    v["type"] = node_type
    v["index"] = i
    if "name" in v:
        # node names aren't unique!
        v["name"] = v["name"] + f"_{i:04}"
    if v.get("parent") is None:
        roots.append(i)

col = bpy.data.collections["Collection"]
world_col = bpy.data.collections.new("world")
col.children.link(world_col)
misc_col = bpy.data.collections.new("misc")
col.children.link(misc_col)
terrain_col = bpy.data.collections.new("terrain")
col.children.link(terrain_col)

with MaterialFactory.with_tempdir(str(data_folder / "textures.zip"), materials_json) as material_factory:
    mesh_factory = MeshFactory(meshes_json, material_factory)
    for i, root_index in enumerate(roots):
        obj = create_object_tree(root_index, mesh_factory, None)
        if obj is None: continue
    
    # the world node doesn't actually have its terrain in children *eyeroll*
    # so we have to add them manually
    for i, n in enumerate(nodes_json):
        v = next(iter(n.values()))
        if v.get("name", "world") not in bpy.data.objects and v.get("parent") == 0:
            v["type"] = "Terrain"
            obj = create_object_tree(i, mesh_factory, world_col)
            obj.parent = bpy.data.objects["world"]

    bpy.data.use_autopack = True
    bpy.ops.wm.save_as_mainfile(filepath=str(out_folder / f"{cname}.blend"))
