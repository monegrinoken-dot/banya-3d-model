# Модульная баня 6000×2500 — перенос Three.js-модели (banya-3d/src/banya.js) в Blender.
# Запуск: blender --background --python blender/build_banya_model.py
# Координаты Three.js (x, y-up, z) → Blender (x, -z, y).
import bpy, math, os, sys

FLOOR = 0.47; WB = 0.45; WT = 2.87; T = 0.12; TI = 0.1
OUT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # корень задачи
BLEND_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'banya_model.blend')
PREVIEW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'review', 'banya_blend_preview.png')

# ---------- очистка ----------
bpy.ops.wm.read_factory_settings(use_empty=True)

def srgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple((v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4) for v in c) + (1.0,)

# ---------- материалы ----------
def mat(name, color, rough=0.7, metal=0.0, emission=None, estr=0.0, alpha=1.0, glass=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = srgb(color)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if glass:
        b.inputs['Transmission Weight'].default_value = 1.0
        b.inputs['IOR'].default_value = 1.5
        m.surface_render_method = 'DITHERED'
    if emission:
        b.inputs['Emission Color'].default_value = srgb(emission)
        b.inputs['Emission Strength'].default_value = estr
    if alpha < 1.0:
        b.inputs['Alpha'].default_value = alpha
        m.surface_render_method = 'DITHERED'
    return m

M = {}
M['facade'] = mat('Фасад · Вертикальная доска', '#2A2723', 0.72)
M['deck'] = mat('Терраса · Палубная доска', '#453B31', 0.7)
M['innerWall'] = mat('Стены · Вагонка липа', '#C9AE85', 0.65)
M['benchWood'] = mat('Парная · Полок абаш', '#D9BE94', 0.6)
M['floorWood'] = mat('Пол · Доска', '#A98F6B', 0.6)
M['ceiling'] = mat('Потолок · Вагонка', '#C4A87E', 0.7)
M['tile'] = mat('Душевая · Плитка', '#2E3234', 0.35)
M['metal'] = mat('Профиль · Алюминий чёрный', '#1B1B1B', 0.5, 0.6)
M['roof'] = mat('Кровля · Мембрана', '#2A2A28', 0.9)
M['plinth'] = mat('Цоколь · Сталь', '#191919', 0.6, 0.4)
M['concrete'] = mat('Опоры · Бетон', '#8D8A84', 0.9)
M['glass'] = mat('Стекло', '#DFE9EC', 0.05, glass=True)
M['glassDoor'] = mat('Стекло дверное', '#D5E0E4', 0.05, glass=True)
M['curtain'] = mat('Шторы · Тюль', '#F2EFE8', 0.9, alpha=0.55)
M['fabric'] = mat('Кресла · Рогожка горчичная', '#B08D4F', 0.9)
M['cushion'] = mat('Лавка · Подушки лён', '#8F8A7C', 0.95)
M['darkWood'] = mat('Мебель · Дуб тёмный', '#4A3B2C', 0.55)
M['stove'] = mat('Печь · Сталь чёрная', '#1C1C1C', 0.55, 0.7)
M['stones'] = mat('Камни · Габбро', '#6E6A64', 0.85)
M['snow'] = mat('Снег', '#E8EEF4', 0.92)
M['rug'] = mat('Ковёр · Джут', '#7A7468', 1.0)
M['lampShade'] = mat('Светильник · Абажур', '#E8E0D0', 0.8, emission='#FFD9A0', estr=0.9)
M['sconce'] = mat('Бра · Свечение', '#2A2A2A', 0.6, emission='#FFC27D', estr=1.6)
M['ledStrip'] = mat('Парная · LED-подсветка', '#FFF1D6', 0.5, emission='#FFC98A', estr=2.2)
M['towel'] = mat('Полотенце', '#CFC8B8', 1.0)
M['logs'] = mat('Дрова · Берёза', '#B9A98E', 0.9)
M['plant'] = mat('Растение · Листва', '#3E5B33', 0.8)
M['pot'] = mat('Кашпо · Керамика', '#5C564E', 0.8)
M['groundSnow'] = mat('Земля · Снег', '#E3EAF1', 0.95)

# вертикальная доска на фасаде — волновой рельеф
def add_boards(m):
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tex = nt.nodes.new('ShaderNodeTexWave'); tex.wave_type = 'BANDS'; tex.bands_direction = 'X'
    tex.inputs['Scale'].default_value = 6.5; tex.inputs['Distortion'].default_value = 2.0
    bnode = nt.nodes.new('ShaderNodeBump'); bnode.inputs['Strength'].default_value = 0.35; bnode.inputs['Distance'].default_value = 0.02
    nt.links.new(tex.outputs['Color'], bnode.inputs['Height'])
    nt.links.new(bnode.outputs['Normal'], b.inputs['Normal'])
add_boards(M['facade'])

# ---------- коллекции ----------
def coll(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c
C_BANYA = coll('Баня · Корпус')
C_INT = coll('Интерьер')
C_TER = coll('Терраса')
C_LIGHT = coll('Свет')
C_SITE = coll('Участок')

def link(obj, c):
    for cc in list(obj.users_collection):
        cc.objects.unlink(obj)
    c.objects.link(obj)
    return obj

def P(x, y, z):
    return (x, -z, y)

def box(name, mt, w, h, d, x, y, z, c=C_BANYA, rotY=0.0):
    # three: w(x) h(y) d(z); blender: (w, d, h)
    bpy.ops.mesh.primitive_cube_add(location=P(x, y, z))
    o = bpy.context.object; o.name = name
    o.scale = (w / 2, d / 2, h / 2)
    bpy.ops.object.transform_apply(scale=True)
    if rotY: o.rotation_euler.z = rotY
    if mt: o.data.materials.append(mt)
    return link(o, c)

def cyl(name, mt, r1, r2, h, x, y, z, c=C_BANYA, rotX=0.0, rotY=0.0, n=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r1, depth=h, location=P(x, y, z))
    o = bpy.context.object; o.name = name
    if r1 != r2:  # конусность
        o.scale = (1, 1, 1)
        bpy.ops.object.transform_apply(scale=True)
        # приближение: конус через отдельный примитив
        bpy.ops.object.delete()
        bpy.ops.mesh.primitive_cone_add(vertices=n, radius1=r2, radius2=r1, depth=h, location=P(x, y, z))
        o = bpy.context.object; o.name = name
    if rotX: o.rotation_euler.x = rotX
    if rotY: o.rotation_euler.z = rotY
    if mt: o.data.materials.append(mt)
    return link(o, c)

def empty(name, x, y, z, c, rotY=0.0):
    o = bpy.data.objects.new(name, None)
    o.location = P(x, y, z)
    o.rotation_euler.z = rotY
    c.objects.link(o)
    return o

def parent(o, e):
    o.parent = e
    o.matrix_parent_inverse.identity()
    return o

# ---------- стены с проёмами ----------
def wallX(mt, x0, x1, z, y0=WB, y1=WT, t=T, openings=(), c=C_BANYA, name='Стена'):
    ops = sorted(openings, key=lambda o: o['x0'])
    cur = x0; i = 0
    for o in ops:
        if o['x0'] > cur:
            box(f'{name}.{i}', mt, o['x0'] - cur, y1 - y0, t, (cur + o['x0']) / 2, (y0 + y1) / 2, z, c); i += 1
        if o['y0'] > y0:
            box(f'{name}.{i}', mt, o['x1'] - o['x0'], o['y0'] - y0, t, (o['x0'] + o['x1']) / 2, (y0 + o['y0']) / 2, z, c); i += 1
        if o['y1'] < y1:
            box(f'{name}.{i}', mt, o['x1'] - o['x0'], y1 - o['y1'], t, (o['x0'] + o['x1']) / 2, (o['y1'] + y1) / 2, z, c); i += 1
        cur = max(cur, o['x1'])
    if cur < x1:
        box(f'{name}.{i}', mt, x1 - cur, y1 - y0, t, (cur + x1) / 2, (y0 + y1) / 2, z, c)

def wallZ(mt, z0, z1, x, y0=WB, y1=WT, t=T, openings=(), c=C_BANYA, name='Стена'):
    ops = sorted(openings, key=lambda o: o['z0'])
    cur = z0; i = 0
    for o in ops:
        if o['z0'] > cur:
            box(f'{name}.{i}', mt, t, y1 - y0, o['z0'] - cur, x, (y0 + y1) / 2, (cur + o['z0']) / 2, c); i += 1
        if o['y0'] > y0:
            box(f'{name}.{i}', mt, t, o['y0'] - y0, o['z1'] - o['z0'], x, (y0 + o['y0']) / 2, (o['z0'] + o['z1']) / 2, c); i += 1
        if o['y1'] < y1:
            box(f'{name}.{i}', mt, t, y1 - o['y1'], o['z1'] - o['z0'], x, (y0 + y1) / 2, (o['y1'] + y1) / 2, z, c); i += 1
        cur = max(cur, o['z1'])
    if cur < z1:
        box(f'{name}.{i}', mt, t, y1 - y0, z1 - cur, x, (y0 + y1) / 2, (y0 + y1) / 2, z, c)

def windowX(x0, x1, y0, y1, z, t=T, sill=True, name='Окно', c=C_BANYA):
    w = x1 - x0; h = y1 - y0; cx = (x0 + x1) / 2; cy = (y0 + y1) / 2; f = 0.055
    box(f'{name} · рама В', M['metal'], w, f, t + 0.04, cx, y1 - f / 2, z, c)
    box(f'{name} · рама Н', M['metal'], w, f, t + 0.04, cx, y0 + f / 2, z, c)
    box(f'{name} · рама Л', M['metal'], f, h - 2 * f, t + 0.04, x0 + f / 2, cy, z, c)
    box(f'{name} · рама П', M['metal'], f, h - 2 * f, t + 0.04, x1 - f / 2, cy, z, c)
    if w > 1.4:
        box(f'{name} · импост', M['metal'], 0.04, h - 2 * f, 0.05, cx, cy, z, c)
    box(f'{name} · стекло', M['glass'], w - 2 * f, h - 2 * f, 0.012, cx, cy, z, c)
    if sill:
        box(f'{name} · подоконник', M['innerWall'], w + 0.06, 0.03, 0.14, cx, y0 - 0.005, z - t / 2 - 0.05, c)

def windowZ(z0, z1, y0, y1, x, t=T, name='Окно', c=C_BANYA):
    # окно в торцевой стене (вдоль Z)
    w = z1 - z0; h = y1 - y0; cz = (z0 + z1) / 2; cy = (y0 + y1) / 2; f = 0.055
    box(f'{name} · рама В', M['metal'], t + 0.04, f, w, x, y1 - f / 2, cz, c)
    box(f'{name} · рама Н', M['metal'], t + 0.04, f, w, x, y0 + f / 2, cz, c)
    box(f'{name} · рама Л', M['metal'], t + 0.04, h - 2 * f, f, x, cy, z0 + f / 2, c)
    box(f'{name} · рама П', M['metal'], t + 0.04, h - 2 * f, f, x, cy, z1 - f / 2, c)
    box(f'{name} · стекло', M['glass'], 0.012, h - 2 * f, w - 2 * f, x, cy, cz, c)

# ===== наружная оболочка =====
southWin1 = dict(x0=-2.75, x1=-0.45, y0=0.55, y1=2.72)
southDoor = dict(x0=0.075, x1=0.925, y0=FLOOR, y1=2.52)
southWin3 = dict(x0=1.3, x1=2.75, y0=0.55, y1=2.55)
wallX(M['facade'], -3, 3, 1.25 - T / 2, openings=[southWin1, southDoor, southWin3], name='Фасад юг')
northWin1 = dict(x0=-2.5, x1=-1.1, y0=1.35, y1=2.45)
northVent = dict(x0=0.3, x1=0.7, y0=1.9, y1=2.3)
northWin3 = dict(x0=1.5, x1=2.3, y0=1.55, y1=2.35)
wallX(M['facade'], -3, 3, -1.25 + T / 2, openings=[northWin1, northVent, northWin3], name='Фасад север')
westWin = dict(z0=-0.35, z1=0.35, y0=1.35, y1=2.15)
wallZ(M['facade'], -1.25 + T, 1.25 - T, -3 + T / 2, openings=[westWin], name='Торец запад')
eastVent = dict(z0=-0.2, z1=0.4, y0=1.6, y1=2.2)
wallZ(M['facade'], -1.25 + T, 1.25 - T, 3 - T / 2, openings=[eastVent], name='Торец восток')

windowX(**southWin1, z=1.25 - T / 2, name='Окно комнаты отдыха')
windowX(**southWin3, z=1.25 - T / 2, name='Окно парной юг')
windowX(**northWin1, z=-1.25 + T / 2, name='Окно комнаты отдыха север')
windowX(**northVent, z=-1.25 + T / 2, sill=False, name='Вентиляция душевой')
windowX(**northWin3, z=-1.25 + T / 2, name='Окно парной север')
windowZ(westWin['z0'], westWin['z1'], westWin['y0'], westWin['y1'], -3 + T / 2, name='Окно торец запад')
windowZ(eastVent['z0'], eastVent['z1'], eastVent['y0'], eastVent['y1'], 3 - T / 2, name='Вентиляция парной')

# ===== входная дверь (открыта наружу) =====
d = southDoor; cx = (d['x0'] + d['x1']) / 2
box('Дверь · притолока', M['metal'], d['x1'] - d['x0'], 0.06, T + 0.06, cx, d['y1'] - 0.03, 1.25 - T / 2)
box('Дверь · косяк Л', M['metal'], 0.06, d['y1'] - d['y0'], T + 0.06, d['x0'] + 0.03, (d['y0'] + d['y1']) / 2, 1.25 - T / 2)
box('Дверь · косяк П', M['metal'], 0.06, d['y1'] - d['y0'], T + 0.06, d['x1'] - 0.03, (d['y0'] + d['y1']) / 2, 1.25 - T / 2)
H = d['y1'] - d['y0'] - 0.12; W = d['x1'] - d['x0'] - 0.12
leafE = empty('Дверь · створка (открыта)', d['x1'] - 0.06, d['y0'] + 0.06, 1.25 + 0.03, C_BANYA, rotY=-1.45)
for nm, w, h, dd, lx, ly, lz in [
    ('верх', W, 0.05, 0.045, W / 2, H - 0.025, 0), ('низ', W, 0.05, 0.045, W / 2, 0.025, 0),
    ('левая', 0.05, H, 0.045, 0.025, H / 2, 0), ('правая', 0.05, H, 0.045, W - 0.025, H / 2, 0)]:
    o = parent(box(f'Створка · {nm}', M['metal'], w, h, dd, 0, 0, 0), leafE)
    o.location = P(lx, ly, lz)
gl = parent(box('Створка · стекло', M['glassDoor'], W - 0.1, H - 0.1, 0.012, 0, 0, 0), leafE)
gl.location = P(W / 2, H / 2, 0)
hd = parent(box('Створка · ручка', M['metal'], 0.02, 0.5, 0.03, 0, 0, 0), leafE)
hd.location = P(W - 0.09, H / 2, 0.05)

# ===== кровля =====
box('Кровля', M['roof'], 6.36, 0.16, 2.86, 0, WT + 0.08, 0)
box('Фаска кровли', M['metal'], 6.44, 0.1, 2.94, 0, WT + 0.02, 0)
box('Снег на кровле', M['snow'], 6.3, 0.05, 2.8, 0, WT + 0.185, 0)

# ===== дымоход =====
cyl('Дымоход', M['stove'], 0.075, 0.075, 1.1, 2.5, WT + 0.55, 0.75)
bpy.ops.mesh.primitive_cone_add(vertices=20, radius1=0.16, radius2=0, depth=0.14, location=P(2.5, WT + 1.17, 0.75))
o = bpy.context.object; o.name = 'Дымоход · колпак'; o.data.materials.append(M['stove']); link(o, C_BANYA)
box('Дымоход · основание', M['metal'], 0.3, 0.06, 0.3, 2.5, WT + 0.2, 0.75)

# ===== цоколь и опоры =====
box('Цоколь', M['plinth'], 5.9, 0.3, 2.4, 0, 0.3, 0)
for px, pz in [(-2.7, -1), (-2.7, 1), (0, -1), (0, 1), (2.7, -1), (2.7, 1)]:
    box('Опора', M['concrete'], 0.3, 0.34, 0.3, px, 0.17, pz)

# ===== внутренние стены =====
door1 = dict(z0=0.25, z1=1.05, y0=FLOOR, y1=2.47)
door3 = dict(z0=0.25, z1=1.05, y0=FLOOR, y1=2.47)
wallZ(M['innerWall'], -1.13, 1.13, 0, t=TI, openings=[door1], name='Стена 01-02')
wallZ(M['innerWall'], -1.13, 1.13, 1.0, t=TI, openings=[door3], name='Стена 02-03')
for x, dd in [(0, door1), (1.0, door3)]:
    box('Наличник верх', M['darkWood'], TI + 0.04, 0.05, dd['z1'] - dd['z0'] + 0.1, x, dd['y1'] + 0.025, (dd['z0'] + dd['z1']) / 2)
    box('Пенал раздвижной двери', M['darkWood'], TI + 0.02, dd['y1'] - dd['y0'], 0.14, x, (dd['y0'] + dd['y1']) / 2, dd['z0'] + 0.07)

# ===== внутренняя обшивка наружных стен =====
L = 0.02
wallX(M['innerWall'], -2.88, 2.88, 1.13 - L / 2, y0=FLOOR, t=L, openings=[southWin1, southDoor, southWin3], c=C_INT, name='Обшивка юг')
wallX(M['innerWall'], -2.88, 2.88, -1.13 + L / 2, y0=FLOOR, t=L, openings=[northWin1, northVent, northWin3], c=C_INT, name='Обшивка север')
wallZ(M['innerWall'], -1.13 + L, 1.13 - L, -2.88 + L / 2, y0=FLOOR, t=L, openings=[westWin], c=C_INT, name='Обшивка запад')
wallZ(M['innerWall'], -1.13 + L, 1.13 - L, 2.88 - L / 2, y0=FLOOR, t=L, openings=[eastVent], c=C_INT, name='Обшивка восток')

# ===== полы и потолок =====
box('Пол · комната отдыха', M['floorWood'], 2.83, 0.02, 2.26, -1.465, FLOOR - 0.01, 0, C_INT)
box('Пол · душевая', M['tile'], 0.9, 0.02, 2.26, 0.5, FLOOR - 0.01, 0, C_INT)
box('Пол · парная', M['floorWood'], 1.83, 0.02, 2.26, 1.965, FLOOR - 0.01, 0, C_INT)
box('Потолок', M['ceiling'], 5.76, 0.02, 2.26, 0, WT - 0.01, 0, C_INT)
for w, x, z in [(2.83, -1.465, -1.1), (2.83, -1.465, 1.1), (1.83, 1.965, -1.1), (1.83, 1.965, 1.1)]:
    box('Плинтус', M['darkWood'], w, 0.05, 0.015, x, FLOOR + 0.025, z, C_INT)

# ===== терраса =====
deckTop = 0.44
box('Терраса · настил', M['deck'], 7.6, 0.06, 2.1, 0.7, deckTop - 0.03, 2.3, C_TER)
box('Терраса · юбка фронт', M['plinth'], 7.6, 0.28, 0.04, 0.7, deckTop - 0.2, 3.33, C_TER)
box('Терраса · юбка Л', M['plinth'], 0.04, 0.28, 2.1, -3.08, deckTop - 0.2, 2.3, C_TER)
box('Терраса · юбка П', M['plinth'], 0.04, 0.28, 2.1, 4.48, deckTop - 0.2, 2.3, C_TER)
box('Ступень 1', M['deck'], 2.0, 0.05, 0.32, -0.5, deckTop - 0.17, 3.51, C_TER)
box('Ступень 2', M['deck'], 2.0, 0.05, 0.32, -0.5, deckTop - 0.33, 3.83, C_TER)

# дровник
fwE = empty('Дровник', 3.85, deckTop, 1.75, C_TER)
for nm, w, h, dd, lx, ly, lz, mt in [
    ('дно', 1.1, 0.05, 0.55, 0, 0.025, 0, M['metal']), ('верх', 1.1, 0.05, 0.55, 0, 0.82, 0, M['metal']),
    ('бок Л', 0.05, 0.85, 0.55, -0.525, 0.425, 0, M['metal']), ('бок П', 0.05, 0.85, 0.55, 0.525, 0.425, 0, M['metal']),
    ('задняя', 1.1, 0.85, 0.05, 0, 0.425, -0.25, M['metal'])]:
    o = parent(box(f'Дровник · {nm}', mt, w, h, dd, 0, 0, 0, C_TER), fwE)
    o.location = P(lx, ly, lz)
rnd_s = [13]
def rnd():
    rnd_s[0] = (rnd_s[0] * 16807) % 2147483647
    return rnd_s[0] / 2147483647
for r in range(3):
    for cc in range(6):
        lr = 0.055 + rnd() * 0.02
        lx = -0.42 + cc * 0.17 + (r % 2) * 0.05; ly = 0.13 + r * 0.21
        o = cyl('Полено', M['logs'], lr, lr * (0.9 + rnd() * 0.2), 0.45, 0, 0, 0, C_TER, rotX=math.pi / 2, n=10)
        parent(o, fwE); o.location = P(lx, ly, 0)

# ===== 01 комната отдыха =====
def mkBench(w, dd, x, z):
    e = empty('Лавка', x, FLOOR, z, C_INT)
    a = parent(box('Лавка · основание', M['innerWall'], w, 0.32, dd, 0, 0, 0, C_INT), e); a.location = P(0, 0.16, 0)
    s = parent(box('Лавка · подушка', M['cushion'], w - 0.02, 0.1, dd - 0.02, 0, 0, 0, C_INT), e); s.location = P(0, 0.37, 0)
mkBench(0.55, 1.55, -2.585, 0.31)
mkBench(1.45, 0.55, -2.135, -0.825)
box('Лавка · спинка запад', M['cushion'], 0.1, 0.42, 1.55, -2.83, FLOOR + 0.62, 0.31, C_INT)
box('Лавка · спинка север', M['cushion'], 1.45, 0.42, 0.1, -2.135, FLOOR + 0.62, -1.07, C_INT)

# стол
tbE = empty('Стол', -1.35, FLOOR, -0.35, C_INT)
o = parent(box('Стол · столешница', M['darkWood'], 0.8, 0.045, 0.8, 0, 0, 0, C_INT), tbE); o.location = P(0, 0.44, 0)
for sx, sz in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
    o = parent(box('Стол · нога', M['darkWood'], 0.05, 0.42, 0.05, 0, 0, 0, C_INT), tbE); o.location = P(sx * 0.33, 0.21, sz * 0.33)
o = parent(box('Книга 1', M['cushion'], 0.24, 0.035, 0.17, 0, 0, 0, C_INT), tbE); o.location = P(0.1, 0.48, -0.08)
o = parent(box('Книга 2', M['fabric'], 0.2, 0.03, 0.14, 0, 0, 0, C_INT), tbE); o.location = P(0.12, 0.515, -0.07)

# кресла
def loungeChair(x, z, rotY, idx):
    e = empty(f'Кресло {idx}', x, FLOOR, z, C_INT, rotY=rotY)
    W_, D_, seatH = 0.66, 0.72, 0.38
    def fr(w, h, dd, lx, ly, lz, rx=0.0):
        o = parent(box(f'Кресло{idx} · рама', M['darkWood'], w, h, dd, 0, 0, 0, C_INT), e)
        o.location = P(lx, ly, lz)
        if rx: o.rotation_euler.x = rx
    for s in (-1, 1):
        fr(0.05, seatH, D_ - 0.06, s * (W_ / 2 - 0.025), seatH / 2, 0)
        fr(0.05, 0.62, 0.05, s * (W_ / 2 - 0.025), seatH + 0.28, -D_ / 2 + 0.10, rx=0.32)
        fr(0.05, 0.045, D_ - 0.02, s * (W_ / 2 - 0.025), seatH + 0.075, 0.01)
        fr(0.055, 0.05, D_ - 0.04, s * (W_ / 2 - 0.03), seatH + 0.22, -0.02)
    fr(W_ - 0.06, 0.05, 0.06, 0, seatH - 0.02, D_ / 2 - 0.06)
    o = parent(box(f'Кресло{idx} · сиденье', M['fabric'], W_ - 0.12, 0.14, D_ - 0.14, 0, 0, 0, C_INT), e); o.location = P(0, seatH + 0.06, 0.02)
    o = parent(box(f'Кресло{idx} · спинка', M['fabric'], W_ - 0.12, 0.5, 0.13, 0, 0, 0, C_INT), e); o.location = P(0, seatH + 0.30, -D_ / 2 + 0.16); o.rotation_euler.x = 0.32
loungeChair(-1.75, 0.5, math.pi + 0.22, 1)
loungeChair(-0.75, 0.5, math.pi - 0.18, 2)

# торшер
lpE = empty('Торшер', -2.55, FLOOR, 0.85, C_INT)
o = parent(cyl('Торшер · база', M['metal'], 0.16, 0.18, 0.02, 0, 0, 0, C_INT, n=24), lpE); o.location = P(0, 0.01, 0)
o = parent(cyl('Торшер · стойка', M['metal'], 0.012, 0.012, 1.45, 0, 0, 0, C_INT, n=12), lpE); o.location = P(0, 0.74, 0)
o = parent(cyl('Торшер · абажур', M['lampShade'], 0.14, 0.19, 0.24, 0, 0, 0, C_INT, n=24), lpE); o.location = P(0, 1.52, 0)

# ковёр
cyl('Ковёр', M['rug'], 0.85, 0.85, 0.012, -1.3, FLOOR + 0.008, 0.25, C_INT, n=28)

# растение
plE = empty('Растение', -0.25, FLOOR, -0.9, C_INT)
o = parent(cyl('Кашпо', M['pot'], 0.14, 0.11, 0.24, 0, 0, 0, C_INT, n=18), plE); o.location = P(0, 0.12, 0)
for s, a, t in [(1, 0, 0), (0.9, 2.1, 0.06), (0.85, 4.2, 0.03), (0.7, 1.1, 0.14), (0.7, 3.3, 0.12)]:
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.16)
    o = bpy.context.object; o.name = 'Листва'; o.data.materials.append(M['plant']); link(o, C_INT)
    parent(o, plE)
    o.scale = (0.5 * s, 0.5 * s, 1.1 * s)
    o.location = P(math.cos(a) * 0.07, 0.42 + t, math.sin(a) * 0.07)
    o.rotation_euler.x = -math.sin(a) * 0.4
    o.rotation_euler.y = math.cos(a) * 0.4

# шторы (волна)
def curtain(x, z, w=0.85, h=2.3):
    seg = 24
    verts = []
    for i in range(seg + 1):
        u = i / seg - 0.5
        wave = math.sin((u + 0.5) * math.pi * 6) * 0.045
        verts.append((u * w, wave, -h / 2))
        verts.append((u * w, wave, h / 2))
    faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(seg)]
    me = bpy.data.meshes.new('Штора')
    me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new('Штора', me)
    o.data.materials.append(M['curtain'])
    o.location = P(x, 1.75, z)
    C_INT.objects.link(o)
curtain(-2.6, 1.02)
curtain(-0.62, 1.02)

# ===== 02 душевая =====
box('Душ · стекло', M['glassDoor'], 0.54, 1.95, 0.01, 0.32, FLOOR + 0.975, -0.35, C_INT)
box('Душ · профиль', M['metal'], 0.58, 0.05, 0.03, 0.32, FLOOR + 1.95, -0.35, C_INT)
box('Душ · трап', M['floorWood'], 0.8, 0.03, 0.7, 0.5, FLOOR + 0.015, -0.75, C_INT)
box('Душ · стойка', M['metal'], 0.03, 1.1, 0.03, 0.5, FLOOR + 1.5, -1.08, C_INT)
cyl('Душ · лейка', M['metal'], 0.11, 0.11, 0.012, 0.5, FLOOR + 2.05, -0.95, C_INT)
box('Душ · кронштейн', M['metal'], 0.03, 0.03, 0.2, 0.5, FLOOR + 2.08, -1.0, C_INT)
box('Душ · смеситель', M['metal'], 0.16, 0.22, 0.06, 0.5, FLOOR + 1.15, -1.08, C_INT)
box('Полотенце', M['towel'], 0.3, 0.5, 0.04, 0.85, FLOOR + 1.35, 0.6, C_INT)

# ===== 03 парная =====
def tier(w, dd, x, z, h, nm):
    e = empty(nm, x, FLOOR, z, C_INT)
    a = parent(box(f'{nm} · настил', M['benchWood'], w, 0.05, dd, 0, 0, 0, C_INT), e); a.location = P(0, h - FLOOR, 0)
    for sx in (-1, 1):
        o = parent(box(f'{nm} · опора', M['benchWood'], 0.05, h - FLOOR, dd - 0.06, 0, 0, 0, C_INT), e)
        o.location = P(sx * (w / 2 - 0.05), (h - FLOOR) / 2 - 0.02, 0)
tier(1.83, 0.55, 1.965, -0.835, FLOOR + 0.55, 'Полок нижний')
tier(1.83, 0.55, 1.965, -0.835, FLOOR + 1.1, 'Полок верхний')
tier(0.55, 1.1, 2.605, -0.01, FLOOR + 1.1, 'Полок восточный')
box('Полок · спинка', M['benchWood'], 1.83, 0.35, 0.03, 1.965, FLOOR + 1.35, -1.08, C_INT)
box('Полок · LED', M['ledStrip'], 1.7, 0.015, 0.02, 1.965, FLOOR + 1.06, -1.07, C_INT)
box('Подголовник', M['benchWood'], 0.4, 0.06, 0.14, 1.6, FLOOR + 1.16, -0.8, C_INT)

# печь
stE = empty('Печь-каменка', 2.5, FLOOR, 0.75, C_INT)
o = parent(box('Печь · корпус', M['stove'], 0.52, 0.72, 0.42, 0, 0, 0, C_INT), stE); o.location = P(0, 0.36 + 0.1, 0)
o = parent(box('Печь · дверца', M['metal'], 0.34, 0.4, 0.02, 0, 0, 0, C_INT), stE); o.location = P(0, 0.42, 0.215)
o = parent(cyl('Печь · каменка', M['stove'], 0.24, 0.2, 0.16, 0, 0, 0, C_INT, n=12), stE); o.location = P(0, 0.9, 0)
rnd_s[0] = 7
for i in range(14):
    rr = 0.05 + rnd() * 0.035
    a = rnd() * math.pi * 2; rad = rnd() * 0.13
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rr)
    o = bpy.context.object; o.name = 'Камень'; o.data.materials.append(M['stones']); link(o, C_INT)
    parent(o, stE)
    o.location = P(math.cos(a) * rad, 0.93 + rnd() * 0.08, math.sin(a) * rad)
    o.rotation_euler = (rnd() * 3, rnd() * 3, rnd() * 3)
for sx, sz in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
    o = parent(box('Печь · ножка', M['stove'], 0.04, 0.1, 0.04, 0, 0, 0, C_INT), stE); o.location = P(sx * 0.2, 0.05, sz * 0.15)

# ведро
bkE = empty('Ведро', 1.85, FLOOR, 0.85, C_INT)
o = parent(cyl('Ведро · корпус', M['darkWood'], 0.13, 0.11, 0.22, 0, 0, 0, C_INT, n=16), bkE); o.location = P(0, 0.11, 0)
o = parent(cyl('Ведро · дно', M['darkWood'], 0.11, 0.11, 0.015, 0, 0, 0, C_INT, n=16), bkE); o.location = P(0, 0.008, 0)

# ===== бра на фасаде =====
for sx in (-0.22, 1.13):
    box('Бра', M['sconce'], 0.07, 0.16, 0.06, sx, 2.35, 1.3, C_BANYA)

# ===== свет =====
def point(name, color, energy, x, y, z):
    li = bpy.data.lights.new(name, 'POINT')
    li.color = srgb(color)[:3]
    li.energy = energy
    o = bpy.data.objects.new(name, li)
    o.location = P(x, y, z)
    C_LIGHT.objects.link(o)
point('Свет · Комната отдыха', '#FFD9A8', 60, -1.5, 2.55, 0)
point('Свет · Душевая', '#FFF0DC', 30, 0.5, 2.5, 0.3)
point('Свет · Парная', '#FFC98A', 50, 1.9, 2.5, 0.2)
for sx in (-0.22, 1.13):
    point('Бра · свет', '#FFC27D', 20, sx, 2.25, 1.45)

# солнце + мир
sun_d = bpy.data.lights.new('Солнце', 'SUN'); sun_d.energy = 3; sun_d.color = srgb('#FFFFFF')[:3]
sun = bpy.data.objects.new('Солнце', sun_d)
sun.rotation_euler = (math.radians(55), 0, math.radians(30))
C_LIGHT.objects.link(sun)
world = bpy.data.worlds.new('Мир · Зимний день')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = srgb('#DFE5EC')
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
bpy.context.scene.world = world

# ===== участок: снег =====
box('Участок · снег', M['groundSnow'], 40, 0.1, 40, 0.7, -0.05, 1.8, C_SITE)

# ===== камера для превью =====
cam_d = bpy.data.cameras.new('Камера')
cam = bpy.data.objects.new('Камера', cam_d)
cam.location = P(11.5, 4.4, 13.5)
C_SITE.objects.link(cam)
tgt = bpy.data.objects.new('Камера · цель', None)
tgt.location = P(0.5, 1.5, 0.6)
C_SITE.objects.link(tgt)
con = cam.constraints.new('TRACK_TO'); con.target = tgt; con.track_axis = 'TRACK_NEGATIVE_Z'; con.up_axis = 'UP_Y'
bpy.context.scene.camera = cam

# ===== сохранение + рендер + экспорт =====
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
print('[banya] saved:', BLEND_PATH)

sc = bpy.context.scene
sc.render.engine = 'BLENDER_EEVEE'
sc.render.resolution_x = 1280; sc.render.resolution_y = 720
sc.render.filepath = PREVIEW
os.makedirs(os.path.dirname(PREVIEW), exist_ok=True)
bpy.ops.render.render(write_still=True)
print('[banya] preview:', PREVIEW)

bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
