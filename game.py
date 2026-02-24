import math
import os
import random
import sys
import pygame

from scripts.particle import Particle
from scripts.spark import Spark
from scripts.utils import load_image, load_images, Animation
from scripts.entities import PhysicsEntity, Player, Enemy, Boss
from scripts.tilemap import Tilemap
from scripts.clouds import Clouds


class Game:
    def __init__(self):
        pygame.init()

        pygame.display.set_caption("Arcane Ascension")

        self.screen = pygame.display.set_mode((640, 480), pygame.RESIZABLE)
        self.display = pygame.surface.Surface((320, 240), pygame.SRCALPHA)
        self.display_2 = pygame.surface.Surface((320, 240))

        self.fullscreen = False

        self.clock = pygame.time.Clock()

        self.movement = [False, False]

        self.assets = {
            'decor': load_images('tiles/decor'),
            'grass': load_images('tiles/grass'),
            'large_decor': load_images('tiles/large_decor'),
            'stone': load_images('tiles/stone'),
            'player' : load_image('entities/player.png'),
            'background' : load_image('background.png'),
            'clouds' : load_images('clouds'),
            'enemy/idle' : Animation(load_images('entities/enemy/idle'), img_dur=6),
            'enemy/run' : Animation(load_images('entities/enemy/run'), img_dur=4),
            'player/idle' : Animation(load_images('entities/player/idle'), img_dur=6),
            'player/run' : Animation(load_images('entities/player/run'), img_dur=4),
            'player/jump' : Animation(load_images('entities/player/jump')),
            'player/slide' : Animation(load_images('entities/player/slide')),
            'player/wall_slide' : Animation(load_images('entities/player/wall_slide')),
            'particle/leaf': Animation(load_images('particles/leaf'), img_dur=20, loop=False),
            'particle/particle': Animation(load_images('particles/particle'), img_dur=6, loop=False),
            'gun' : load_image('gun.png'),
            'projectile' : load_image('projectile.png'),
            'boss/idle' : Animation(load_images('entities/boss/idle'), img_dur=6),
            'boss/run' : Animation(load_images('entities/boss/run'), img_dur=4),
        }

        self.sfx = {
            'jump' : pygame.mixer.Sound('data/sfx/jump.wav'),
            'dash' : pygame.mixer.Sound('data/sfx/dash.wav'),
            'hit' : pygame.mixer.Sound('data/sfx/hit.wav'),
            'shoot' : pygame.mixer.Sound('data/sfx/shoot.wav'),
            'ambience' : pygame.mixer.Sound('data/sfx/ambience.wav'),
            'victory' : pygame.mixer.Sound('data/sfx/victory.wav'),
        }

        self.sfx['ambience'].set_volume(0.2)
        self.sfx['shoot'].set_volume(0.4)
        self.sfx['hit'].set_volume(0.8)
        self.sfx['dash'].set_volume(0.3)
        self.sfx['jump'].set_volume(0.7)
        self.sfx['victory'].set_volume(0.6)



        self.clouds = Clouds(self.assets['clouds'], count=16)

        self.player = Player(self,(100, 100), (8, 15))

        self.tilemap = Tilemap(self, tile_size=16)

        self.level = 0

        self.load_level(self.level)
        self.screenshake = 0

    def load_level(self, map_id):
        self.tilemap.load('data/maps/' + str(map_id) + '.json')

        self.leaf_spawners = []

        for tree in self.tilemap.extract([('large_decor', 2)], keep=True):
            self.leaf_spawners.append(pygame.Rect(4 + tree['pos'][0], 4 + tree['pos'][1], 23, 13))
        self.enemies = []
        self.boss = None
        self.boss_dead = False
        for spawner in self.tilemap.extract([('spawners', 0), ('spawners', 1)]):
            if spawner['variant'] == 0:
                self.player.pos = spawner['pos']
                self.player.air_time = 0
            else:
                if self.level == 3:
                    self.boss = Boss(self, spawner['pos'], (12, 24))
                else:
                    self.enemies.append(Enemy(self, spawner['pos'], (8, 15)))

        self.particles = []
        self.projectiles = []
        self.boss_projectiles = []
        self.sparks = []

        self.scroll = [0, 0]
        self.dead = 0
        self.transition = -30
        self.boss_win_timer = 0
        self.paused = False

    def menu(self):
        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)

        title_font = pygame.font.Font(None, 40)
        option_font = pygame.font.Font(None, 20)
        small_font = pygame.font.Font(None, 16)

        menu_options = ['Play', 'Controls', 'Quit']
        selected = 0
        show_controls = False
        menu_tick = 0

        controls_list = [
            ('A / D', 'Move Left / Right'),
            ('SPACE', 'Jump'),
            ('X', 'Dash (damage enemies)'),
            ('F', 'Toggle Fullscreen'),
        ]

        while True:
            menu_tick += 1
            self.display_2.blit(self.assets['background'], (0, 0))

            self.clouds.update()
            self.clouds.render(self.display_2, offset=(0, 0))

            # Darken overlay
            overlay = pygame.Surface((320, 240), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.display_2.blit(overlay, (0, 0))

            if show_controls:
                # Controls screen
                ctrl_title = title_font.render('Controls', True, (255, 255, 255))
                self.display_2.blit(ctrl_title, (160 - ctrl_title.get_width() // 2, 30))

                # Separator line
                pygame.draw.line(self.display_2, (255, 255, 255), (60, 60), (260, 60), 1)

                y_offset = 75
                for key, action in controls_list:
                    key_surf = option_font.render(key, True, (180, 220, 255))
                    action_surf = small_font.render(action, True, (200, 200, 200))
                    self.display_2.blit(key_surf, (70, y_offset))
                    self.display_2.blit(action_surf, (160, y_offset + 2))
                    y_offset += 28

                back_text = small_font.render('Press ESC to go back', True, (150, 150, 150))
                # Pulsing alpha
                alpha = int(150 + 105 * math.sin(menu_tick * 0.05))
                back_text.set_alpha(alpha)
                self.display_2.blit(back_text, (160 - back_text.get_width() // 2, 210))
            else:
                # Title with glow effect
                title_text = title_font.render('Arcane Ascension', True, (255, 255, 255))
                # Shadow
                title_shadow = title_font.render('Arcane Ascension', True, (50, 50, 80))
                self.display_2.blit(title_shadow, (160 - title_shadow.get_width() // 2 + 2, 52))
                self.display_2.blit(title_text, (160 - title_text.get_width() // 2, 50))

                # Menu options
                for i, option in enumerate(menu_options):
                    if i == selected:
                        # Pulsing highlight color
                        pulse = int(200 + 55 * math.sin(menu_tick * 0.08))
                        color = (pulse, pulse, 255)
                        prefix = '> '
                        suffix = ' <'
                    else:
                        color = (160, 160, 160)
                        prefix = '  '
                        suffix = '  '
                    text = option_font.render(prefix + option + suffix, True, color)
                    self.display_2.blit(text, (160 - text.get_width() // 2, 120 + i * 30))

                # Footer hint
                hint = small_font.render('Use W/S or UP/DOWN to select, ENTER to confirm', True, (120, 120, 120))
                self.display_2.blit(hint, (160 - hint.get_width() // 2, 215))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.VIDEORESIZE:
                    if not self.fullscreen:
                        self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

                if event.type == pygame.KEYDOWN:
                    if show_controls:
                        if event.key == pygame.K_ESCAPE:
                            show_controls = False
                    else:
                        if event.key in (pygame.K_w, pygame.K_UP):
                            selected = (selected - 1) % len(menu_options)
                        if event.key in (pygame.K_s, pygame.K_DOWN):
                            selected = (selected + 1) % len(menu_options)
                        if event.key == pygame.K_RETURN:
                            if menu_options[selected] == 'Play':
                                self.run()
                                return
                            elif menu_options[selected] == 'Controls':
                                show_controls = True
                            elif menu_options[selected] == 'Quit':
                                pygame.quit()
                                sys.exit()

                    if event.key == pygame.K_f:
                        self.fullscreen = not self.fullscreen
                        if self.fullscreen:
                            self.screen = pygame.display.set_mode(self.screen.get_size(), pygame.FULLSCREEN | pygame.RESIZABLE)
                            pygame.mouse.set_visible(False)
                        else:
                            self.screen = pygame.display.set_mode(self.screen.get_size(), pygame.RESIZABLE)
                            pygame.mouse.set_visible(True)

            self.screen.blit(pygame.transform.scale(self.display_2, self.screen.get_size()), (0, 0))
            pygame.display.update()
            self.clock.tick(60)

    def run(self):
        self.sfx['ambience'].play(-1)

        while True:
            if self.paused:
                quit_to_menu = self.pause_screen()
                if quit_to_menu:
                    return
                continue

            self.display.fill((0, 0, 0, 0))
            self.display_2.blit(self.assets['background'], (0, 0))

            self.screenshake = max(0, self.screenshake - 1)

            # Level transition: all enemies dead (and boss dead if on boss level)
            level_clear = not len(self.enemies) and (self.boss is None or self.boss_dead)
            if level_clear:
                if self.level == 3 and self.boss_dead:
                    self.boss_win_timer += 1
                    # Circle-close transition during win timer
                    if self.boss_win_timer > 60:
                        transition_progress = min(30, self.boss_win_timer - 60)
                        transition_surf = pygame.Surface(self.display.get_size())
                        radius = max(0, (30 - transition_progress) * 8)
                        pygame.draw.circle(transition_surf, (255, 255, 255), (self.display.get_width() // 2, self.display.get_height() // 2), radius)
                        transition_surf.set_colorkey((255, 255, 255))
                        self.display.blit(transition_surf, (0, 0))
                    if self.boss_win_timer > 120:
                        self.win_screen()
                        return
                else:
                    self.transition += 1
                    if self.transition > 30:
                        self.level = min(self.level + 1, len(os.listdir('data/maps/')) - 1)
                        self.load_level(self.level)
            if self.transition < 0:
                self.transition += 1


            if self.dead:
                self.dead += 1
                if self.dead >= 10:
                    self.transition = min(30, self.transition + 1)
                if self.dead > 40:
                    self.load_level(self.level)

            self.scroll[0] += (self.player.rect().centerx - self.display.get_width() / 2 - self.scroll[0]) / 30
            self.scroll[1] += (self.player.rect().centery - self.display.get_height() / 2 - self.scroll[1]) / 30
            render_scroll = (int(self.scroll[0]), int(self.scroll[1]))

            for rect in self.leaf_spawners:
                if random.random() * 49999 < rect.width * rect.height:
                    pos = (rect.x + random.random() * rect.width, rect.y + random.random() * rect.height)
                    self.particles.append(Particle(self, 'leaf', pos, velocity=[-0.1, 0.3], frame=random.randint(0,20)))

            self.clouds.update()
            self.clouds.render(self.display_2, offset=render_scroll)

            self.tilemap.render(self.display, offset=render_scroll)

            for enemy in self.enemies.copy():
                kill = enemy.update(self.tilemap, (0,0))
                enemy.render(self.display, offset=render_scroll)
                if kill:
                    self.enemies.remove(enemy)

            # Boss update and render
            if self.boss and not self.boss_dead:
                kill = self.boss.update(self.tilemap, (0, 0))
                self.boss.render(self.display, offset=render_scroll)
                if kill:
                    self.boss_dead = True
                    self.screenshake = max(30, self.screenshake)
                    self.sfx['victory'].play()
                    for i in range(50):
                        angle = random.random() * math.pi * 2
                        speed = random.random() * 5
                        self.sparks.append(Spark(self.boss.rect().center, angle, 3 + random.random()))
                        self.particles.append(Particle(self, 'particle', self.boss.rect().center,
                            velocity=[math.cos(angle + math.pi) * speed * 0.5,
                                      math.sin(angle + math.pi) * speed * 0.5],
                            frame=random.randint(0, 7)))

            if not self.dead:
                self.player.update(self.tilemap, (self.movement[1] - self.movement[0], 0))
                self.player.render(self.display, offset=render_scroll)

            for projectile in self.projectiles.copy():
                projectile[0][0] += projectile[1]
                projectile[2] += 1
                img = self.assets['projectile']
                self.display.blit(img, (projectile[0][0] - img.get_width() / 2 - render_scroll[0], projectile[0][1] - img.get_height() / 2 - render_scroll[1]))
                if self.tilemap.solid_check(projectile[0]):
                    self.projectiles.remove(projectile)
                    for i in range(4):
                        self.sparks.append(Spark(projectile[0], random.random() - 0.5 + (math.pi if projectile[1] > 0 else 0), 2 + random.random()))
                elif projectile[2] > 360:
                    self.projectiles.remove(projectile)
                elif abs(self.player.dashing) < 50:
                    if self.player.rect().colliderect(pygame.Rect(projectile[0][0], projectile[0][1], 4, 4)):
                        self.projectiles.remove(projectile)
                        self.dead += 1
                        self.sfx['hit'].play()
                        self.screenshake = max(16, self.screenshake)
                        for i in range(30):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 5
                            self.sparks.append(Spark(self.player.rect().center, angle, 2 + random.random()))
                            self.particles.append(Particle(self, 'particle', self.player.rect().center, velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], frame=random.randint(0,7)))

            # Boss aimed projectiles
            for proj in self.boss_projectiles.copy():
                proj[0][0] += proj[1][0]
                proj[0][1] += proj[1][1]
                proj[2] += 1
                img = self.assets['projectile']
                self.display.blit(img, (proj[0][0] - img.get_width() / 2 - render_scroll[0], proj[0][1] - img.get_height() / 2 - render_scroll[1]))
                if self.tilemap.solid_check(proj[0]):
                    self.boss_projectiles.remove(proj)
                    for i in range(4):
                        self.sparks.append(Spark(proj[0], random.random() * math.pi * 2, 2 + random.random()))
                elif proj[2] > 360:
                    self.boss_projectiles.remove(proj)
                elif abs(self.player.dashing) < 50:
                    if self.player.rect().colliderect(pygame.Rect(proj[0][0], proj[0][1], 4, 4)):
                        self.boss_projectiles.remove(proj)
                        self.dead += 1
                        self.sfx['hit'].play()
                        self.screenshake = max(16, self.screenshake)
                        for i in range(30):
                            angle = random.random() * math.pi * 2
                            speed = random.random() * 5
                            self.sparks.append(Spark(self.player.rect().center, angle, 2 + random.random()))
                            self.particles.append(Particle(self, 'particle', self.player.rect().center, velocity=[math.cos(angle + math.pi) * speed * 0.5, math.sin(angle + math.pi) * speed * 0.5], frame=random.randint(0,7)))

            for spark in self.sparks.copy():
                kill = spark.update()
                spark.render(self.display, offset=render_scroll)
                if kill:
                    self.sparks.remove(spark)

            display_mask = pygame.mask.from_surface(self.display)
            display_sillhouette = display_mask.to_surface(setcolor=(0,0,0,180), unsetcolor=(0,0,0,0))
            for offset in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                self.display_2.blit(display_sillhouette, offset)

            for particle in self.particles.copy():
                kill = particle.update()
                particle.render(self.display, offset=render_scroll)
                if particle.type == 'leaf':
                    particle.pos[0] += math.sin(particle.animation.frame *0.035) * 0.3
                if kill:
                    self.particles.remove(particle)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.VIDEORESIZE:
                    if not self.fullscreen:
                        self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_a:
                        self.movement[0] = True
                    if event.key == pygame.K_d:
                        self.movement[1] = True
                    if event.key == pygame.K_SPACE:
                        self.player.jump()
                        self.sfx['jump'].play()
                    if event.key == pygame.K_x:
                        self.player.dash()
                    if event.key == pygame.K_ESCAPE:
                        self.paused = True
                    if event.key == pygame.K_f:
                        self.fullscreen = not self.fullscreen
                        if self.fullscreen:
                            self.screen = pygame.display.set_mode(self.screen.get_size(), pygame.FULLSCREEN | pygame.RESIZABLE)
                            pygame.mouse.set_visible(False)
                        else:
                            self.screen = pygame.display.set_mode(self.screen.get_size(), pygame.RESIZABLE)
                            pygame.mouse.set_visible(True)

                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_a:
                        self.movement[0] = False
                    if event.key == pygame.K_d:
                        self.movement[1] = False

            if self.transition:
                transition_surf = pygame.Surface(self.display.get_size())
                pygame.draw.circle(transition_surf, (255, 255, 255), (self.display.get_width() // 2, self.display.get_height() // 2), (30 - abs(self.transition)) * 8)
                transition_surf.set_colorkey((255, 255, 255))
                self.display.blit(transition_surf, (0,0))

            self.display_2.blit(self.display, (0, 0))

            # Boss HP bar
            if self.boss and not self.boss_dead and self.level == 3:
                bar_width = 100
                bar_height = 6
                bar_x = 160 - bar_width // 2
                bar_y = 10
                # Background
                pygame.draw.rect(self.display_2, (40, 40, 40), (bar_x - 1, bar_y - 1, bar_width + 2, bar_height + 2))
                # Red background
                pygame.draw.rect(self.display_2, (80, 20, 20), (bar_x, bar_y, bar_width, bar_height))
                # Green HP
                hp_ratio = self.boss.hp / self.boss.max_hp
                pygame.draw.rect(self.display_2, (200, 30, 30), (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))
                # Boss label
                boss_font = pygame.font.Font(None, 14)
                boss_label = boss_font.render('BOSS', True, (255, 255, 255))
                self.display_2.blit(boss_label, (160 - boss_label.get_width() // 2, bar_y + bar_height + 2))

            screenshake_offset = (random.random() * self.screenshake - self.screenshake / 2, random.random() * self.screenshake - self.screenshake / 2)
            self.screen.blit(pygame.transform.scale(self.display_2, self.screen.get_size()), (screenshake_offset))
            pygame.display.update()
            self.clock.tick(60)

    def pause_screen(self):
        pause_font = pygame.font.Font(None, 40)
        option_font = pygame.font.Font(None, 20)
        small_font = pygame.font.Font(None, 16)
        pause_options = ['Resume', 'Quit to Menu']
        selected = 0
        pause_tick = 0

        while self.paused:
            pause_tick += 1
            # Keep rendering the game underneath
            overlay = pygame.Surface((320, 240), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            self.display_2.blit(overlay, (0, 0))

            # Pause title
            title = pause_font.render('PAUSED', True, (255, 255, 255))
            self.display_2.blit(title, (160 - title.get_width() // 2, 60))

            # Options
            for i, option in enumerate(pause_options):
                if i == selected:
                    pulse = int(200 + 55 * math.sin(pause_tick * 0.08))
                    color = (pulse, pulse, 255)
                    prefix = '> '
                    suffix = ' <'
                else:
                    color = (160, 160, 160)
                    prefix = '  '
                    suffix = '  '
                text = option_font.render(prefix + option + suffix, True, color)
                self.display_2.blit(text, (160 - text.get_width() // 2, 110 + i * 30))

            hint = small_font.render('ESC to resume', True, (120, 120, 120))
            self.display_2.blit(hint, (160 - hint.get_width() // 2, 200))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.VIDEORESIZE:
                    if not self.fullscreen:
                        self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.paused = False
                    if event.key in (pygame.K_w, pygame.K_UP):
                        selected = (selected - 1) % len(pause_options)
                    if event.key in (pygame.K_s, pygame.K_DOWN):
                        selected = (selected + 1) % len(pause_options)
                    if event.key == pygame.K_RETURN:
                        if pause_options[selected] == 'Resume':
                            self.paused = False
                        elif pause_options[selected] == 'Quit to Menu':
                            self.paused = False
                            self.sfx['ambience'].stop()
                            self.level = 0
                            self.load_level(self.level)
                            self.menu()
                            return True
                    if event.key == pygame.K_f:
                        self.fullscreen = not self.fullscreen
                        if self.fullscreen:
                            self.screen = pygame.display.set_mode(self.screen.get_size(), pygame.FULLSCREEN | pygame.RESIZABLE)
                            pygame.mouse.set_visible(False)
                        else:
                            self.screen = pygame.display.set_mode(self.screen.get_size(), pygame.RESIZABLE)
                            pygame.mouse.set_visible(True)

            self.screen.blit(pygame.transform.scale(self.display_2, self.screen.get_size()), (0, 0))
            pygame.display.update()
            self.clock.tick(60)

    def win_screen(self):
        pygame.mixer.music.stop()
        self.sfx['ambience'].stop()

        title_font = pygame.font.Font(None, 40)
        sub_font = pygame.font.Font(None, 20)
        small_font = pygame.font.Font(None, 16)
        win_tick = 0
        fade_in_duration = 40

        while True:
            win_tick += 1
            self.display_2.blit(self.assets['background'], (0, 0))
            self.clouds.update()
            self.clouds.render(self.display_2, offset=(0, 0))

            overlay = pygame.Surface((320, 240), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            self.display_2.blit(overlay, (0, 0))

            # Circle-open transition at start of victory screen
            if win_tick < fade_in_duration:
                transition_surf = pygame.Surface((320, 240))
                radius = int(win_tick * (320 / fade_in_duration))
                pygame.draw.circle(transition_surf, (255, 255, 255), (160, 120), radius)
                transition_surf.set_colorkey((255, 255, 255))
                self.display_2.blit(transition_surf, (0, 0))

            # Victory title
            title = title_font.render('VICTORY!', True, (255, 215, 0))
            shadow = title_font.render('VICTORY!', True, (100, 80, 0))
            self.display_2.blit(shadow, (160 - shadow.get_width() // 2 + 2, 62))
            self.display_2.blit(title, (160 - title.get_width() // 2, 60))

            sub = sub_font.render('You defeated the boss!', True, (220, 220, 220))
            self.display_2.blit(sub, (160 - sub.get_width() // 2, 100))

            # Pulsing restart hint
            alpha = int(150 + 105 * math.sin(win_tick * 0.05))
            hint = small_font.render('Press ENTER to return to menu', True, (180, 180, 180))
            hint.set_alpha(alpha)
            self.display_2.blit(hint, (160 - hint.get_width() // 2, 160))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.VIDEORESIZE:
                    if not self.fullscreen:
                        self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        self.level = 0
                        self.load_level(self.level)
                        self.menu()
                        return
                    if event.key == pygame.K_f:
                        self.fullscreen = not self.fullscreen
                        if self.fullscreen:
                            self.screen = pygame.display.set_mode(self.screen.get_size(), pygame.FULLSCREEN | pygame.RESIZABLE)
                            pygame.mouse.set_visible(False)
                        else:
                            self.screen = pygame.display.set_mode(self.screen.get_size(), pygame.RESIZABLE)
                            pygame.mouse.set_visible(True)

            self.screen.blit(pygame.transform.scale(self.display_2, self.screen.get_size()), (0, 0))
            pygame.display.update()
            self.clock.tick(60)

Game().menu()