# Downloads the CC0 Poly Haven assets used by build_room.py (2k textures, glTF models).
import json, os, sys, urllib.request
o = urllib.request.build_opener(); o.addheaders = [("User-Agent", "glenda-scene-builder/1.0")]; urllib.request.install_opener(o)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
def get(u, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if not os.path.exists(p): urllib.request.urlretrieve(u, p)
def files(a): return json.load(urllib.request.urlopen(f"https://api.polyhaven.com/files/{a}"))
TEX = ["wood_floor_worn", "quatrefoil_jacquard_fabric", "white_plaster_rough_01", "decrepit_wallpaper", "old_linoleum_flooring_01", "fabric_pattern_05"]
MOD = ["ArmChair_01", "ClassicNightstand_01", "GreenChair_01", "Ottoman_01", "bananas", "book_encyclopedia_set_01", "cardboard_box_01", "ceramic_vase_01", "ceramic_vase_03", "coffee_table_round_01", "dining_chair_02", "drawer_cabinet", "fancy_picture_frame_01", "gaming_console", "hanging_picture_frame_01", "hanging_picture_frame_02", "hanging_picture_frame_03", "mantel_clock_01", "mid_century_lounge_chair", "modern_arm_chair_01", "modern_ceiling_lamp_01", "modern_coffee_table_02", "modern_wooden_cabinet", "painted_wooden_cabinet", "potted_plant_01", "potted_plant_02", "potted_plant_04", "round_spectacles", "side_table_01", "sofa_02", "sofa_03", "standing_picture_frame_01", "tea_set_01", "television_02", "throw_pillows_01", "trashbag", "vintage_cabinet_01", "vintage_electric_kettle", "vintage_microwave", "wall_clock", "wicker_basket_01", "wooden_bookshelf_worn", "wooden_bowl_01", "wooden_display_shelves_01"]
for t in TEX:
    f = files(t)
    for key, name in [("Diffuse", "diff"), ("nor_gl", "nor"), ("Rough", "rough")]:
        if key in f: get(f[key]["2k"]["jpg"]["url"], f"{OUT}/tex/{t}_{name}.jpg")
    print("tex", t)
for m in MOD:
    g = files(m)["gltf"]["2k"]["gltf"]
    get(g["url"], f"{OUT}/models/{m}/{m}.gltf")
    for rel, inc in g.get("include", {}).items(): get(inc["url"], f"{OUT}/models/{m}/{rel}")
    print("model", m)
