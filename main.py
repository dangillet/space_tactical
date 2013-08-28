import cocos
from cocos.director import director
import grid
import entity

class Battle(object):
    def __init__(self):
        self.players = []
        #How many players?
        for i in range(2):
            player = entity.Player("Player %d" % i)
            self.players.append(player)
            # How many ships ?
            for _ in range(2):
                ship = entity.Ship("ship.png")
                ship.scale = float(grid.CELL_WIDTH) / ship.width
                player.add_ship(ship)
        self.grid = grid.GridLayer(self.players)
        
def main():
    director.init(width = 1600, height=900)
    battle = Battle()
    main_scene = cocos.scene.Scene(battle.grid)
    director.show_FPS = True
    director.run (main_scene)

if __name__ == '__main__':
    main()
