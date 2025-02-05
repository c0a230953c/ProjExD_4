import math
import os
import random
import sys
import time
import pygame as pg


WIDTH = 1100  # ゲームウィンドウの幅
HEIGHT = 650  # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        
        self.state = "normal" #こうかとんの無敵状態の有無
        self.hyper_life = 0 #無敵時間のフレーム時間
        self.score = 0 #スコアの保持

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        current_speed = self.speed
        if key_lst[pg.K_LSHIFT]:
            current_speed = 20
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        self.rect.move_ip(current_speed*sum_mv[0], current_speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-current_speed*sum_mv[0], -current_speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]

        #無敵状態の管理
        if self.state == "hyper":
            self.image = pg.transform.laplacian(self.image)
            self.hyper_life -= 1
            if self.hyper_life <= 0:
                self.state = "normal"

        screen.blit(self.image, self.rect)

    def activate_hyper(self, score):
        """
        無敵状態
        """
        if score.value >= 30: #スコアが100以上ならば
            self.state = "hyper"
            self.hyper_life = 500 #無敵状態の持続時間
            score.value -= 30 #スコアを100消費

    def check_collision(self, bomb):
        if self.rect.colliderect(bomb.rect):
            if self.state == "hyper": #無敵状態ならば
                bomb.kill() #爆弾を破壊
                self.score += 1 #スコア加点
            else: #それ以外(通常状態)ならば、ゲームオーバー
                self.change_img(8, screen)
                time.sleep(2)
                sys.exit() #ゲーム終了



class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height//2
        self.speed = 6

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    def __init__(self, bird: Bird, angle: float = 0):
        super().__init__()
        self.vx, self.vy = bird.dire
        angle += math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 2.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery + bird.rect.height * self.vy
        self.rect.centerx = bird.rect.centerx + bird.rect.width * self.vx
        self.speed = 10



    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()
class NeoBeam:
    def __init__(self, bird: Bird, num: int):
        self.bird = bird
        self.num = num

    def gen_beams(self) -> list[Beam]:
        beams = []
        step = 100 / (self.num - 1) if self.num > 1 else 0  # ステップを計算
        angles = range(-50, 51, int(step))  # ビームの角度を生成
        for angle in angles:
            beams.append(Beam(self.bird, angle))  # Beamインスタンスを生成
        return beams



class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)

class EMP(pg.sprite.Sprite):
    """
    電磁パルス（EMP）に関するクラス
    発動時、敵機の爆弾投下を無効化し、爆弾の動きを鈍化させる
    """
    def __init__(self, emys: pg.sprite.Group, bombs: pg.sprite.Group, screen: pg.Surface):
        """
        EMPを発動する
        引数1 emys：敵機のグループ
        引数2 bombs：爆弾のグループ
        引数3 screen：画面Surface
        """
        super().__init__()
        self.emys = emys
        self.bombs = bombs

        # EMPエフェクトとしての画像 (画面全体に表示する半透明の黄色い矩形)
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.image.set_alpha(128)  # 半透明
        self.image.fill((255, 255, 0))  # 黄色い矩形

        self.rect = self.image.get_rect()  # 矩形の範囲を画面全体に設定

        self.duration = 3  # EMP効果の持続フレーム数

        # 敵機と爆弾を無効化
        for emy in self.emys:
            emy.interval = float('inf')  # 爆弾投下を無効化

            
            # ラプラシアンフィルタを適用
            emy.image = pg.transform.laplacian(emy.image)  

            # ラプラシアンフィルタ適用後、再度透過色を設定
            emy.image.set_colorkey((0, 0, 0))  # 黒を再度透過色に設定

        for bomb in self.bombs:
            bomb.speed /= 2  # 爆弾の速度を半減

    def update(self):
        """
        EMPの効果を画面に表示し、一定時間後に効果を終了する
        """
        if self.duration > 0:
            self.duration -= 1
        else:
            self.kill()  # 効果終了
class Gravity(pg.sprite.Sprite):
    """
    重力に関するクラス
    """
    def __init__(self,life:int):
        super().__init__()
        self.image = pg.Surface((WIDTH,HEIGHT))
        self.image.set_alpha(100)
        self.image.fill((0,0,0))
        self.rect = self.image.get_rect()
        self.life = life
        pg.draw.rect(self.image,(0,0,0),(0,0,WIDTH,HEIGHT))
    def update(self,bombs,enemies,score,exps):
        self.life -= 1
        if self.life < 0:
            self.kill()
        for bomb in pg.sprite.spritecollide(self, bombs, True):
            exps.add(Explosion(bomb, 50))  # 爆発エフェクトを追加
            score.value += 1  # スコアを加算

        for enemy in pg.sprite.spritecollide(self, enemies, True):
            exps.add(Explosion(enemy, 50))  # 爆発エフェクトを追加
            score.value += 10  # スコアを加算（敵機の場合）

class Shield(pg.sprite.Sprite):
    """
    防御壁に関するクラス
    防御壁は常に自機の前方に設置され、触れた爆弾は削除される
    引数 bird: 自機となるBirdクラスのインスタンス, life: 整数型のシールド持続時間
    """
    def __init__(self, bird: Bird, life: int):
        super().__init__()
        self.life = life    #防御壁残り時間
        self.bird = bird    #追従すべき自機
        self.image_origin = pg.Surface((20, self.bird.imgs[(+1, 0)].get_width() * 2))   #Surfaceを作成
        pg.draw.rect(self.image_origin, (0, 0, 255), pg.Rect(0, 0, 20, self.bird.imgs[(+1, 0)].get_width() * 2))    #防御壁を描画
        self.image = self.image_origin  #描画する画像
        self.rect = self.image.get_rect()   #防御壁のrect

    def update(self):
        vx, vy = self.bird.dire #自機の向き
        angle = math.degrees(math.atan2(-vy, vx))   #自機の向きから防御壁の角度を計算
        self.image = pg.transform.rotozoom(self.image_origin, angle, 1.0)   #防御壁の角度を変更
        self.rect = self.image.get_rect()   #rectを更新
        #画像の描画位置を更新
        if angle % 90 != 0:
            self.rect.center = (self.bird.rect.centerx + self.bird.rect.width * vx / math.sqrt(2), self.bird.rect.centery + self.bird.rect.height * vy / math.sqrt(2))
        else:
            self.rect.center = (self.bird.rect.centerx + self.bird.rect.width * vx, self.bird.rect.centery + self.bird.rect.height * vy)
        self.image.set_colorkey((0, 0, 0))  #画像を透過
        self.life -= 1  #持続時間を減少
        #持続時間が切れたら防御壁を削除
        if self.life <= 0:
            self.kill()


def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    emps = pg.sprite.Group()  # EMPのグループ
    gravities = pg.sprite.Group()
    shields = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_SPACE:
                    beams.add(Beam(bird))
                if event.key == pg.K_e and score.value >= 20:
                    # スコアが20以上で「e」キーが押された場合、EMP発動
                    emps.add(EMP(emys, bombs, screen))
                    score.value -= 20  # スコアを20減らす

            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                if key_lst[pg.K_LSHIFT]:  # 左Shiftキーが押下されているか
                    neo_beam = NeoBeam(bird, 5)  # ビーム数を5に設定
                    beams.add(*neo_beam.gen_beams())  # ビームを生成し追加
                else:
                    beams.add(Beam(bird))
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN and score.value >= 200:
                gravities.add(Gravity(400))
                score.value -= 200
            if event.type == pg.KEYDOWN and event.key == pg.K_RSHIFT:
                print(score)
                bird.activate_hyper(score)
                beams.add(Beam(bird))
            #capslockが押された場合かつスコアが50以上の場合かつシールドが存在しない場合に実行
            if event.type == pg.KEYDOWN and event.key == pg.K_CAPSLOCK and score.value >= 50 and len(shields) <= 0:
                score.value -= 50   #スコアを50消費
                shields.add(Shield(bird, 400))  #シールドインスタンスを生成
        screen.blit(bg_img, [0, 0])

        if tmr % 200 == 0:
            emys.add(Enemy())

        for emy in emys:
            if emy.state == "stop" and tmr % emy.interval == 0:
                bombs.add(Bomb(emy, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))
            score.value += 10
            bird.change_img(6, screen)

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))
            score.value += 1

        pg.sprite.groupcollide(shields, bombs, False, True) #シールドに接触した爆弾を削除

        if bird.state == "normal":
            if len(pg.sprite.spritecollide(bird, bombs, True)) != 0:
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                score.update(screen)
                pg.display.update()
                time.sleep(2)
                return
        if bird.state == "hyper":
            for bomb in pg.sprite.spritecollide(bird, bombs, True):
                exps.add(Explosion(bomb, 50))
                score.value += 1
            

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        emps.update()  # EMPの更新
        emps.draw(screen)  # EMPの描画
        gravities.update(bombs,emys,score,exps)
        gravities.draw(screen)
        score.update(screen)
        shields.update()    #シールドの情報を更新
        shields.draw(screen)    #シールドを描画
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
