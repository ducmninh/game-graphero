"""World: tile-based map with houses, props, doors, collidables.

The world is composed of:
- A background tile grid (grass / road / dirt / concrete / sand)
- A list of solid rects (walls, houses, fences, containers, ...) for collision
- A list of props (cars, oil drums, crates, trees) for visuals + some collidable
- A list of pickups (gold, ammo, medkit)
- A list of building interiors (we render them differently if biome wants it)

Each level builds its own World via LevelBuilder.
"""
from __future__ import annotations
import math
import random
import pygame
from utils import Vec, draw_text
from settings import (
    TILE, SCREEN_WIDTH, SCREEN_HEIGHT, ROAD, ROAD_LINE, GRASS, GRASS_DARK, DIRT, CONCRETE,
    WALL_TAN, WALL_WHITE, ROOF_RED, ROOF_BLUE, BROWN, DARK_BROWN,
    DARK_GRAY, GRAY, LIGHT_GRAY, SAND, RED, YELLOW, GREEN, BLUE,
    DARK_GREEN, NEON_PINK, NEON_CYAN, BLACK, WHITE, ASH,
)


# ============================================================
# TILE TYPES
# ============================================================
T_GRASS = 0
T_ROAD_H = 1     # horizontal road (with dashed line)
T_ROAD_V = 2     # vertical road
T_ROAD_X = 3     # intersection
T_DIRT = 4
T_CONCRETE = 5
T_SAND = 6
T_GRASS_DARK = 7
T_FLOOR_WOOD = 8
T_FLOOR_TILE = 9
T_WATER = 10
T_ASH = 11        # industrial dark floor


TILE_COLORS = {
    T_GRASS: GRASS,
    T_ROAD_H: ROAD,
    T_ROAD_V: ROAD,
    T_ROAD_X: ROAD,
    T_DIRT: DIRT,
    T_CONCRETE: CONCRETE,
    T_SAND: SAND,
    T_GRASS_DARK: GRASS_DARK,
    T_FLOOR_WOOD: (130, 90, 55),
    T_FLOOR_TILE: (210, 210, 220),
    T_WATER: (60, 110, 180),
    T_ASH: ASH,
}


# ============================================================
# Pickup types
# ============================================================
P_GOLD = "gold"
P_MEDKIT = "medkit"
P_AMMO = "ammo"
P_KEY = "key"


class Pickup:
    def __init__(self, pos: Vec, kind: str, amount: int = 0):
        self.pos = Vec(pos)
        self.kind = kind
        self.amount = amount
        self.bob = random.uniform(0, math.tau)
        self.alive = True

    def update(self, dt, t):
        self.bob += dt * 3

    def draw(self, surf, cam):
        p = cam.apply(self.pos)
        offset = math.sin(self.bob) * 3
        cx, cy = p[0], int(p[1] + offset)
        if self.kind == P_GOLD:
            pygame.draw.circle(surf, (110, 80, 0), (cx, cy + 1), 11)
            pygame.draw.circle(surf, (255, 215, 0), (cx, cy), 10)
            pygame.draw.circle(surf, (255, 240, 130), (cx - 3, cy - 3), 3)
            draw_text(surf, "$", (cx, cy), size=14, color=(110, 80, 0),
                      bold=True, center=True, shadow=False)
        elif self.kind == P_MEDKIT:
            pygame.draw.rect(surf, (240, 240, 240),
                             (cx - 11, cy - 9 + offset, 22, 18), border_radius=3)
            pygame.draw.rect(surf, (210, 40, 40),
                             (cx - 3, cy - 7 + offset, 6, 14))
            pygame.draw.rect(surf, (210, 40, 40),
                             (cx - 9, cy - 1 + offset, 18, 4))
        elif self.kind == P_AMMO:
            pygame.draw.rect(surf, (140, 100, 40),
                             (cx - 12, cy - 8 + offset, 24, 14), border_radius=2)
            pygame.draw.rect(surf, (200, 170, 80),
                             (cx - 12, cy - 8 + offset, 24, 5))
            draw_text(surf, "AMMO", (cx, cy + offset), size=10,
                      color=(0, 0, 0), bold=True, center=True, shadow=False)
        elif self.kind == P_KEY:
            pygame.draw.circle(surf, (255, 215, 0), (cx - 4, cy), 7, 3)
            pygame.draw.rect(surf, (255, 215, 0), (cx, cy - 2, 14, 4))
            pygame.draw.rect(surf, (255, 215, 0), (cx + 8, cy + 2, 4, 4))


# ============================================================
# Sprite cache + drawing helpers for Solid props
#
# Each `_build_*` function returns a tuple of (surface, offset_x, offset_y)
# where the surface is the pre-rendered art and the offsets indicate where
# to blit the surface relative to the solid rect's top-left (so visuals can
# extend beyond the collision rect, e.g. roof overhangs and wheels).
# Surfaces are cached per (kind, size, color) so each frame just blits.
# ============================================================
_SPRITE_CACHE: dict[tuple, tuple[pygame.Surface, int, int]] = {}


def _shade(color, delta):
    """Return color clamped after adding delta to each channel."""
    return (max(0, min(255, color[0] + delta)),
            max(0, min(255, color[1] + delta)),
            max(0, min(255, color[2] + delta)))


def _norm_color(c):
    if c is None:
        return None
    return (int(c[0]), int(c[1]), int(c[2]))


def _blit_cached(surf, r, key, builder):
    cached = _SPRITE_CACHE.get(key)
    if cached is None:
        cached = builder()
        _SPRITE_CACHE[key] = cached
    img, ox, oy = cached
    surf.blit(img, (r.left + ox, r.top + oy))


# ---------- Wall ----------
def _build_wall(w, h, color):
    base = color or (110, 110, 115)
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, _shade(base, -35), (0, 0, w, h))
    pygame.draw.rect(surf, base, (1, 1, w - 2, h - 2))
    # top highlight
    pygame.draw.rect(surf, _shade(base, +25), (2, 2, w - 4, max(2, h // 10)))
    # bottom shadow
    pygame.draw.rect(surf, _shade(base, -25),
                     (2, h - max(3, h // 8) - 1, w - 4, max(3, h // 8)))
    # subtle brick lines if the wall is large enough
    if w >= 32 and h >= 32:
        brick_h = max(8, h // 5)
        for j, y in enumerate(range(brick_h, h - 2, brick_h)):
            pygame.draw.line(surf, _shade(base, -20),
                             (2, y), (w - 2, y), 1)
            offset = (brick_h // 2) if (j % 2 == 0) else 0
            for x in range(2 + offset, w - 2, brick_h):
                pygame.draw.line(surf, _shade(base, -20),
                                 (x, y - brick_h), (x, y), 1)
    pygame.draw.rect(surf, (0, 0, 0), (0, 0, w, h), 2)
    return (surf, 0, 0)


# ---------- House ----------
def _build_house(w, h, wall, roof):
    """Polished cartoon house with gabled tile roof, stone foundation,
    framed shuttered windows + flower boxes, paneled door with awning,
    porch posts, chimney, dormer + weathervane on top of the gable.

    The drawing is laid out in three vertical bands:
        - top: gable + roof slope (extends ABOVE the collision rect)
        - middle: wall body with siding, windows, door
        - bottom: stone foundation strip + ground shadow
    """
    roof_overhang = 10
    roof_h = max(30, min(h // 2 - 4, h // 3 + 14))
    pad_top = roof_h + max(20, roof_h // 2 + 6)  # gable + weathervane room
    pad_x = roof_overhang + 6
    pad_bot = 8
    surf = pygame.Surface((w + 2 * pad_x, h + pad_top + pad_bot),
                          pygame.SRCALPHA)

    body_x, body_y = pad_x, pad_top
    body_rect = pygame.Rect(body_x, body_y, w, h)

    # ground shadow
    shadow_w = w + 32
    shadow = pygame.Surface((shadow_w, 16), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow, (0, 0, 0, 110), shadow.get_rect())
    surf.blit(shadow, (body_x + w // 2 - shadow_w // 2, body_y + h - 4))

    # ── Wall body with subtle horizontal gradient ──────────────
    light_wall = _shade(wall, +12)
    right_wall = _shade(wall, -30)
    wall_top = body_y + max(8, roof_h // 4)
    for i in range(w):
        t = i / max(1, w - 1)
        col = (
            int(light_wall[0] * (1 - t) + right_wall[0] * t),
            int(light_wall[1] * (1 - t) + right_wall[1] * t),
            int(light_wall[2] * (1 - t) + right_wall[2] * t),
        )
        pygame.draw.line(surf, col,
                         (body_x + i, wall_top),
                         (body_x + i, body_y + h))

    # ── Stone foundation strip ─────────────────────────────────
    foundation_h = max(12, h // 10)
    foundation_rect = pygame.Rect(body_x - 3, body_y + h - foundation_h,
                                  w + 6, foundation_h + 3)
    stone = (118, 110, 100)
    pygame.draw.rect(surf, _shade(stone, -20), foundation_rect)
    # stone "blocks" with irregular sizing
    block_w = 14
    rnd = random.Random(hash((w, h, wall[0], wall[1], wall[2])) & 0xFFFF)
    rows = max(1, foundation_h // 8)
    for r in range(rows):
        ry = foundation_rect.top + r * 8
        offset = (block_w // 2) if (r % 2) else 0
        for x in range(foundation_rect.left + offset, foundation_rect.right, block_w):
            bw = block_w + rnd.randint(-2, 2)
            stone_col = _shade(stone, rnd.randint(-12, 12))
            pygame.draw.rect(surf, stone_col, (x, ry, bw, 8))
            pygame.draw.rect(surf, _shade(stone, -45),
                             (x, ry, bw, 8), 1)
            # tiny stone highlight
            pygame.draw.line(surf, _shade(stone, +25),
                             (x + 1, ry + 1), (x + bw - 2, ry + 1), 1)

    # ── Corner pillars / trim ──────────────────────────────────
    pillar_w = max(7, w // 16)
    pillar_col = _shade(wall, +6)
    pygame.draw.rect(surf, pillar_col,
                     (body_x, wall_top, pillar_w,
                      h - (wall_top - body_y) - foundation_h + 4))
    pygame.draw.rect(surf, _shade(wall, -36),
                     (body_x + w - pillar_w, wall_top,
                      pillar_w, h - (wall_top - body_y) - foundation_h + 4))
    # pillar trim outlines
    pygame.draw.line(surf, _shade(wall, -40),
                     (body_x + pillar_w - 1, wall_top),
                     (body_x + pillar_w - 1, body_y + h - foundation_h),
                     1)
    pygame.draw.line(surf, _shade(wall, -45),
                     (body_x + w - pillar_w, wall_top),
                     (body_x + w - pillar_w, body_y + h - foundation_h),
                     1)

    # ── Horizontal siding (clapboards) ─────────────────────────
    for y in range(wall_top + 12, body_y + h - foundation_h - 4, 8):
        pygame.draw.line(surf, _shade(wall, -22),
                         (body_x + pillar_w, y),
                         (body_x + w - pillar_w, y), 1)
        pygame.draw.line(surf, _shade(wall, +14),
                         (body_x + pillar_w, y + 1),
                         (body_x + w - pillar_w, y + 1), 1)

    # decorative trim under the roof (header band)
    header_h = max(6, roof_h // 6)
    header_y = wall_top - header_h + 2
    pygame.draw.rect(surf, _shade(wall, +20),
                     (body_x, header_y, w, header_h))
    pygame.draw.line(surf, _shade(wall, -45),
                     (body_x, header_y), (body_x + w, header_y), 1)
    pygame.draw.line(surf, _shade(wall, -45),
                     (body_x, header_y + header_h),
                     (body_x + w, header_y + header_h), 1)
    # tiny dentil pattern under header
    for x in range(body_x + 4, body_x + w - 4, 6):
        pygame.draw.rect(surf, _shade(wall, -30),
                         (x, header_y + header_h - 2, 3, 2))

    # ── Roof (main hip-style with central gable) ───────────────
    roof_color = roof
    roof_shade = _shade(roof, -38)
    roof_hi = _shade(roof, +28)
    roof_mid = _shade(roof, -16)
    roof_rect = pygame.Rect(body_x - roof_overhang,
                            body_y - 4,
                            w + 2 * roof_overhang, roof_h)
    pygame.draw.rect(surf, roof_color, roof_rect)

    # central gable triangle
    gable_h = max(14, roof_h // 2 + 4)
    gable_w = min(max(48, w // 2), w - 8)
    gable_left = (roof_rect.centerx - gable_w // 2, roof_rect.top + 2)
    gable_right = (roof_rect.centerx + gable_w // 2, roof_rect.top + 2)
    gable_peak = (roof_rect.centerx, roof_rect.top - gable_h)
    pygame.draw.polygon(surf, roof_color,
                        [gable_peak, gable_left, gable_right])
    # gable shadow
    pygame.draw.polygon(surf, roof_shade,
                        [gable_peak,
                         (roof_rect.centerx + gable_w // 4, gable_peak[1] + gable_h // 2),
                         gable_right])
    # gable bright edge
    pygame.draw.line(surf, roof_hi, gable_peak,
                     (gable_left[0] + 2, gable_left[1] + 2), 2)

    # gable face: small attic round window in the triangle
    attic_r = max(3, min(gable_w, gable_h) // 7)
    if attic_r >= 3:
        ax = roof_rect.centerx
        ay = gable_peak[1] + gable_h // 2 + 4
        pygame.draw.circle(surf, _shade(wall, +15), (ax, ay), attic_r + 1)
        pygame.draw.circle(surf, (170, 215, 235), (ax, ay), attic_r)
        pygame.draw.circle(surf, (90, 140, 175), (ax, ay), attic_r, 1)
        # cross mullion
        pygame.draw.line(surf, (50, 50, 50),
                         (ax - attic_r, ay), (ax + attic_r, ay), 1)
        pygame.draw.line(surf, (50, 50, 50),
                         (ax, ay - attic_r), (ax, ay + attic_r), 1)

    # weathervane on the gable peak
    wv_top = (gable_peak[0], gable_peak[1] - 8)
    pygame.draw.line(surf, (60, 60, 70), gable_peak, wv_top, 2)
    pygame.draw.polygon(surf, (90, 90, 100),
                        [(wv_top[0] - 3, wv_top[1] + 2),
                         (wv_top[0] + 4, wv_top[1] + 2),
                         (wv_top[0] + 4, wv_top[1] - 1)])
    pygame.draw.circle(surf, (220, 200, 80), wv_top, 2)

    # tile rows (two-tone for depth)
    tile_row_h = 7
    for r_idx, row in enumerate(range(0, roof_h, tile_row_h)):
        ry = roof_rect.top + row + tile_row_h - 1
        if ry < roof_rect.bottom - 1:
            band_col = roof_mid if (r_idx % 2 == 0) else roof_shade
            pygame.draw.line(surf, band_col,
                             (roof_rect.left + 1, ry),
                             (roof_rect.right - 1, ry), 1)
    # vertical tile divisions (staggered)
    for r_idx, ry in enumerate(range(roof_rect.top, roof_rect.bottom, tile_row_h)):
        offset = (tile_row_h) if (r_idx % 2) else 0
        for x in range(roof_rect.left + 2 + offset, roof_rect.right - 2, 14):
            pygame.draw.line(surf, roof_shade,
                             (x, ry), (x, ry + tile_row_h), 1)
    # ridge highlight
    pygame.draw.line(surf, roof_hi,
                     (roof_rect.left + 4, roof_rect.top + 2),
                     (roof_rect.right - 4, roof_rect.top + 2), 2)
    pygame.draw.line(surf, _shade(roof, +50),
                     (roof_rect.left + 4, roof_rect.top + 3),
                     (roof_rect.right - 4, roof_rect.top + 3), 1)
    # roof drip-shadow
    pygame.draw.line(surf, _shade(roof, -60),
                     (roof_rect.left, roof_rect.bottom - 2),
                     (roof_rect.right, roof_rect.bottom - 2), 2)
    # gutter
    pygame.draw.rect(surf, (90, 90, 100),
                     (roof_rect.left, roof_rect.bottom - 1,
                      roof_rect.width, 3))
    pygame.draw.rect(surf, (0, 0, 0), roof_rect, 2)

    # chimney (left side of roof, with cap)
    chim_w = max(8, w // 18)
    chim_h = max(14, roof_h // 2 + 6)
    chim_x = roof_rect.left + roof_rect.width // 4
    chim_y = roof_rect.top - chim_h + 4
    # brick chimney
    chim_brick = (140, 80, 70)
    pygame.draw.rect(surf, chim_brick,
                     (chim_x, chim_y, chim_w, chim_h))
    # brick mortar lines
    for j in range(2, chim_h, 4):
        pygame.draw.line(surf, _shade(chim_brick, -30),
                         (chim_x, chim_y + j),
                         (chim_x + chim_w, chim_y + j), 1)
    pygame.draw.line(surf, _shade(chim_brick, -30),
                     (chim_x + chim_w // 2, chim_y),
                     (chim_x + chim_w // 2, chim_y + chim_h), 1)
    # chimney cap
    pygame.draw.rect(surf, (60, 60, 60),
                     (chim_x - 2, chim_y - 3, chim_w + 4, 4))
    pygame.draw.rect(surf, (0, 0, 0),
                     (chim_x, chim_y, chim_w, chim_h), 1)
    # tiny smoke puff
    pygame.draw.circle(surf, (235, 235, 235, 200),
                       (chim_x + chim_w // 2, chim_y - 6), 3)
    pygame.draw.circle(surf, (255, 255, 255, 240),
                       (chim_x + chim_w // 2 + 2, chim_y - 10), 2)

    # ── Door with awning + porch posts ─────────────────────────
    door_w = max(24, min(w // 5, 48))
    door_h = max(38, min(int(h * 0.42), 72))
    door_rect = pygame.Rect(body_x + w // 2 - door_w // 2,
                            body_y + h - foundation_h - door_h,
                            door_w, door_h)
    frame = door_rect.inflate(10, 10)
    pygame.draw.rect(surf, _shade(wall, -55), frame)
    door_color = (88, 50, 30)
    pygame.draw.rect(surf, door_color, door_rect)
    # door panels (4-panel design)
    p_inset = 4
    p_w = (door_rect.width - 3 * p_inset) // 2
    p_h = (door_rect.height - 3 * p_inset - 6) // 2
    for r in range(2):
        for c in range(2):
            px = door_rect.left + p_inset + c * (p_w + p_inset)
            py = door_rect.top + p_inset + r * (p_h + p_inset)
            pygame.draw.rect(surf, _shade(door_color, -20),
                             (px, py, p_w, p_h))
            pygame.draw.rect(surf, _shade(door_color, +25),
                             (px + 1, py + 1, p_w - 2, 1))
            pygame.draw.rect(surf, _shade(door_color, -40),
                             (px, py, p_w, p_h), 1)
    # door hinges
    pygame.draw.rect(surf, (50, 50, 55),
                     (door_rect.left + 2, door_rect.top + 8, 3, 4))
    pygame.draw.rect(surf, (50, 50, 55),
                     (door_rect.left + 2, door_rect.bottom - 12, 3, 4))
    # door knob (brass) + plate
    knob_x = door_rect.right - 7
    knob_y = door_rect.centery
    pygame.draw.rect(surf, (180, 130, 40),
                     (knob_x - 2, knob_y - 4, 4, 8))
    pygame.draw.circle(surf, (240, 200, 80), (knob_x, knob_y), 3)
    pygame.draw.circle(surf, (140, 100, 30), (knob_x, knob_y), 3, 1)
    # door knocker
    pygame.draw.circle(surf, (210, 180, 60),
                       (door_rect.centerx, door_rect.top + 14), 2)
    # step
    pygame.draw.rect(surf, _shade(stone, -10),
                     (door_rect.left - 8, door_rect.bottom - 3,
                      door_rect.width + 16, 6))
    pygame.draw.rect(surf, _shade(stone, -40),
                     (door_rect.left - 8, door_rect.bottom - 3,
                      door_rect.width + 16, 6), 1)
    pygame.draw.rect(surf, (0, 0, 0), door_rect, 2)
    pygame.draw.rect(surf, (0, 0, 0), frame, 2)

    # awning over the door
    awn_w = door_w + 22
    awn_h = 7
    awn_y = door_rect.top - awn_h - 3
    awn_pts = [(door_rect.centerx - awn_w // 2, awn_y + awn_h),
               (door_rect.centerx + awn_w // 2, awn_y + awn_h),
               (door_rect.centerx + awn_w // 2 - 5, awn_y),
               (door_rect.centerx - awn_w // 2 + 5, awn_y)]
    pygame.draw.polygon(surf, _shade(roof, -8), awn_pts)
    # awning stripes
    for i in range(1, 4):
        pygame.draw.line(surf, _shade(roof, +18),
                         (door_rect.centerx - awn_w // 2 + i * 4 + 5,
                          awn_y),
                         (door_rect.centerx - awn_w // 2 + i * 4 + 1,
                          awn_y + awn_h), 1)
    pygame.draw.polygon(surf, (0, 0, 0), awn_pts, 1)
    # awning support posts
    pygame.draw.line(surf, _shade(wall, -45),
                     (door_rect.left - 6, awn_y + awn_h),
                     (door_rect.left - 6, door_rect.bottom + 4), 2)
    pygame.draw.line(surf, _shade(wall, -45),
                     (door_rect.right + 5, awn_y + awn_h),
                     (door_rect.right + 5, door_rect.bottom + 4), 2)
    # porch lantern
    lantern_x = door_rect.centerx
    lantern_y = awn_y + awn_h + 2
    pygame.draw.circle(surf, (255, 230, 140),
                       (lantern_x, lantern_y), 3)
    pygame.draw.circle(surf, (200, 140, 40),
                       (lantern_x, lantern_y), 3, 1)
    # tiny bushes flanking the door
    bush_col_a = (60, 130, 60)
    bush_col_b = (100, 170, 80)
    for bx in (door_rect.left - 10, door_rect.right + 9):
        by = door_rect.bottom - 2
        pygame.draw.circle(surf, bush_col_a, (bx, by), 5)
        pygame.draw.circle(surf, bush_col_b, (bx - 1, by - 1), 3)
        pygame.draw.circle(surf, (255, 235, 100), (bx + 1, by - 2), 1)

    # ── Windows (framed + shuttered + flower box) ──────────────
    win_w = max(24, min(w // 6, 40))
    win_h = max(26, min(h // 5, 44))
    glass_hi = (200, 230, 245)
    glass_mid = (150, 195, 220)
    glass_dark = (95, 145, 180)
    window_y = wall_top + 14
    win_positions = [body_x + pillar_w + 12,
                     body_x + w - pillar_w - 12 - win_w]
    for wx in win_positions:
        wr = pygame.Rect(wx, window_y, win_w, win_h)
        # window sill + frame
        outer = wr.inflate(8, 8)
        pygame.draw.rect(surf, _shade(wall, +30), outer)
        pygame.draw.rect(surf, _shade(wall, -55),
                         outer.inflate(-2, -2))
        # glass (3-tone diagonal reflection)
        pygame.draw.rect(surf, glass_dark, wr)
        pygame.draw.polygon(surf, glass_mid,
                            [(wr.left, wr.top),
                             (wr.right, wr.top),
                             (wr.right, wr.top + wr.height * 2 // 3),
                             (wr.left + wr.width // 3, wr.bottom)])
        pygame.draw.polygon(surf, glass_hi,
                            [(wr.left + 2, wr.top + 2),
                             (wr.left + wr.width // 2, wr.top + 2),
                             (wr.left + 2, wr.top + wr.height // 2)])
        # cross mullions (thicker)
        pygame.draw.line(surf, (45, 45, 45),
                         (wr.centerx, wr.top),
                         (wr.centerx, wr.bottom), 2)
        pygame.draw.line(surf, (45, 45, 45),
                         (wr.left, wr.centery),
                         (wr.right, wr.centery), 2)
        # window sill
        sill_y = wr.bottom + 1
        pygame.draw.rect(surf, _shade(wall, +20),
                         (wr.left - 4, sill_y, wr.width + 8, 3))
        pygame.draw.rect(surf, _shade(wall, -45),
                         (wr.left - 4, sill_y, wr.width + 8, 3), 1)
        # shutters (with slats)
        sh_col = _shade(roof, -5)
        sh_dark = _shade(roof, -35)
        for side_x in (wr.left - 7, wr.right + 1):
            pygame.draw.rect(surf, sh_col,
                             (side_x, wr.top - 1, 6, wr.height + 2))
            # slats
            for sy in range(wr.top + 2, wr.bottom, 4):
                pygame.draw.line(surf, sh_dark,
                                 (side_x + 1, sy),
                                 (side_x + 5, sy), 1)
            pygame.draw.rect(surf, sh_dark,
                             (side_x, wr.top - 1, 6, wr.height + 2), 1)
        pygame.draw.rect(surf, (0, 0, 0), outer, 2)
        # flower box under the sill
        fb_h = 5
        fb_y = sill_y + 3
        pygame.draw.rect(surf, (90, 60, 35),
                         (wr.left - 4, fb_y, wr.width + 8, fb_h))
        pygame.draw.line(surf, (50, 30, 15),
                         (wr.left - 4, fb_y),
                         (wr.right + 4, fb_y), 1)
        # multi-colored flowers
        flower_colors = [(235, 90, 110), (240, 200, 80),
                         (180, 100, 230), (250, 250, 250)]
        for fx in range(wr.left - 2, wr.right + 4, 4):
            col = flower_colors[(fx // 4) % len(flower_colors)]
            pygame.draw.circle(surf, col, (fx, fb_y - 1), 2)
            pygame.draw.circle(surf, (255, 240, 120),
                               (fx, fb_y - 1), 1)
        # leaves peeking from box
        for fx in range(wr.left, wr.right, 5):
            pygame.draw.circle(surf, (60, 130, 60),
                               (fx + 1, fb_y), 1)

    # body outline last (crisp)
    pygame.draw.rect(surf, (0, 0, 0), body_rect, 2)

    return (surf, -pad_x, -pad_top)


# ---------- Tree ----------
def _build_tree(w, h, seed):
    """Stylized top-down tree with a visible trunk under a layered canopy.

    The canopy is drawn as a slightly egg-shaped silhouette (taller than
    wide) made of a handful of overlapping leaf "blobs" with a bright
    sun-side highlight and a few procedural variants (fruits, blossoms,
    autumn leaves) keyed off the seed.
    """
    rnd = random.Random(seed)
    pad = 14
    surf = pygame.Surface((w + 2 * pad, h + 2 * pad), pygame.SRCALPHA)
    cx, cy = pad + w // 2, pad + h // 2
    radius = max(7, min(w, h) // 2)

    # ── Ground shadow ──────────────────────────────────────────────
    sh_w = int((w + 32) * 0.9)
    sh = pygame.Surface((sh_w, 18), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 120), sh.get_rect())
    surf.blit(sh, (cx - sh_w // 2, cy + radius - 2))

    # ── Trunk poking out below the canopy ─────────────────────────
    trunk_w = max(6, radius // 3)
    trunk_h = max(9, int(radius * 0.7))
    tx = cx - trunk_w // 2
    ty = cy + radius - 2
    pygame.draw.rect(surf, _shade(DARK_BROWN, -20),
                     (tx - 1, ty + trunk_h - 4, trunk_w + 2, 4))  # root flare
    pygame.draw.rect(surf, DARK_BROWN, (tx, ty, trunk_w, trunk_h))
    pygame.draw.rect(surf, BROWN, (tx, ty, max(2, trunk_w // 2), trunk_h))
    pygame.draw.line(surf, _shade(DARK_BROWN, -35),
                     (tx + trunk_w - 1, ty),
                     (tx + trunk_w - 1, ty + trunk_h), 1)
    # bark texture lines
    for i in range(1, max(2, trunk_h // 3)):
        pygame.draw.line(surf, _shade(BROWN, -25),
                         (tx + 1, ty + i * 3),
                         (tx + trunk_w - 2, ty + i * 3), 1)
    pygame.draw.rect(surf, (0, 0, 0), (tx, ty, trunk_w, trunk_h), 1)

    # ── Canopy palette (cartoon green, high saturation) ───────────
    deep    = (28, 64, 28)
    dark    = (48, 100, 46)
    mid     = (84, 150, 68)
    bright  = (140, 200, 90)
    sun     = (210, 240, 140)

    # egg-shaped canopy: taller than wide
    canopy_rx = radius
    canopy_ry = int(radius * 1.08)

    # deep outer rim ellipse (creates a thicker silhouette edge)
    pygame.draw.ellipse(surf, deep,
                        (cx - canopy_rx - 1, cy - canopy_ry - 1 + 2,
                         canopy_rx * 2 + 2, canopy_ry * 2 + 2))
    # main mid-tone ellipse
    pygame.draw.ellipse(surf, mid,
                        (cx - canopy_rx, cy - canopy_ry,
                         canopy_rx * 2, canopy_ry * 2))

    # leaf cluster bumps along the silhouette
    num_bumps = 8 if radius >= 18 else 6
    bump_positions = []
    for i in range(num_bumps):
        ang = i * (math.tau / num_bumps) - math.pi / 2 + rnd.uniform(-0.25, 0.25)
        rr = radius * 0.78
        bx = int(cx + math.cos(ang) * rr)
        by = int(cy + math.sin(ang) * rr * 1.05)
        r_bump = max(4, radius // 3) + rnd.randint(-1, 1)
        bump_positions.append((bx, by, r_bump, ang))
        pygame.draw.circle(surf, deep, (bx, by), r_bump + 1)
        pygame.draw.circle(surf, dark, (bx, by), r_bump)

    # bright highlight on the sun-side (upper-left) blobs
    for bx, by, r_bump, ang in bump_positions:
        if math.cos(ang) < 0.4 and math.sin(ang) < 0.4:
            pygame.draw.circle(surf, mid, (bx, by), r_bump - 1)
            pygame.draw.circle(surf, bright,
                               (bx - r_bump // 3, by - r_bump // 3),
                               max(2, r_bump // 2))

    # central sun-catch highlight
    hi_r = max(3, radius // 2)
    pygame.draw.circle(surf, bright,
                       (cx - radius // 3, cy - radius // 3),
                       hi_r)
    pygame.draw.circle(surf, sun,
                       (cx - radius // 2 + 1, cy - radius // 2 + 2),
                       max(2, radius // 4))
    # rim highlight on the top
    pygame.draw.arc(surf, bright,
                    (cx - canopy_rx + 2, cy - canopy_ry + 2,
                     canopy_rx * 2 - 4, canopy_ry * 2 - 4),
                    math.radians(120), math.radians(180), 2)

    # leaf speckles for organic texture
    speckle_count = max(5, radius // 2)
    for _ in range(speckle_count):
        ang = rnd.uniform(0, math.tau)
        rr = rnd.uniform(0, radius * 0.92)
        fx = int(cx + math.cos(ang) * rr)
        fy = int(cy + math.sin(ang) * rr * 1.05)
        col = rnd.choice([deep, bright, mid, dark])
        pygame.draw.circle(surf, col, (fx, fy), 1)

    # one or two small darker "leaf gaps" for organic feel
    for _ in range(2):
        ang = rnd.uniform(0, math.tau)
        rr = rnd.uniform(radius * 0.2, radius * 0.5)
        gx = int(cx + math.cos(ang) * rr)
        gy = int(cy + math.sin(ang) * rr)
        pygame.draw.circle(surf, deep, (gx, gy), 1)

    # crisp dark outline silhouette so the tree pops
    pygame.draw.ellipse(surf, (16, 36, 16),
                        (cx - canopy_rx, cy - canopy_ry,
                         canopy_rx * 2, canopy_ry * 2), 2)

    # ── Variant fruits / blossoms / autumn leaves ─────────────────
    flavor = seed % 4
    if flavor == 0:
        # red fruits
        for _ in range(6):
            ang = rnd.uniform(0, math.tau)
            rr = rnd.uniform(radius * 0.3, radius * 0.85)
            fx = int(cx + math.cos(ang) * rr)
            fy = int(cy + math.sin(ang) * rr)
            pygame.draw.circle(surf, (40, 30, 20), (fx + 1, fy + 1), 2)
            pygame.draw.circle(surf, (220, 60, 60), (fx, fy), 2)
            pygame.draw.circle(surf, (255, 180, 170), (fx - 1, fy - 1), 1)
    elif flavor == 1:
        # pink blossoms
        for _ in range(7):
            ang = rnd.uniform(0, math.tau)
            rr = rnd.uniform(radius * 0.3, radius * 0.9)
            fx = int(cx + math.cos(ang) * rr)
            fy = int(cy + math.sin(ang) * rr)
            pygame.draw.circle(surf, (255, 170, 215), (fx, fy), 2)
            pygame.draw.circle(surf, (255, 240, 245), (fx, fy), 1)
    elif flavor == 2:
        # autumn yellow/orange spots
        for _ in range(6):
            ang = rnd.uniform(0, math.tau)
            rr = rnd.uniform(radius * 0.3, radius * 0.9)
            fx = int(cx + math.cos(ang) * rr)
            fy = int(cy + math.sin(ang) * rr)
            col = rnd.choice([(235, 180, 60), (230, 120, 50)])
            pygame.draw.circle(surf, col, (fx, fy), 2)
            pygame.draw.circle(surf, (255, 230, 150), (fx - 1, fy - 1), 1)

    return (surf, -pad, -pad)


# ---------- Fence ----------
def _build_fence(w, h):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    base = (175, 135, 75)
    dark = (110, 75, 35)
    hi = (215, 180, 115)
    vertical = w >= h
    if vertical:
        # rails (top + bottom)
        rail_h = max(3, min(h // 4, 6))
        pygame.draw.rect(surf, dark, (0, 0, w, rail_h + 1))
        pygame.draw.rect(surf, base, (0, 1, w, rail_h - 1))
        pygame.draw.rect(surf, dark, (0, h - rail_h - 1, w, rail_h + 1))
        pygame.draw.rect(surf, base, (0, h - rail_h, w, rail_h - 1))
        # pickets
        pkt_w = 7
        step = pkt_w + 3
        for x in range(2, w - pkt_w, step):
            pygame.draw.rect(surf, base, (x, 0, pkt_w, h))
            pygame.draw.line(surf, hi, (x, 1), (x, h - 1), 1)
            pygame.draw.line(surf, dark,
                             (x + pkt_w - 1, 1),
                             (x + pkt_w - 1, h - 1), 1)
            # pointed top (clipped if outside)
            pygame.draw.polygon(surf, base,
                                [(x, 0),
                                 (x + pkt_w, 0),
                                 (x + pkt_w // 2, max(0, -3))])
        # middle rail bands (so it reads as fence, not wood floor)
        pygame.draw.rect(surf, _shade(base, -25),
                         (0, h // 3, w, max(2, h // 24)))
        pygame.draw.rect(surf, _shade(base, -25),
                         (0, 2 * h // 3, w, max(2, h // 24)))
    else:
        rail_w = max(3, min(w // 4, 6))
        pygame.draw.rect(surf, dark, (0, 0, rail_w + 1, h))
        pygame.draw.rect(surf, base, (1, 0, rail_w - 1, h))
        pygame.draw.rect(surf, dark, (w - rail_w - 1, 0, rail_w + 1, h))
        pygame.draw.rect(surf, base, (w - rail_w, 0, rail_w - 1, h))
        pkt_h = 7
        step = pkt_h + 3
        for y in range(2, h - pkt_h, step):
            pygame.draw.rect(surf, base, (0, y, w, pkt_h))
            pygame.draw.line(surf, hi, (1, y), (w - 1, y), 1)
            pygame.draw.line(surf, dark,
                             (1, y + pkt_h - 1),
                             (w - 1, y + pkt_h - 1), 1)
        pygame.draw.rect(surf, _shade(base, -25),
                         (w // 3, 0, max(2, w // 24), h))
        pygame.draw.rect(surf, _shade(base, -25),
                         (2 * w // 3, 0, max(2, w // 24), h))
    pygame.draw.rect(surf, (0, 0, 0), (0, 0, w, h), 1)
    return (surf, 0, 0)


# ---------- Shipping container ----------
def _build_container(w, h, color):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    base = color
    dark = _shade(color, -45)
    darker = _shade(color, -70)
    hi = _shade(color, +28)
    # body
    pygame.draw.rect(surf, base, (0, 0, w, h))
    # top sunlit edge
    pygame.draw.rect(surf, hi, (3, 2, w - 6, 5))
    # bottom shadow
    pygame.draw.rect(surf, dark, (3, h - 8, w - 6, 6))
    # corrugation ridges
    horizontal_ridges = w > h
    if horizontal_ridges:
        for x in range(6, w - 6, 8):
            pygame.draw.line(surf, dark, (x, 8), (x, h - 9), 1)
            pygame.draw.line(surf, hi, (x + 1, 8), (x + 1, h - 9), 1)
    else:
        for y in range(8, h - 8, 8):
            pygame.draw.line(surf, dark, (6, y), (w - 6, y), 1)
            pygame.draw.line(surf, hi, (6, y + 1), (w - 6, y + 1), 1)
    # corner caps
    cap = max(8, min(w, h) // 6)
    for cx, cy in [(0, 0), (w - cap, 0), (0, h - cap), (w - cap, h - cap)]:
        pygame.draw.rect(surf, darker, (cx, cy, cap, cap))
        pygame.draw.rect(surf, _shade(color, -20),
                         (cx + 1, cy + 1, cap - 2, cap - 2))
        pygame.draw.circle(surf, darker,
                           (cx + cap // 2, cy + cap // 2), 2)
        pygame.draw.circle(surf, hi,
                           (cx + cap // 2 - 1, cy + cap // 2 - 1), 1)
    # door panels (right side, two doors)
    door_w = max(8, w // 6)
    pygame.draw.line(surf, dark, (w - door_w, 6), (w - door_w, h - 6), 1)
    pygame.draw.line(surf, dark, (w - 2 * door_w, 6),
                     (w - 2 * door_w, h - 6), 1)
    handle_y = h // 2
    pygame.draw.rect(surf, hi,
                     (w - door_w + 3, handle_y - 8, 2, 16))
    pygame.draw.rect(surf, hi,
                     (w - 2 * door_w + 3, handle_y - 8, 2, 16))
    # warning numbers (just a small dark rectangle for shipping label)
    label_w = max(8, w // 8)
    label_h = max(4, h // 12)
    pygame.draw.rect(surf, darker,
                     (cap + 4, h - cap - label_h - 4,
                      label_w, label_h))
    pygame.draw.rect(surf, hi,
                     (cap + 4, h - cap - label_h - 4,
                      label_w, label_h), 1)
    pygame.draw.rect(surf, (0, 0, 0), (0, 0, w, h), 2)
    return (surf, 0, 0)


# ---------- Car ----------
def _build_car(w, h, color):
    pad = 4
    surf = pygame.Surface((w + 2 * pad, h + 2 * pad), pygame.SRCALPHA)
    rect = pygame.Rect(pad, pad, w, h)
    body = color
    dark = _shade(color, -45)
    hi = _shade(color, +28)
    # ground shadow
    sh = pygame.Surface((w + 8, h + 4), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 90), sh.get_rect(), border_radius=8)
    surf.blit(sh, (rect.left - 4, rect.top + 4))
    # body
    pygame.draw.rect(surf, dark, rect, border_radius=8)
    pygame.draw.rect(surf, body, rect.inflate(-2, -2), border_radius=7)
    # body highlight stripe
    pygame.draw.rect(surf, hi,
                     (rect.left + 4, rect.top + 4,
                      rect.width - 8, max(4, h // 8)),
                     border_radius=5)
    # hood + trunk lines
    hood_y = rect.top + h // 4
    trunk_y = rect.bottom - h // 4
    pygame.draw.line(surf, dark, (rect.left + 4, hood_y),
                     (rect.right - 4, hood_y), 1)
    pygame.draw.line(surf, dark, (rect.left + 4, trunk_y),
                     (rect.right - 4, trunk_y), 1)
    # windshields
    glass = (140, 185, 215)
    glass_dark = (90, 130, 165)
    win_inset = 6
    front = pygame.Rect(rect.left + win_inset, hood_y + 2,
                        rect.width - 2 * win_inset, max(6, h // 5))
    rear = pygame.Rect(rect.left + win_inset, trunk_y - max(6, h // 5),
                       rect.width - 2 * win_inset, max(6, h // 5))
    pygame.draw.rect(surf, glass_dark, front)
    pygame.draw.rect(surf, glass, front.inflate(0, -front.height // 2))
    pygame.draw.rect(surf, glass_dark, rear)
    pygame.draw.rect(surf, glass, rear.inflate(0, -rear.height // 2))
    # central roof panel
    roof_panel_h = max(6, h // 4)
    pygame.draw.rect(surf, _shade(color, -15),
                     (rect.left + 6, rect.centery - roof_panel_h // 2,
                      rect.width - 12, roof_panel_h))
    pygame.draw.rect(surf, _shade(color, +12),
                     (rect.left + 6, rect.centery - roof_panel_h // 2,
                      rect.width - 12, max(2, roof_panel_h // 4)))
    # side mirrors
    mirror = 4
    pygame.draw.rect(surf, dark,
                     (rect.left - 2, hood_y + 5, mirror, mirror))
    pygame.draw.rect(surf, dark,
                     (rect.right - 2, hood_y + 5, mirror, mirror))
    # wheels (rounded rect tires)
    wheel_w = 5
    wheel_h = max(8, h // 4)
    wy_top = rect.top + h // 8
    wy_bot = rect.bottom - h // 8 - wheel_h
    for wx in (rect.left - 1, rect.right - wheel_w + 1):
        pygame.draw.rect(surf, (8, 8, 10),
                         (wx, wy_top, wheel_w, wheel_h),
                         border_radius=2)
        pygame.draw.rect(surf, (60, 60, 65),
                         (wx, wy_top + 1, wheel_w, max(2, wheel_h // 3)),
                         border_radius=1)
        pygame.draw.rect(surf, (8, 8, 10),
                         (wx, wy_bot, wheel_w, wheel_h),
                         border_radius=2)
        pygame.draw.rect(surf, (60, 60, 65),
                         (wx, wy_bot + 1, wheel_w, max(2, wheel_h // 3)),
                         border_radius=1)
    # headlights and taillights
    pygame.draw.circle(surf, (255, 240, 180),
                       (rect.left + 6, rect.top + 4), 3)
    pygame.draw.circle(surf, (255, 240, 180),
                       (rect.right - 6, rect.top + 4), 3)
    pygame.draw.circle(surf, (220, 40, 40),
                       (rect.left + 6, rect.bottom - 4), 3)
    pygame.draw.circle(surf, (220, 40, 40),
                       (rect.right - 6, rect.bottom - 4), 3)
    # outline
    pygame.draw.rect(surf, (0, 0, 0), rect, 2, border_radius=8)
    return (surf, -pad, -pad)


# ---------- Oil drum ----------
def _build_drum(w, h):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    cx, cy = w // 2, h // 2
    rad = max(4, min(w, h) // 2 - 1)
    # ground shadow
    sh = pygame.Surface((w + 4, 8), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 120), sh.get_rect())
    surf.blit(sh, (-2, h - 7))
    # outer rim
    pygame.draw.circle(surf, (50, 28, 18), (cx, cy), rad)
    # red body
    pygame.draw.circle(surf, (175, 60, 35), (cx, cy), rad - 2)
    # specular highlight (offset upper-left)
    pygame.draw.circle(surf, (215, 100, 65),
                       (cx - rad // 3, cy - rad // 3),
                       max(2, rad // 2))
    # concentric bands
    pygame.draw.circle(surf, (110, 40, 22), (cx, cy), max(2, rad - 4), 1)
    pygame.draw.circle(surf, (110, 40, 22), (cx, cy), max(2, rad - 8), 1)
    # cap
    cap_r = max(2, rad // 3)
    pygame.draw.circle(surf, (60, 35, 20), (cx, cy), cap_r)
    pygame.draw.circle(surf, (110, 70, 40), (cx, cy), max(1, cap_r - 1))
    pygame.draw.line(surf, (40, 25, 15),
                     (cx - cap_r, cy), (cx + cap_r, cy), 1)
    pygame.draw.line(surf, (40, 25, 15),
                     (cx, cy - cap_r), (cx, cy + cap_r), 1)
    # yellow hazard arc bottom-right
    if rad >= 9:
        pygame.draw.arc(surf, (240, 200, 60),
                        (cx - rad + 3, cy - rad + 3,
                         2 * rad - 6, 2 * rad - 6),
                        math.pi * 0.85, math.pi * 1.3, 3)
    # outline
    pygame.draw.circle(surf, (0, 0, 0), (cx, cy), rad, 2)
    return (surf, 0, 0)


# ---------- Wooden crate ----------
def _build_crate(w, h):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    base = (165, 120, 65)
    plank = (190, 145, 80)
    dark = (105, 70, 30)
    pygame.draw.rect(surf, base, (0, 0, w, h))
    plank_h = max(6, h // 4)
    for y in range(0, h, plank_h):
        pygame.draw.rect(surf, plank, (1, y + 1, w - 2, plank_h - 2))
        pygame.draw.line(surf, dark, (0, y), (w, y), 1)
        # wood grain
        pygame.draw.line(surf, _shade(plank, -25),
                         (4, y + plank_h // 2),
                         (w - 4, y + plank_h // 2), 1)
        pygame.draw.line(surf, _shade(plank, +18),
                         (4, y + 2),
                         (w - 6, y + 2), 1)
    # metal corner caps
    cc = max(5, min(w, h) // 6)
    for cx, cy in [(0, 0), (w - cc, 0), (0, h - cc), (w - cc, h - cc)]:
        pygame.draw.rect(surf, (90, 90, 100), (cx, cy, cc, cc))
        pygame.draw.rect(surf, (140, 140, 150),
                         (cx + 1, cy + 1, cc - 2, cc - 2))
        pygame.draw.circle(surf, (60, 60, 70),
                           (cx + cc // 2, cy + cc // 2), 1)
    # stamp (FRAGILE-looking marks)
    stamp_w = max(10, w // 2)
    stamp_h = max(4, h // 5)
    sx = (w - stamp_w) // 2
    sy = (h - stamp_h) // 2
    pygame.draw.rect(surf, dark, (sx, sy, stamp_w, stamp_h), 1)
    for i in range(3):
        pygame.draw.line(surf, dark,
                         (sx + 3 + i * (stamp_w - 6) // 3, sy + 2),
                         (sx + 3 + i * (stamp_w - 6) // 3,
                          sy + stamp_h - 2), 1)
    pygame.draw.rect(surf, (0, 0, 0), (0, 0, w, h), 2)
    return (surf, 0, 0)


# ---------- Industrial machine ----------
def _build_machine(w, h):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    body = (95, 100, 115)
    dark = (50, 55, 65)
    hi = (160, 165, 180)
    accent = (220, 160, 60)
    pygame.draw.rect(surf, dark, (2, 4, w - 4, h - 4), border_radius=6)
    pygame.draw.rect(surf, body, (4, 4, w - 8, h - 10), border_radius=6)
    # vent grille
    vent_top = 8
    vent_h = max(8, h // 4)
    pygame.draw.rect(surf, dark, (10, vent_top, w - 20, vent_h),
                     border_radius=3)
    for x in range(12, w - 12, 4):
        pygame.draw.line(surf, hi,
                         (x, vent_top + 2),
                         (x, vent_top + vent_h - 2), 1)
    # control panel
    panel_y = vent_top + vent_h + 6
    panel_h = max(10, h // 4)
    pygame.draw.rect(surf, dark, (10, panel_y, w - 20, panel_h),
                     border_radius=2)
    pygame.draw.rect(surf, (32, 38, 45),
                     (12, panel_y + 2, w - 24, panel_h - 4),
                     border_radius=2)
    # status lights
    for i, col in enumerate([(220, 60, 50), (220, 180, 50), (80, 220, 100)]):
        cx = 16 + i * 12
        cy = panel_y + panel_h // 2
        pygame.draw.circle(surf, col, (cx, cy), 3)
        pygame.draw.circle(surf, (240, 240, 240), (cx - 1, cy - 1), 1)
    # green screen on the right
    sc_w = max(8, (w - 20) // 3)
    sc_x = w - 12 - sc_w
    pygame.draw.rect(surf, (40, 130, 70),
                     (sc_x, panel_y + 2, sc_w, panel_h - 4))
    pygame.draw.line(surf, (90, 220, 130),
                     (sc_x + 2, panel_y + panel_h // 2),
                     (sc_x + sc_w - 2, panel_y + panel_h // 2), 1)
    # warning hazard stripe at bottom
    stripe_y = h - 12
    for x in range(2, w - 2, 12):
        pygame.draw.polygon(surf, accent,
                            [(x, stripe_y), (x + 6, stripe_y),
                             (x + 10, stripe_y + 5),
                             (x + 4, stripe_y + 5)])
        pygame.draw.polygon(surf, (0, 0, 0),
                            [(x + 6, stripe_y),
                             (x + 12, stripe_y),
                             (x + 16, stripe_y + 5),
                             (x + 10, stripe_y + 5)])
    # corner bolts
    for bx, by in [(6, 6), (w - 7, 6), (6, h - 14), (w - 7, h - 14)]:
        pygame.draw.circle(surf, dark, (bx, by), 2)
        pygame.draw.circle(surf, hi, (bx - 1, by - 1), 1)
    # outline
    pygame.draw.rect(surf, (0, 0, 0), (2, 4, w - 4, h - 4),
                     2, border_radius=6)
    return (surf, 0, 0)


# ---------- Rubble pile ----------
def _build_rubble(w, h, seed):
    rnd = random.Random(seed)
    pad = 4
    surf = pygame.Surface((w + 2 * pad, h + 2 * pad), pygame.SRCALPHA)
    # base shadow
    sh = pygame.Surface((w + 10, h // 2 + 6), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 110), sh.get_rect())
    surf.blit(sh, (pad - 5, pad + h // 2))
    # cluster of rocks
    rock_colors = [(120, 115, 105), (100, 95, 90),
                   (85, 80, 75), (140, 135, 125), (160, 150, 135)]
    num = 8 if (w * h) < 4000 else 12
    for _ in range(num):
        rw = rnd.randint(max(8, w // 5), max(12, w // 3))
        rh = rnd.randint(max(6, h // 5), max(10, h // 3))
        rx = pad + rnd.randint(2, max(2, w - rw - 2))
        ry = pad + rnd.randint(2, max(2, h - rh - 2))
        c = rnd.choice(rock_colors)
        pygame.draw.ellipse(surf, _shade(c, -25),
                            (rx + 1, ry + 2, rw, rh))
        pygame.draw.ellipse(surf, c, (rx, ry, rw, rh))
        pygame.draw.ellipse(surf, _shade(c, +25),
                            (rx + 2, ry + 1,
                             max(2, rw - rw // 2),
                             max(2, rh // 3)))
        pygame.draw.ellipse(surf, (40, 40, 40), (rx, ry, rw, rh), 1)
    # debris specks
    for _ in range(6):
        x = pad + rnd.randint(0, w - 1)
        y = pad + rnd.randint(0, h - 1)
        pygame.draw.circle(surf, (160, 150, 140), (x, y), 1)
    return (surf, -pad, -pad)


# ---------- Dog cage (puppy / mother dog) ----------
def _build_dog_cage(w, h, large=False):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    # ground shadow
    sh = pygame.Surface((w + 4, 12), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 130), sh.get_rect())
    surf.blit(sh, (-2, h - 8))
    # cage floor strip
    pygame.draw.rect(surf, (95, 90, 85), (2, h - 12, w - 4, 10))
    pygame.draw.rect(surf, (60, 55, 50), (2, h - 12, w - 4, 10), 1)
    # puppy/dog drawing
    cx, cy = w // 2, h // 2 + 2
    base = (160, 110, 60) if large else (200, 155, 95)
    body_w = max(10, int(w * 0.55))
    body_h = max(8, int(h * 0.36))
    # body shadow
    pygame.draw.ellipse(surf, _shade(base, -35),
                        (cx - body_w // 2 + 2, cy - body_h // 2 + 4,
                         body_w, body_h))
    pygame.draw.ellipse(surf, base,
                        (cx - body_w // 2, cy - body_h // 2 + 2,
                         body_w, body_h))
    # belly highlight
    pygame.draw.ellipse(surf, _shade(base, +15),
                        (cx - body_w // 4, cy + 1,
                         body_w // 2, max(2, body_h // 3)))
    # head
    head_r = max(5, int(min(w, h) * 0.2))
    head_x = cx - body_w // 2 + head_r - 2
    head_y = cy - body_h // 2 - head_r + 6
    pygame.draw.circle(surf, _shade(base, -25),
                       (head_x + 1, head_y + 2), head_r)
    pygame.draw.circle(surf, base, (head_x, head_y), head_r)
    # snout
    pygame.draw.ellipse(surf, _shade(base, +18),
                        (head_x - head_r // 2,
                         head_y + head_r // 4,
                         head_r + 2, max(2, head_r // 2)))
    # nose
    pygame.draw.circle(surf, (35, 25, 20),
                       (head_x - head_r // 2 - 1,
                        head_y + head_r // 2),
                       max(1, head_r // 5))
    # floppy ears
    ear_w = max(3, head_r // 2)
    pygame.draw.ellipse(surf, _shade(base, -32),
                        (head_x - head_r,
                         head_y - head_r // 2,
                         ear_w, head_r))
    pygame.draw.ellipse(surf, _shade(base, -32),
                        (head_x + head_r // 3,
                         head_y - head_r // 2,
                         ear_w, head_r))
    # eyes
    eye_r = max(1, head_r // 5)
    pygame.draw.circle(surf, (35, 25, 20),
                       (head_x - head_r // 4, head_y - 1), eye_r)
    pygame.draw.circle(surf, (35, 25, 20),
                       (head_x + head_r // 4, head_y - 1), eye_r)
    pygame.draw.circle(surf, (240, 240, 240),
                       (head_x - head_r // 4 - 1, head_y - 2), 1)
    pygame.draw.circle(surf, (240, 240, 240),
                       (head_x + head_r // 4 - 1, head_y - 2), 1)
    # tail
    pygame.draw.line(surf, base,
                     (cx + body_w // 2 - 2, cy - 2),
                     (cx + body_w // 2 + 6, cy - 8), 3)
    # paws/legs hint
    pygame.draw.rect(surf, _shade(base, -25),
                     (cx - body_w // 3, cy + body_h // 2 - 1,
                      max(2, body_w // 8), 3))
    pygame.draw.rect(surf, _shade(base, -25),
                     (cx + body_w // 4, cy + body_h // 2 - 1,
                      max(2, body_w // 8), 3))
    # sad tear if mother dog
    if large:
        pygame.draw.circle(surf, (120, 180, 220),
                           (head_x - head_r // 4, head_y + 2), 1)

    # cage frame
    frame = (195, 195, 205)
    frame_dark = (130, 130, 140)
    pygame.draw.rect(surf, frame_dark, (0, 0, w, h), 4)
    pygame.draw.rect(surf, frame, (2, 2, w - 4, h - 4), 2)
    # vertical bars (over the dog so it shows imprisoned)
    bar_step = 8 if large else 6
    for x in range(bar_step, w - bar_step + 1, bar_step):
        pygame.draw.line(surf, frame, (x, 4), (x, h - 4), 2)
        pygame.draw.line(surf, frame_dark,
                         (x + 1, 4), (x + 1, h - 4), 1)
    # horizontal cross bars
    for y in (h // 3, 2 * h // 3):
        pygame.draw.line(surf, frame_dark, (4, y), (w - 4, y), 2)
        pygame.draw.line(surf, frame, (4, y - 1), (w - 4, y - 1), 1)
    # padlock at front-bottom
    pl_w = 6
    pl_h = 8
    pl_x = w // 2 - pl_w // 2
    pl_y = h - pl_h - 2
    pygame.draw.rect(surf, (220, 200, 90),
                     (pl_x, pl_y, pl_w, pl_h))
    pygame.draw.rect(surf, (180, 150, 50),
                     (pl_x, pl_y, pl_w, pl_h), 1)
    pygame.draw.line(surf, (180, 150, 50),
                     (pl_x + pl_w // 2, pl_y),
                     (pl_x + pl_w // 2, pl_y - 3), 2)
    return (surf, 0, 0)


# ---------- Boss gate (heavy steel door) ----------
def _build_boss_gate(w, h):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    base = (75, 75, 85)
    dark = (40, 40, 50)
    bright = (140, 140, 155)
    pygame.draw.rect(surf, dark, (0, 0, w, h))
    pygame.draw.rect(surf, base, (1, 1, w - 2, h - 2))
    # vertical seam in middle (the door split)
    pygame.draw.line(surf, dark, (w // 2, 4), (w // 2, h - 4), 2)
    # rivets
    rivet_step = 14 if h > 80 else 10
    for y in range(8, h - 8, rivet_step):
        pygame.draw.circle(surf, bright, (3, y), 2)
        pygame.draw.circle(surf, bright, (w - 4, y), 2)
        pygame.draw.circle(surf, dark, (3, y), 2, 1)
        pygame.draw.circle(surf, dark, (w - 4, y), 2, 1)
    # hazard yellow stripes on both sides
    for y in range(0, h, 12):
        pygame.draw.polygon(surf, (230, 200, 60),
                            [(2, y), (8, y),
                             (4, y + 6), (max(-1, -2), y + 6)])
        pygame.draw.polygon(surf, (230, 200, 60),
                            [(w - 8, y), (w - 2, y),
                             (w - 6, y + 6), (w - 12, y + 6)])
    # warning triangle in center
    cy = h // 2
    tri_pts = [(w // 2, cy - 9),
               (w // 2 - 8, cy + 6),
               (w // 2 + 8, cy + 6)]
    pygame.draw.polygon(surf, (220, 60, 50), tri_pts)
    pygame.draw.polygon(surf, (0, 0, 0), tri_pts, 1)
    pygame.draw.rect(surf, (240, 240, 240),
                     (w // 2 - 1, cy - 4, 2, 6))
    pygame.draw.rect(surf, (240, 240, 240),
                     (w // 2 - 1, cy + 3, 2, 2))
    pygame.draw.rect(surf, (0, 0, 0), (0, 0, w, h), 2)
    return (surf, 0, 0)


# ============================================================
# Solid object (collidable rect, optionally drawable as house/wall/etc.)
# ============================================================
class Solid:
    def __init__(self, rect: pygame.Rect, kind: str = "wall", color=None, height=0):
        self.rect = rect
        self.kind = kind   # wall, house, fence, container, car, drum, tree, crate
        self.color = color
        self.height = height
        self.hp = 0        # 0 = indestructible
        self.alive = True
        self.sprite: pygame.Surface | None = None
        self.aux = {}      # any extra data

    def draw(self, surf, cam):
        if not self.alive:
            return
        r = cam.apply_rect(self.rect)
        k = self.kind
        # fast-path for sprite-backed solids (e.g. banh_mi, pho_house)
        if k == "sprite":
            if self.sprite:
                surf.blit(self.sprite, r)
            return
        if r.width <= 0 or r.height <= 0:
            return

        if k == "wall":
            color = _norm_color(self.color)
            _blit_cached(surf, r,
                         ("wall", r.width, r.height, color),
                         lambda: _build_wall(r.width, r.height, color))
        elif k == "house":
            wall = _norm_color(self.aux.get("wall", WALL_TAN))
            roof = _norm_color(self.aux.get("roof", ROOF_RED))
            _blit_cached(surf, r,
                         ("house", r.width, r.height, wall, roof),
                         lambda: _build_house(r.width, r.height, wall, roof))
        elif k == "fence":
            _blit_cached(surf, r,
                         ("fence", r.width, r.height),
                         lambda: _build_fence(r.width, r.height))
        elif k == "container":
            color = _norm_color(self.color) or (180, 60, 50)
            _blit_cached(surf, r,
                         ("container", r.width, r.height, color),
                         lambda: _build_container(r.width, r.height, color))
        elif k == "car":
            color = _norm_color(self.color) or (180, 60, 60)
            _blit_cached(surf, r,
                         ("car", r.width, r.height, color),
                         lambda: _build_car(r.width, r.height, color))
        elif k == "drum":
            _blit_cached(surf, r,
                         ("drum", r.width, r.height),
                         lambda: _build_drum(r.width, r.height))
        elif k == "tree":
            # vary by position so adjacent trees look unique
            seed = ((self.rect.x * 73856093) ^ (self.rect.y * 19349663)) & 0xffffffff
            _blit_cached(surf, r,
                         ("tree", r.width, r.height, seed & 0xff),
                         lambda: _build_tree(r.width, r.height, seed))
        elif k == "crate":
            _blit_cached(surf, r,
                         ("crate", r.width, r.height),
                         lambda: _build_crate(r.width, r.height))
        elif k == "machine":
            _blit_cached(surf, r,
                         ("machine", r.width, r.height),
                         lambda: _build_machine(r.width, r.height))
        elif k == "rubble":
            seed = ((self.rect.x * 73856093) ^ (self.rect.y * 19349663)) & 0xffffffff
            _blit_cached(surf, r,
                         ("rubble", r.width, r.height, seed & 0xff),
                         lambda: _build_rubble(r.width, r.height, seed))
        elif k == "boss_gate":
            _blit_cached(surf, r,
                         ("boss_gate", r.width, r.height),
                         lambda: _build_boss_gate(r.width, r.height))
        elif k == "puppy":
            _blit_cached(surf, r,
                         ("puppy", r.width, r.height),
                         lambda: _build_dog_cage(r.width, r.height, large=False))
        elif k == "mother_dog":
            _blit_cached(surf, r,
                         ("mother_dog", r.width, r.height),
                         lambda: _build_dog_cage(r.width, r.height, large=True))
        else:
            # fallback: simple coloured rect
            pygame.draw.rect(surf, self.color or (90, 90, 90), r)
            pygame.draw.rect(surf, BLACK, r, 1)


# ============================================================
# Decals (purely visual, drawn under entities)
# ============================================================
class Decal:
    def __init__(self, rect, kind, color=None):
        self.rect = rect
        self.kind = kind
        self.color = color

    def draw(self, surf, cam):
        r = cam.apply_rect(self.rect)
        k = self.kind
        if k == "flower":
            cx, cy = r.center
            pygame.draw.circle(surf, self.color or (240, 80, 80), (cx, cy), 3)
            pygame.draw.circle(surf, (255, 240, 100), (cx, cy), 1)
        elif k == "puddle":
            pygame.draw.ellipse(surf, (60, 90, 120, 180), r)
        elif k == "crack":
            pygame.draw.line(surf, (60, 60, 60),
                             r.topleft, r.bottomright, 1)
            pygame.draw.line(surf, (60, 60, 60),
                             (r.centerx, r.top), (r.right, r.bottom), 1)
        elif k == "blood":
            pygame.draw.circle(surf, (110, 20, 20), r.center, r.width // 2)
            pygame.draw.circle(surf, (160, 30, 30), r.center, r.width // 3)


# ============================================================
# World container
# ============================================================
class World:
    def __init__(self, w_tiles: int, h_tiles: int, default_tile: int = T_GRASS):
        self.w = w_tiles
        self.h = h_tiles
        self.tile_size = TILE
        self.tiles = [[default_tile] * w_tiles for _ in range(h_tiles)]
        self.solids: list[Solid] = []
        self.pickups: list[Pickup] = []
        self.decals: list[Decal] = []
        self.spawn = Vec(0, 0)
        self.exit_rect: pygame.Rect | None = None
        self.exit_locked = True
        self.shop_rect: pygame.Rect | None = None
        self.dog_rect: pygame.Rect | None = None
        self.boss_gate_rect: pygame.Rect | None = None
        self.boss_gate_active = True
        self.boss_dialog_triggered = False
        self._dirty = True

    def clear(self):
        """Reset all dynamic entities and markers for a fresh level."""
        self.solids = []
        self.pickups = []
        self.decals = []
        self.exit_rect = None
        self.exit_locked = True
        self.shop_rect = None
        self.dog_rect = None
        self.boss_gate_rect = None
        self.boss_gate_active = True
        self.boss_dialog_triggered = False
        self._dirty = True

    # ---------- map editing helpers ----------
    def fill_rect_tiles(self, x, y, w, h, t):
        for j in range(y, y + h):
            for i in range(x, x + w):
                if 0 <= i < self.w and 0 <= j < self.h:
                    self.tiles[j][i] = t
        self._dirty = True

    def fill_pixel_rect(self, px_rect: pygame.Rect, t: int):
        x = px_rect.left // TILE
        y = px_rect.top // TILE
        w = px_rect.width // TILE
        h = px_rect.height // TILE
        self.fill_rect_tiles(x, y, w, h, t)

    def set_tile(self, x, y, t):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.tiles[y][x] = t
            self._dirty = True

    def add_solid(self, s: Solid):
        self.solids.append(s)

    def add_pickup(self, p: Pickup):
        self.pickups.append(p)

    def add_decal(self, d: Decal):
        self.decals.append(d)

    def get_walkable_grid(self, ignore_boss_gates=False):
        if ignore_boss_gates:
            grid = [[True] * self.w for _ in range(self.h)]
            for s in self.solids:
                kinds_to_ignore = ("decoration", "boss_gate_trigger", "dialogue_trigger", "boss_gate")
                if s.alive and s.kind not in kinds_to_ignore:
                    x1 = max(0, s.rect.left // TILE)
                    y1 = max(0, s.rect.top // TILE)
                    x2 = min(self.w - 1, s.rect.right // TILE)
                    y2 = min(self.h - 1, s.rect.bottom // TILE)
                    for y in range(y1, y2 + 1):
                        for x in range(x1, x2 + 1):
                            grid[y][x] = False
            return grid

        if not hasattr(self, "_walkable_grid") or self._dirty:
            self._walkable_grid = [[True] * self.w for _ in range(self.h)]
            for s in self.solids:
                if s.alive and s.kind not in ("decoration", "boss_gate_trigger", "dialogue_trigger"):
                    x1 = max(0, s.rect.left // TILE)
                    y1 = max(0, s.rect.top // TILE)
                    x2 = min(self.w - 1, s.rect.right // TILE)
                    y2 = min(self.h - 1, s.rect.bottom // TILE)
                    for y in range(y1, y2 + 1):
                        for x in range(x1, x2 + 1):
                            self._walkable_grid[y][x] = False
            self._dirty = False
        return self._walkable_grid

    # ---------- collision ----------
    def collides(self, rect: pygame.Rect) -> bool:
        for s in self.solids:
            if s.alive and s.kind not in ("decoration",) and s.rect.colliderect(rect):
                return True
        return False

    def hit_solid(self, point: Vec) -> Solid | None:
        for s in self.solids:
            if s.alive and s.kind != "decoration" and s.rect.collidepoint(point):
                return s
        return None

    # ---------- size ----------
    def pixel_size(self):
        return self.w * TILE, self.h * TILE

    # ---------- drawing ----------
    def _is_road_center_h(self, i, j):
        if self.tiles[j][i] not in (T_ROAD_H, T_ROAD_X):
            return False
        up = 0
        k = j - 1
        while k >= 0 and self.tiles[k][i] in (T_ROAD_H, T_ROAD_X):
            up += 1
            k -= 1
        dn = 0
        k = j + 1
        while k < self.h and self.tiles[k][i] in (T_ROAD_H, T_ROAD_X):
            dn += 1
            k += 1
        return up == dn

    def _is_road_center_v(self, i, j):
        if self.tiles[j][i] not in (T_ROAD_V, T_ROAD_X):
            return False
        left = 0
        k = i - 1
        while k >= 0 and self.tiles[j][k] in (T_ROAD_V, T_ROAD_X):
            left += 1
            k -= 1
        right = 0
        k = i + 1
        while k < self.w and self.tiles[j][k] in (T_ROAD_V, T_ROAD_X):
            right += 1
            k += 1
        return left == right

    def _build_bg(self):
        w, h = self.pixel_size()
        self._bg_surface = pygame.Surface((w, h)).convert()
        bg = self._bg_surface
        for j in range(self.h):
            for i in range(self.w):
                t = self.tiles[j][i]
                col = TILE_COLORS.get(t, GRASS)
                # slight noise
                noise = ((i * 73856093) ^ (j * 19349663)) & 15
                c = (max(0, col[0] - noise // 2 + 4),
                     max(0, col[1] - noise // 2 + 4),
                     max(0, col[2] - noise // 2 + 4))
                pygame.draw.rect(bg, c, (i * TILE, j * TILE, TILE, TILE))

        # paint road centerline dashes only on the true center row/col
        for j in range(self.h):
                if t == T_GRASS and rnd.random() < 0.05:
                    cx = i * TILE + rnd.randint(4, TILE - 4)
                    cy = j * TILE + rnd.randint(4, TILE - 4)
                    pygame.draw.line(bg, GRASS_DARK, (cx, cy), (cx, cy - 3), 1)
                    pygame.draw.line(bg, GRASS_DARK, (cx, cy), (cx - 2, cy - 2), 1)
                    pygame.draw.line(bg, GRASS_DARK, (cx, cy), (cx + 2, cy - 2), 1)
                if t == T_ASH and rnd.random() < 0.07:
                    cx = i * TILE + rnd.randint(4, TILE - 4)
                    cy = j * TILE + rnd.randint(4, TILE - 4)
                    pygame.draw.circle(bg, (35, 35, 38), (cx, cy), 1)
        self._dirty = False

    def draw_bg(self, surf, cam):
        # Calculate visible tile range
        start_x = max(0, int(cam.offset.x // TILE))
        end_x = min(self.w, int((cam.offset.x + SCREEN_WIDTH) // TILE) + 1)
        start_y = max(0, int(cam.offset.y // TILE))
        end_y = min(self.h, int((cam.offset.y + SCREEN_HEIGHT) // TILE) + 1)

        off_x = -int(cam.offset.x) + int(cam.shake_offset.x)
        off_y = -int(cam.offset.y) + int(cam.shake_offset.y)

        # Draw base tiles
        for j in range(start_y, end_y):
            for i in range(start_x, end_x):
                t = self.tiles[j][i]
                color = TILE_COLORS.get(t, GRASS)
                pygame.draw.rect(surf, color, (i * TILE + off_x, j * TILE + off_y, TILE, TILE))
                
                # Draw simple details in real-time
                if t == T_ROAD_H:
                    cy = j * TILE + TILE // 2 + off_y
                    pygame.draw.rect(surf, ROAD_LINE, (i * TILE + off_x + 10, cy - 1, TILE - 20, 2))
                elif t == T_ROAD_V:
                    cx = i * TILE + TILE // 2 + off_x
                    pygame.draw.rect(surf, ROAD_LINE, (cx - 1, j * TILE + off_y + 10, 2, TILE - 20))
                elif t == T_ASH:
                    # Subtle ash dots
                    seed = (i * 12345 + j * 67890) % 100
                    if seed < 10:
                        pygame.draw.circle(surf, (35, 35, 38), (i * TILE + off_x + 20, j * TILE + off_y + 20), 1)

        # decals on top of bg (culled)
        view_rect = pygame.Rect(cam.offset.x - 50, cam.offset.y - 50, SCREEN_WIDTH + 100, SCREEN_HEIGHT + 100)
        for d in self.decals:
            if view_rect.colliderect(d.rect):
                d.draw(surf, cam)

    def draw_solids(self, surf, cam):
        for s in self.solids:
            if s.alive:
                s.draw(surf, cam)

    def draw_pickups(self, surf, cam):
        for p in self.pickups:
            if p.alive:
                p.draw(surf, cam)

    def draw_exit_marker(self, surf, cam, t):
        if self.exit_rect is None:
            return
        r = cam.apply_rect(self.exit_rect)
        color = (200, 200, 200) if self.exit_locked else (90, 220, 100)
        pygame.draw.rect(surf, color, r, 4, border_radius=4)
        flash = (math.sin(t * 4) + 1) / 2
        text_col = (40, 40, 40) if self.exit_locked else (10, 60, 20)
        msg = "LOCKED" if self.exit_locked else "EXIT >>"
        from utils import draw_text
        draw_text(surf, msg, (r.centerx, r.centery), size=20,
                  color=text_col, bold=True, center=True)
        if not self.exit_locked:
            arrow_size = 18 + int(flash * 6)
            pts = [(r.right + 10, r.centery),
                   (r.right + 10 + arrow_size, r.centery - arrow_size // 2),
                   (r.right + 10 + arrow_size, r.centery + arrow_size // 2)]
            pygame.draw.polygon(surf, (90, 220, 100), pts)
