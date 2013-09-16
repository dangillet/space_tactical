import random, json
import cocos

import main

class Damage(object):
    def __init__(self, minimum, maximum):
        self.min = minimum
        self.max = maximum
    
    def __repr__(self):
        return "%d-%d" % (self.min, self.max)
    
    def roll(self):
        return random.randint(self.min, self.max)

class Weapon(object):
    #Damage Type
    energy_type=[_("URANIUM"), _("PLASMA"), _("SONIC"), _("WARP")]
    
    def __init__( self, weapon_type, weapon_range, precision, temp,
                  reliability, dmg_type, dmg):
        "dmg is a list with min and max values."
        self.ship = None
        self.weapon_type = weapon_type
        self.range = weapon_range
        self.precision = precision
        self.temperature = temp
        self.reliability = reliability
        self.energy_type = dmg_type
        self.damage = Damage(dmg[0], dmg[1])
    
    def show(self):
        return _("""
{color [255, 0, 0, 255]}%s {color [255, 255, 255, 255]} {}
Energy type: %s {}
{.tab_stops [120]}
damage: %r{#x09}range: %d {}
precision: %d%%{#x09}temperature: %d {}
reliability: %d%%{}
""") % (self.weapon_type, self.energy_type, self.damage, 
             self.range, self.precision*100, self.temperature, self.reliability*100)
    
    def __repr__(self):
        return """
%s
Energy type: %s
damage: %r\trange: %d
precision: %d%%\ttemperature: %d
reliability: %d%%
""" % (self.weapon_type, self.energy_type, self.damage, 
             self.range, self.precision*100, self.temperature, self.reliability*100)

    def hit(self):
        "Returns True if the weapon hit."
        return random.random() <= self.precision

class Ship(cocos.sprite.Sprite):
    def __init__( self, image, ship_type="Fighter", speed= 5, hull= 10,
                shield=2, weapon=None):
        """
            Initialize the Ship
            player: Player
            The player controlling this ship
            sprite: cocos.sprite.Sprite
            The sprite representing this ship
        """
        super(Ship, self).__init__(image)
        self.player = None
        self.ship_type = ship_type
        self.speed = speed
        self.hull = hull
        self.shield = shield
        self.add_weapon(weapon)
        
        self.turn_completed = False
        self.move_completed = False
        self.attack_completed = False
    
    def show(self):
        shield = " - ".join(["%d/%s" % (pr, en_type) for en_type, pr in self.shield.iteritems()])
        s =  _("""
{font_name 'Classic Robot'}{font_size 18}{color [255, 0, 0, 255]}{italic True}%s{italic False}{}
{font_size 14}{.tab_stops [90, 170]}{color [255, 255, 255, 255]}Speed: %d{#x09}Hull: %d{#x09}Shield: %s
""") % (self.ship_type, self.speed, self.hull, shield)
        s += _("""
{underline [255, 255, 255, 255]}Weapon{underline None}: {}
%s""") % (self.weapon.show())
        return s
    
    def __repr__(self):
        shield = " - ".join(["%d/%s" % (pr, en_type) for en_type, pr in self.shield.iteritems()])
        s = """
%s
Speed: %d\tHull: %d\tShield: %s
""" % (self.ship_type, self.speed, self.hull, shield)
        s += """
Weapon:
%s""" % (self.weapon)
        return s
        
    def add_weapon(self, weapon):
        "Add a weapon to the ship"
        self.weapon = weapon
        self.weapon.ship = self
    
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
        "Add a ship to the fleet"
        ship.player = self
        self.fleet.append(ship)
    
    def destroy_ship(self, ship):
        "Destroys a ship from the fleet"
        self.fleet.remove(ship)
    
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
    
    def end_round(self):
        """Ends the round of the player"""
        for ship in self.fleet:
            ship.turn_completed = True

class Asteroid(cocos.sprite.Sprite):
    def __init__(self, image, *args, **kwargs):
         super(Asteroid, self).__init__(image, *args, **kwargs)
         frame_num = len(image.frames)
         self._frame_index = random.randint(0, frame_num-1)
         

class ShipFactory(object):
    def __init__(self):
        self.load_ship_types()

    def load_ship_types(self):
        "Loads the definition of the ship types"
        with open("ships_catalog.json") as f:
            self.ships = {}
            self.weapons = {}
            data = json.load(f)
            # Read all the weapons
            for v in data['weapons']: # v for value
                self.weapons[v['weapon_type']] = \
                    (v['weapon_type'],
                     v['range'],
                     v['precision'],
                     v['temperature'],
                     v['reliability'],
                     # Translate the energy type
                     _(v['energy_type']),
                     v['damage'],
                    )
            # Read all the ships
            for v in data['ships']:
                # Read the different shields on the ship
                shields = {}
                for shield in v['shield']:
                    shields[_(shield['energy_type'])] = shield['pr']
                self.ships[v['ship_type']] = \
                    (v['image'].encode('utf-8'), # cocos.Sprite needs a str, not a unicode
                     v['ship_type'],
                     v['speed'],
                     v['hull'],
                     shields,
                     v['weapon']
                    )
    
    def create_ship(self, ship_type):
        "Create a new ship of type ship_type"
        # The 5th element in the ship definition is the weapon
        weapon_type = self.ships[ship_type][5]
        weapon_args = self.weapons[weapon_type]
        weapon = Weapon(*weapon_args)
        # Take all args except the last, and replace it with the constructed weapon
        return Ship(*self.ships[ship_type][:-1], weapon=weapon)
    
if __name__ == '__main__':
    from cocos.director import director
    
    director.init(width = 1600, height=900)
    main.load_resource()
    ships_factory = ShipFactory()

    for ship_type in ships_factory.ships.iterkeys():
        print ships_factory.create_ship(ship_type)
