#!/usr/bin/python3

import sys
import random
import math
import os
import getopt
import pygame
import shelve
import time
from pygame.locals import *

if not pygame.font:
    print('Warning, fonts disabled')
if not pygame.mixer:
    print('Warning, sound disabled')

# setting up constants
WINDOW_WIDTH = 640
WINDOW_HEIGHT = 480
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
DARK_GREEN = (0, 65, 0)
GREY = (100, 100, 100)
BACKGROUND_COLOR = DARK_GREEN
COLLISION_RECT_COLOR = [n * 0.8 for n in BACKGROUND_COLOR]
MAX_FPS = 60
ENEMY_SPAWNDELAY = 500  # divided by current level
windowcolor = BLACK
PLAYER_SPEED = .025
FRICTION = 0.00667
ENEMY_MIN_SPEED = 0.01
ENEMY_MAX_SPEED = 0.2
LEVEL_LENGTH = 6 * 1000  # in milliseconds

# get fonts from /data/fonts*
FONTFILES = [f for f in os.listdir(os.path.join("data", "fonts"))
             if f.endswith('.ttf')]
FONTS = []  # None = default font
for file in FONTFILES:
    FONTS.append(os.path.join("data", "fonts", file))
MENU_FONT = os.path.join("data", "fonts", "kenpixel.ttf")  # used for main menu
GAME_OVER_FONT = None  # None = pygame default, used for game over screen
# None = pygame default, used for fps/frametime/enemy number indicators in game
GUI_FONT = None

NUMBER_IMAGES = []
for i in range(10):
    image = pygame.image.load(
        os.path.join("data", "numbers", "%d.png" % i))
    image.set_colorkey(BLACK)
    NUMBER_IMAGES.append(image)


class Player():

    """The player, can move left/right and up/down
    Functions: reinit, update
    Attributes: which, speed"""

    def __init__(self, controls='all'):
        self.image, self.rect = load_image('player.png')
        self.pos = WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2

        screen = pygame.display.get_surface()
        self.area = screen.get_rect()
        self.speed = PLAYER_SPEED

        self.state = "still"
        self.moveright = 0
        self.moveleft = 0
        self.moveup = 0
        self.movedown = 0
        self.controls = controls

        self.reinit()

    def reinit(self):
        self.state = "still"
        self.movepos = [0, 0]

    def update(self, time_passed):

        # friction
        for i in range(time_passed):
            self.movepos[0] = self.movepos[0] * (1.0 - FRICTION)
            self.movepos[1] = self.movepos[1] * (1.0 - FRICTION)
        if abs(self.movepos[0]) < 0.1:
            self.movepos[0] = 0
        if abs(self.movepos[1]) < 0.1:
            self.movepos[1] = 0
        # apply player movement to velocity
        self.movepos[
            0] += (self.moveright - self.moveleft) * self.speed * time_passed
        self.movepos[1] += (self.movedown - self.moveup) * \
            self.speed * time_passed

        # update x and y seperately to allow smooth movement along screen
        # edge

        # first, move x
        newpos = self.pos[0] + self.movepos[0], self.pos[1]
        newrect = Rect(newpos[0], newpos[1], self.rect.w, self.rect.h)

        # if new position is in screen, move
        if self.area.contains(newrect):
            self.rect = newrect
            self.pos = newpos

        # then, move y
        newpos = self.pos[0], self.pos[1] + self.movepos[1]
        newrect = Rect(newpos[0], newpos[1], self.rect.w, self.rect.h)

        # if new position is in screen, move
        if self.area.contains(newrect):
            self.rect = newrect
            self.pos = newpos


class Enemy(pygame.sprite.Sprite):

    """an enemy: comes from the right
    heads to the left
    appearance as text or sprite if text is not specified
    functions: reinit, update"""

    def __init__(self, x, y, speed, game, image, erratic=False, aimed=False,
                 rotated=False):
        pygame.sprite.Sprite.__init__(self)
        self.image = image
        self.rect = self.image.get_rect()
        if rotated:
            # rotate the image of the enemy in a random increment of 90
            self.image = pygame.transform.rotate(
                self.image, random.choice([90, 180, 270]))
            # and get a new rect for it, too
            self.rect = self.image.get_rect()
        self.pos = x, y
        screen = pygame.display.get_surface()
        self.area = screen.get_rect()
        self.speed = speed
        self.game = game
        self.erratic = erratic
        self.aimed = aimed
        self.reinit()

    def reinit(self):
        self.state = "still"
        if not self.aimed:
            # enemies are by default moving left
            self.movepos = [-self.speed, 0]
        else:
            # pick random player to move towards
            player = self.game.players[
                random.randint(0, len(self.game.players) - 1)]
            # calculate vector to player
            self.movepos = [
                player.pos[0] - self.pos[0], player.pos[1] - self.pos[1]]
            # calculate current mag
            mag = math.sqrt(self.movepos[0] ** 2 + self.movepos[1] ** 2)
            # divide x/y movement by mag, changing angled movement to 1
            self.movepos[0], self.movepos[1] = self.movepos[
                0] / mag, self.movepos[1] / mag
            # multiiply it by self.speed
            self.movepos[0], self.movepos[1] = self.speed * \
                self.movepos[0], self.speed * self.movepos[1]

    def update(self, time_passed):

        if self.erratic:  # moves erratically up and down
            self.movepos[
                1] += random.uniform(-ENEMY_MIN_SPEED, ENEMY_MIN_SPEED)

        newpos = self.pos[0] + self.movepos[0] * \
            time_passed, self.pos[1] + self.movepos[1] * time_passed
        if newpos[0] + self.rect.w > -5:
            self.pos = newpos
            self.rect.x, self.rect.y = newpos
        else:
            self.game.enemies.remove(self)


class TextEnemy(Enemy):

    def __init__(self, x, y, speed, game, text, **kwargs):
        image = render_number(text)
        super(TextEnemy, self).__init__(x, y, speed, game, image, **kwargs)


class Dimmer:

    """class for dimming the screen
    functions: dim, undim"""

    def __init__(self, keepalive=0):
        self.keepalive = keepalive
        if self.keepalive:
            self.buffer = pygame.Surface(
                pygame.display.get_surface().get_size())
        else:
            self.buffer = None

    def dim(self, darken_factor=64, color_filter=(0, 0, 0)):
        if not self.keepalive:
            self.buffer = pygame.Surface(
                pygame.display.get_surface().get_size())
        self.buffer.blit(pygame.display.get_surface(), (0, 0))
        if darken_factor > 0:
            darken = pygame.Surface(pygame.display.get_surface().get_size())
            darken.fill(color_filter)
            darken.set_alpha(darken_factor)
            # safe old clipping rectangle...
            old_clip = pygame.display.get_surface().get_clip()
            # ..blit over entire screen...
            pygame.display.get_surface().blit(darken, (0, 0))
            # pygame.display.flip()
            # ... and restore clipping
            pygame.display.get_surface().set_clip(old_clip)

    def undim(self):
        if self.buffer:
            pygame.display.get_surface().blit(self.buffer, (0, 0))
            if not self.keepalive:
                self.buffer = None


def render_number(text_number):
    font_width = 5
    font_height = 7

    int_digits = [int(digit) for digit in text_number]

    image_width = sum(NUMBER_IMAGES[d].get_width() for d in int_digits) + \
        2 * (len(text_number) - 1)

    image = pygame.Surface((image_width, font_height))

    x = 0

    for digit in text_number:
        int_digit = int(digit)
        digit_image = NUMBER_IMAGES[int_digit]
        image.blit(digit_image, ((x, 0), digit_image.get_size()))
        x += NUMBER_IMAGES[int_digit].get_width() + 2
        image.set_colorkey(BLACK)
    scale = random.randint(3, 4)
    return pygame.transform.scale(
        image, (image.get_width() * scale, image.get_height() * scale))


def load_image(name, colorkey=None):
    fullname = os.path.join('data', name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error as message:
        print(('Cannot load image:', name))
        raise SystemExit(message)
    image = image.convert_alpha()
    if colorkey is not None:
        if colorkey is -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey, RLEACCEL)
    return image, image.get_rect()


def get_random_font():
    # returns a random font from the list FONTS
    return FONTS[random.randint(0, len(FONTS) - 1)]


def get_frames_from_image(base_image, framenumber, framesize):
    # gets frames of an animation from an image

    frames = []
    offsets = []
    for n in range(framenumber):
        offsets.append(framesize[0] * n)

    for i in range(framenumber):
        # for each frame, turn it into a seperate image
        image = pygame.Surface(framesize)
        # image.blit(base_image, (0,0))#, (offsets[i], framesize))
        image = base_image.subsurface(
            offsets[i], 0, framesize[0], framesize[1])
        frames.append(image)
    return frames


def load_sound(name):
    class NoneSound:

        def play(self):
            pass
    if not pygame.mixer:
        return NoneSound()
    fullname = os.path.join('data', name)
    try:
        sound = pygame.mixer.Sound(fullname)
    except pygame.error as message:
        print(('Cannot load sound:', wav))
        raise SystemExit(message)
    return sound


def terminate():
    print('goodbye')
    pygame.quit()
    sys.exit()


def save_highscores(highscores):
    file = shelve.open('data/highscores', 'n')
    file['highscores'] = highscores
    file.close()


def load_highscores():
    file = shelve.open('data/highscores', 'r')
    highscores = file['highscores']
    file.close()
    return highscores


def playertouchingenemy(playerrect, enemies):
    for enemy in enemies:
        if playerrect.colliderect(enemy.rect):
            return True
    return False


def draw_text(text, font, surface, x, y, color=WHITE, background=None,
              position="topleft"):
    # draws some text using font to the surface
    textobj = font.render(text, 1, color)
    textrect = textobj.get_rect()
    if position == 'center':
        textrect.center = (x, y)
    elif position == 'bottomright':
        textrect.bottomright = (x, y)
    elif position == 'topleft':
        textrect.topleft = (x, y)
    elif position == 'topright':
        textrect.topright = (x, y)
    if background:
        pygame.draw.rect(screen, background, textrect.inflate(2, 2))
    surface.blit(textobj, textrect)
    return textrect.inflate(2, 2)  # for knowing where to redraw the background


class TextSprite(pygame.sprite.Sprite):

    """For use in menus"""

    def __init__(self, text, font, x, y, color=WHITE):
        self.text = text
        self.font = font
        self.color = color
        self.image = font.render(text, 1, color)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)

    def draw(self, screen):
        return screen.blit(self.image, self.rect)

    def change_color(self, color):
        self.image = self.font.render(self.text, 1, color)
        self.color = color


class Game(object):
    base_enemy_spawn_delay = 500  # divided by current level
    base_level_length = 6000  # in milliseconds
    enemy_min_speed = 0.01
    enemy_max_speed = 0.2
    background_color = DARK_GREEN
    show_hitboxes = False
    show_debug_info = False
    hotseat_multiplayer = False
    # if controls == '', player is not playing
    types_of_controls = ['wasd', 'arrows', 'tfgh', 'ijkl', 'numpad', '']
    # default controls for each player
    players_controls = ['wasd', 'arrows', 'tfgh', 'ijkl']

    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()

        self.background = pygame.Surface(screen.get_size()).convert()
        self.background.fill(BACKGROUND_COLOR)

        # load highscores from data/highscores
        try:
            self.highscores = load_highscores()
        except:
            # get new highscores if it cannot load highscores
            self.highscores = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        self.init_game()

    def init_game(self):
        self.players = []
        self.enemies = []
        self.level = 1
        # old textrects: used for filling background color
        self.old_textrects = []

    def menu(self, title, options, title_size=50, option_size=25,
             enemies_background=True, option_selected=0):
        """
        A basic menu.
        Arrow keys are used to navigate.
        """
        x = WINDOW_WIDTH / 2

        titlefont = pygame.font.Font(MENU_FONT, title_size)
        title_y = title_size / 2 + 30
        title = TextSprite(title, titlefont, x, title_y, RED)

        optioncolor = WHITE
        selectedoptioncolor = RED
        optionfont = pygame.font.Font(MENU_FONT, option_size)
        space_below_title = title_size
        space_between_options = optionfont.get_height()
        option_sprites = []
        for i in range(len(options)):
            y = space_below_title + title_y \
                + (i + 1) * space_between_options
            if option_selected == i:
                color = selectedoptioncolor
            else:
                color = optioncolor
            option_sprites.append(
                TextSprite(options[i], optionfont, x, y, color))

        spawntimer = pygame.time.Clock()
        spawntime = 0
        screen_dimmer = Dimmer()

        def update_option_sprites(option_sprites, old_option, new_option):
            option_sprites[old_option].change_color(optioncolor)
            option_sprites[new_option].change_color(selectedoptioncolor)

        while 1:
            time_since_last_frame = self.clock.tick(MAX_FPS)
            # clear screen with backgroundcolor
            screen_dimmer.undim()
            self.screen.blit(self.background, (0, 0))

            if enemies_background:
                # draw background fanciness
                # scrolling enemies
                spawntime += spawntimer.tick()
                if spawntime >= ENEMY_SPAWNDELAY:
                    spawntime -= ENEMY_SPAWNDELAY
                    x = WINDOW_WIDTH - 10
                    y = random.randint(0, WINDOW_HEIGHT)
                    speed = random.uniform(ENEMY_MIN_SPEED, ENEMY_MAX_SPEED)
                    text = random.choice([str(random.randint(1, 1024))])
                    self.enemies.append(
                        TextEnemy(x, y, speed, self, text))
                for object in self.enemies[:]:
                    object.update(time_since_last_frame)
                    self.screen.blit(object.image, object.rect)
            # then, darken the screen without the title/options
            screen_dimmer.dim(darken_factor=200)
            title.draw(self.screen)
            for option in option_sprites:
                option.draw(self.screen)
            # update display
            pygame.display.update()
            # handle keys for menu
            for event in pygame.event.get():
                if event.type == QUIT:
                    self.exit()

                if event.type == KEYDOWN:
                    if event.key == K_UP or event.key == ord('w'):
                        old_option = option_selected
                        option_selected -= 1
                        if option_selected < 0:
                            option_selected = len(options) - 1
                        update_option_sprites(
                            option_sprites, old_option, option_selected)
                    elif event.key == K_DOWN or event.key == ord('s'):
                        old_option = option_selected
                        option_selected += 1
                        if option_selected > len(options) - 1:
                            option_selected = 0
                        update_option_sprites(
                            option_sprites, old_option, option_selected)
                    elif event.key == K_ESCAPE:  # pressing escape quits

                        return "exit"
                    elif event.key == K_RETURN:
                        return option_selected

                elif event.type == MOUSEMOTION:
                    for option in option_sprites:
                        if option.rect.collidepoint(event.pos):
                            old_option = option_selected
                            option_selected = option_sprites.index(option)
                            update_option_sprites(
                                option_sprites, old_option, option_selected)
                            break
                elif event.type == MOUSEBUTTONDOWN:
                    return option_selected

    def main_menu(self):
        while 1:
            choice = self.menu("THE RNG", ["Play", "Options", "Exit"],
                               title_size=100, option_size=50)

            if choice == 0:
                while 1:
                    self.run()

            elif choice == 1:
                self.options_menu()

            elif choice == 2:  # 'exit'
                self.exit()

            # if player presses ESC or tries to exit window
            elif choice == 'exit':
                self.exit()

    def exit(self):
        save_highscores(self.highscores)
        terminate()

    def options_menu(self):
        option_selected = 0
        while 1:

            if self.hotseat_multiplayer:
                # if hotseat, show controls for all players
                options = [
                    "Show hitboxes " + str(self.show_hitboxes),
                    "Hotseat multiplayer " + str(self.hotseat_multiplayer),
                    "Player 1 controls = " + self.players_controls[0],
                    "Player 2 controls = " + self.players_controls[1],
                    "Player 3 controls = " + self.players_controls[2],
                    "Player 4 controls = " + self.players_controls[3],
                    "Back"
                ]
                # indicate if any player is not playing
                for i in range(len(options[2:6])):
                    if self.players_controls[i] == '':
                        options[i + 2] = options[i + 2][:9] + "Not Playing"

            else:
                options = [
                    "Show hitboxes " + str(self.show_hitboxes),
                    "Hotseat multiplayer " + str(self.hotseat_multiplayer),
                    "Back"
                ]
            choice = self.menu("Options", options,
                               option_selected=option_selected)

            if choice == 0:
                # toggle showing hitboxes
                self.show_hitboxes = not self.show_hitboxes

            if choice == 1:
                # toggle hotseat multiplayer
                self.hotseat_multiplayer = not self.hotseat_multiplayer

            elif not self.hotseat_multiplayer and choice == 2:
                # exit to main menu
                break
            elif 2 <= choice <= 5:
                player_index = choice - 2
                control_type = self.players_controls[player_index]
                self.players_controls[player_index] = \
                    self.get_next_control_type(control_type)

            elif choice == 6 or choice == 'exit':
                break

            option_selected = choice

    def get_next_control_type(control_type):
        i = self.types_of_controls.index(control_type) - 1
        return self.types_of_controls[i]

    def spawn_number_enemies(self):
        x = WINDOW_WIDTH - 10
        y = random.randint(0, WINDOW_HEIGHT)
        speed = random.uniform(ENEMY_MIN_SPEED, ENEMY_MAX_SPEED)
        text = str(self.score)
        if self.level >= 4:
            # 1/10 chance of erratic movement from level 4 onward
            erratic_movement = (1 == random.randint(1, 10))
        else:
            erratic_movement = False
        if self.level >= 2:
            # 1/10 chance of aimed movement from level 2 onward
            aimed = (1 == random.randint(1, 10))
        else:
            aimed = False
        if self.level >= 2:
            # 1/4 chance of starting rotated from level 2 onward
            start_rotated = (1 == random.randint(1, 4))
        else:
            start_rotated = False

        self.enemies.append(TextEnemy(
            x, y, speed, self,
            text, erratic=erratic_movement, aimed=aimed,
            rotated=start_rotated))

        # spawn enemies on left to encourage player to run
        # and to look cool
        x = 10
        y = random.randint(0, WINDOW_HEIGHT)
        # fast as the average speed of an enemy
        speed = (ENEMY_MAX_SPEED + ENEMY_MIN_SPEED) / 2
        # 1/2 chance of number, 1/2 chance of sprite
        # , None])
        textsprite = random.choice([str(random.randint(1, 99999999))])
        if self.level >= 3:
            # after level 3, half of the left enemies move erratically
            # this makes them look cooler and more terrifying
            erratic_movement = (1 == random.randint(1, 2))
        else:
            erratic_movement = False

        self.enemies.append(TextEnemy(
            x, y, speed, self, text, erratic=erratic_movement))

    def handle_keys(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.exit()

            if event.type == KEYDOWN:
                for player in self.players:
                    if player.controls == 'all' or player.controls == 'wasd':
                        if event.key == ord('a'):
                            player.moveleft = 1
                        if event.key == ord('d'):
                            player.moveright = 1
                        if event.key == ord('w'):
                            player.moveup = 1
                        if event.key == ord('s'):
                            player.movedown = 1

                    if player.controls == 'all' or player.controls == 'arrows':
                        if event.key == K_LEFT:
                            player.moveleft = 1
                        if event.key == K_RIGHT:
                            player.moveright = 1
                        if event.key == K_UP:
                            player.moveup = 1
                        if event.key == K_DOWN:
                            player.movedown = 1
                    if player.controls == 'all' or player.controls == 'tfgh':
                        if event.key == ord('f'):
                            player.moveleft = 1
                        if event.key == ord('h'):
                            player.moveright = 1
                        if event.key == ord('t'):
                            player.moveup = 1
                        if event.key == ord('g'):
                            player.movedown = 1
                    if player.controls == 'all' or player.controls == 'ijkl':
                        if event.key == ord('j'):
                            player.moveleft = 1
                        if event.key == ord('l'):
                            player.moveright = 1
                        if event.key == ord('i'):
                            player.moveup = 1
                        if event.key == ord('k'):
                            player.movedown = 1

                    if player.controls == 'all' or player.controls == 'numpad':
                        if event.key == K_KP4:
                            player.moveleft = 1
                        if event.key == K_KP6:
                            player.moveright = 1
                        if event.key == K_KP8:
                            player.moveup = 1
                        if event.key == K_KP2:
                            player.movedown = 1
                if event.key == K_F3:
                    # toggle showing debug info
                    self.show_debug_info = not(self.show_debug_info)
                if event.key == K_F4:
                    # toggle drawing hitboxes of enemies
                    self.show_hitboxes = not(self.show_hitboxes)

            if event.type == KEYUP:
                if event.key == K_ESCAPE:
                    return 'exit'
                for player in self.players:
                    if player.controls == 'all' or player.controls == 'arrows':
                        if event.key == K_LEFT:
                            player.moveleft = 0
                        if event.key == K_RIGHT:
                            player.moveright = 0
                        if event.key == K_UP:
                            player.moveup = 0
                        if event.key == K_DOWN:
                            player.movedown = 0

                    if player.controls == 'all' or player.controls == 'wasd':
                        if event.key == ord('a'):
                            player.moveleft = 0
                        if event.key == ord('d'):
                            player.moveright = 0
                        if event.key == ord('w'):
                            player.moveup = 0
                        if event.key == ord('s'):
                            player.movedown = 0

                    if player.controls == 'all' or player.controls == 'tfgh':
                        if event.key == ord('f'):
                            player.moveleft = 0
                        if event.key == ord('h'):
                            player.moveright = 0
                        if event.key == ord('t'):
                            player.moveup = 0
                        if event.key == ord('g'):
                            player.movedown = 0

                    if player.controls == 'all' or player.controls == 'ijkl':
                        if event.key == ord('j'):
                            player.moveleft = 0
                        if event.key == ord('l'):
                            player.moveright = 0
                        if event.key == ord('i'):
                            player.moveup = 0
                        if event.key == ord('k'):
                            player.movedown = 0

                    if player.controls == 'all' or player.controls == 'numpad':
                        if event.key == K_KP4:
                            player.moveleft = 0
                        if event.key == K_KP6:
                            player.moveright = 0
                        if event.key == K_KP8:
                            player.moveup = 0
                        if event.key == K_KP2:
                            player.movedown = 0

    def handle_game_over(self):
        # first, save highscore
        # add score to highscores
        self.highscores.append(self.score)
        # sort highscores in descending order
        self.highscores.sort(reverse=True)
        # get rid of lowest highscore
        self.highscores.pop(-1)

        # dim screen
        screen_dimmer = Dimmer()
        screen_dimmer.dim(darken_factor=200)

        # draw gameover text, including score
        font = pygame.font.Font(GAME_OVER_FONT, 58)
        draw_text('GAME OVER', font, self.screen, (WINDOW_WIDTH / 2),
                  20, color=RED, position='center')

        # show highscores
        draw_text('Score:' + str(self.score), font, self.screen,
                  (WINDOW_WIDTH / 2), 110, color=WHITE, position='center')
        # render highscores in a smaller font
        font = pygame.font.Font(GAME_OVER_FONT, 36)
        draw_text('HIGHSCORES', font, self.screen, WINDOW_WIDTH / 2,
                  150, color=WHITE, position='center')
        for i in range(len(self.highscores)):
            x = WINDOW_WIDTH / 2
            y = 180 + 30 * i
            draw_text(
                str(self.highscores[i]), font, self.screen, x, y,
                color=WHITE, position='center')
            if self.highscores[i] == self.score:
                draw_text("YOU ->" + " " * len(str(self.highscores[i])),
                          font, self.screen, x - 20, y + 10,
                          color=WHITE, position='bottomright')

        pygame.display.update()
        # wait 1 second to stop people accidentally skipping this screen
        time.sleep(1)
        font = pygame.font.Font(GAME_OVER_FONT, 58)
        draw_text('Press Enter to play again.', font, self.screen,
                  WINDOW_WIDTH / 2, 60, color=WHITE, position='center')
        pygame.display.update()
        self.wait_for_keypress(certainkey=K_RETURN)
        screen_dimmer.undim()

        self.game_over = True
        self.init_game()

    def wait_for_keypress(self, certainkey=None):
        # wait until the player presses a key
        # clears the pygame events, ensuring it isn't going to register an old
        # keypress
        pygame.event.clear()
        while True:
            # 5 frames a second; nothing's moving, so it should be ok: the
            # player won't notice
            self.clock.tick(5)
            for event in pygame.event.get():
                # if player tries to close the window, terminate everything
                if event.type == QUIT:
                    self.exit()
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE:  # pressing escape quits
                        self.main_menu()
                    elif certainkey is None:
                        return  # all other keys just return
                    elif event.key == certainkey:
                        return

    def run(self):
        self.init_game()
        # Blit everything to the screen
        self.screen.blit(self.background, (0, 0))
        pygame.display.update()
        self.score = 0
        self.spawntime = 0
        self.clock.tick()
        self.time_until_new_level = LEVEL_LENGTH
        # sleep 1 millisecond at game start to prevent error when trying to
        # divide by time_since_last_frame when it is zero
        time.sleep(0.001)

        if self.hotseat_multiplayer:
            self.players = [Player(controls)
                            for controls in self.players_controls
                            if controls != '']
        else:
            self.players = [Player()]

        self.game_over = False

        while not self.game_over:

            # Make sure game doesn't run at more than MAX_FPS frames per second
            self.time_since_last_frame = self.clock.tick(MAX_FPS)

            event = self.handle_keys()
            if event == "exit":  # exit to main menu
                self.main_menu()

            # check if player has hit an enemy using smaller hitbox
            for player in self.players:
                player_rect = player.rect.inflate(-14, -14)
                if playertouchingenemy(player_rect, self.enemies):
                    # first, clear the player's sprite with background
                    self.screen.blit(self.background, player.rect, player.rect)
                    self.players.remove(player)
            # check if all players are dead or not
            # check seperate from death check to stop starting with no
            # players
            if len(self.players) == 0:
                # show game over screen
                self.handle_game_over()
                # break the loop
                self.game_over = True
            # new level if time
            self.time_until_new_level -= self.time_since_last_frame
            if self.time_until_new_level <= 0:
                self.level += 1
                self.time_until_new_level = LEVEL_LENGTH
                # spawn 'new level' enemy
                x = WINDOW_WIDTH - 10
                y = random.randint(50, WINDOW_HEIGHT - 50)
                speed = ENEMY_MAX_SPEED
                text = "LEVEL " + str(self.level)
                # new level enemy uses pygame default font, due to munro having
                # bad hitbox at large sizes
                enemyfont = pygame.font.Font(None, 50)
                self.enemies.append(Enemy(
                    x, y, speed, self, enemyfont.render(text, True, RED)))
            # spawn enemies
            self.spawntime += self.time_since_last_frame
            # spawn enemies on right if SPAWN_DELAY time has passed
            if self.spawntime >= ENEMY_SPAWNDELAY / math.sqrt(self.level):
                self.spawntime -= ENEMY_SPAWNDELAY / math.sqrt(self.level)
                self.score += 1
                self.spawn_number_enemies()

            # RENDER EVERYTHING
            for player in self.players:
                self.screen.blit(self.background, player.rect, player.rect)
            for enemy in self.enemies:
                self.screen.blit(self.background, enemy.rect, enemy.rect)
            for player in self.players:
                player.update(self.time_since_last_frame)

            for rect in self.old_textrects:
                self.screen.blit(self.background, rect, rect)

            self.old_textrects = []

            # draw score at top-middle of screen
            font = pygame.font.Font(GUI_FONT, 20)
            self.old_textrects.append(
                draw_text('Score:' + str(self.score), font, self.screen,
                          WINDOW_WIDTH / 2, 20, color=RED, position='center')
            )

            if self.show_debug_info:  # show all debug info if enabled

                # draw FPS at topright screen
                fps = 1.0 / self.time_since_last_frame * 1000
                self.old_textrects.append(
                    draw_text(
                        'FPS:' + str(int(fps)) + '/' + str(MAX_FPS),
                        font, self.screen, WINDOW_WIDTH - 100, 10,
                        color=WHITE, background=BLACK, position='topleft')
                )

                # draw frame time: time it takes to render each frame
                self.old_textrects.append(
                    draw_text('FT: ' + str(self.time_since_last_frame), font,
                              self.screen, WINDOW_WIDTH - 100, 25,
                              color=WHITE, background=BLACK,
                              position='topleft')
                )

                # draw number of enemies on topright, for debug
                self.old_textrects.append(
                    draw_text("Numbers:" + str(len(self.enemies)), font,
                              self.screen, WINDOW_WIDTH - 100, 40,
                              color=WHITE, background=BLACK,
                              position="topleft")
                )

            # draw enemies in enemies
            for enemy in self.enemies[:]:
                enemy.update(self.time_since_last_frame)
                if self.show_hitboxes:
                    # draw slightly darker then background rectangle
                    pygame.draw.rect(
                        self.screen, COLLISION_RECT_COLOR, enemy.rect)
            for enemy in self.enemies[:]:
                self.screen.blit(enemy.image, enemy.rect)

            # draw player
            for player in self.players:
                self.screen.blit(player.image, player.rect)
                if self.show_hitboxes:
                    # draw player rect
                    pygame.draw.rect(
                        self.screen, WHITE, player.rect.inflate(-14, -14))

            # blit to screen
            pygame.display.update()

            pygame.event.pump()


def main():
    # Initialise screen and window
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("The RNG")
    pygame.display.set_icon(load_image('icon.gif')[0])

    game = Game(screen)
    game.main_menu()


if __name__ == '__main__':
    main()
