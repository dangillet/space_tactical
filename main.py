import cocos
from cocos.director import director
import battle
import grid

class ViewPort(object):
    width = 1500
    height = 800
    position = (50, 50)

def main():
    director.init(width = 1600, height=900)
    my_battle = battle.Battle()
    scroller = cocos.layer.ScrollingManager(ViewPort())
    scroller.add(my_battle.grid)
    main_scene = cocos.scene.Scene(scroller)
    director.show_FPS = True
    director.run(main_scene)

if __name__ == '__main__':
    main()
