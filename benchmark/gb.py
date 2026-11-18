"""Pokemon Red memory reading shared by build.py (truth) and nothing else.

Addresses are Pokemon Red (US) WRAM, from the pret disassembly (pret/pokered ram/wram.asm,
constants/map_constants.asm, constants/sprite_constants.asm); the Gen 1 character table is
pret/pokered constants/charmap.asm (subset: what appears on screen in the early game).
"""
import re

TILEMAP = 0xC3A0          # wTileMap, 20x18 tiles: the screen as the game drew it
IS_IN_BATTLE = 0xD057     # wIsInBattle (0 none, 1 wild, 2 trainer, 0xFF lost)
CUR_MAP = 0xD35E          # wCurMap
Y_COORD, X_COORD = 0xD361, 0xD362
TILESET = 0xD367          # wCurMapTileset
WALK_COUNTER = 0xCFC5     # wWalkCounter (nonzero while a step is animating)
JOY_IGNORE = 0xCD6B       # wJoyIgnore (scripted events lock the pad)
PLAYER_FACING = 0xC109    # wSpritePlayerStateData1FacingDirection
SPRITE_DATA1 = 0xC100     # wSpriteStateData1: 16 sprites x 16 bytes (+0 picture id, +2 image index, +4 y px, +6 x px)
ENEMY_HP = 0xCFE6         # wEnemyMonHP (2 bytes, big endian)
ENEMY_LEVEL = 0xCFF3      # wEnemyMonLevel
ENEMY_MAX_HP = 0xCFF4     # wEnemyMonMaxHP (2 bytes, big endian)

FACING = {0x0: "down", 0x4: "up", 0x8: "left", 0xC: "right"}

# picture ids (sprite_constants.asm) >= SPRITE_POKE_BALL ($3D) are still objects (balls, books/dex, clipboards, ...)
FIRST_OBJECT_SPRITE = 0x3D

CH = {0x7F: " ", 0xBA: "é", 0xBB: "'d", 0xBC: "'l", 0xBD: "'s", 0xBE: "'t", 0xBF: "'v", 0xE0: "'", 0xE1: "PK", 0xE2: "MN",
      0xE3: "-", 0xE4: "'r", 0xE5: "'m", 0xE6: "?", 0xE7: "!", 0xE8: ".", 0xEC: "▷", 0xED: "▶", 0xEE: "▼", 0xEF: "♂", 0xF1: "×",
      0xF2: ".", 0xF3: "/", 0xF4: ",", 0xF5: "♀", 0x9A: "(", 0x9B: ")", 0x9C: ":", 0x9D: ";", 0x9E: "[", 0x9F: "]", 0x6E: "<LV>"}
for _i in range(26):
    CH[0x80 + _i] = chr(65 + _i)
    CH[0xA0 + _i] = chr(97 + _i)
for _i in range(10):
    CH[0xF6 + _i] = str(_i)

# map id -> kind of place (map_constants.asm; everything a Pallet-to-Pewter game can reach)
PLACE = {}
for _m in range(0, 11):
    PLACE[_m] = "outdoors"            # towns and cities
for _m in range(12, 37):
    PLACE[_m] = "outdoors"            # ROUTE_1 .. ROUTE_25
PLACE.update({
    37: "house", 38: "house", 39: "house",          # REDS_HOUSE_1F/2F, BLUES_HOUSE
    40: "lab",                                      # OAKS_LAB
    41: "pokemon_center", 58: "pokemon_center",     # VIRIDIAN_/PEWTER_POKECENTER
    42: "poke_mart", 56: "poke_mart",               # VIRIDIAN_/PEWTER_MART
    44: "house", 48: "house", 55: "house", 57: "house",  # nickname / trade / nidoran / speech houses
    45: "gym", 54: "gym",                           # VIRIDIAN_GYM, PEWTER_GYM
    47: "gate", 49: "gate", 50: "gate",             # forest gates, route 2 gate
    51: "forest",                                   # VIRIDIAN_FOREST
    52: "museum", 53: "museum",                     # MUSEUM_1F/2F
})  # 43 VIRIDIAN_SCHOOL_HOUSE left out on purpose: a house with desks (ambiguous)


def tiles(m):
    return [[m[TILEMAP + 20 * r + c] for c in range(20)] for r in range(18)]


def decode_row(row):
    return "".join(CH.get(x, "") if x != 0x6E else ":L" for x in row)


def screen_text(t):
    return "\n".join(decode_row(row).rstrip() for row in t)


def dialogue_box(t):
    """The standard dialogue box: rows 12-17, full width (border tiles 0x79 top-left, 0x7E bottom-right)."""
    return t[12][0] == 0x79 and t[17][19] == 0x7E


def dialogue_text(t):
    return "\n".join(decode_row(t[r][1:19]).replace("▼", "").rstrip() for r in (14, 16)).strip("\n")


def arrows(t):
    return [(r, c) for r, row in enumerate(t) for c, x in enumerate(row) if x == 0xED]


BATTLE_WORDS = ("FIGHT", "PKMN", "ITEM", "RUN")


def cursor_label(t, r, c):
    """The menu entry the filled cursor (▶) points at: the text right of it up to a wide gap, a border or another cursor."""
    out = ""
    for x in t[r][c + 1:]:
        if x not in CH or x in (0xEC, 0xED) or (x == 0x7F and out.endswith(" ")):
            break
        out += CH[x]
    label = out.strip()
    for w in BATTLE_WORDS:
        if label.startswith(w):
            return w
    return label


def battle_hud(t):
    """Enemy name (row 0) and level (row 1), player HP numbers (rows 8-11), if the battle HUD is drawn."""
    out = {}
    name = decode_row(t[0][1:11]).strip()
    lv = re.search(r":L(\d+)", decode_row(t[1][0:10]))
    if name and re.fullmatch(r"[A-Z0-9 .'♂♀-]+", name) and lv:
        out["enemy_name"] = name
        out["enemy_level"] = int(lv.group(1))
    for r in range(8, 12):
        m = re.search(r"(\d+)/\s*(\d+)", decode_row(t[r][9:20]))
        if m:
            out["player_hp"] = f"{int(m.group(1))}/{int(m.group(2))}"
    bar = t[2][4:10]
    if t[2][3] == 0x62 and t[2][10] == 0x6C and all(0x63 <= x <= 0x6B for x in bar):
        out["enemy_bar_px"] = sum(x - 0x63 for x in bar)   # 6 tiles x 8 px; tile 0x63 + n = n px filled
    return out


def word(m, a):
    return m[a] << 8 | m[a + 1]


def visible_sprites(m):
    """Non-player sprites the game has on screen (image index != 0xFF), with picture id and screen pixels."""
    out = []
    for n in range(1, 16):
        b = SPRITE_DATA1 + 16 * n
        if m[b] and m[b + 2] != 0xFF:
            out.append({"slot": n, "picture": m[b], "y": m[b + 4], "x": m[b + 6]})
    return out
