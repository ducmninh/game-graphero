"""Sảnh (Hub) — between-level menu for permanent upgrades + shop + pets.

Layout: a single overlay with 4 tabs at the top:
  • NÂNG CẤP NHÂN VẬT   (character permanent upgrades)
  • MUA SÚNG            (unlock weapons directly)
  • MUA PET             (buy and equip companions)
  • CHƠI                (start / continue the run)

Gold and upgrade state are persistent: any gold the player ends a run with is
banked into the save when they enter the hub, and all purchases come out of
the banked total. Leaving the hub via "CHƠI" applies the upgrades + spawns
the pet on the player and starts (or resumes) the run.
"""
from __future__ import annotations
import math
import pygame

from utils import Vec, draw_text
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, SPRITES,
    CHAR_UPGRADES, CHAR_UPGRADE_ORDER,
    PETS, PET_ORDER,
    HUB_GUN_ORDER, WEAPONS,
    GRAB_GREEN, DARK_GREEN, GOLD, YELLOW, FONT_PATH,
)


# Cached preview sprites (loaded on first access)
_gun_previews: dict = {}
_grab_previews: dict = {}
_pet_egg_previews: dict = {}


def get_pet_egg_preview(key):
    if key in _pet_egg_previews:
        return _pet_egg_previews[key]
    fname = f"pet_egg_{key}.png"
    img = _load_preview(fname, 64)
    _pet_egg_previews[key] = img
    return img


def _load_preview(filename, target_w):
    path = SPRITES / filename
    if not path.exists():
        return None
    try:
        img = pygame.image.load(str(path)).convert_alpha()
    except (pygame.error, OSError):
        return None
    w, h = img.get_size()
    if w > target_w:
        scale = target_w / w
        img = pygame.transform.smoothscale(img, (target_w, int(h * scale)))
    return img


def get_gun_preview(key):
    if key in _gun_previews:
        return _gun_previews[key]

    from pathlib import Path
    import sys
    if getattr(sys, 'frozen', False):
        root = Path(sys._MEIPASS).parent
    else:
        # hub.py is at grab_hero(1)/grab_hero/tong/hub.py → root = grab_hero(1)
        root = Path(__file__).resolve().parent.parent.parent

    # Ánh xạ từng súng sang file ảnh thực tế
    # Súng nhỏ (pistol, smg, pistol_mk2) → image-removebg-preview (6).png
    # Grenade Launcher (súng cuối) → image-removebg-preview (1).png
    # Các súng khác → thử file cũ trong SPRITES
    root_map = {
        "pistol":      root / "image-removebg-preview (6).png",
        "pistol_mk2":  root / "image-removebg-preview (6).png",
        "grenade":     root / "image-removebg-preview (1).png",
    }
    sprite_map = {
        "shotgun": "gun_shotgun.png",
        "smg":     "gun_smg.png",
        "ar":      "gun_ar.png",
        "sniper":  "gun_sniper.png",
    }

    img = None
    if key in root_map:
        p = root_map[key]
        if p.exists():
            try:
                raw = pygame.image.load(str(p)).convert_alpha()
                # Scale chiều rộng về 220px
                tw = 220
                scale = tw / max(1, raw.get_width())
                img = pygame.transform.smoothscale(
                    raw, (tw, int(raw.get_height() * scale)))
            except Exception as e:
                print(f"gun preview load error {key}: {e}")
    elif key in sprite_map:
        img = _load_preview(sprite_map[key], 220)

    _gun_previews[key] = img
    return img


def get_grab_preview(key):
    if key in _grab_previews:
        return _grab_previews[key]
    name_map = {
        "pistol": "grab_holds_pistol.png",
        "pistol_mk2": "grab_holds_pistol.png",
        "smg": "grab_holds_smg.png",
        "shotgun": "grab_holds_shotgun.png",
        "sniper": "grab_holds_sniper.png",
        "ar": "grab_holds_smg.png",
    }
    fname = name_map.get(key)
    img = _load_preview(fname, 180) if fname else None
    _grab_previews[key] = img
    return img


TAB_UPGRADE = 0
TAB_GUN = 1
TAB_PET = 2
TAB_PLAY = 3

TAB_NAMES = [
    "NÂNG CẤP NHÂN VẬT",
    "MUA SÚNG",
    "MUA PET",
    "CHƠI",
]


class Hub:
    def __init__(self, save: dict):
        self.save = save
        self.tab = TAB_UPGRADE
        self.row = 0                # selected row in current tab
        self.message = ""
        self.message_t = 0.0
        self.open = True
        self.exit_to_play = False   # set True when player picks CHƠI
        self.t = 0.0

    # ----------------------------------------------------------
    def feedback(self, msg: str):
        self.message = msg
        self.message_t = 1.8

    # ----------------------------------------------------------
    def _row_count(self):
        if self.tab == TAB_UPGRADE:
            return len(CHAR_UPGRADE_ORDER)
        if self.tab == TAB_GUN:
            return len(HUB_GUN_ORDER)
        if self.tab == TAB_PET:
            # one row per pet, plus a "không dùng" row
            return len(PET_ORDER) + 1
        return 1  # play tab has a single big action

    # ----------------------------------------------------------
    def handle(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k in (pygame.K_LEFT, pygame.K_a):
            self.tab = (self.tab - 1) % 4
            self.row = 0
            return
        if k in (pygame.K_RIGHT, pygame.K_d):
            self.tab = (self.tab + 1) % 4
            self.row = 0
            return
        if k in (pygame.K_TAB,):
            self.tab = (self.tab + 1) % 4
            self.row = 0
            return
        if k in (pygame.K_UP, pygame.K_w):
            self.row = (self.row - 1) % self._row_count()
            return
        if k in (pygame.K_DOWN, pygame.K_s):
            self.row = (self.row + 1) % self._row_count()
            return
        if k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            self._activate()
            return
        if k == pygame.K_p:
            # quick "Play"
            self.tab = TAB_PLAY
            self.row = 0
            self._activate()
            return

    # ----------------------------------------------------------
    def _activate(self):
        if self.tab == TAB_UPGRADE:
            self._buy_upgrade(CHAR_UPGRADE_ORDER[self.row])
        elif self.tab == TAB_GUN:
            self._buy_gun(HUB_GUN_ORDER[self.row])
        elif self.tab == TAB_PET:
            if self.row < len(PET_ORDER):
                self._buy_or_equip_pet(PET_ORDER[self.row])
            else:
                # "không dùng pet" row
                self.save["equipped_pet"] = None
                self.feedback("Đã bỏ pet — solo run")
        elif self.tab == TAB_PLAY:
            self.exit_to_play = True
            self.open = False

    # ----------------------------------------------------------
    def _buy_upgrade(self, key: str):
        u = CHAR_UPGRADES[key]
        lvl = self.save["upgrades"].get(key, 0)
        if lvl >= u["max_level"]:
            self.feedback(f"{u['name']} đã đạt cấp tối đa")
            return
        cost = u["cost"][lvl]
        if self.save["gold"] < cost:
            self.feedback("Không đủ vàng")
            return
        self.save["gold"] -= cost
        self.save["upgrades"][key] = lvl + 1
        from saveload import write_save
        write_save(self.save)
        self.feedback(f"Đã nâng {u['name']} lên cấp {lvl + 1}!")

    def _buy_gun(self, key: str):
        if key in self.save["owned_guns"]:
            self.feedback("Đã sở hữu súng này")
            return
        price = WEAPONS[key]["price"]
        if self.save["gold"] < price:
            self.feedback("Không đủ vàng")
            return
        self.save["gold"] -= price
        self.save["owned_guns"].append(key)
        from saveload import write_save
        write_save(self.save)
        self.feedback(f"Đã mua {WEAPONS[key]['name']}!")

    def _buy_or_equip_pet(self, key: str):
        spec = PETS[key]
        if key in self.save["owned_pets"]:
            if self.save.get("equipped_pet") == key:
                self.feedback(f"{spec['emoji']} {spec['name']} đang theo bạn")
            else:
                self.save["equipped_pet"] = key
                self.feedback(f"Đã trang bị {spec['name']}")
            return
        price = spec["price"]
        if self.save["gold"] < price:
            self.feedback("Không đủ vàng để mua pet này")
            return
        self.save["gold"] -= price
        self.save["owned_pets"].append(key)
        from saveload import write_save
        write_save(self.save)
        self.save["equipped_pet"] = key
        self.feedback(f"Đã mua {spec['name']}!")

    # ----------------------------------------------------------
    def update(self, dt):
        self.t += dt
        if self.message_t > 0:
            self.message_t = max(0.0, self.message_t - dt)

    # ==========================================================
    # DRAW
    # ==========================================================
    def draw(self, surf):
        surf.fill((20, 28, 22))
        self._draw_backdrop(surf)

        # Title bar
        draw_text(surf, "SẢNH GRAB HERO",
                  (SCREEN_WIDTH // 2, 28), size=44,
                  color=GOLD, bold=True, center=True)
        draw_text(surf, f"Vàng tích luỹ: {self.save['gold']}",
                  (SCREEN_WIDTH // 2, 70), size=22,
                  color=(255, 230, 100), bold=True, center=True)

        # Tabs
        self._draw_tabs(surf)

        # Panel
        panel = pygame.Rect(60, 160, SCREEN_WIDTH - 120, SCREEN_HEIGHT - 240)
        pygame.draw.rect(surf, (24, 32, 28), panel)
        pygame.draw.rect(surf, GRAB_GREEN, panel, 3)

        if self.tab == TAB_UPGRADE:
            self._draw_upgrade_panel(surf, panel)
        elif self.tab == TAB_GUN:
            self._draw_gun_panel(surf, panel)
        elif self.tab == TAB_PET:
            self._draw_pet_panel(surf, panel)
        else:
            self._draw_play_panel(surf, panel)

        # Footer help
        draw_text(surf,
                  "←/→ chuyển panel    ↑/↓ chọn    ENTER mua / chọn    P để chơi",
                  (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50), size=18,
                  color=(220, 220, 220), bold=True, center=True)

        # Message
        if self.message_t > 0:
            mt = self.message_t
            draw_text(surf, self.message,
                      (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 90),
                      size=22, color=YELLOW, bold=True, center=True)

    def _draw_backdrop(self, surf):
        """Subtle parallax 'garage' backdrop."""
        # gradient
        for y in range(0, SCREEN_HEIGHT, 6):
            t = y / SCREEN_HEIGHT
            col = (int(20 + t * 12), int(30 + t * 10), int(22 + t * 8))
            pygame.draw.rect(surf, col, (0, y, SCREEN_WIDTH, 6))
        # floor band
        pygame.draw.rect(surf, (32, 36, 30),
                         (0, SCREEN_HEIGHT - 200, SCREEN_WIDTH, 200))
        # decorative columns / Grab green stripes
        for x in range(0, SCREEN_WIDTH, 220):
            offset = int(math.sin(self.t + x * 0.01) * 4)
            pygame.draw.rect(surf, (28, 60, 38),
                             (x + offset, 100, 8, SCREEN_HEIGHT - 160))
        # subtle scanlines for retro look
        for y in range(0, SCREEN_HEIGHT, 3):
            pygame.draw.line(surf, (0, 0, 0, 6),
                             (0, y), (SCREEN_WIDTH, y), 1)

    def _draw_tabs(self, surf):
        n = len(TAB_NAMES)
        tab_w = (SCREEN_WIDTH - 120) // n
        for i, name in enumerate(TAB_NAMES):
            x = 60 + i * tab_w
            r = pygame.Rect(x, 110, tab_w - 10, 44)
            selected = (i == self.tab)
            bg = GRAB_GREEN if selected else (40, 50, 44)
            pygame.draw.rect(surf, bg, r)
            pygame.draw.rect(surf, (10, 20, 14), r, 2)
            txt_col = (10, 30, 16) if selected else (200, 220, 200)
            draw_text(surf, name, r.center, size=18,
                      color=txt_col, bold=True, center=True)

    # ----------------------------------------------------------
    def _draw_row(self, surf, x, y, w, h, title, sub, right_text,
                  selected, color, afford, img=None):
        r = pygame.Rect(x, y, w, h)
        bg = (60, 70, 64) if not selected else (80, 110, 90)
        pygame.draw.rect(surf, bg, r)
        border = GOLD if selected else (20, 30, 24)
        pygame.draw.rect(surf, border, r, 3 if selected else 2)
        # color chip or image
        if img is not None:
            scaled = pygame.transform.smoothscale(img, (36, h - 24))
            surf.blit(scaled, (x + 8, y + 12))
        else:
            pygame.draw.rect(surf, color, (x + 8, y + 12, 36, h - 24))
            pygame.draw.rect(surf, (0, 0, 0), (x + 8, y + 12, 36, h - 24), 2)
        draw_text(surf, title, (x + 60, y + 8), size=22,
                  bold=True, color=(255, 255, 255))
        draw_text(surf, sub, (x + 60, y + 38), size=15,
                  color=(210, 210, 210))
        col = YELLOW if afford else (200, 100, 100)
        font = pygame.font.SysFont(FONT_PATH, 22, bold=True)
        img = font.render(right_text, True, col)
        sh = font.render(right_text, True, (0, 0, 0))
        rect = img.get_rect(midright=(x + w - 16, y + h // 2))
        surf.blit(sh, rect.move(2, 2))
        surf.blit(img, rect)

    # ----------------------------------------------------------
    def _draw_upgrade_panel(self, surf, panel):
        draw_text(surf, "Nâng cấp vĩnh viễn — lưu vào save, áp dụng mỗi lần chơi",
                  (panel.centerx, panel.top + 24), size=18,
                  color=(200, 210, 200), bold=True, center=True)
        y = panel.top + 60
        row_w = panel.width - 48
        x = panel.left + 24
        row_h = 74

        for i, key in enumerate(CHAR_UPGRADE_ORDER):
            u = CHAR_UPGRADES[key]
            lvl = self.save["upgrades"].get(key, 0)
            max_lvl = u["max_level"]
            selected = (self.row == i)

            if lvl >= max_lvl:
                right = "MAX"
                afford = False
            else:
                cost = u["cost"][lvl]
                right = f"{cost}$"
                afford = self.save["gold"] >= cost
            
            sub = f"{u['desc']}  •  Cấp: {lvl}/{max_lvl}"

            # --- Row Background ---
            bg_rect = pygame.Rect(x, y, row_w, row_h)
            # Metallic Sci-fi base
            bg_color = (40, 50, 45) if not selected else (55, 70, 60)
            pygame.draw.rect(surf, bg_color, bg_rect, border_radius=8)
            
            # Border
            border_col = (100, 110, 105) if not selected else (255, 215, 0)
            pygame.draw.rect(surf, border_col, bg_rect, 2, border_radius=8)

            # Glow if selected
            if selected:
                glow_rect = pygame.Rect(x - 3, y - 3, row_w + 6, row_h + 6)
                pygame.draw.rect(surf, (255, 200, 0, 100), glow_rect, 3, border_radius=10)

            # --- Left: Icon placeholder & Text ---
            icon_rect = pygame.Rect(x + 15, y + 12, 50, 50)
            pygame.draw.rect(surf, (20, 25, 22), icon_rect, border_radius=6)
            pygame.draw.rect(surf, u.get("color", (200, 200, 200)), icon_rect, 2, border_radius=6)
            
            # Draw title
            draw_text(surf, u["name"], (x + 80, y + 15), size=24, bold=True, color=(255, 255, 255))
            # Draw sub
            draw_text(surf, sub, (x + 80, y + 42), size=14, color=(180, 190, 185))

            # --- Middle: Segmented Progress Bar ---
            bar_w = 260
            bar_h = 16
            bar_x = x + row_w // 2 - bar_w // 2
            bar_y = y + row_h // 2 - bar_h // 2
            
            # Draw bar container
            pygame.draw.rect(surf, (15, 20, 18), (bar_x - 4, bar_y - 4, bar_w + 8, bar_h + 8), border_radius=4)
            pygame.draw.rect(surf, (80, 90, 85) if not selected else (180, 150, 50), 
                             (bar_x - 4, bar_y - 4, bar_w + 8, bar_h + 8), 1, border_radius=4)

            # Draw segments
            seg_gap = 4
            seg_w = (bar_w - (max_lvl - 1) * seg_gap) / max_lvl
            for s in range(max_lvl):
                sx = bar_x + s * (seg_w + seg_gap)
                s_rect = pygame.Rect(sx, bar_y, seg_w, bar_h)
                if s < lvl:
                    # Filled segment (Red if MAX, Yellow/Gold otherwise)
                    fill_col = (200, 50, 50) if lvl >= max_lvl else (255, 215, 0)
                    pygame.draw.rect(surf, fill_col, s_rect, border_radius=2)
                else:
                    # Empty segment
                    pygame.draw.rect(surf, (40, 45, 40), s_rect, border_radius=2)

            # --- Right: Price / MAX ---
            right_x = x + row_w - 20
            if lvl >= max_lvl:
                draw_text(surf, "MAX", (right_x - 40, y + 25), size=28, color=(255, 60, 60), bold=True)
            else:
                col = (255, 220, 0) if afford else (200, 80, 80)
                font = pygame.font.SysFont(FONT_PATH, 26, bold=True)
                txt_img = font.render(right, True, col)
                txt_rect = txt_img.get_rect(midright=(right_x, y + row_h // 2))
                # Shadow
                sh_img = font.render(right, True, (0, 0, 0))
                surf.blit(sh_img, txt_rect.move(2, 2))
                surf.blit(txt_img, txt_rect)

            # Draw connecting neon line to the next row (if not last)
            if i < len(CHAR_UPGRADE_ORDER) - 1:
                cx = x + row_w // 2
                cy_start = y + row_h + 2
                cy_end = y + row_h + 8
                # Draw a glowing cyan tick between rows
                pygame.draw.line(surf, (50, 255, 200), (cx, cy_start), (cx, cy_end), 4)

            y += row_h + 10

    def _draw_gun_panel(self, surf, panel):
        draw_text(surf,
                  "KHO VŨ KHÍ CAO CẤP",
                  (panel.centerx, panel.top + 30), size=32,
                  color=GOLD, bold=True, center=True)

        n_guns = len(HUB_GUN_ORDER)
        card_w = 240
        card_h = 360
        spacing = 40
        
        # Tính toán vị trí cuộn (Scroll) để thẻ đang chọn luôn ở giữa
        target_scroll = self.row * (card_w + spacing)
        if not hasattr(self, 'gun_scroll'):
            self.gun_scroll = target_scroll
        
        # Cuộn mượt (Smooth lerp)
        self.gun_scroll += (target_scroll - self.gun_scroll) * 0.15
        
        start_x = panel.centerx - card_w // 2 - int(self.gun_scroll)
        start_y = panel.top + 80

        for i, key in enumerate(HUB_GUN_ORDER):
            spec = WEAPONS[key]
            owned = key in self.save["owned_guns"]
            selected = (self.row == i)
            
            # Card rect logic with pop-up animation for selected
            cx = start_x + i * (card_w + spacing)
            cy = start_y
            
            if selected:
                cy -= 12
                c_w = card_w + 12
                c_h = card_h + 16
                cx -= 6
            else:
                c_w = card_w
                c_h = card_h
                
            # Draw glow behind selected card
            if selected:
                glow_rect = pygame.Rect(cx - 8, cy - 8, c_w + 16, c_h + 16)
                pygame.draw.rect(surf, (255, 215, 0), glow_rect, border_radius=20)
            
            # Glassmorphism background
            bg_surface = pygame.Surface((c_w, c_h), pygame.SRCALPHA)
            bg_color = (25, 35, 30, 220) if not selected else (40, 55, 45, 255)
            pygame.draw.rect(bg_surface, bg_color, (0, 0, c_w, c_h), border_radius=16)
            
            # Sleek Border
            border_color = (50, 70, 60, 255) if not selected else (255, 230, 100, 255)
            border_width = 2 if not selected else 3
            pygame.draw.rect(bg_surface, border_color, (0, 0, c_w, c_h), border_width, border_radius=16)
            surf.blit(bg_surface, (cx, cy))
            
            # Gun Name with gradient-like styling (or just colored)
            draw_text(surf, spec['name'], (cx + c_w//2, cy + 25), 
                      size=24 if not selected else 28, color=spec['color'], bold=True, center=True)
            
            # Gun Image
            gimg = get_gun_preview(key)
            if gimg:
                # Khung hiển thị súng
                img_w = c_w - 40
                scale = img_w / max(1, gimg.get_width())
                img_h = int(gimg.get_height() * scale)
                scaled_gimg = pygame.transform.smoothscale(gimg, (img_w, img_h))
                
                # Hiệu ứng nảy (floating) nếu đang chọn
                img_y = cy + 80
                if selected:
                    img_y += math.sin(self.t * 6) * 6
                
                surf.blit(scaled_gimg, (cx + 20, int(img_y)))
            
            # Thông số vũ khí
            stat_y = cy + c_h - 135
            stats = [
                f"Sát thương: {spec['damage']}",
                f"Tốc bắn: {spec['fire_rate']} RPS",
                f"Băng đạn: {spec['mag']} viên"
            ]
            for stat in stats:
                draw_text(surf, stat, (cx + c_w//2, stat_y), size=16, color=(200, 220, 210), center=True)
                stat_y += 22
                
            # Nút Mua / Sở hữu
            btn_rect = pygame.Rect(cx + 20, cy + c_h - 55, c_w - 40, 40)
            if owned:
                pygame.draw.rect(surf, (40, 140, 80), btn_rect, border_radius=8)
                draw_text(surf, "ĐÃ SỞ HỮU", btn_rect.center, size=18, color=(255, 255, 255), bold=True, center=True)
            else:
                afford = self.save["gold"] >= spec["price"]
                btn_color = (200, 160, 20) if afford else (120, 40, 40)
                pygame.draw.rect(surf, btn_color, btn_rect, border_radius=8)
                draw_text(surf, f"MUA: {spec['price']}$", btn_rect.center, size=18, color=(255, 255, 255), bold=True, center=True)

    def _draw_pet_panel(self, surf, panel):
        draw_text(surf,
                  "Mua pet — pet đi theo bạn vào mọi level và đánh enemy",
                  (panel.centerx, panel.top + 24), size=18,
                  color=(220, 220, 220), bold=True, center=True)
        y = panel.top + 60
        for i, key in enumerate(PET_ORDER):
            spec = PETS[key]
            owned = key in self.save["owned_pets"]
            equipped = (self.save.get("equipped_pet") == key)
            if equipped:
                right = "ĐANG DÙNG"
                afford = False
            elif owned:
                right = "TRANG BỊ"
                afford = True
            else:
                right = f"{spec['price']}$"
                afford = self.save["gold"] >= spec["price"]
            sub = f"{spec['emoji']}  {spec['desc']}"
            pimg = get_pet_egg_preview(key)
            self._draw_row(surf, panel.left + 24, y, panel.width - 48, 70,
                           spec["name"], sub, right,
                           selected=(self.row == i),
                           color=spec["color"], afford=afford, img=pimg)
            y += 82
        # "Không dùng pet" row
        none_idx = len(PET_ORDER)
        none_sel = (self.row == none_idx)
        is_none = self.save.get("equipped_pet") is None
        right = "ĐANG DÙNG" if is_none else "BỎ PET"
        self._draw_row(surf, panel.left + 24, y, panel.width - 48, 60,
                       "Không dùng pet", "Chơi một mình", right,
                       selected=none_sel, color=(120, 120, 130),
                       afford=not is_none)

    def _draw_play_panel(self, surf, panel):
        draw_text(surf, "Sẵn sàng chiến đấu?",
                  (panel.centerx, panel.top + 60), size=34,
                  color=(255, 255, 255), bold=True, center=True)
        # owned summary
        lines = [
            f"Súng sở hữu: {len(self.save['owned_guns'])}/"
            f"{1 + len(HUB_GUN_ORDER)}",
            f"Pet: {len(self.save['owned_pets'])}/{len(PET_ORDER)}"
            f"   |   Đang dùng: "
            f"{PETS[self.save['equipped_pet']]['name'] if self.save.get('equipped_pet') else 'không có'}",
            f"Level đã clear: {self.save['best_level']}/4",
        ]
        for i, line in enumerate(lines):
            draw_text(surf, line,
                      (panel.centerx, panel.top + 130 + i * 36),
                      size=20, color=(220, 230, 220),
                      bold=True, center=True)

        # Big play button
        btn = pygame.Rect(panel.centerx - 220, panel.bottom - 140, 440, 90)
        pulse = (math.sin(self.t * 3) + 1) / 2
        col = (int(GRAB_GREEN[0] + pulse * 30),
               int(GRAB_GREEN[1] + pulse * 30),
               int(GRAB_GREEN[2] + pulse * 20))
        pygame.draw.rect(surf, col, btn)
        pygame.draw.rect(surf, GOLD if self.row == 0 else (20, 30, 24),
                         btn, 5 if self.row == 0 else 2)
        draw_text(surf, "BẮT ĐẦU CHƠI", btn.center, size=36,
                  color=(10, 30, 16), bold=True, center=True)


# ============================================================
# Apply hub upgrades to a Player + spawn pet
# ============================================================
def apply_upgrades_to_player(player, save: dict):
    """Apply persistent character upgrades to a freshly initialised player.

    This is called once per level load. The player object must be the live
    instance so we can mutate hp/max_hp/etc.
    """
    from settings import (
        PLAYER_MAX_HP, PLAYER_WALK_SPEED, PLAYER_RUN_SPEED,
        PLAYER_BIKE_SPEED, STAMINA_MAX,
    )
    up = save.get("upgrades", {})
    player.upgrade_speed_mult = 1.0 + up.get("speed", 0) * CHAR_UPGRADES["speed"]["per_level"]
    player.upgrade_fr_mult = 1.0 + up.get("fire_rate", 0) * CHAR_UPGRADES["fire_rate"]["per_level"]
    player.upgrade_dmg_mult = 1.0 + up.get("damage", 0) * CHAR_UPGRADES["damage"]["per_level"]
    player.max_hp = int(PLAYER_MAX_HP + up.get("max_hp", 0) * CHAR_UPGRADES["max_hp"]["per_level"])
    player.max_stamina = int(STAMINA_MAX + up.get("stamina", 0) * CHAR_UPGRADES["stamina"]["per_level"])
    player.hp = min(player.hp, player.max_hp) if player.hp > 0 else player.max_hp
    player.stamina = player.max_stamina
