import random, json

import cocos

from pyglet import event
import pyglet.text as text

import main

class Damage(object):
    """
    Object that has a min and max value and gives a number between these
    2 values
    """
    def __init__(self, minimum, maximum):
        self.min = minimum
        self.max = maximum
    
    def __repr__(self):
        return "%d-%d" % (self.min, self.max)
    
    def roll(self):
        return random.randint(self.min, self.max)

class EnergyType(object):
    "Class holding the different energy types."
    # Damage Type provided here for translation.
    [_("URANIUM"), _("PLASMA"), _("SONIC"), _("WARP")]
    
    names = ["URANIUM", "PLASMA", "SONIC", "WARP"]
    
    @classmethod
    def name(cls, index):
        "Returns the translated energy_type name"
        return _(cls.names[index])

class Boost(object):
    def __init__(self, ship):
        self.ship = ship
    
    def use(self):
        raise NotImplemented

    def reverse(self):
        raise NotImplemented

class BoostSpeed(Boost):
    def __init__(self, ship):
        super(BoostSpeed, self).__init__(ship)
        self.used = False
        self.name = _("Boost Speed")
    
    def use(self):
        self.used = True
        self.ship.speed += 2
        self.ship.dispatch_event("on_speed_change")
    
    def reverse(self):
        self.used = False
        self.ship.speed -= 2

class BoostShield(Boost):
    def __init__(self, ship):
        super(BoostShield, self).__init__(ship)
        self.used = False
        self.name = _("Boost Shield")
    
    def use(self):
        self.used = True
        for energy_type in self.ship.shield.iterkeys():
            self.ship.shield[energy_type] += 5
        self.ship.dispatch_event("on_change")
        self.used = True
    
    def reverse(self):
        self.used = False
        for energy_type in self.ship.shield.iterkeys():
            self.ship.shield[energy_type] -= 5
        self.used = False

class Weapon(object):
    """
    Weapon with all its caracteristics. 
    """
    def __init__( self, weapon_type, weapon_range, precision, heating, cooldown,
                  reliability, dmg_type, dmg):
        "dmg is a list with min and max values."
        self.ship = None
        self.weapon_type = weapon_type
        self.range = weapon_range
        self.precision = precision
        self.heating = heating
        self.cooldown = cooldown
        self.temperature = 0
        self.reliability = reliability
        self.energy_type = dmg_type # index of the EnergyType.names list
        self.damage = Damage(dmg[0], dmg[1])
        self.is_inop = False
    
    def display(self):
        "Display the weapon in the formatted text style"
        return _("""
{color [255, 0, 0, 255]}%s {color [255, 255, 255, 255]} {}
{.tab_stops [150]}
Energy type: %s{#x09}Range: %d{}
Precision: %d%%{#x09}Damage: %r {}
Temperature: %d{#x09}Heating: %d {}
Reliability: %d%%{}
""") % (self.weapon_type, EnergyType.name(self.energy_type), self.range,
        self.precision*100, self.damage, self.temperature, self.heating, self.reliability*100)
    
    def __repr__(self):
        return """
%s
Energy type: %s\tRange: %d
Precision: %d%%\tDamage: %r
Temperature: %d\tHeating: %d
Reliability: %d%%
""" % (self.weapon_type, EnergyType.name(self.energy_type), self.range,
        self.precision*100, self.damage, self.temperature, self.heating, self.reliability*100)

    def hit(self):
        "Returns True if the weapon hit."
        return random.random() <= self.precision
    
    def fumble(self):
        "Returns True if the weapon jammed."
        if random.random() > self.reliability:
            self.is_inop = True
            return True
        return False
    
    def fire(self):
        self.temperature += self.heating
    
    def reset_turn(self):
        self.temperature = max(0, self.temperature - self.cooldown)

class Ship(cocos.sprite.Sprite):
    def __init__( self, image, ship_type, speed, hull,
                shield, weapons):
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
        # shield = {energy_idx:protection}
        self.shield = shield
        self.weapons = []
        self.weapon_idx = None
        for weapon in weapons:
            self.add_weapon(weapon, weapon is weapons[-1])
        self.boosts = [BoostShield(self),
                    BoostSpeed(self)]
        self.boost_used = False
        
        self.turn_completed = False
        self.move_completed = False
        self.attack_completed = False

    
    def display(self):
        "Display the ship and its weapons in the formatted text style"
        shield = " - ".join(["%d/%s" % (pr, EnergyType.name(en_idx)) for en_idx, pr in self.shield.iteritems() if pr != 0])
        s =  _("""
{font_name 'Classic Robot'}{font_size 16}{color [255, 0, 0, 255]}{italic True}%s{italic False}{}
{font_size 12}{.tab_stops [90, 170]}{color [255, 255, 255, 255]}Speed: %d{#x09}Hull: %d{#x09}Shield: %s
""") % (self.ship_type, self.speed, self.hull, shield)
        if self.weapon_idx is not None:
            s += _("""
{underline [255, 255, 255, 255]}Weapon{underline None}: {}
%s""") % (self.weapons[self.weapon_idx].display())
        return s
    
    def __repr__(self):
        shield = " - ".join(["%d/%s" % (pr, EnergyType.names[en_idx]) for en_idx, pr in self.shield.iteritems()])
        s = """
%s
Speed: %d\tHull: %d\tShield: %s
""" % (self.ship_type, self.speed, self.hull, shield)
        if self.weapon_idx is not None:
            s += """
    Weapon:
    %s""" % (self.weapons[self.weapon_idx])
        return s
        
    def add_weapon(self, weapon, select=True):
        "Add a weapon to the ship"
        weapon.ship = self
        self.weapons.append(weapon)
        if select:
            self.weapon_idx = len(self.weapons)-1
    
    def change_weapon(self, idx):
        self.weapon_idx = idx
        self.dispatch_event("on_weapon_change")

    def use_boost(self, idx):
        if not self.boost_used:
            self.boosts[idx].use()
            self.boost_used = True
            self.dispatch_event("on_boost_use")
            
    def reset_turn(self):
        self.turn_completed = False
        self.move_completed = False
        self.attack_completed = False
        for weapon in self.weapons:
            weapon.reset_turn()
        if self.boost_used:
            [boost.reverse() for boost in self.boosts if boost.used]
            self.boost_used = False
    
    def attack(self, defender):
        weapon = self.weapons[self.weapon_idx]
        weapon.fire()
        self.dispatch_event("on_change")
        if weapon.fumble():
            self.weapon_idx = None
            self.dispatch_event("on_weapon_jammed", weapon)
        elif weapon.hit():
            dmg = weapon.damage.roll()
            defender.take_damage(dmg, weapon.energy_type)
        else:
            self.dispatch_event("on_missed")
            
    
    def take_damage(self, damage, energy_type):
        # If our shield is against the weapon energy type, use it
        protection = self.shield.get(energy_type, 0)
        # Take min 0 damage if shield is greater than dmg
        damage = max(0, damage - protection)
        self.hull -= damage
        self.dispatch_event("on_damage", self, damage)
        if self.hull <= 0:
            self.dispatch_event("on_destroyed", self)
            self.player.destroy_ship(self)

Ship.register_event_type("on_change")
Ship.register_event_type("on_weapon_jammed")
Ship.register_event_type("on_damage")
Ship.register_event_type("on_destroyed")
Ship.register_event_type("on_missed")
Ship.register_event_type("on_weapon_change")
Ship.register_event_type("on_speed_change")
Ship.register_event_type("on_boost_use")

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
            ship.reset_turn()
    
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
                     v['heating'],
                     v['cooldown'],
                     v['reliability'],
                     EnergyType.names.index(v['energy_type']), # The index of the energy type in the list of energies
                     v['damage'],
                    )
            # Read all the ships
            for v in data['ships']:
                # Read the different shields on the ship
                shields = {energy_idx:0 for energy_idx, _ in enumerate(EnergyType.names)}
                for shield in v['shield']:
                    energy_idx = EnergyType.names.index(shield['energy_type'])
                    shields[energy_idx] = shield['pr']
                self.ships[v['ship_type']] = \
                    (v['image'].encode('utf-8'), # cocos.Sprite needs a str, not a unicode
                     v['ship_type'],
                     v['speed'],
                     v['hull'],
                     shields,
                     v['weapons']
                    )
    
    def create_ship(self, ship_type):
        "Create a new ship of type ship_type"
        # The 5th element in the ship definition is the list of weapons
        weapons = []
        for weapon_type in self.ships[ship_type][5]:
            weapon_args = self.weapons[weapon_type]
            weapons.append(Weapon(*weapon_args))
        # Take all args except the last, and replace it with the constructed weapon
        return Ship(*self.ships[ship_type][:-1], weapons=weapons)
    
if __name__ == '__main__':
    from cocos.director import director
    
    director.init(width = 1600, height=900)
    main.load_resource()
    ships_factory = ShipFactory()

    for ship_type in ships_factory.ships.iterkeys():
        print ships_factory.create_ship(ship_type)
