import cocos

class Ship(cocos.sprite.Sprite):
    def __init__( self, image, player=None, distance= 5):
         """Initialize the Ship
            player: Player
                The player controlling this ship
            sprite: cocos.sprite.Sprite
                The sprite representing this ship
         """
         super(Ship, self).__init__(image)
         self.player = player
         self.distance = distance
         self.weapon_range = 5
         self.turn_completed = False
         self.move_completed = False
         self.attack_completed = False

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
        for ship in self.fleet:
            if not ship.turn_completed:
                return False
        return True
    
    def reset_ships_turn(self):
        """Reset the ships turn_completed"""
        for ship in self.fleet:
            ship.turn_completed = False
            ship.move_completed = False
            ship.attack_completed = False

class Asteroid(cocos.sprite.Sprite):
    def __init__(self, pos):
         super(Asteroid, self).__init__("asteroid.png", position=pos)
