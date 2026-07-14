"""
ヴェルダラ：砕かれた門
Pygameで制作した2D見下ろし型アクションRPG。

操作方法
--------
WASD / 矢印キー : 移動
K               : 近接攻撃
J               : 銃を撃つ（MPを1消費）
R               : リロード（MPを最大まで回復）
L               : 回復スキルを使用（習得後，クールダウンあり）
1〜5             : レベルアップ時に能力またはスキルを選択
ESC             : 終了
"""

import os
import random

import pygame as pg


# どの場所から実行しても，相対パスでファイルを読み込めるようにする。
os.chdir(os.path.dirname(os.path.abspath(__file__)))

WIDTH, HEIGHT = 1100, 700
FPS = 60

# 色の定義
SAND = (231, 211, 151)
WATER = (67, 189, 226)
GRASS = (104, 170, 92)
STONE = (126, 124, 117)
DARK_STONE = (86, 84, 81)
UI_DARK = (35, 36, 46)
UI_MID = (68, 70, 84)
UI_LIGHT = (235, 229, 207)
HP_RED = (205, 56, 63)
MP_BLUE = (55, 130, 220)
EXP_GREEN = (157, 205, 53)
GUN_YELLOW = (229, 183, 52)
PLAYER_BLUE = (45, 108, 196)
ONIGIRI_WHITE = (245, 244, 234)
NORI_BLACK = (40, 45, 45)
BULLET_ORANGE = (250, 154, 48)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)


def clamp(value: float, low: float, high: float) -> float:
    """valueをlow以上high以下の範囲に収めて返す。"""
    return max(low, min(value, high))


class FloatingText:
    """ダメージや報酬をオブジェクトの上に短時間表示するクラス。"""

    def __init__(self, text: str, pos: tuple[int, int], color: tuple[int, int, int]) -> None:
        self.text = text
        self.x, self.y = pos
        self.color = color
        self.timer = 0.75

    def update(self, dt: float) -> None:
        """表示文字を上へ移動し，残り表示時間を減らす。"""
        self.y -= 32 * dt
        self.timer -= dt

    def draw(self, screen: pg.Surface, font: pg.font.Font) -> None:
        """フローティングメッセージを描画する。"""
        image = font.render(self.text, True, self.color)
        screen.blit(image, image.get_rect(center=(self.x, self.y)))


class Bullet:
    """銃から発射される弾丸を表すクラス。"""

    def __init__(self, pos: pg.Vector2, direction: pg.Vector2, damage: int) -> None:
        self.pos = pg.Vector2(pos)
        self.direction = pg.Vector2(direction).normalize()
        self.damage = damage
        self.speed = 620
        self.radius = 5
        self.timer = 1.0

    @property
    def rect(self) -> pg.Rect:
        """弾丸の当たり判定を返す。"""
        return pg.Rect(
            int(self.pos.x - self.radius),
            int(self.pos.y - self.radius),
            self.radius * 2,
            self.radius * 2,
        )

    def update(self, dt: float) -> None:
        """弾丸を進行方向へ移動し，残り時間を減らす。"""
        self.pos += self.direction * self.speed * dt
        self.timer -= dt

    def draw(self, screen: pg.Surface) -> None:
        """弾丸を描画する。"""
        pg.draw.circle(screen, (255, 226, 135), self.pos, self.radius + 2)
        pg.draw.circle(screen, BULLET_ORANGE, self.pos, self.radius)
#山形が追加したクラス　下
class GUN:
    # 引数に max_ammo: int を追加して受け取れるようにする
    def __init__(self, damage: int, cooldown_time: float, mp_cost: int, max_ammo: int):
        self.damage = damage
        self.cooldown_time = cooldown_time
        self.mp_cost = mp_cost
        
        # 追加：最大弾数と現在の弾数を設定する
        self.max_ammo = max_ammo
        self.current_ammo = max_ammo  # 最初は弾が満タンの状態
        
        self.current_cooldown = 0.0
    
    def update(self, dt: float):
        if self.current_cooldown > 0:
            self.current_cooldown -= dt

    def shoot(self, pos: pg.Vector2, direction: pg.Vector2) -> list[Bullet]:
        pass
#下作業中
class DoubleBarrelShotgun(GUN):
    def __init__(self):
        super().__init__(damage=30, cooldown_time=0.4, mp_cost=2,max_ammo=4)
        self.kakusan = 15#弾丸の拡散角度
    
    def shoot(self, pos: pg.Vector2, direction: pg.Vector2) -> list[Bullet]:
        if self.current_cooldown > 0:
            return [] # クールダウン中は撃てない
        
        self.current_cooldown = self.cooldown_time
        
        # 基準の方向から kakusan の角度分だけ左右にずらす
        dir1 = direction.rotate(self.kakusan)
        dir2 = direction.rotate(-self.kakusan)

        # ずらした方向で2発の弾を生成
        bullet1 = Bullet(pos, dir1, self.damage)
        bullet2 = Bullet(pos, dir2, self.damage)

        return [bullet1, bullet2]
#7/14かついか実装中
class AssaultRifle(GUN):
    def __init__(self):
        # ダメージ, クールダウン, 消費MP1
        super().__init__(damage=6, cooldown_time=0.12, mp_cost=1, max_ammo=30)
    
    def shoot(self, pos: pg.Vector2, direction: pg.Vector2) -> list[Bullet]:
        if self.current_cooldown > 0:
            return []  # クールダウン中は撃てない
        
        self.current_cooldown = self.cooldown_time
        
        # まっすぐ1発だけ生成してリストで返す
        bullet = Bullet(pos, direction, self.damage)
        return [bullet]




class Player:
    """移動，攻撃，銃，経験値，レベルアップを持つプレイヤークラス。"""

    def __init__(self) -> None:
        self.rect = pg.Rect(500, 330, 34, 42)
        self.direction = pg.Vector2(0, 1)

        # レベルと経験値
        self.level = 1
        self.exp = 0
        self.exp_to_next = 100
        self.choosing_level_up = False

        # READMEに記載する主要ステータス
        self.max_hp = 100
        self.hp = 100
        #self.max_mp = 10  # MPは銃の弾数として使用する。
        self.attack = 12
        self.speed = 230

        #ショットガンを持たせる
 # シューティングに関する設定（古いコードを以下に置き換え）
        self.weapons = [DoubleBarrelShotgun(), AssaultRifle()]
        self.weapon_index = 0
        self.equipped_gun = self.weapons[self.weapon_index]

        # 攻撃，銃，リロードのクールダウン
        self.melee_cooldown = 0.0
        #self.gun_cooldown = 0.0
        self.reload_cooldown = 0.0

        # レベルアップ時に習得できる回復スキル
        self.heal_skill = False
        self.heal_cooldown = 0.0

    def update(self, dt: float, keys: pg.key.ScancodeWrapper) -> None:
        """プレイヤーの移動とクールダウンを更新する。"""
        move = pg.Vector2(
            int(keys[pg.K_d] or keys[pg.K_RIGHT]) - int(keys[pg.K_a] or keys[pg.K_LEFT]),
            int(keys[pg.K_s] or keys[pg.K_DOWN]) - int(keys[pg.K_w] or keys[pg.K_UP]),
        )

        if move.length_squared() > 0:
            # 斜め移動だけが速くならないように正規化する。
            move = move.normalize()
            self.direction = move
            self.rect.x += round(move.x * self.speed * dt)
            self.rect.y += round(move.y * self.speed * dt)

        # 画面外およびGUI領域へ出ないように位置を制限する。
        self.rect.x = int(clamp(self.rect.x, 20, WIDTH - self.rect.width - 20))
        self.rect.y = int(clamp(self.rect.y, 120, HEIGHT - self.rect.height - 85))

        self.melee_cooldown = max(0.0, self.melee_cooldown - dt)
        self.equipped_gun.update(dt)
        self.reload_cooldown = max(0.0, self.reload_cooldown - dt)
        self.heal_cooldown = max(0.0, self.heal_cooldown - dt)

    def melee_area(self) -> pg.Rect:
        """プレイヤー前方の近接攻撃当たり判定を返す。"""
        center = pg.Vector2(self.rect.center) + self.direction * 42
        return pg.Rect(int(center.x - 28), int(center.y - 28), 56, 56)

    def try_melee_attack(self) -> pg.Rect | None:
        """クールダウン終了時だけ近接攻撃の当たり判定を返す。"""
        if self.melee_cooldown > 0:
            return None
        self.melee_cooldown = 0.35
        return self.melee_area()

    def try_shoot(self) -> list[Bullet]:
        """弾が残っている場合に弾丸を1発生成する。"""
        gun = self.equipped_gun
        # 銃がクールダウン中、または弾が足りない場合は撃てない
        if gun.current_cooldown > 0 or gun.current_ammo < gun.mp_cost:
            return []

        # 武器の消費MP分だけMPを減らす
        gun.current_ammo -= gun.mp_cost
        
        # 銃口の位置を計算
        origin = pg.Vector2(self.rect.center) + self.direction * 27
        
        # 装備している銃から、発射された弾のリストを受け取って返す
        return gun.shoot(origin, self.direction)
    
    def reload(self) -> bool:
        """装備している銃の弾を最大まで回復する。"""
        gun = self.equipped_gun
        if self.reload_cooldown > 0 or gun.current_ammo >= gun.max_ammo:
            return False
        gun.current_ammo = gun.max_ammo
        self.reload_cooldown = 1.2
        return True

    def use_heal_skill(self) -> bool:
        """習得済みの回復スキルを使用し，成功時はTrueを返す。"""
        if not self.heal_skill or self.heal_cooldown > 0 or self.hp >= self.max_hp:
            return False
        self.hp = min(self.max_hp, self.hp + 35)
        self.heal_cooldown = 8.0
        return True

    def gain_exp(self, amount: int) -> bool:
        """経験値を加算し，レベルアップ選択が必要かどうかを返す。"""
        self.exp += amount
        if self.exp >= self.exp_to_next:
            self.exp -= self.exp_to_next
            self.level += 1
            self.exp_to_next = int(self.exp_to_next * 1.35)
            self.choosing_level_up = True
            return True
        return False

    def choose_level_up(self, choice: int) -> str | None:
        """レベルアップ時に選んだ能力を適用し，結果の表示文字を返す。"""
        if not self.choosing_level_up:
            return None

        result = None
        if choice == 1:
            self.max_hp += 20
            self.hp = self.max_hp
            result = "HP +20"
        elif choice == 2:
            # レベルアップで「MP(Ammo)+3」を選んだら、所持しているすべての武器の上限を増やす
            for weapon in self.weapons:
                weapon.max_ammo += 3
                weapon.current_ammo = weapon.max_ammo
            result = "Ammo Capacity +3"
        elif choice == 3:
            self.attack += 4
            result = "Attack +4"
        elif choice == 4:
            self.speed += 20
            result = "Speed +20"
        elif choice == 5 and not self.heal_skill:
            self.heal_skill = True
            result = "Heal Skill Acquired"
        else:
            return None

        self.choosing_level_up = False
        return result
    def switch_weapon(self) -> str:
        """武器を切り替えて、切り替えた武器の名前を返す。"""
        self.weapon_index = (self.weapon_index + 1) % len(self.weapons)
        self.equipped_gun = self.weapons[self.weapon_index]
        
        if isinstance(self.equipped_gun, DoubleBarrelShotgun):
            return "Shotgun"
        return "Assault Rifle"
    def draw(self, screen: pg.Surface) -> None:
        """プレイヤーを描画する。"""
        pg.draw.ellipse(screen, (55, 55, 55), (self.rect.x - 2, self.rect.bottom - 9, 38, 13))
        pg.draw.rect(screen, PLAYER_BLUE, self.rect, border_radius=8)
        pg.draw.circle(screen, (255, 220, 158), (self.rect.centerx, self.rect.y + 10), 11)
        pg.draw.circle(screen, (242, 191, 59), (self.rect.centerx, self.rect.y + 5), 11)

        # 向いている方向を線で表示する。
        tip = pg.Vector2(self.rect.center) + self.direction * 28
        pg.draw.line(screen, WHITE, self.rect.center, tip, 3)


class OnigiriEnemy:
    """プレイヤーを追跡して攻撃するおにぎり型の敵クラス。"""

    def __init__(self, pos: tuple[int, int]) -> None:
        self.rect = pg.Rect(pos[0], pos[1], 38, 34)
        self.max_hp = 45
        self.hp = self.max_hp
        self.speed = random.randint(65, 90)
        self.attack = 8
        self.attack_timer = random.uniform(0.0, 0.8)
        self.exp_reward = 35

    def update(self, dt: float, player: Player) -> int:
        """プレイヤーを追跡し，攻撃した場合はダメージを返す。"""
        to_player = pg.Vector2(player.rect.center) - pg.Vector2(self.rect.center)
        distance = to_player.length()

        if 42 < distance < 250:
            direction = to_player.normalize()
            self.rect.x += round(direction.x * self.speed * dt)
            self.rect.y += round(direction.y * self.speed * dt)

        self.attack_timer -= dt
        if distance <= 44 and self.attack_timer <= 0:
            self.attack_timer = 0.85
            return self.attack
        return 0

    def draw(self, screen: pg.Surface) -> None:
        """おにぎり敵とHPバーを描画する。"""
        pg.draw.ellipse(screen, (54, 44, 64), (self.rect.x, self.rect.bottom - 7, 38, 12))

        # 三角形のおにぎり本体
        points = [
            (self.rect.centerx, self.rect.y),
            (self.rect.right, self.rect.bottom),
            (self.rect.left, self.rect.bottom),
        ]
        pg.draw.polygon(screen, ONIGIRI_WHITE, points)
        pg.draw.polygon(screen, BLACK, points, 2)

        # のりと目
        pg.draw.rect(screen, NORI_BLACK, (self.rect.centerx - 7, self.rect.bottom - 13, 14, 12), border_radius=2)
        pg.draw.circle(screen, BLACK, (self.rect.centerx - 6, self.rect.centery + 2), 2)
        pg.draw.circle(screen, BLACK, (self.rect.centerx + 6, self.rect.centery + 2), 2)

        # 敵HPバー
        bar = pg.Rect(self.rect.x, self.rect.y - 10, self.rect.width, 5)
        pg.draw.rect(screen, UI_DARK, bar)
        width = int(bar.width * max(0, self.hp) / self.max_hp)
        pg.draw.rect(screen, HP_RED, (bar.x, bar.y, width, bar.height))


def draw_bar(
    screen: pg.Surface,
    rect: pg.Rect,
    current: float,
    maximum: float,
    color: tuple[int, int, int],
) -> None:
    """HP，MP，EXPなどのステータスバーを描画する。"""
    pg.draw.rect(screen, (50, 48, 48), rect, border_radius=5)
    ratio = 0 if maximum == 0 else current / maximum
    fill = rect.copy()
    fill.width = int(rect.width * clamp(ratio, 0, 1))
    pg.draw.rect(screen, color, fill, border_radius=5)
    pg.draw.rect(screen, UI_LIGHT, rect, 2, border_radius=5)


def draw_world(screen: pg.Surface) -> None:
    """おにぎり敵と戦うための見下ろし型ワールドを描画する。"""
    screen.fill(SAND)

    # 海
    pg.draw.rect(screen, WATER, (720, 0, WIDTH - 720, 430))
    for y in range(35, 420, 26):
        for x in range(740 + (y % 40), WIDTH, 54):
            pg.draw.arc(screen, (129, 230, 244), (x, y, 26, 12), 0.2, 2.8, 2)

    # 移動・戦闘用の広い草地
    pg.draw.rect(screen, GRASS, (0, 430, 480, 185), border_radius=30)
    pg.draw.rect(screen, GRASS, (680, 470, 390, 140), border_radius=25)

    # 遺跡の飾り。移動を邪魔しない配置にする。
    for x, y in [(85, 155), (205, 500), (555, 220), (870, 540)]:
        pg.draw.rect(screen, STONE, (x, y, 85, 24), border_radius=5)
        pg.draw.rect(screen, DARK_STONE, (x + 4, y + 7, 77, 13), border_radius=5)

    # ポータル
    pg.draw.ellipse(screen, (75, 49, 140), (560, 490, 72, 92))
    pg.draw.ellipse(screen, (173, 109, 255), (571, 501, 50, 70))


def draw_gui(
    screen: pg.Surface,
    player: Player,
    font: pg.font.Font,
    small_font: pg.font.Font,
    defeated_count: int,
) -> None:
    """READMEに合わせて目標，ステータス，スキル，銃情報を表示する。"""
    # 左上：目標表示
    objective = pg.Rect(16, 16, 300, 90)
    pg.draw.rect(screen, UI_DARK, objective, border_radius=12)
    pg.draw.rect(screen, UI_LIGHT, objective, 2, border_radius=12)
    screen.blit(font.render("Objective", True, WHITE), (objective.x + 14, objective.y + 12))
    screen.blit(
        small_font.render(f"Defeat Onigiri Enemies: {defeated_count}", True, WHITE),
        (objective.x + 14, objective.y + 46),
    )

    # 右上：ステータスとスキル表示
    panel = pg.Rect(WIDTH - 315, 16, 299, 176)
    pg.draw.rect(screen, UI_DARK, panel, border_radius=12)
    pg.draw.rect(screen, UI_LIGHT, panel, 2, border_radius=12)
    screen.blit(font.render(f"Status  Lv.{player.level}", True, WHITE), (panel.x + 14, panel.y + 12))

    hp_bar = pg.Rect(panel.x + 14, panel.y + 47, 260, 17)
    mp_bar = pg.Rect(panel.x + 14, panel.y + 73, 260, 17)
    exp_bar = pg.Rect(panel.x + 14, panel.y + 99, 260, 12)
    draw_bar(screen, hp_bar, player.hp, player.max_hp, HP_RED)
    draw_bar(screen, mp_bar, player.equipped_gun.current_ammo, player.equipped_gun.max_ammo, MP_BLUE)
    draw_bar(screen, exp_bar, player.exp, player.exp_to_next, EXP_GREEN)

    screen.blit(small_font.render(f"HP {int(player.hp)}/{player.max_hp}", True, WHITE), (panel.x + 20, panel.y + 47))
    screen.blit(
        small_font.render(f"Ammo {int(player.equipped_gun.current_ammo)}/{player.equipped_gun.max_ammo}", True, WHITE),
        (panel.x + 20, panel.y + 73),
    )

    if not player.heal_skill:
        skill_text = "Heal Skill: Locked"
    elif player.heal_cooldown <= 0:
        skill_text = "Heal Skill: Ready [L]"
    else:
        skill_text = f"Heal Skill: {player.heal_cooldown:.1f}s"

    screen.blit(font.render("Skill", True, GUN_YELLOW), (panel.x + 14, panel.y + 122))
    screen.blit(small_font.render(skill_text, True, WHITE), (panel.x + 14, panel.y + 150))

    # 右下：銃の種類と弾数
# 右下：銃の種類と弾数
    gun_panel = pg.Rect(WIDTH - 300, HEIGHT - 92, 284, 76)
    gun_panel = pg.Rect(WIDTH - 300, HEIGHT - 92, 284, 76)
    pg.draw.rect(screen, UI_DARK, gun_panel, border_radius=12)
    pg.draw.rect(screen, UI_LIGHT, gun_panel, 2, border_radius=12)
    
    gun_name = "Double-Barrel Shotgun" if isinstance(player.equipped_gun, DoubleBarrelShotgun) else "Assault Rifle"
    screen.blit(font.render(f"Gun: {gun_name}", True, WHITE), (gun_panel.x + 14, gun_panel.y + 10))
    ammo_text = small_font.render(
        f"Ammo: {int(player.equipped_gun.current_ammo)} / {player.equipped_gun.max_ammo}    [J] Shoot   [R] Reload",
        True,
        GUN_YELLOW,
    )
    screen.blit(ammo_text, (gun_panel.x + 14, gun_panel.y + 44))

    # 画面下部：最低限の操作説明
    controls = "Move: WASD/Arrows   K: Melee   J: Shoot   R: Reload   L: Heal Skill"
    screen.blit(small_font.render(controls, True, UI_LIGHT), (16, HEIGHT - 32))


def draw_level_up_menu(screen: pg.Surface, font: pg.font.Font, small_font: pg.font.Font) -> None:
    """レベルアップ時に能力・スキルを選ぶ画面を描画する。"""
    overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
    overlay.fill((0, 0, 0, 170))
    screen.blit(overlay, (0, 0))

    panel = pg.Rect(250, 165, 600, 360)
    pg.draw.rect(screen, UI_DARK, panel, border_radius=16)
    pg.draw.rect(screen, UI_LIGHT, panel, 3, border_radius=16)

    title = font.render("LEVEL UP! Choose One", True, GUN_YELLOW)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, panel.y + 45)))

    choices = [
        "1: HP +20",
        "2: MP (Ammo) +3",
        "3: Attack +4",
        "4: Speed +20",
        "5: Learn Heal Skill",
    ]
    for index, text in enumerate(choices):
        image = small_font.render(text, True, WHITE)
        screen.blit(image, image.get_rect(center=(WIDTH // 2, panel.y + 100 + index * 43)))


def main() -> None:
    """ゲームを初期化し，メインループを実行する。"""
    pg.init()
    pg.display.set_caption("ヴェルダラ：砕かれた門")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    clock = pg.time.Clock()

    font = pg.font.Font(None, 27)
    small_font = pg.font.Font(None, 20)
    large_font = pg.font.Font(None, 56)

    player = Player()
    enemies = [
        OnigiriEnemy((260, 270)),
        OnigiriEnemy((420, 480)),
        OnigiriEnemy((680, 335)),
        OnigiriEnemy((840, 390)),
        OnigiriEnemy((950, 580)),
    ]
    bullets: list[Bullet] = []
    texts: list[FloatingText] = []
    defeated_count = 0
    game_over = False
    running = True

    while running:
        # 1フレームにかかった時間（秒）。FPSが変化しても速度を一定に保つ。
        dt = clock.tick(FPS) / 1000

        # 1. ウィンドウイベントとキーボード入力を処理する。
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    running = False

                # レベルアップ選択中は，能力・スキルの選択だけを受け付ける。
                elif player.choosing_level_up:
                    result = player.choose_level_up(event.key - pg.K_0)
                    if result:
                        texts.append(FloatingText(result, player.rect.midtop, GUN_YELLOW))

                elif not game_over:
                    # Kキー：近接攻撃
                    if event.key == pg.K_k:
                        hitbox = player.try_melee_attack()
                        if hitbox:
                            for enemy in enemies[:]:
                                if hitbox.colliderect(enemy.rect):
                                    enemy.hp -= player.attack
                                    texts.append(FloatingText(f"-{player.attack}", enemy.rect.midtop, WHITE))

                    # Jキー：銃を撃つ
                    elif event.key == pg.K_j:
                        new_bullets = player.try_shoot()
                        if new_bullets:
                            # 複数の弾のリストが返ってくるため、extendで追加する
                            bullets.extend(new_bullets)
                        else:
                            if player.equipped_gun.current_ammo < player.equipped_gun.mp_cost:
                                texts.append(FloatingText("No Ammo", player.rect.midtop, MP_BLUE))

                    # Rキー：リロード
                    elif event.key == pg.K_r:
                        if player.reload():
                            texts.append(FloatingText("Reloaded", player.rect.midtop, MP_BLUE))
                    # Qキー：武器切り替え
                    elif event.key == pg.K_q:
                        weapon_name = player.switch_weapon()
                        texts.append(FloatingText(f"Equipped: {weapon_name}", player.rect.midtop, GUN_YELLOW))                            

                    # Lキー：習得後の回復スキル
                    elif event.key == pg.K_l:
                        if player.use_heal_skill():
                            texts.append(FloatingText("+35 HP", player.rect.midtop, (125, 255, 150)))

        if not game_over and not player.choosing_level_up:
            # 2. プレイヤー，敵，弾丸，メッセージを更新する。
            keys = pg.key.get_pressed()
            player.update(dt, keys)

            # 敵の移動と攻撃
            for enemy in enemies:
                damage = enemy.update(dt, player)
                if damage:
                    player.hp -= damage
                    texts.append(FloatingText(f"-{damage}", player.rect.midtop, HP_RED))

            # 弾丸の移動と敵との当たり判定
            for bullet in bullets[:]:
                bullet.update(dt)
                if bullet.timer <= 0:
                    bullets.remove(bullet)
                    continue

                for enemy in enemies[:]:
                    if bullet.rect.colliderect(enemy.rect):
                        enemy.hp -= bullet.damage
                        texts.append(FloatingText(f"-{bullet.damage}", enemy.rect.midtop, BULLET_ORANGE))
                        if bullet in bullets:
                            bullets.remove(bullet)
                        break

            # 倒された敵を削除し，経験値を与えて新しい敵を生成する。
            for enemy in enemies[:]:
                if enemy.hp <= 0:
                    enemies.remove(enemy)
                    defeated_count += 1
                    texts.append(FloatingText(f"+{enemy.exp_reward} EXP", enemy.rect.midtop, EXP_GREEN))

                    if player.gain_exp(enemy.exp_reward):
                        texts.append(FloatingText("LEVEL UP!", player.rect.midtop, GUN_YELLOW))

                    spawn_x = random.choice([random.randint(80, 600), random.randint(710, 1000)])
                    spawn_y = random.randint(180, 560)
                    enemies.append(OnigiriEnemy((spawn_x, spawn_y)))

            # 時間切れのフローティングメッセージを削除する。
            for text in texts[:]:
                text.update(dt)
                if text.timer <= 0:
                    texts.remove(text)

            if player.hp <= 0:
                player.hp = 0
                game_over = True

        # 3. ワールド，オブジェクト，GUIを描画する。
        draw_world(screen)

        # 画面下側にあるオブジェクトを後から描画して，簡単な奥行きを表現する。
        objects = [(enemy.rect.bottom, enemy) for enemy in enemies]
        objects.append((player.rect.bottom, player))
        objects.sort(key=lambda item: item[0])

        for _, obj in objects:
            obj.draw(screen)

        for bullet in bullets:
            bullet.draw(screen)

        for text in texts:
            text.draw(screen, font)

        draw_gui(screen, player, font, small_font, defeated_count)

        if player.choosing_level_up:
            draw_level_up_menu(screen, font, small_font)

        if game_over:
            overlay = pg.Surface((WIDTH, HEIGHT), pg.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))

            title = large_font.render("GAME OVER", True, WHITE)
            subtitle = font.render("Press ESC to quit.", True, WHITE)
            screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))
            screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 30)))

        pg.display.update()

    pg.quit()


if __name__ == "__main__":
    main()
