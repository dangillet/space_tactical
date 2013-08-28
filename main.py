import cocos
from cocos.director import director
import battle

        
def main():
    director.init(width = 1600, height=900)
    my_battle = battle.Battle()
    main_scene = cocos.scene.Scene(my_battle.grid)
    director.show_FPS = True
    director.run (main_scene)

if __name__ == '__main__':
    main()
