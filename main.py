import cocos
from cocos.director import director
import grid
import entity

def main():
    director.init(width = 1600, height=900)
    players = []
    
    #How many players?
    for i in range(2):
        player = entity.Player("Player %d" % i)
        players.append(player)
        # How many ships ?
        for _ in range(2):
            ship = entity.Ship("ship.png")
            ship.scale = float(grid.CELL_WIDTH) / ship.width
            player.add_ship(ship)

    grid_layer = grid.GridLayer (players)
    main_scene = cocos.scene.Scene(grid_layer)
    director.show_FPS = True
    director.run (main_scene)

if __name__ == '__main__':
    main()
