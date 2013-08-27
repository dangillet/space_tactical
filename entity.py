import cocos

class Ship(cocos.sprite.Sprite):
    def __init__( self, image, player=None):
         """Initialize the Ship
            player: Player
                The player controlling this ship
            sprite: cocos.sprite.Sprite
                The sprite representing this ship
         """
         super(Ship, self).__init__(image)
         self.player = player
         self.turn_completed = False

class Player(object):
    def __init__(self, name):
        """Initialize the Player
            name: str
                The player name
            fleet: list
                List of ships
         """
        self.name = name
        self.fleet = []
    
    def add_ship(self, ship):
        """Add a ship to the fleet"""
        ship.player = self
        self.fleet.append(ship)
    
    def turn_completed(self):
        """Test if all ships have played"""
        completed = True
        for ship in self.fleet:
            completed = completed and ship.turn_completed
        return completed
    
    def reset_ships_turn(self):
        """Reset the ships turn_completed"""
        for ship in self.fleet:
            ship.turn_completed = False
