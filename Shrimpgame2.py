# shrimp_snakes_fullscreen_fast.py
import math
import os
import random
import sys
from collections import deque
import pygame

# ---------------------------
# Настройки
# ---------------------------
FPS = 60
GAME_TIME = 20  # секунд

# Награды
REWARD_RED = 50
REWARD_CYAN = 100
REWARD_GOLD = 200

# Скорости (как в начале реверс-режима)
SNAKE_MIN_SPEED = 6.0
SNAKE_MAX_SPEED = 10.0
PLAYER_SPEED = 8.2

SPAWN_EVERY = (0.35, 0.75)  # чаще спавним для динамики
SNAKE_LEN = (12, 28)
SNAKE_SPACING = 10
SNAKE_HEAD_R = 9
PLAYER_R = 16
COLLECT_DIST = PLAYER_R + SNAKE_HEAD_R + 2

# Текстура игрока
TEXTURE_PATH = "krevetka_game_pfp.png"  # PNG с прозрачностью рядом с файлом
SPRITE_SCALE = 2.6
DEFAULT_ANGLE = 0

# Цвета
BG = (18, 18, 18)
WHITE = (240, 240, 240)
GRAY = (140, 140, 140)
GOLD = (252, 186, 3)
CYAN = (0, 200, 220)
RED = (230, 70, 70)

FONT_NAME = "freesansbold.ttf"

# Глобальные размеры экрана определим после создания окна
WIDTH, HEIGHT = 1280, 720  # временно (перепишутся при запуске)


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
    if side == "top":
        return random.randint(0, WIDTH), -40
    if side == "bottom":
        return random.randint(0, WIDTH), HEIGHT + 40
    if side == "left":
        return -40, random.randint(0, HEIGHT)
    return WIDTH + 40, random.randint(0, HEIGHT)


# ---------------------------
# Классы
# ---------------------------
class Snake:
    def __init__(self):
        self.x, self.y = random_edge_spawn()

        # длина -> редкость/награда
        self.length = random.randint(*SNAKE_LEN)
        if self.length >= SNAKE_LEN[1] - 2:
            self.color, self.value = GOLD, REWARD_GOLD
        elif self.length >= (SNAKE_LEN[0] + SNAKE_LEN[1]) // 2:
            self.color, self.value = CYAN, REWARD_CYAN
        else:
            self.color, self.value = RED, REWARD_RED

        # скорость растёт с наградой (но база — как в реверсе)
        t = (self.value - REWARD_RED) / float(REWARD_GOLD - REWARD_RED)  # 0..1
        speed = SNAKE_MIN_SPEED + t * (SNAKE_MAX_SPEED - SNAKE_MIN_SPEED)

        # летим к случайной точке внутри поля
        tx = random.randint(WIDTH // 6, WIDTH * 5 // 6)
        ty = random.randint(HEIGHT // 6, HEIGHT * 5 // 6)
        ux, uy = vec_from_to(self.x, self.y, tx, ty)
        self.vx, self.vy = ux * speed, uy * speed

        self.trail = deque([(self.x, self.y)], maxlen=self.length * SNAKE_SPACING)
        self.alive = True

        # «извилистость»
        self.phase = random.random() * math.tau
        self.wobble = random.uniform(0.8, 1.6)
        self.wfreq = random.uniform(0.07, 0.12)

    def update(self, dt):
        # синусоидальное смещение поперёк траектории
        self.phase += self.wfreq
        speed = math.hypot(self.vx, self.vy)
        ox, oy = -self.vy / (speed or 1.0), self.vx / (speed or 1.0)
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

        # очистка, если далеко
        if self.x < -200 or self.x > WIDTH + 200 or self.y < -200 or self.y > HEIGHT + 200:
            self.alive = False

    def head_pos(self):
        try: return self.trail[-1]
        except IndexError: return self.x, self.y

    def iter_segments(self):
        pts = list(self.trail)
        if len(pts) < 2: return None
        step = SNAKE_SPACING
        idx = len(pts) - 1
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
            self.sprite = pygame.transform.rotozoom(scaled, DEFAULT_ANGLE, 1.0)

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
# Вспомогательные функции
# ---------------------------
def load_shrimp_texture():
    if os.path.exists(TEXTURE_PATH):
        try:
            return pygame.image.load(TEXTURE_PATH).convert_alpha()
        except Exception:
            pass
    return None


# ---------------------------
# Игровой цикл
# ---------------------------
def main():
    global WIDTH, HEIGHT
    pygame.init()
    pygame.display.set_caption("S.H.R.I.M.P — CATCH YOUR SHRIMP!")

    # Нативный fullscreen без чёрных полос: берём текущую «родную» развертку
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    WIDTH, HEIGHT = screen.get_size()  # обновляем глобальные размеры под монитор

    clock = pygame.time.Clock()
    font = pygame.font.Font(FONT_NAME, 22)
    small = pygame.font.Font(FONT_NAME, 18)
    big = pygame.font.Font(FONT_NAME, 46)

    player = Player(WIDTH // 2, HEIGHT // 2, load_shrimp_texture())
    snakes, particles = [], []

    score = 0
    time_left = GAME_TIME
    paused = False
    game_over = False
    next_spawn = random.uniform(*SPAWN_EVERY)

    def spawn_snake():
        snakes.append(Snake())

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
            time_left -= dt
            if time_left <= 0:
                time_left = 0
                game_over = True

            player.update(keys)

            for s in snakes:
                s.update(dt)
            snakes = [s for s in snakes if s.alive]

            next_spawn -= dt
            if next_spawn <= 0:
                spawn_snake()
                next_spawn = random.uniform(*SPAWN_EVERY)

            # сбор
            px, py = player.x, player.y
            for s in list(snakes):
                hx, hy = s.head_pos()
                if (px - hx) ** 2 + (py - hy) ** 2 <= COLLECT_DIST ** 2:
                    score += s.value
                    snakes.remove(s)
                    for _ in range(18):
                        ang = random.random() * math.tau
                        sp = random.uniform(40, 140)
                        vx, vy = math.cos(ang)*sp, math.sin(ang)*sp
                        particles.append([hx, hy, vx, vy, 0.5])

            for p in particles:
                p[0] += p[2] * dt; p[1] += p[3] * dt; p[4] -= dt
            particles[:] = [p for p in particles if p[4] > 0]

        # ---- Рендер ----
        screen.fill(BG)

        for s in snakes:
            s.draw(screen)

        for x, y, _, _, _life in particles:
            pygame.draw.circle(screen, GOLD, (int(x), int(y)), 2)

        player.draw(screen)

        # HUD: счёт и время
        screen.blit(small.render(f"Score: {score}", True, WHITE), (16, 12))
        time_surf = small.render(f"Time: {int(time_left):02d}s", True, WHITE)
        screen.blit(time_surf, (WIDTH - time_surf.get_width() - 16, 12))

        # Легенда слева снизу (награды)
        legend_y = HEIGHT - 70
        pygame.draw.circle(screen, RED, (26, legend_y), 6)
        screen.blit(small.render(f"= {REWARD_RED}", True, WHITE), (44, legend_y - 12))
        pygame.draw.circle(screen, CYAN, (26, legend_y + 22), 6)
        screen.blit(small.render(f"= {REWARD_CYAN}", True, WHITE), (44, legend_y + 10))
        pygame.draw.circle(screen, GOLD, (26, legend_y + 44), 6)
        screen.blit(small.render(f"= {REWARD_GOLD}", True, WHITE), (44, legend_y + 32))

        if paused:
            t = big.render("PAUSE (P)", True, GRAY)
            screen.blit(t, (WIDTH // 2 - t.get_width() // 2,
                            HEIGHT // 2 - t.get_height() // 2))

        if game_over:
            over = big.render("Time out!", True, WHITE)
            sc = small.render(f"Your score: {score}", True, GOLD)
            hint = small.render("Esc — play again", True, GRAY)
            screen.blit(over, (WIDTH // 2 - over.get_width() // 2, HEIGHT // 2 - 80))
            screen.blit(sc, (WIDTH // 2 - sc.get_width() // 2, HEIGHT // 2 - 20))
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 24))

        pygame.display.flip()


if __name__ == "__main__":
    main()
