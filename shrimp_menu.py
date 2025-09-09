# shrimp_menu.py
import math
import os
import random
import sys
from collections import deque
import pygame

# ---------------------------
# Общие настройки/цвета
# ---------------------------
FPS = 60
FONT_NAME = "freesansbold.ttf"

# скоростя (быстрые как "reverse"-старт)
SNAKE_MIN_SPEED = 6.0
SNAKE_MAX_SPEED = 10.0
PLAYER_SPEED   = 8.2

SPAWN_EVERY = (0.35, 0.75)
SNAKE_LEN = (12, 28)
SNAKE_SPACING = 10
SNAKE_HEAD_R = 11
PLAYER_R = 18

# Награды для режима catcher
REWARD_RED  = 50
REWARD_CYAN = 100
REWARD_GOLD = 200

# Визуал игрока (статичный спрайт)
PLAYER_TEXTURE = "krevetka_game_pfp.png"
SPRITE_SCALE = 2.8
FIXED_ANGLE  = 0

# Меню фон
MENU_BG_CANDIDATES = ["menu_bg.png", "menu_bg.jpg", "menu.jpg", "menu.png"]

# Цвета
BG     = (18, 18, 18)
WHITE  = (240, 240, 240)
GRAY   = (150, 150, 150)
RED    = (230, 70, 70)
CYAN   = (0, 200, 220)
GOLD   = (252, 186, 3)
BLACK  = (0, 0, 0)

# Глобальные размеры экрана объявим после создания окна
WIDTH, HEIGHT = 1280, 720


# ---------------------------
# Утилиты
# ---------------------------
def clamp(x, lo, hi): return lo if x < lo else hi if x > hi else x

def vec_from_to(ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    d = math.hypot(dx, dy) or 1.0
    return dx / d, dy / d

def random_edge_spawn():
    side = random.choice(("top", "bottom", "left", "right"))
    margin = 70
    if side == "top":
        return random.randint(0, WIDTH), -margin
    if side == "bottom":
        return random.randint(0, WIDTH), HEIGHT + margin
    if side == "left":
        return -margin, random.randint(0, HEIGHT)
    return WIDTH + margin, random.randint(0, HEIGHT)

def random_edge_spawn_with_direction():
    """старт на краю и цель на противоположной стороне — прямой пролёт через экран"""
    side = random.choice(("top", "bottom", "left", "right"))
    margin = 70
    if side == "top":
        sx, sy = random.randint(0, WIDTH), -margin
        tx, ty = random.randint(0, WIDTH), HEIGHT + margin
    elif side == "bottom":
        sx, sy = random.randint(0, WIDTH), HEIGHT + margin
        tx, ty = random.randint(0, WIDTH), -margin
    elif side == "left":
        sx, sy = -margin, random.randint(0, HEIGHT)
        tx, ty = WIDTH + margin, random.randint(0, HEIGHT)
    else:
        sx, sy = WIDTH + margin, random.randint(0, HEIGHT)
        tx, ty = -margin, random.randint(0, HEIGHT)
    return (sx, sy), (tx, ty)


# ---------------------------
# Игровые сущности
# ---------------------------
class Snake:
    """Змейка: разделяем логику движения (для обоих режимов одинаковая — прямой пролет)."""
    def __init__(self):
        (self.x, self.y), (tx, ty) = random_edge_spawn_with_direction()
        self.length = random.randint(*SNAKE_LEN)
        if self.length >= SNAKE_LEN[1] - 2:
            self.color, self.value = GOLD, REWARD_GOLD
        elif self.length >= (SNAKE_LEN[0] + SNAKE_LEN[1]) // 2:
            self.color, self.value = CYAN, REWARD_CYAN
        else:
            self.color, self.value = RED, REWARD_RED

        base = random.uniform(SNAKE_MIN_SPEED, SNAKE_MAX_SPEED)
        ux, uy = vec_from_to(self.x, self.y, tx, ty)
        self.vx, self.vy = ux * base, uy * base
        self.speed = base

        self.trail = deque([(self.x, self.y)], maxlen=self.length * SNAKE_SPACING)
        self.alive = True

        # лёгкая «извилистость»
        self.phase = random.random() * math.tau
        self.wobble = random.uniform(0.6, 1.2)
        self.wfreq  = random.uniform(0.08, 0.12)

    def update(self, dt):
        # синусоидальное смещение перпендикулярно траектории
        self.phase += self.wfreq
        ox, oy = -self.vy / (self.speed or 1.0), self.vx / (self.speed or 1.0)
        wob = math.sin(self.phase) * self.wobble
        self.x += self.vx + ox * wob
        self.y += self.vy + oy * wob

        # след для сегментов
        lastx, lasty = self.trail[-1]
        steps = int(max(1, math.hypot(self.x - lastx, self.y - lasty)))
        for i in range(steps):
            t = (i + 1) / steps
            self.trail.append((lastx + (self.x - lastx) * t,
                               lasty + (self.y - lasty) * t))

        # если далеко — удалить
        if self.x < -300 or self.x > WIDTH + 300 or self.y < -300 or self.y > HEIGHT + 300:
            self.alive = False

    def head_pos(self):
        try:
            return self.trail[-1]
        except IndexError:
            return self.x, self.y

    def iter_segments(self):
        pts = list(self.trail)
        if len(pts) < 2:
            return None
        step = SNAKE_SPACING
        idx  = len(pts) - 1
        segs = []
        r = SNAKE_HEAD_R
        for n in range(self.length):
            p = max(0, idx - n * step)
            x, y = pts[p]
            rr = max(2, r * (1 - n / (self.length + 2)))
            segs.append((x, y, rr))
        return segs

    def draw(self, surf):
        segs = list(self.iter_segments() or [])
        for sx, sy, rr in segs:
            pygame.draw.circle(surf, self.color, (int(sx), int(sy)), int(rr))
        if segs:
            hx, hy, r = segs[-1]
            pygame.draw.circle(surf, (15, 15, 15),
                               (int(hx + r * 0.3), int(hy - r * 0.1)),
                               max(2, int(r * 0.18)))


class Player:
    """Креветка — статичный спрайт; хитбокс круглый."""
    def __init__(self, x, y, image_surf=None):
        self.x, self.y = x, y
        self.r = PLAYER_R
        self.speed = PLAYER_SPEED
        self.sprite = None
        if image_surf:
            target = int(self.r * 2 * SPRITE_SCALE)
            w, h = image_surf.get_width(), image_surf.get_height()
            if w >= h:
                nw, nh = target, max(1, int(target * h / w))
            else:
                nh, nw = target, max(1, int(target * w / h))
            scaled = pygame.transform.smoothscale(image_surf, (nw, nh))
            self.sprite = pygame.transform.rotozoom(scaled, FIXED_ANGLE, 1.0)

    def update(self, keys):
        dx = dy = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]: dy += 1
        if dx or dy:
            l = math.hypot(dx, dy)
            dx, dy = dx / l, dy / l
            self.x += dx * self.speed
            self.y += dy * self.speed
        self.x = clamp(self.x, self.r, WIDTH - self.r)
        self.y = clamp(self.y, self.r, HEIGHT - self.r)

    def draw(self, surf):
        if self.sprite:
            rect = self.sprite.get_rect(center=(int(self.x), int(self.y)))
            surf.blit(self.sprite, rect)
        else:
            pygame.draw.circle(surf, (255, 120, 90), (int(self.x), int(self.y)), self.r)


# ---------------------------
# Загрузка ассетов
# ---------------------------
def load_player_texture():
    if os.path.exists(PLAYER_TEXTURE):
        try:
            return pygame.image.load(PLAYER_TEXTURE).convert_alpha()
        except Exception:
            pass
    return None

def load_menu_bg():
    for p in MENU_BG_CANDIDATES:
        if os.path.exists(p):
            try:
                return pygame.image.load(p).convert()
            except Exception:
                pass
    return None


# ---------------------------
# UI — кнопка
# ---------------------------
class Button:
    def __init__(self, x, y, w, h, text, font, bg=(30, 30, 30), fg=WHITE):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = font
        self.bg = bg
        self.fg = fg

    def draw(self, surf, hover=False):
        base = (self.bg[0]+15, self.bg[1]+15, self.bg[2]+15) if hover else self.bg
        pygame.draw.rect(surf, base, self.rect, border_radius=12)
        pygame.draw.rect(surf, (255,255,255,40), self.rect, width=2, border_radius=12)
        label = self.font.render(self.text, True, self.fg)
        surf.blit(label, (self.rect.x + 16, self.rect.y + (self.rect.h - label.get_height()) // 2))

    def is_hover(self, pos):
        return self.rect.collidepoint(pos)


# ---------------------------
# Экран меню
# ---------------------------
def run_menu(screen, clock):
    bg = load_menu_bg()
    if bg:
        bg = pygame.transform.scale(bg, screen.get_size())

    title_font = pygame.font.Font(FONT_NAME, 64)
    btn_font   = pygame.font.Font(FONT_NAME, 28)
    hint_font  = pygame.font.Font(FONT_NAME, 20)

    # две кнопки внизу слева
    pad  = 24
    b_w, b_h = 220, 56
    bx, by = 24, HEIGHT - pad - b_h*2 - 10  # две кнопки столбиком
    btn_surv = Button(bx, by, b_w, b_h, "SURVIVER", btn_font, bg=(40, 40, 60))
    btn_catch = Button(bx, by + b_h + 10, b_w, b_h, "CATCHER", btn_font, bg=(60, 40, 40))

    while True:
        dt = clock.tick(FPS) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                pygame.quit(); sys.exit()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                pos = pygame.mouse.get_pos()
                if btn_surv.is_hover(pos):
                    return "surviver"
                if btn_catch.is_hover(pos):
                    return "catcher"

        # рисуем
        if bg:
            screen.blit(bg, (0, 0))
        else:
            screen.fill(BG)

        # лёгкий затемняющий слой, чтобы текст читался
        dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 80))
        screen.blit(dim, (0, 0))

        # заголовок
        title = title_font.render("S.H.R.I.M.P", True, WHITE)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 40))

        # кнопки
        mouse = pygame.mouse.get_pos()
        btn_surv.draw(screen, btn_surv.is_hover(mouse))
        btn_catch.draw(screen, btn_catch.is_hover(mouse))

        # подсказка
        hint = hint_font.render("Choose mode", True, WHITE)
        screen.blit(hint, (bx, btn_surv.rect.y - 30))

        pygame.display.flip()


# ---------------------------
# Игровые режимы
# ---------------------------
def run_surviver(screen, clock):
    """Убегаем: секундомер, любое касание тела змейки = проигрыш."""
    font  = pygame.font.Font(FONT_NAME, 30)
    big   = pygame.font.Font(FONT_NAME, 56)
    small = pygame.font.Font(FONT_NAME, 22)

    player = Player(WIDTH//2, HEIGHT//2, load_player_texture())
    snakes, particles = [], []
    elapsed = 0.0
    paused = False
    game_over = False
    next_spawn = 0.0

    def spawn(): snakes.append(Snake())

    while True:
        dt = clock.tick(FPS) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_p and not game_over: paused = not paused
                if e.key == pygame.K_ESCAPE and game_over: return  # в меню
        keys = pygame.key.get_pressed()

        if not paused and not game_over:
            elapsed += dt
            player.update(keys)
            for s in snakes: s.update(dt)
            snakes = [s for s in snakes if s.alive]
            next_spawn -= dt
            if next_spawn <= 0:
                spawn()
                next_spawn = random.uniform(*SPAWN_EVERY)

            # коллизия по всей змейке
            px, py, pr = player.x, player.y, PLAYER_R
            hit = False
            for s in snakes:
                segs = s.iter_segments() or []
                for (sx, sy, rr) in segs:
                    if (px - sx)**2 + (py - sy)**2 <= (pr + rr)**2:
                        hit = True; break
                if hit: break
            if hit:
                game_over = True

        # рендер
        screen.fill(BLACK)
        for s in snakes: s.draw(screen)
        player.draw(screen)
        # HUD
        screen.blit(font.render(f"Time: {elapsed:05.2f}s", True, WHITE), (24, 20))
        screen.blit(small.render("WASD/Arrows — move, P — pause", True, GRAY), (24, 60))

        if paused:
            t = big.render("PAUSED", True, CYAN)
            screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - t.get_height()//2))

        if game_over:
            over = big.render("GAME OVER", True, RED)
            res  = font.render(f"You survived: {elapsed:.2f} s", True, WHITE)
            hint = font.render("Esc — back to menu", True, WHITE)
            screen.blit(over, (WIDTH//2 - over.get_width()//2, HEIGHT//2 - 110))
            screen.blit(res,  (WIDTH//2 - res.get_width()//2,   HEIGHT//2 - 40))
            screen.blit(hint, (WIDTH//2 - hint.get_width()//2,  HEIGHT//2 + 20))

        pygame.display.flip()


def run_catcher(screen, clock):
    """Собираем головы змей: таймер 20с, очки."""
    font  = pygame.font.Font(FONT_NAME, 22)
    small = pygame.font.Font(FONT_NAME, 18)
    big   = pygame.font.Font(FONT_NAME, 46)
    GAME_TIME = 20

    player = Player(WIDTH//2, HEIGHT//2, load_player_texture())
    snakes, particles = [], []
    score = 0
    time_left = GAME_TIME
    paused = False
    game_over = False
    next_spawn = random.uniform(*SPAWN_EVERY)

    def spawn(): snakes.append(Snake())

    while True:
        dt = clock.tick(FPS) / 1000.0
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_p and not game_over: paused = not paused
                if e.key == pygame.K_ESCAPE and game_over: return  # в меню
        keys = pygame.key.get_pressed()

        if not paused and not game_over:
            time_left -= dt
            if time_left <= 0:
                time_left = 0; game_over = True

            player.update(keys)
            for s in snakes: s.update(dt)
            snakes = [s for s in snakes if s.alive]

            next_spawn -= dt
            if next_spawn <= 0:
                spawn()
                next_spawn = random.uniform(*SPAWN_EVERY)

            # сбор по голове
            px, py = player.x, player.y
            for s in list(snakes):
                hx, hy = s.head_pos()
                if (px - hx)**2 + (py - hy)**2 <= (PLAYER_R + SNAKE_HEAD_R)**2:
                    score += s.value
                    snakes.remove(s)

        # рендер
        screen.fill(BG)
        for s in snakes: s.draw(screen)
        player.draw(screen)

        screen.blit(small.render(f"Score: {score}", True, WHITE), (16, 12))
        t = small.render(f"Time: {int(time_left):02d}s", True, WHITE)
        screen.blit(t, (WIDTH - t.get_width() - 16, 12))

        # легенда слева снизу
        legend_y = HEIGHT - 70
        pygame.draw.circle(screen, RED, (26, legend_y), 6)
        screen.blit(small.render(f"= {REWARD_RED}", True, WHITE), (44, legend_y - 12))
        pygame.draw.circle(screen, CYAN, (26, legend_y + 22), 6)
        screen.blit(small.render(f"= {REWARD_CYAN}", True, WHITE), (44, legend_y + 10))
        pygame.draw.circle(screen, GOLD, (26, legend_y + 44), 6)
        screen.blit(small.render(f"= {REWARD_GOLD}", True, WHITE), (44, legend_y + 32))

        if paused:
            p = big.render("PAUSED", True, GRAY)
            screen.blit(p, (WIDTH//2 - p.get_width()//2, HEIGHT//2 - p.get_height()//2))

        if game_over:
            over = big.render("Time out!", True, WHITE)
            sc   = small.render(f"Your score: {score}", True, GOLD)
            hint = small.render("Esc — back to menu", True, GRAY)
            screen.blit(over, (WIDTH//2 - over.get_width()//2, HEIGHT//2 - 80))
            screen.blit(sc,   (WIDTH//2 - sc.get_width()//2,   HEIGHT//2 - 20))
            screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2 + 24))

        pygame.display.flip()


# ---------------------------
# Точка входа
# ---------------------------
def main():
    global WIDTH, HEIGHT
    pygame.init()
    pygame.display.set_caption("S.H.R.I.M.P — Menu")

    # --- Жёсткий полноэкранный без чёрных полос ---
    # пробуем 1920x1080; если нет — берём максимальный доступный режим
    want = (1920, 1080)
    modes = pygame.display.list_modes()  # отсортированы по убыванию
    size = want if want in modes else (modes[0] if modes else (0, 0))

    # FULLSCREEN без SCALED -> рисуем в нативное, ничего не «масштабируется» и не обрезается
    flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
    screen = pygame.display.set_mode(size, flags)

    WIDTH, HEIGHT = screen.get_size()     # обновляем глобальные размеры под реальное фуллскрин-окно
    # ---------------------------------------------

    clock = pygame.time.Clock()

    while True:
        mode = run_menu(screen, clock)
        if mode == "surviver":
            run_surviver(screen, clock)
        elif mode == "catcher":
            run_catcher(screen, clock)


if __name__ == "__main__":
    main()
