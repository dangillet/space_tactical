import gettext

localedir = './i18n'
translations = {'fr': gettext.translation('messages', localedir, languages=['fr_FR']),
                'en': gettext.translation('messages', localedir, languages=['en_US'])
                }
translations['fr'].install(True)

import cocos
from cocos.director import director

import pyglet

SCREEN_W, SCREEN_H = 1120, 630 #16/9 aspect ratio. Small enough for my laptop to work comfortably

import battle, gui


def load_resource():
    pyglet.resource.path = ['res', 'res/images', 'res/fonts']
    pyglet.resource.reindex()
    pyglet.resource.add_font('Classic Robot.ttf')
    action_man = pyglet.font.load('Classic Robot')
    pyglet.resource.add_font('Classic Robot Bold.ttf')
    action_man = pyglet.font.load('Classic Robot', bold=True)
    pyglet.resource.add_font('Classic Robot Italic.ttf')
    action_man = pyglet.font.load('Classic Robot', italic=True)
    
def main():
    # do_not_scale is set to True because otherwise the fonts get blurred
    # when the director applies some scaling.
    director.init(width = SCREEN_W, height=SCREEN_H, do_not_scale=True)
    load_resource()
    my_battle = battle.Battle()
    main_scene = cocos.scene.Scene(my_battle)

    director.run(main_scene)

if __name__ == '__main__':
    main()
