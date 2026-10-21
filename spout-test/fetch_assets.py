import json, os, sys, urllib.request
o=urllib.request.build_opener(); o.addheaders=[("User-Agent","glenda-scene-builder/1.0")]; urllib.request.install_opener(o)
import sys
OUT = sys.argv[1]
def get(u, p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    if not os.path.exists(p): urllib.request.urlretrieve(u, p)
def files(a): return json.load(urllib.request.urlopen(f'https://api.polyhaven.com/files/{a}'))
TEX = ['dirty_carpet','decrepit_wallpaper','ceiling_interior','old_linoleum_flooring_01']
MOD = ['ArmChair_01','side_table_01','cardboard_box_01','trashbag','wicker_basket_01','television_02',
       'vintage_cabinet_01','painted_wooden_cabinet','vintage_electric_kettle','vintage_microwave','bananas',
       'throw_pillows_01','coffee_table_round_01','wall_clock','standing_picture_frame_01','potted_plant_02']
for t in TEX:
    f = files(t)
    for key, name in [('Diffuse','diff'),('nor_gl','nor'),('Rough','rough')]:
        if key in f:
            get(f[key]['1k']['jpg']['url'], f'{OUT}/tex/{t}_{name}.jpg')
    print('tex', t, [k for k in f.keys()][:12])
for m in MOD:
    try:
        g = files(m)['gltf']['1k']['gltf']
        get(g['url'], f'{OUT}/models/{m}/{m}.gltf')
        for rel, inc in g.get('include', {}).items():
            get(inc['url'], f'{OUT}/models/{m}/{rel}')
        print('model', m, 'ok')
    except Exception as e: print('model', m, 'FAIL', e)
