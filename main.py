import cocos
from cocos.director import director
import battle

        
def main():
    director.init(width = 1600, height=900)
    my_battle = battle.Battle()
    scroller = cocos.layer.ScrollingManager()
    scroller.add(my_battle.grid)
    scroller.position = (50,50)
    scroller.anchor = (50, 50)
    main_scene = cocos.scene.Scene(scroller)
    director.show_FPS = True
    director.run (main_scene)

if __name__ == '__main__':
    main()
