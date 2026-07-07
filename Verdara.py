"""
Aetherfall: Shards of Mira
Original 2D top-down RPG prototype made with Pygame.

Controls
--------
Arrow keys / WASD : Move
SPACE             : Melee attack
F                 : Fire Orb (uses MP)
1                 : Use small HP potion
ESC               : Quit
"""

import math
import os
import random
import pygame as pg


# どの場所から実行しても，相対パスでファイルを読み込めるようにする。
os.chdir(os.path.dirname(os.path.abspath(__file__)))

WIDTH, HEIGHT = 1100, 700
FPS = 60

# Colors
SAND = (231, 211, 151)
WATER = (67, 189, 226)
GRASS = (104, 170, 92)
STONE = (126, 124, 117)
DARK_STONE = (86, 84, 81)
UI_DARK = (35, 36, 46)
UI_LIGHT = (235, 229, 207)
HP_RED = (205, 56, 63)
MP_BLUE = (55, 130, 220)
EXP_GREEN = (157, 205, 53)
PLAYER_BLUE = (45, 108, 196)
ENEMY_PURPLE = (120, 61, 153)
FIRE_ORANGE = (255, 132, 37)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def clamp(value: float, low: float, high: float) -> float:
    """Return value limited between low and high."""
    return max(low, min(value, high))


class FloatingText:
    """Short message displayed above a game object."""

    def __init__(self, text: str, pos: tuple[int, int], color: tuple[int, int, int]):
        self.text = text
        self.x, self.y = pos
        self.color = color
        self.timer = 0.75

    def update(self, dt: float) -> None:
        # ダメージや報酬のメッセージを上へ移動し，短時間後に削除する。
        self.y -= 32 * dt
        self.timer -= dt

    def draw(self, screen: pg.Surface, font: pg.font.Font) -> None:
        image = font.render(self.text, True, self.color)
        rect = image.get_rect(center=(self.x, self.y))
        screen.blit(image, rect)


class Player:
    """Player character with basic RPG stats and actions."""

    def __init__(self) -> None:
        self.rect = pg.Rect(500, 330, 34, 42)
        self.direction = pg.Vector2(0, 1)

        self.level = 1
        self.exp = 0
        self.exp_to_next = 100

        self.max_hp = 100
        self.hp = 100
        self.max_mp = 30
        self.mp = 30

        self.attack = 12
        self.magic_attack = 16
        self.speed = 230

        self.attack_cooldown = 0.0
        self.magic_cooldown = 0.0
        self.potions = 3

    def update(self, dt: float, keys: pg.key.ScancodeWrapper) -> None:
        # Convert keyboard input into one movement vector.
        move = pg.Vector2(
            int(keys[pg.K_d] or keys[pg.K_RIGHT]) - int(keys[pg.K_a] or keys[pg.K_LEFT]),
            int(keys[pg.K_s] or keys[pg.K_DOWN]) - int(keys[pg.K_w] or keys[pg.K_UP]),
        )

        if move.length_squared() > 0:
            # Normalize diagonal movement so it is not faster than horizontal movement.
            move = move.normalize()
            self.direction = move
            self.rect.x += round(move.x * self.speed * dt)
            self.rect.y += round(move.y * self.speed * dt)

        # Keep the player inside the playable area and away from the HUD.
        self.rect.x = int(clamp(self.rect.x, 20, WIDTH - self.rect.width - 20))
        self.rect.y = int(clamp(self.rect.y, 115, HEIGHT - self.rect.height - 88))

        # Count down the cooldowns every frame.
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        self.magic_cooldown = max(0.0, self.magic_cooldown - dt)

        # Slow MP regeneration.
        self.mp = min(self.max_mp, self.mp + 2.5 * dt)

    def melee_area(self) -> pg.Rect:
        """Return the hitbox in front of the player."""
        reach = 42
        center = pg.Vector2(self.rect.center) + self.direction * reach
        return pg.Rect(int(center.x - 28), int(center.y - 28), 56, 56)

    def try_melee_attack(self) -> pg.Rect | None:
        """Return an attack hitbox only when the melee cooldown has finished."""
        if self.attack_cooldown > 0:
            return None
        self.attack_cooldown = 0.35
        return self.melee_area()

    def try_fire_orb(self) -> "Projectile | None":
        """Create a fireball only when enough MP is available and magic is ready."""
        if self.magic_cooldown > 0 or self.mp < 8:
            return None

        self.mp -= 8
        self.magic_cooldown = 0.45
        origin = pg.Vector2(self.rect.center) + self.direction * 26
        return Projectile(origin, self.direction, self.magic_attack)

    def use_potion(self) -> bool:
        """Use one potion and return whether HP was actually restored."""
        if self.potions <= 0 or self.hp >= self.max_hp:
            return False
        self.potions -= 1
        self.hp = min(self.max_hp, self.hp + 35)
        return True

    def gain_exp(self, amount: int) -> bool:
        """Add EXP. Return True when a level up happens."""
        self.exp += amount
        leveled_up = False

        while self.exp >= self.exp_to_next:
            self.exp -= self.exp_to_next
            self.level += 1
            self.exp_to_next = int(self.exp_to_next * 1.35)

            self.max_hp += 10
            self.max_mp += 5
            self.attack += 2
            self.magic_attack += 2
            self.speed += 5
            self.hp = self.max_hp
            self.mp = self.max_mp
            leveled_up = True

        return leveled_up

    def draw(self, screen: pg.Surface) -> None:
        # Shadow
        pg.draw.ellipse(screen, (55, 55, 55), (self.rect.x - 2, self.rect.bottom - 9, 38, 13))
        # Body
        pg.draw.rect(screen, PLAYER_BLUE, self.rect, border_radius=8)
        # Hair / face
        pg.draw.circle(screen, (255, 220, 158), (self.rect.centerx, self.rect.y + 10), 11)
        pg.draw.circle(screen, (242, 191, 59), (self.rect.centerx, self.rect.y + 5), 11)
        # Direction indicator
        tip = pg.Vector2(self.rect.center) + self.direction * 28
        pg.draw.line(screen, WHITE, self.rect.center, tip, 3)


class Enemy:
    """Simple enemy that chases the player when close."""

    def __init__(self, pos: tuple[int, int], enemy_type: str = "Shadow Slime") -> None:
        self.rect = pg.Rect(pos[0], pos[1], 34, 34)
        self.enemy_type = enemy_type
        self.max_hp = 40
        self.hp = self.max_hp
        self.speed = random.randint(65, 85)
        self.attack = 8
        self.attack_timer = random.uniform(0.0, 0.8)
        self.exp_reward = 35
        self.coin_reward = random.randint(4, 8)

    def update(self, dt: float, player: Player) -> int:
        """Move and return damage dealt to player this frame."""
        to_player = pg.Vector2(player.rect.center) - pg.Vector2(self.rect.center)
        distance = to_player.length()

        # Chase only inside the detection range; stop when close enough to attack.
        if 42 < distance < 250:
            direction = to_player.normalize()
            self.rect.x += round(direction.x * self.speed * dt)
            self.rect.y += round(direction.y * self.speed * dt)

        # The timer prevents the enemy from damaging the player
        self.attack_timer -= dt
        if distance <= 44 and self.attack_timer <= 0:
            self.attack_timer = 0.85
            return self.attack

        return 0

    def draw(self, screen: pg.Surface) -> None:
        pg.draw.ellipse(screen, (54, 44, 64), (self.rect.x, self.rect.bottom - 7, 34, 12))
        pg.draw.circle(screen, ENEMY_PURPLE, self.rect.center, 17)
        pg.draw.circle(screen, WHITE, (self.rect.centerx - 6, self.rect.centery - 2), 4)
        pg.draw.circle(screen, WHITE, (self.rect.centerx + 6, self.rect.centery - 2), 4)
        pg.draw.circle(screen, BLACK, (self.rect.centerx - 6, self.rect.centery - 1), 2)
        pg.draw.circle(screen, BLACK, (self.rect.centerx + 6, self.rect.centery - 1), 2)

        # 敵のHPバー
        bar = pg.Rect(self.rect.x, self.rect.y - 10, self.rect.width, 5)
        pg.draw.rect(screen, UI_DARK, bar)
        fill_width = int(bar.width * max(0, self.hp) / self.max_hp)
        pg.draw.rect(screen, HP_RED, (bar.x, bar.y, fill_width, bar.height))


class Projectile:
    """A small fireball projectile."""

    def __init__(self, pos: pg.Vector2, direction: pg.Vector2, damage: int) -> None:
        self.pos = pg.Vector2(pos)
        self.direction = pg.Vector2(direction).normalize()
        self.damage = damage
        self.speed = 500
        self.radius = 8
        self.timer = 1.2

    @property
    def rect(self) -> pg.Rect:
        return pg.Rect(
            int(self.pos.x - self.radius),
            int(self.pos.y - self.radius),
            self.radius * 2,
            self.radius * 2,
        )

    def update(self, dt: float) -> None:
        # Move the projectile forward and reduce its remaining lifetime.
        self.pos += self.direction * self.speed * dt
        self.timer -= dt

    def draw(self, screen: pg.Surface) -> None:
        pg.draw.circle(screen, (255, 219, 104), self.pos, self.radius + 3)
        pg.draw.circle(screen, FIRE_ORANGE, self.pos, self.radius)


def draw_bar(
    screen: pg.Surface,
    rect: pg.Rect,
    current: float,
    maximum: float,
    color: tuple[int, int, int],
) -> None:
    """Draw a labeled-style bar background and fill."""
    pg.draw.rect(screen, (50, 48, 48), rect, border_radius=5)
    # Avoid division by zero, then limit the fill length to the bar width.
    ratio = 0 if maximum == 0 else current / maximum
    inner = rect.copy()
    inner.width = int(rect.width * clamp(ratio, 0, 1))
    pg.draw.rect(screen, color, inner, border_radius=5)
    pg.draw.rect(screen, UI_LIGHT, rect, 2, border_radius=5)


def draw_world(screen: pg.Surface) -> None:
    """Draw original placeholder terrain using simple shapes."""
    screen.fill(SAND)

    # 海
    pg.draw.rect(screen, WATER, (720, 0, WIDTH - 720, 430))
    for y in range(35, 420, 26):
        for x in range(740 + (y % 40), WIDTH, 54):
            pg.draw.arc(screen, (129, 230, 244), (x, y, 26, 12), 0.2, 2.8, 2)

    # Grass / ruins / paths
    pg.draw.rect(screen, GRASS, (0, 430, 480, 185), border_radius=30)
    pg.draw.rect(screen, GRASS, (680, 470, 390, 140), border_radius=25)

    for x, y in [(85, 155), (205, 500), (555, 220), (870, 540)]:
        pg.draw.rect(screen, STONE, (x, y, 85, 24), border_radius=5)
        pg.draw.rect(screen, DARK_STONE, (x + 4, y + 7, 77, 13), border_radius=5)

    # ヤシの木のような木
    for x, y in [(830, 220), (350, 530), (920, 480)]:
        pg.draw.rect(screen, (97, 65, 36), (x - 7, y - 5, 14, 78), border_radius=5)
        for angle in (0, 72, 144, 216, 288):
            end = pg.Vector2(x, y) + pg.Vector2(46, 0).rotate(angle)
            pg.draw.line(screen, (63, 130, 58), (x, y), end, 13)

    # ポータル
    pg.draw.ellipse(screen, (75, 49, 140), (560, 490, 72, 92))
    pg.draw.ellipse(screen, (173, 109, 255), (571, 501, 50, 70))


def draw_gui(
    screen: pg.Surface,
    player: Player,
    font: pg.font.Font,
    small_font: pg.font.Font,
    coins: int,
) -> None:
    """Draw RPG style status box, hotbar, minimap, and quest box."""
    # ステータスパネル
    panel = pg.Rect(16, 16, 330, 113)
    pg.draw.rect(screen, UI_DARK, panel, border_radius=12)
    pg.draw.rect(screen, UI_LIGHT, panel, 3, border_radius=12)

    pg.draw.circle(screen, (242, 191, 59), (52, 57), 29)
    pg.draw.circle(screen, (255, 220, 158), (52, 63), 22)
    pg.draw.circle(screen, PLAYER_BLUE, (52, 84), 17)

    title = font.render(f"Explorer  Lv.{player.level}", True, WHITE)
    screen.blit(title, (92, 24))

    hp_rect = pg.Rect(92, 57, 220, 18)
    mp_rect = pg.Rect(92, 81, 220, 18)
    exp_rect = pg.Rect(92, 105, 220, 11)

    draw_bar(screen, hp_rect, player.hp, player.max_hp, HP_RED)
    draw_bar(screen, mp_rect, player.mp, player.max_mp, MP_BLUE)
    draw_bar(screen, exp_rect, player.exp, player.exp_to_next, EXP_GREEN)

    hp_text = small_font.render(f"HP {int(player.hp)} / {player.max_hp}", True, WHITE)
    mp_text = small_font.render(f"MP {int(player.mp)} / {player.max_mp}", True, WHITE)
    screen.blit(hp_text, (158, 57))
    screen.blit(mp_text, (158, 81))

    # ミニマップ
    minimap = pg.Rect(WIDTH - 155, 16, 130, 130)
    pg.draw.ellipse(screen, UI_DARK, minimap)
    pg.draw.ellipse(screen, UI_LIGHT, minimap, 3)
    pg.draw.rect(screen, (70, 104, 101), (WIDTH - 131, 42, 84, 77), border_radius=12)
    pg.draw.circle(screen, (240, 205, 58), (WIDTH - 95, 84), 5)
    minimap_label = small_font.render("MIRA BEACH", True, WHITE)
    screen.blit(minimap_label, (WIDTH - 143, 146))

    # クエスト表示欄
    quest = pg.Rect(WIDTH - 270, 175, 250, 93)
    pg.draw.rect(screen, UI_DARK, quest, border_radius=10)
    pg.draw.rect(screen, UI_LIGHT, quest, 2, border_radius=10)
    screen.blit(font.render("Quest", True, WHITE), (quest.x + 14, quest.y + 10))
    screen.blit(small_font.render("Defeat Shadow Slimes", True, WHITE), (quest.x + 14, quest.y + 39))
    screen.blit(small_font.render("Explore the ancient portal", True, WHITE), (quest.x + 14, quest.y + 63))

    # 画面下部のホットバー
    bar_y = HEIGHT - 78
    pg.draw.rect(screen, UI_DARK, (12, bar_y, WIDTH - 24, 65), border_radius=12)
    pg.draw.rect(screen, UI_LIGHT, (12, bar_y, WIDTH - 24, 65), 3, border_radius=12)

    labels = ["Sword", "Fire", "Potion", "Empty", "Empty", "Empty", "Empty", "Empty"]
    for index, label in enumerate(labels):
        box = pg.Rect(30 + index * 75, bar_y + 8, 58, 49)
        pg.draw.rect(screen, (65, 65, 70), box, border_radius=7)
        pg.draw.rect(screen, UI_LIGHT if index < 3 else (110, 110, 110), box, 2, border_radius=7)

        key_text = small_font.render(str(index + 1), True, WHITE)
        item_text = small_font.render(label, True, WHITE)
        screen.blit(key_text, (box.x + 4, box.y + 3))
        item_rect = item_text.get_rect(center=(box.centerx, box.centery + 8))
        screen.blit(item_text, item_rect)

    right_text = small_font.render(
        f"Coins: {coins}    ATK: {player.attack}    MATK: {player.magic_attack}    SPD: {int(player.speed)}",
        True,
        WHITE,
    )
    screen.blit(right_text, (650, bar_y + 24))

    control_text = small_font.render(
        "Move: WASD / Arrows   Attack: SPACE   Fire Orb: F   Potion: 1",
        True,
        UI_LIGHT,
    )
    screen.blit(control_text, (18, 138))


def main() -> None:
    pg.init()
    pg.display.set_caption("Aetherfall: Shards of Mira")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    clock = pg.time.Clock()

    font = pg.font.Font(None, 27)
    small_font = pg.font.Font(None, 20)
    large_font = pg.font.Font(None, 56)

    # Create the player and the first set of enemies for the current map.
    player = Player()
    enemies = [
        Enemy((260, 270)),
        Enemy((420, 480)),
        Enemy((680, 335)),
        Enemy((840, 390)),
        Enemy((950, 580)),
    ]
    projectiles: list[Projectile] = []
    texts: list[FloatingText] = []
    coins = 0
    game_over = False
    running = True

    while running:
        # dt is the elapsed time in seconds, used for frame-rate-independent movement.
        dt = clock.tick(FPS) / 1000

        # 1. Handle window events and keyboard actions.
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            if event.type == pg.KEYDOWN and not game_over:
                if event.key == pg.K_SPACE:
                    hitbox = player.try_melee_attack()
                    if hitbox:
                        for enemy in enemies[:]:
                            if hitbox.colliderect(enemy.rect):
                                enemy.hp -= player.attack
                                texts.append(FloatingText(f"-{player.attack}", enemy.rect.midtop, WHITE))

                elif event.key == pg.K_f:
                    projectile = player.try_fire_orb()
                    if projectile:
                        projectiles.append(projectile)

                elif event.key == pg.K_1:
                    if player.use_potion():
                        texts.append(FloatingText("+35 HP", player.rect.midtop, (125, 255, 150)))

            if event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE:
                running = False

        if not game_over:
            # 2. Update all game state while the player is alive.
            keys = pg.key.get_pressed()
            player.update(dt, keys)

            # Enemy updates and player damage.
            for enemy in enemies:
                damage = enemy.update(dt, player)
                if damage:
                    player.hp -= damage
                    texts.append(FloatingText(f"-{damage}", player.rect.midtop, HP_RED))

            # Projectile movement and collision.
            for projectile in projectiles[:]:
                projectile.update(dt)
                if projectile.timer <= 0:
                    projectiles.remove(projectile)
                    continue

                for enemy in enemies[:]:
                    if projectile.rect.colliderect(enemy.rect):
                        enemy.hp -= projectile.damage
                        texts.append(FloatingText(f"-{projectile.damage}", enemy.rect.midtop, FIRE_ORANGE))
                        if projectile in projectiles:
                            projectiles.remove(projectile)
                        break

            # Remove defeated enemies, award EXP / coins, and spawn a replacement.
            for enemy in enemies[:]:
                if enemy.hp <= 0:
                    enemies.remove(enemy)
                    coins += enemy.coin_reward
                    texts.append(FloatingText(f"+{enemy.exp_reward} EXP", enemy.rect.midtop, EXP_GREEN))
                    if player.gain_exp(enemy.exp_reward):
                        texts.append(FloatingText("LEVEL UP!", player.rect.midtop, (255, 226, 80)))

                    # Spawn a replacement enemy so combat remains available.
                    spawn_x = random.choice([random.randint(80, 600), random.randint(710, 1000)])
                    spawn_y = random.randint(180, 560)
                    enemies.append(Enemy((spawn_x, spawn_y)))

            for text in texts[:]:
                text.update(dt)
                if text.timer <= 0:
                    texts.remove(text)

            if player.hp <= 0:
                player.hp = 0
                game_over = True

        # 3. Draw the world, characters, effects, and interface.
        draw_world(screen)

        # Draw order: objects lower on screen are drawn later to create simple depth.
        world_objects = [(enemy.rect.bottom, enemy) for enemy in enemies]
        world_objects.append((player.rect.bottom, player))
        world_objects.sort(key=lambda item: item[0])

        for _, obj in world_objects:
            obj.draw(screen)

        for projectile in projectiles:
            projectile.draw(screen)

        for text in texts:
            text.draw(screen, font)

        draw_gui(screen, player, font, small_font, coins)

        if game_over:
            overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))
            title = large_font.render("YOU HAVE FALLEN", True, WHITE)
            subtitle = font.render("Press ESC to quit, then run the game again.", True, WHITE)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
            screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))

        pg.display.update()

    pg.quit()


if __name__ == "__main__":
    main()
