# shrimp_escape_arcade_scaling.py
import math
import os
import random
import sys
from collections import deque

import pygame

# ---------------------------
# Экран (Full HD)
# ---------------------------
WIDTH, HEIGHT = 1920, 1080
FPS = 60
FULLSCREEN = True

# ---------------------------
# Геймплей (базовые значения)
# ---------------------------
# БАЗА (на старте игры)
SNAKE_MIN_SPEED_BASE = 6.0
SNAKE_MAX_SPEED_BASE = 10.0
SPAWN_EVERY_BASE = (0.35, 0.75)   # интервал спавна (сек)

# РОСТ СЛОЖНОСТИ
SPEED_GROWTH_PER_SEC = 0.028      # +2.8% скорости в секунду (экспоненциально)
SPAWN_GROWTH_PER_SEC = 0.035      # -3.5% к интервалу спавна в секунду
SNAKE_SPEED_CAP = 20.0            # потолок скорости
SPAWN_INTERVAL_FLOOR = 0.10       # нижняя граница интервала спавна

SNAKE_LEN = (10, 24)
SNAKE_SPACING = 10
SNAKE_HEAD_R = 11
PLAYER_R = 18

# Игрок быстрее базовой змейки, но медленнее сильно разогнавшихся
PLAYER_SPEED = 8.6

# Игрок — статичный спрайт (хитбокс круглый)
TEXTURE_BASENAME = "krevetka_game_pfp"  # .png/.webp/.jpg
SPRITE_SCALE = 2.8
FIXED_ANGLE = -12

# Цвета
BG = (18, 18, 18)
WHITE = (240, 240, 240)
GRAY = (150, 150, 150)
RED = (230, 70, 70)
CYAN = (0, 200, 220)
GOLD = (252, 186, 3)

FONT_NAME = "freesansbold.ttf"


# ---------------------------
# Утилиты
# ---------------------------
def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

def vec_from_to(ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    d = math.hypot(dx, dy) or 1.0
    return dx / d, dy / d

def random_edge_spawn_with_direction():
    """Старт на краю и цель на противоположной стороне — полёт по прямой через экран."""
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

def difficulty_scalars(elapsed):
    """
    Возвращает (speed_mult, spawn_mult) для времени elapsed (сек).
    speed_mult растёт, spawn_mult уменьшается (для деления интервала).
    """
    # экспоненциальный рост: mult = e^(k * t)
    speed_mult = math.exp(SPEED_GROWTH_PER_SEC * elapsed)
    spawn_mult = math.exp(SPAWN_GROWTH_PER_SEC * elapsed)
    return speed_mult, spawn_mult


# ---------------------------
# Классы
# ---------------------------
class Snake:
    """Змейка быстро пролетает через экран. Не преследует игрока."""
    def __init__(self, speed_now):
        (self.x, self.y), (tx, ty) = random_edge_spawn_with_direction()

        # длина и цвет для разнообразия
        self.length = random.randint(*SNAKE_LEN)
        if self.length >= SNAKE_LEN[1] - 2:
            self.color = GOLD
        elif self.length >= (SNAKE_LEN[0] + SNAKE_LEN[1]) // 2:
            self.color = CYAN
        else:
            self.color = RED

        # скорость — из текущей сложности + небольшой разброс
        base = random.uniform(SNAKE_MIN_SPEED_BASE, SNAKE_MAX_SPEED_BASE)
        self.speed = clamp(base * speed_now, 0, SNAKE_SPEED_CAP)

        ux, uy = vec_from_to(self.x, self.y, tx, ty)
        self.vx, self.vy = ux * self.speed, uy * self.speed

        self.trail = deque([(self.x, self.y)], maxlen=self.length * SNAKE_SPACING)
        self.alive = True

        # лёгкая «извилистость»
        self.phase = random.random() * math.tau
        self.wobble = random.uniform(0.5, 1.2)
        self.wfreq = random.uniform(0.08, 0.12)

    def update(self, dt):
        # синусоидальное смещение поперёк траектории
        self.phase += self.wfreq
        ox, oy = -self.vy / (self.speed or 1.0), self.vx / (self.speed or 1.0)
        wob = math.sin(self.phase) * self.wobble
        self.x += self.vx + ox * wob
        self.y += self.vy + oy * wob

        # след
        lastx, lasty = self.trail[-1]
        steps = int(max(1, math.hypot(self.x - lastx, self.y - lasty)))
        for i in range(steps):
            t = (i + 1) / steps
            ix = lastx + (self.x - lastx) * t
            iy = lasty + (self.y - lasty) * t
            self.trail.append((ix, iy))

        # далеко за экраном — удалить
        if self.x < -300 or self.x > WIDTH + 300 or self.y < -300 or self.y > HEIGHT + 300:
            self.alive = False

    def iter_segments(self):
        """Сегменты тела для рисования/коллизии: (x, y, r) от хвоста к голове."""
        pts = list(self.trail)
        if len(pts) < 2:
            return None
        step = SNAKE_SPACING
        idx = len(pts) - 1
        segs = []
        head_r = SNAKE_HEAD_R
        for n in range(self.length):
            p = max(0, idx - n * step)
            x, y = pts[p]
            rr = max(2, head_r * (1 - n / (self.length + 2)))
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
# Загрузка спрайта игрока
# ---------------------------
def load_shrimp_texture():
    for ext in (".png", ".webp", ".jpg", ".jpeg"):
        path = TEXTURE_BASENAME + ext
        if os.path.exists(path):
            try:
                return pygame.image.load(path).convert_alpha()
            except Exception:
                pass
    return None


# ---------------------------
# Основной цикл
# ---------------------------
def main():
    pygame.init()
    flags = pygame.FULLSCREEN if FULLSCREEN else 0
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption("S.H.R.I.M.P — RUN!")
    clock = pygame.time.Clock()

    font = pygame.font.Font(FONT_NAME, 30)
    big = pygame.font.Font(FONT_NAME, 56)
    small = pygame.font.Font(FONT_NAME, 22)

    player = Player(WIDTH // 2, HEIGHT // 2, load_shrimp_texture())
    snakes = []
    particles = []

    # секундомер
    elapsed = 0.0
    paused = False
    game_over = False

    # спавнер
    next_spawn = 0.0  # сразу спавним в начале

    def spawn():
        speed_mult, _ = difficulty_scalars(elapsed)
        snakes.append(Snake(speed_now=speed_mult))

    while True:
        dt = clock.tick(FPS) / 1000.0

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_p and not game_over:
                    paused = not paused
                if e.key == pygame.K_ESCAPE and game_over:
                    return main()

        keys = pygame.key.get_pressed()

        if not paused and not game_over:
            elapsed += dt

            # --- сложность
            speed_mult, spawn_mult = difficulty_scalars(elapsed)
            # актуальный интервал спавна — базовый / spawn_mult, с полом
            low = max(SPAWN_INTERVAL_FLOOR, SPAWN_EVERY_BASE[0] / spawn_mult)
            high = max(SPAWN_INTERVAL_FLOOR, SPAWN_EVERY_BASE[1] / spawn_mult)

            player.update(keys)

            for s in snakes:
                s.update(dt)
            snakes = [s for s in snakes if s.alive]

            # спавн
            next_spawn -= dt
            if next_spawn <= 0:
                spawn()
                next_spawn = random.uniform(low, high)

            # столкновение: по всей змейке (любой сегмент)
            px, py = player.x, player.y
            pr = PLAYER_R
            collided = False
            for s in snakes:
                segs = s.iter_segments() or []
                for (sx, sy, rr) in segs:
                    if (px - sx) ** 2 + (py - sy) ** 2 <= (pr + rr) ** 2:
                        collided = True
                        break
                if collided:
                    break

            if collided:
                game_over = True
                # эффект «удара»
                for _ in range(40):
                    ang = random.random() * math.tau
                    sp = random.uniform(80, 240)
                    vx, vy = math.cos(ang) * sp, math.sin(ang) * sp
                    particles.append([px, py, vx, vy, 0.6])

            # апдейт частиц
            for p in particles:
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                p[4] -= dt
            particles[:] = [p for p in particles if p[4] > 0]

        # ----- Рендер -----
        screen.fill(BG)

        for s in snakes:
            s.draw(screen)

        # частицы
        for x, y, _, _, life in particles:
            a = max(0, min(255, int(255 * (life / 0.6))))
            surf = pygame.Surface((4, 4), pygame.SRCALPHA)
            surf.fill((255, 255, 255, a))
            screen.blit(surf, (int(x), int(y)))

        player.draw(screen)

        # HUD: секундомер + подсказка + индикатор сложности
        time_txt = f"Время: {elapsed:05.2f} s"
        screen.blit(font.render(time_txt, True, WHITE), (24, 20))
        screen.blit(small.render("WASD — MOVE, P — PAUSE", True, GRAY), (24, 60))

        # Индикатор сложности (для отладки/ощущения) — текущий множитель скорости/спавна
        if not game_over:
            spd_mult, spn_mult = difficulty_scalars(elapsed)
            info = f"Difficult: speed ×{spd_mult:.2f} | spawn ×{spn_mult:.2f}"
            screen.blit(small.render(info, True, CYAN), (24, 90))

        if paused:
            t = big.render("PAUSE", True, CYAN)
            screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - t.get_height()//2))

        if game_over:
            over = big.render("DEFEAT!", True, RED)
            res = font.render(f"You were alive: {elapsed:.2f} сек", True, WHITE)
            hint = font.render("Esc — play again", True, WHITE)
            screen.blit(over, (WIDTH//2 - over.get_width()//2, HEIGHT//2 - 110))
            screen.blit(res, (WIDTH//2 - res.get_width()//2, HEIGHT//2 - 40))
            screen.blit(hint, (WIDTH//2 - hint.get_width()//2, HEIGHT//2 + 20))

        pygame.display.flip()


if __name__ == "__main__":
    main()
