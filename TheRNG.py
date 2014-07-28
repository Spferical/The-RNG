#!/usr/bin/python2

import sys
import random
import math
import os
import getopt
import pygame
import shelve
import time
from pygame.locals import *

if not pygame.font: print 'Warning, fonts disabled'
if not pygame.mixer: print 'Warning, sound disabled'

#setting up constants
WINDOW_WIDTH=640
WINDOW_HEIGHT=480
windowsurface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), 0, 32)
BLACK = (0,0,0)
WHITE=(255,255,255)
RED=(255,0,0)
GREEN=(0,255,0)
BLUE=(0,0,255)
DARK_GREEN = (0,65,0)
GREY = (100, 100, 100)
BACKGROUND_COLOR = DARK_GREEN
MAX_FPS = 60
ENEMY_SPAWNDELAY = 500 # divided by current level
windowcolor = BLACK
PLAYER_SPEED = .025
FRICTION = 0.00667
ENEMY_MIN_SPEED = 0.01
ENEMY_MAX_SPEED = 0.2
LEVEL_LENGTH = 6 * 1000 # in milliseconds

#get fonts from /data/fonts*
FONTFILES = [f for f in os.listdir(os.path.join("data", "fonts"))
             if f.endswith('.ttf')]
FONTS = []  # None = default font
for file in FONTFILES:
    FONTS.append(os.path.join("data", "fonts", file))
#get fonts natively available on system
#SYSFONTS = pygame.font.get_fonts()
MENU_FONT = os.path.join("data", "fonts", "kenpixel.ttf") # used for main menu
GAME_OVER_FONT = None # None = pygame default, used for game over screen
GUI_FONT = None # None = pygame default, used for fps/frametime/enemy number indicators in game


class Player():
    """The player, can move left/right and up/down
    Functions: reinit, update
    Attributes: which, speed"""

    def __init__(self, controls = 'all'):
        self.image, self.rect = load_image('player.png')
        #old code; used to be used for frames
        #can still be used if an animation is added
        #self.frames = get_frames_from_image(self.image, 4, (16, 16))
        #self.rect = self.frames[0].get_rect()
        #self.frameindex = 0
        #self.image = self.frames[0]
        #self.framedelay = 10
        #self.framewait = 0
        self.pos = WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2
        #self.rect.x = WINDOW_WIDTH / 2
        #self.rect.y = WINDOW_HEIGHT / 2

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
        self.movepos = [0,0]

    def update(self, time_passed):
        #update frame
        #self.framewait += 1
        #if self.framewait >= self.framedelay:
        #    self.framewait = 0
        #    self.frameindex += 1
        #    if self.frameindex > len(self.frames) - 1:
        #        self.frameindex = 0
        #    self.image = self.frames[self.frameindex]

        #friction
        for i in range(time_passed):
            self.movepos[0] = self.movepos[0] * (1.0-FRICTION)
            self.movepos[1] = self.movepos[1] * (1.0-FRICTION)
        if abs(self.movepos[0]) < 0.1:
            self.movepos[0] = 0
        if abs(self.movepos[1]) < 0.1:
            self.movepos[1] = 0
        #apply player movement to velocity
        self.movepos[0] += (self.moveright - self.moveleft) * self.speed * time_passed
        self.movepos[1] += (self.movedown - self.moveup) * self.speed * time_passed


        ###UPDATE X AND Y SEPERATELY TO ALLOW SMOOTH MOVEMENT ALONG SCREEN EDGE###

        #first, move x
        newpos = self.pos[0] + self.movepos[0], self.pos[1]
        newrect = Rect(newpos[0], newpos[1], self.rect.w, self.rect.h)

        #if new position is in screen, move
        if self.area.contains(newrect):
            self.rect = newrect
            self.pos = newpos

        #then, move y
        newpos = self.pos[0], self.pos[1] + self.movepos[1]
        newrect = Rect(newpos[0], newpos[1], self.rect.w, self.rect.h)

        #if new position is in screen, move
        if self.area.contains(newrect):
            self.rect = newrect
            self.pos = newpos
        #pygame.event.pump()


class Enemy(pygame.sprite.Sprite):
    """an enemy: comes from the right
    heads to the left
    appearance as text or sprite if text is not specified
    functions: reinit, update"""

    def __init__(self, x, y, speed, text = None, font = None, color = WHITE, erratic = False, aimed = False,
            rotated = False):
        pygame.sprite.Sprite.__init__(self)
        if text:
            if font == None:
                font = pygame.font.Font(get_random_font(), random.randint(20, 50))
            self.image = font.render(text, True, color)
            self.rect = self.image.get_rect()
        else:
            self.image, self.rect = load_image('Enemy.gif')
        if rotated:
            #rotate the image of the enemy in a random increment of 90
            self.image = pygame.transform.rotate(self.image, random.choice([90, 180, 270]))
            #and get a new rect for it, too
            self.rect = self.image.get_rect()
        self.pos = x, y
        screen = pygame.display.get_surface()
        self.area = screen.get_rect()
        self.speed = speed
        self.erratic = erratic
        self.aimed = aimed
        self.reinit()

    def reinit(self):
        self.state = "still"
        if not self.aimed:
            self.movepos = [-self.speed,0]#enemies are by default moving left
        else:
            global players
            #pick random player to move towards
            player = players[random.randint(0, len(players) - 1)]
                ##WARNING: TRIGONOMETRY##
            #calculate vector to player
            self.movepos = [player.pos[0] - self.pos[0], player.pos[1] - self.pos[1]]
            #calculate current mag
            mag = math.sqrt(self.movepos[0] ** 2 + self.movepos[1] ** 2)
            #divide x/y movement by mag, changing angled movement to 1
            self.movepos[0], self.movepos[1] = self.movepos[0] / mag, self.movepos[1] / mag
            #multiiply it by self.speed
            self.movepos[0], self.movepos[1] = self.speed * self.movepos[0], self.speed * self.movepos[1]
    def update(self, time_passed):

        if self.erratic: # moves erratically up and down
            self.movepos[1] += random.uniform(-ENEMY_MIN_SPEED, ENEMY_MIN_SPEED)

        newpos = self.pos[0] + self.movepos[0] * time_passed, self.pos[1] + self.movepos[1] * time_passed
        if newpos[0] + self.rect.w > -5:
            #self.rect = newpos
            self.pos = newpos
            self.rect.x, self.rect.y = newpos
        else:
            enemies.remove(self)



class Dimmer:
    """class for dimming the screen
    functions: dim, undim"""
    def __init__(self, keepalive=0):
        self.keepalive=keepalive
        if self.keepalive:
            self.buffer=pygame.Surface(pygame.display.get_surface().get_size())
        else:
            self.buffer=None

    def dim(self, darken_factor=64, color_filter=(0,0,0)):
        if not self.keepalive:
            self.buffer=pygame.Surface(pygame.display.get_surface().get_size())
        self.buffer.blit(pygame.display.get_surface(),(0,0))
        if darken_factor>0:
            darken=pygame.Surface(pygame.display.get_surface().get_size())
            darken.fill(color_filter)
            darken.set_alpha(darken_factor)
            # safe old clipping rectangle...
            old_clip=pygame.display.get_surface().get_clip()
            # ..blit over entire screen...
            pygame.display.get_surface().blit(darken,(0,0))
            #pygame.display.flip()
            # ... and restore clipping
            pygame.display.get_surface().set_clip(old_clip)

    def undim(self):
        if self.buffer:
            pygame.display.get_surface().blit(self.buffer,(0,0))
            if not self.keepalive:
                self.buffer=None


def load_image(name, colorkey=None):
    fullname = os.path.join('data', name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error, message:
        print 'Cannot load image:', name
        raise SystemExit, message
    image = image.convert_alpha()
    if colorkey is not None:
        if colorkey is -1:
            colorkey = image.get_at((0,0))
        image.set_colorkey(colorkey, RLEACCEL)
    return image, image.get_rect()


def get_random_font():
    #returns a random font from the list FONTS
    return FONTS[random.randint(0, len(FONTS) - 1)]

def get_frames_from_image(base_image, framenumber, framesize):
    #gets frames of an animation from an image

    frames = []
    offsets = []
    for n in range(framenumber):
        offsets.append(framesize[0] * n)

    for i in range(framenumber):
        #for each frame, turn it into a seperate image
        image = pygame.Surface(framesize)
        #image.blit(base_image, (0,0))#, (offsets[i], framesize))
        image = base_image.subsurface(offsets[i], 0, framesize[0], framesize[1])
        frames.append(image)
    return frames


def load_sound(name):
    class NoneSound:
        def play(self): pass
    if not pygame.mixer:
        return NoneSound()
    fullname = os.path.join('data', name)
    try:
        sound = pygame.mixer.Sound(fullname)
    except pygame.error, message:
        print 'Cannot load sound:', wav
        raise SystemExit, message
    return sound


def terminate():
    print 'goodbye'
    #save highscores
    save_highscores()
    pygame.quit()
    sys.exit()


def save_highscores():
    global highscores
    file = shelve.open('data/highscores', 'n')
    file['highscores'] = highscores
    file.close()


def load_highscores():
    global highscores
    file = shelve.open('data/highscores', 'r')
    highscores = file['highscores']
    file.close()


def playertouchingenemy(playerrect, enemies):
    for enemy in enemies:
        if playerrect.colliderect(enemy.rect):
            return True
    return False


def handle_keys():
    global players
    for event in pygame.event.get():
        if event.type == QUIT:
            terminate()

        if event.type == KEYDOWN:
            for player in players:
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
                global show_debug_info
                #toggle showing debug info
                show_debug_info = not(show_debug_info)
            if event.key == K_F4:
                global show_hitboxes
                #toggle drawing hitboxes of enemies
                show_hitboxes = not(show_hitboxes)

        if event.type == KEYUP:
            if event.key == K_ESCAPE:
                return 'exit'
            for player in players:
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

def game_over(show_highscores = True, save_highscores = True):
    #basic game over screen

    #first, save highscore
    if save_highscores == True:
        global score, highscores, score
        #add score to highscores
        highscores.append(score)
        #sort highscores in descending order
        highscores.sort(reverse = True)
        #get rid of lowest highscore
        highscores.pop(-1)
    #dim screen
    screen_dimmer = Dimmer()
    screen_dimmer.dim(darken_factor=200)
    #draw gameover text, including score
    font = pygame.font.Font(GAME_OVER_FONT, 58)
    draw_text('GAME OVER', font, screen, (WINDOW_WIDTH / 2), 20, color = RED, position = 'center')
    if  show_highscores == True:
        draw_text('Score:' + str(score), font, screen, (WINDOW_WIDTH / 2), 110, color = WHITE, position = 'center')
        #render highscores in a smaller font
        font = pygame.font.Font(GAME_OVER_FONT, 36)
        draw_text('HIGHSCORES', font, screen, WINDOW_WIDTH / 2, 150, color = WHITE, position = 'center')
        for i in range(len(highscores)):
            draw_text(str(highscores[i]), font, screen, WINDOW_WIDTH / 2, 180 + (i * 30), color = WHITE, position = 'center')
            if highscores[i] == score:
                draw_text("YOU ->" + " " * len(str(highscores[i])), font, screen, WINDOW_WIDTH / 2 - 20, 180 + (i * 30) + 10, color = WHITE, position = 'bottomright')
    pygame.display.update()
    time.sleep(1) # wait 1 second to stop people accidentally skipping this screen
    font = pygame.font.Font(GAME_OVER_FONT, 58)
    draw_text('Press Enter to play again.', font, screen, (WINDOW_WIDTH / 2), 60, color = WHITE, position = 'center') # tell the player to press a key to continue
    pygame.display.update()
    wait_for_keypress(certainkey=K_RETURN)
    screen_dimmer.undim()


def draw_text(text, font, surface, x, y, color = WHITE, background = None, position = "topleft"):
    #draws some text using font to the surface
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
        pygame.draw.rect(screen, background, textrect.inflate(2,2))
    surface.blit(textobj, textrect)
    return textrect.inflate(2,2) #for knowing where to redraw the background


def wait_for_keypress(certainkey=None):
    #wait until the player presses a key
    global clock
    pygame.event.clear() # clears the pygame events, ensuring it isn't going to register an old keypress
    while True:
        clock.tick(5) #5 frames a second; nothing's moving, so it should be ok: the player won't notice
        for event in pygame.event.get():
            if event.type == QUIT: #if player tries to close the window, terminate everything
                terminate()
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE: # pressing escape quits
                    main_menu()
                elif certainkey == None:
	            return #all other keys just return
	        elif event.key == certainkey:
	            return


def menu(title, options, titlefont, optionfont, titlecolor, optioncolor, selectedoptioncolor,
         space_between_options = 20, space_below_title = 50, enemies_background = False, option_selected = 0):
    #basic menu; title in titlecolor and titlefont, options in optioncolor and optionfont.
    #arrow keys are used to navigate and selected option is displayed in selectedoptioncolor
    global screen, background, clock, enemies
    enemies = []
    spawntimer = pygame.time.Clock()
    spawntime = 0
    screen_dimmer = Dimmer()

    while 1:
        time_since_last_frame = clock.tick(MAX_FPS)
        #clear screen with backgroundcolor
        screen_dimmer.undim()
        screen.blit(background, (0,0))

        if enemies_background:
            #draw background fanciness
            #scrolling enemies
            spawntime += spawntimer.tick()
            if spawntime >= ENEMY_SPAWNDELAY:
                spawntime -= ENEMY_SPAWNDELAY
                x = WINDOW_WIDTH - 10
                y = random.randint(0, WINDOW_HEIGHT)
                speed = random.uniform(ENEMY_MIN_SPEED,ENEMY_MAX_SPEED)
                textsprite = random.choice([str(random.randint(1,1024)) ])
                enemies.append(Enemy(x, y, speed, text = textsprite))
            for object in enemies[:]:
                object.update(time_since_last_frame)
                screen.blit(object.image, object.rect)
        #then, darken the screen without the title/options
        screen_dimmer.dim(darken_factor=200)
        #draw title and options
        draw_text(title, titlefont, screen, (WINDOW_WIDTH / 2), 50, color = titlecolor, position = 'center')
        for i in range(len(options)):
            if option_selected == i:
                draw_text(options[i], optionfont, screen, (WINDOW_WIDTH / 2), space_below_title + 30 + (i + 1) * space_between_options, color = selectedoptioncolor, position = 'center')
            else:
                draw_text(options[i], optionfont, screen, (WINDOW_WIDTH / 2), space_below_title + 30 + (i + 1) * space_between_options, color = optioncolor, position = 'center')
        #update display
        pygame.display.update()
        #handle keys for menu
        for event in pygame.event.get():
            if event.type == QUIT:
                terminate()

            if event.type == KEYDOWN:
                if event.key == K_UP or event.key == ord('w'):
                    option_selected -= 1
                    if option_selected < 0:
                        option_selected = len(options) - 1
                elif event.key == K_DOWN or event.key == ord('s'):
                    option_selected += 1
                    if option_selected > len(options) - 1:
                        option_selected = 0
                elif event.key == K_ESCAPE: # pressing escape quits

                    return "exit"
                elif event.key == K_RETURN:
                    return option_selected


def main_menu():
    while 1:
        choice = menu("THE RNG", ["Play", "Options", "Exit"],
        pygame.font.Font(MENU_FONT, 100), pygame.font.Font(MENU_FONT, 50), RED, WHITE, RED, space_between_options = 50, enemies_background = True)

        if choice == 0:
            while 1:
                arcade()

        elif choice == 1:
            options_menu()

        elif choice == 2: # 'exit'
            terminate()

        elif choice == 'exit': # if player presses ESC or tries to exit window
            terminate()


def options_menu():
    global show_hitboxes, hotseat_multiplayer
    global players_controls, types_of_controls
    option_selected = 0
    while 1:
        if show_hitboxes:
            hitboxes_shown = "True"
        else:
            hitboxes_shown = "False"
        if hotseat_multiplayer:
            hotseat_multiplayer_enabled = "True"
        else:
            hotseat_multiplayer_enabled = "False"

        if hotseat_multiplayer:
            #if hotseat, show controls for all players
            options = [
                      "Show hitboxes " + hitboxes_shown,
                      "Hotseat multiplayer " + hotseat_multiplayer_enabled,
                      "Player 1 controls = " + players_controls[0],
                      "Player 2 controls = " + players_controls[1],
                      "Player 3 controls = " + players_controls[2],
                      "Player 4 controls = " + players_controls[3],
                      "Back"
                      ]
            #indicate if any player is not playing
            for i in range(len(options[2:6])):
                if players_controls[i] == '':
                    options[i+2] = options[i+2][:9] + "Not Playing"

        else:
            options = [
                      "Show hitboxes " + hitboxes_shown,
                      "Hotseat multiplayer " + hotseat_multiplayer_enabled,
                      "Back"
                      ]
        choice = menu("Options",
                                  options,
                      pygame.font.Font(MENU_FONT, 50),
                      pygame.font.Font(MENU_FONT, 25),
                      RED, WHITE, RED,
                      option_selected = option_selected)

        if choice == 0:
            #toggle showing hitboxes
            show_hitboxes = not show_hitboxes
            option_selected = 0

        if choice == 1:
            #toggle hotseat multiplayer
            hotseat_multiplayer = not hotseat_multiplayer
            option_selected = 1

        elif choice == 2:
            option_selected = 2
            if hotseat_multiplayer:
                players_controls[0] = types_of_controls[types_of_controls.index(players_controls[0]) - 1]
            else:
                #exit to main menu
                break
        elif choice == 3:
            option_selected = 3
            players_controls[1] = types_of_controls[types_of_controls.index(players_controls[1]) - 1]

        elif choice == 4:
            option_selected = 4
            players_controls[2] = types_of_controls[types_of_controls.index(players_controls[2]) - 1]

        elif choice == 5:
            option_selected = 5
            players_controls[3] = types_of_controls[types_of_controls.index(players_controls[3]) - 1]

        elif choice == 6:
            break

        elif choice == 'exit':
            #same, exit to main menu
            break


def level_completed_screen():
    #basic level completed screen
    #dim screen
    screen_dimmer = Dimmer()
    screen_dimmer.dim(darken_factor=150)
    #draw gameover text, including score
    font = pygame.font.SysFont(None, 58)
    draw_text('LEVEL COMPLETE', font, screen, (WINDOW_WIDTH / 2), 20, color = BLUE, position = 'center')
    draw_text('Press Enter to continue.', font, screen, (WINDOW_WIDTH / 2), 60, color = WHITE, position = 'center')
    pygame.display.flip()
    wait_for_keypress(certainkey=K_RETURN)
    screen_dimmer.undim()


def arcade():
    global players, enemies, screen, score, clock, background, highscores, level, show_hitboxes, show_debug_info
    global hotseat_multiplayer
    global players_controls

    #init player(s) and enemies
    if hotseat_multiplayer:
        players = [Player(controls) for controls in players_controls if controls != '']
    else:
        players = [Player()]
    enemies = []
    #start at level 1
    level = 1

    #old textrects: used for filling background color
    old_textrects = []

    # Blit everything to the screen
    screen.blit(background, (0, 0))
    pygame.display.update()
    score = 0
    spawntime = 0
    clock.tick() # reset clock to 0
    time_until_new_level = LEVEL_LENGTH
    # main loop
    time.sleep(0.001) # sleep 1 millisecond at game start to prevent error when trying to divide by time_since_last_frame when it is zero
    game_is_over = False
    while game_is_over == False:
        # Make sure game doesn't run at more than MAX_FPS frames per second
        time_since_last_frame = clock.tick(MAX_FPS)

        event = handle_keys()
        if event == "exit": #exit to main menu
            main_menu()

        #check if player has hit an enemy using smaller hitbox
        for player in players:
            if playertouchingenemy(player.rect.inflate(-14, -14), enemies):
                #first, clear the player's sprite with background
                screen.blit(background, player.rect, player.rect)
                players.remove(player)
        #check if all players are dead or not
                #check seperate from death check to stop starting with no players
        if len(players) == 0:
            #show game over screen
            game_over()
            # break the loop
            game_is_over = True
        #new level if time
        time_until_new_level -= time_since_last_frame
        if time_until_new_level <= 0:
            level += 1
            time_until_new_level = LEVEL_LENGTH
            #spawn 'new level' enemy
            x = WINDOW_WIDTH - 10
            y = random.randint(50, WINDOW_HEIGHT - 50)
            speed = ENEMY_MAX_SPEED
            textsprite = "LEVEL " + str(level)
            enemyfont = pygame.font.Font(None, 50) # new level enemy uses pygame default font, due to munro having bad hitbox at large sizes
            enemies.append(Enemy(x, y, speed, text = textsprite, font = enemyfont, color = RED))
        #spawn enemies
        spawntime += time_since_last_frame
        #spawn enemies on right if SPAWN_DELAY time has passed
        if spawntime >= ENEMY_SPAWNDELAY / math.sqrt(level):
            spawntime -= ENEMY_SPAWNDELAY / math.sqrt(level)
            score += 1
            spawn_number_enemies(level)
                                           ###RENDER EVERYTHING###
        ###draw background color everywhere
        #windowsurface.fill(windowcolor)
        for player in players:
            screen.blit(background, player.rect, player.rect)
        #screen.blit(background, (0, 0))
        for enemy in enemies:
            screen.blit(background, enemy.rect, enemy.rect)
        for player in players:
            player.update(time_since_last_frame)

        for rect in old_textrects:
            screen.blit(background, rect, rect)

        old_textrects = []


        #draw score at top-middle of screen
        font = pygame.font.Font(GUI_FONT, 20)
        old_textrects.append(
            draw_text('Score:' + str(score), font, screen, WINDOW_WIDTH / 2, 20, color = RED, position = 'center')
            )


        if show_debug_info: #show all debug info if enabled

            #draw FPS at topright screen
            fps = 1.0 / time_since_last_frame * 1000
            old_textrects.append(
                draw_text('FPS:' + str(int(fps))  + '/' + str(MAX_FPS), font, screen, WINDOW_WIDTH - 100, 10, color = WHITE, background = BLACK, position = 'topleft')
                )

            #draw frame time: time it takes to render each frame
            old_textrects.append(
                draw_text('FT: ' + str(time_since_last_frame), font, screen, WINDOW_WIDTH - 100, 25, color = WHITE, background = BLACK, position = 'topleft')
                )

            #draw number of enemies on topright, for debug
            old_textrects.append(
                draw_text("Numbers:" + str(len(enemies)), font, screen, WINDOW_WIDTH - 100, 40, color = WHITE, background = BLACK, position = "topleft")
                 )

        #draw enemies in enemies
        for enemy in enemies[:]:
            enemy.update(time_since_last_frame)
            if show_hitboxes == True:
                #draw slightly darker then background rectangle
                pygame.draw.rect(screen, ([n * 0.8 for n in BACKGROUND_COLOR]), enemy.rect)
        for enemy in enemies[:]:
            screen.blit(enemy.image, enemy.rect)

        #draw player
        for player in players:
            screen.blit(player.image, player.rect)
            if show_hitboxes == True:
                #draw player rect
                pygame.draw.rect(screen, ([n * 0.8 for n in WHITE]), player.rect.inflate(-14, -14))

        #blit to screen
        pygame.display.update()

        pygame.event.pump()


def spawn_number_enemies(level):
    global enemies
    x = WINDOW_WIDTH - 10
    y = random.randint(0, WINDOW_HEIGHT)
    speed = random.uniform(ENEMY_MIN_SPEED,ENEMY_MAX_SPEED)
    textsprite = random.choice([str(random.randint(1,1024)) ])
    if level >= 4:
        #1/10 chance of erratic movement from level 4 onward
        erratic_movement = (1 == random.randint(1,10))
    else:
        erratic_movement = False
    if level >= 2:
        #1/10 chance of aimed movement from level 2 onward
        aimed = (1 == random.randint(1,10))
    else:
        aimed = False
    if level >= 2:
        #1/4 chance of starting rotated from level 2 onward
        start_rotated = (1 == random.randint(1,4))
    else:
        start_rotated = False
    #get random font
    size = random.randint(20,30)
    font = pygame.font.Font(get_random_font(), size)

    enemies.append(Enemy(x, y, speed,
        text = textsprite, font = font, erratic = erratic_movement, aimed = aimed, rotated = start_rotated))

    #spawn enemies on left to encourage player to run
    #and to look cool
    x = 10
    y = random.randint(0, WINDOW_HEIGHT)
    #fast as the average speed of an enemy
    speed = (ENEMY_MAX_SPEED + ENEMY_MIN_SPEED) / 2
    #1/2 chance of number, 1/2 chance of sprite
    textsprite = random.choice([str(random.randint(1,99999999)) ]) #, None])
    if level >= 3:
        #after level 3, half of the left enemies move erratically
        #this makes them look cooler and more terrifying
        erratic_movement = (1 == random.randint(1,2))
    else:
        erratic_movement = False
    enemies.append(Enemy(x, y, speed, text = textsprite, font = font, erratic = erratic_movement))


def main():
    global screen, background, clock, highscores, show_hitboxes, show_debug_info, hotseat_multiplayer
    global players_controls, types_of_controls
    # Initialise screen and window
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("The RNG")
    pygame.display.set_icon(load_image('icon.gif')[0])

    #init fps clock
    clock = pygame.time.Clock()

    # init background
    background = pygame.Surface(screen.get_size())
    background = background.convert()
    background.fill(BACKGROUND_COLOR)
    windowsurface.fill(windowcolor)

    #by default, enemy hitboxes are not shaded in
    show_hitboxes = False

    #and debug info is not shown
    show_debug_info = False

    #and the game is single player
    hotseat_multiplayer = False

    #default controls for each player
    types_of_controls = ['wasd', 'arrows', 'tfgh', 'ijkl', 'numpad', '' ] # if controls == '', player is not playing
    players_controls = ['wasd', 'arrows', 'tfgh', 'ijkl']

    # Display some text
    font = pygame.font.Font(GUI_FONT, 12)
    text = font.render("By Matthew Pfeiffer", 1, WHITE)
    textpos = text.get_rect()
    textpos.centerx = background.get_rect().centerx
    background.blit(text, textpos)

    #load highscores from data/highscores
    try:
        load_highscores()
    except:
        #get new highscores if it cannot load highscores
        highscores = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    main_menu()


if __name__ == '__main__':
    main()

