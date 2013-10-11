import random, json, fractions, abc, collections

import cocos
from cocos.text import *

from pyglet import event
from pyglet.gl import *

import main

COOLDOWN = 100

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

class Mod(object):
    __metaclass__ = abc.ABCMeta
    def __init__(self, parent=None):
        self.parent = parent
    
    @abc.abstractmethod
    def use(self):
        return

    @abc.abstractmethod
    def reverse(self):
        return
    
    @abc.abstractproperty
    def name(self):
        return ''

class ModSpeed(Mod):
    def __init__(self, level, sf):
        "sf: ShipFactory"
        super(ModSpeed, self).__init__()
        self.level = level
        self.type = "mobility"
    
    @property
    def name(self):
        return " ".join( (_("Speed"), "+%i" % (self.level)) )
    
    def use(self):
        self.parent.speed += self.level
    
    def reverse(self):
        self.parent.speed -= self.level

class ModWeapon(Mod):
    def __init__(self, level, sf):
        super(ModWeapon, self).__init__()
        self.level = level
        self.type = "mod_weapon"
    
    @property
    def name(self):
        return _("Weapon Mod")
    
    def use(self):
        weapon = self.parent
        weapon.damage.min += self.level * 2
        weapon.damage.max += self.level * 2
        # We want the rof to increase according to this serie
        # 1/2..2/3..3/4..4/5..5/6..n/n+1
        # To go from n-1/n to n/n+1 you need to add 1/(n*(n+1))
        n = weapon.rof.denominator
        rof_increase = fractions.Fraction(numerator=1, 
                                denominator=n*(n+1) )
        weapon.rof += rof_increase
        weapon.heating = float(100/weapon.rof)
        weapon.reliability -= 0.02 * self.level
    
    def reverse(self):
        weapon = self.parent
        weapon.damage.min -= self.level * 2
        weapon.damage.max -= self.level * 2
        n = weapon.rof.denominator
        rof_decrease = fractions.Fraction(numerator=1, 
                                denominator=n*(n-1) )
        weapon.rof -= rof_decrease
        weapon.heating = float(100/weapon.rof)
        weapon.reliability += 0.02 * self.level

class ModShield(Mod):
    def __init__(self, level, energy_type, sf):
        super(ModShield, self).__init__()
        self.level = level
        self.energy_type = EnergyType.names.index(energy_type)
        self.pr = level * 2
        self.type = "defense"
        
    @property
    def name(self):
        return " ".join( (_("Shield"),
                "%i/%s" %(self.pr, EnergyType.name(self.energy_type))) )
    
    def use(self):
        if self.energy_type in self.parent.shield:
            self.parent.shield[self.energy_type] += self.pr
        else:
            self.parent.shield[self.energy_type] = self.pr
    
    def reverse(self):
        if self.parent.shield[self.energy_type] == self.pr:
            del self.parent.shield[self.energy_type]
        else:
            self.parent.shield[self.energy_type] -= self.pr

class ModHull(Mod):
    def __init__(self, level, sf):
        super(ModHull, self).__init__()
        self.level = level
        self.hull_increase = self.level * 5
        self.type = "defense"
        
    @property
    def name(self):
        return " ".join( (_("Hull"),
                "+%i" %(self.hull_increase)) )
    
    def use(self):
        self.parent.hull += self.hull_increase
    
    def reverse(self):
        self.parent.hull -= self.hull_increase

class Slot(event.EventDispatcher):
    def __init__(self, parent, slot_type, max_count):
        super(Slot, self).__init__()
        self.parent = parent
        self.type = slot_type
        self.max_count = max_count
        self.mods = []
    
    def add_mod(self, mod):
        if len(self.mods) == self.max_count:
            return False
        mod.parent = self.parent
        self.mods.append(mod)
        mod.use()
        self.dispatch_event("on_change")
        return True
    
    def remove_mod(self, mod):
        # Ships should have at least one weapon with reliability 100%
        if mod.type == "weapon" and not [weapon for weapon in self.mods if 
                (weapon != mod and weapon.reliability == 1.0)]:
            return False
        if mod not in self.mods:
            return False
        self.mods.remove(mod)
        mod.reverse()
        mod.parent = None
        self.dispatch_event("on_change")
        return True
    
    def remove_all_mods(self):
        for mod in self.mods:
            self.mods.remove(mod)
            mod.reverse()
            mod.parent = None

Slot.register_event_type("on_change")

class Weapon(Mod):
    """
    Weapon with all its caracteristics. 
    """
    def __init__( self, weapon_type, slots, weapon_range, precision, rof,
                  reliability, dmg_type, dmg):
        "dmg is a list with min and max values."
        super(Weapon, self).__init__()
        self.type = "weapon"
        self._name = weapon_type
        self.range = weapon_range
        self.precision = precision
        self.rof = rof
        self.heating = float(100 / rof)
        self.temperature = 0
        self.reliability = reliability
        self.energy_type = dmg_type # index of the EnergyType.names list
        self.damage = Damage(dmg[0], dmg[1])
        self.slots = { slot_type: Slot(self, slot_type, max_count) 
                        for slot_type, max_count in slots.iteritems() }
        
        self.is_inop = False
    
    @property
    def name(self):
        return self._name
    
    def use(self):
        pass
    
    def reverse(self):
        pass
    
    def __repr__(self):
        return """
%s
Energy type: %s\tRange: %d
Precision: %d%%\tDamage: %r
Temperature: %d\tHeating: %d
Reliability: %d%%
""" % (self.name, EnergyType.name(self.energy_type), self.range,
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
        self.temperature = max(0, self.temperature - COOLDOWN)
    
    def add_mod(self, mod):
        if self.slots[mod.type].add_mod(mod):
            if self.parent is not None:
                self.parent.dispatch_event("on_change")
            return True
        return False
    
    def remove_mod(self, mod):
        if mod.type not in self.slots:
            return False
        if self.slots[mod.type].remove_mod(mod):
            self.parent.dispatch_event("on_change")
            return True
        return False

class Boost(Mod):
    __metaclass__ = abc.ABCMeta
    def __init__(self, ship):
        super(Boost, self).__init__(ship)
        self.used = False
    
    def use(self):
        self.used = True
    
    def reverse(self):
        self.used = False
    
    @abc.abstractproperty
    def name(self):
        return ''

class BoostSpeed(Boost):
    def __init__(self, ship):
        super(BoostSpeed, self).__init__(ship)
    
    @property
    def name(self):
        return _("Boost Speed")
    
    def use(self):
        super(BoostSpeed, self).use()
        self.ship.speed += 2
        self.ship.dispatch_event("on_speed_change")
    
    def reverse(self):
        super(BoostSpeed, self).reverse()
        self.ship.speed -= 2

class BoostWeaponDamage(Boost):
    def __init__(self, ship):
        super(BoostWeaponDamage, self).__init__(ship)
    
    @property
    def name(self):
        return _("Boost Weapon")
        
    def use(self):
        super(BoostWeaponDamage, self).use()
        damage = self.ship.weapon.damage
        damage.min += 5
        damage.max += 5
        self.ship.dispatch_event("on_change")
    
    def reverse(self):
        super(BoostWeaponDamage, self).reverse()
        damage = self.ship.weapon.damage
        damage.min -= 5
        damage.max -= 5

class BoostShield(Mod):
    def __init__(self, ship):
        super(BoostShield, self).__init__(ship)
    
    @property
    def name(self):
        return _("Boost Shield")
    
    def use(self):
        super(BoostShield, self).use()
        for energy_type in self.ship.shield.iterkeys():
            self.ship.shield[energy_type] += 5
        self.ship.dispatch_event("on_change")
    
    def reverse(self):
        super(BoostShield, self).reverse()
        for energy_type in self.ship.shield.iterkeys():
            self.ship.shield[energy_type] -= 5

class Ship(cocos.sprite.Sprite):
    def __init__( self, image, ship_type, slots, speed, hull, shield):
        """
            Initialize the Ship
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
        self.shield = shield.copy()
        self.boosts = [BoostShield(self),
                    BoostSpeed(self),
                    BoostWeaponDamage(self)]
        self.boost_used = False
        self.slots = { slot_type: Slot(self, slot_type, max_count) 
                        for slot_type, max_count in slots.iteritems() }
        self.weapon_idx = 0
        self._move_completed = False
        self._attack_completed = False
        
        self.label = Label('',
                            font_name = "Classic Robot",
                            font_size = 10,
                            color = (0, 200, 0, 255),
                            anchor_y = "center",
                            anchor_x = "center",
                            x = 20,
                            y = -20)
    
    def draw(self):
        super(Ship, self).draw()
        glPushMatrix()
        glTranslatef( self.position[0], self.position[1], 0 )
        glTranslatef( self.transform_anchor_x, self.transform_anchor_y, 0 )
        if self.transform_anchor != (0,0):
            glTranslatef(
                - self.transform_anchor_x,
                - self.transform_anchor_y,
                0 )
        
        self.label.draw()
        glPopMatrix()
        
    @property
    def move_completed(self):
        return self._move_completed
    
    @move_completed.setter
    def move_completed(self, value):
        if value is True:
            self.label.element.text = self.label.element.text.replace('M','')
        self._move_completed = value
    
    @property
    def attack_completed(self):
        return self._attack_completed
    
    @attack_completed.setter
    def attack_completed(self, value):
        if value is True:
            self.label.element.text = self.label.element.text.replace('A','')
        self._attack_completed = value
    
    @property
    def weapon(self):
        if self.weapon_idx is not None:
            return self.slots['weapon'].mods[self.weapon_idx]
        else:
            return None

    def __repr__(self):
        shield = " - ".join(["%d/%s" % (pr, EnergyType.names[en_idx]) for en_idx, pr in self.shield.iteritems()])
        s = """
%s
Speed: %d\tHull: %d\tShield: %s
""" % (self.ship_type, self.speed, self.hull, shield)
        if self.weapon is not None:
            s += """
Weapon:
%s""" % (self.weapon)
        return s
    
    # Need to change this to a setter of self.weapon
    def change_weapon(self, idx):
        self.weapon_idx = idx
        self.dispatch_event("on_weapon_change")

    def add_mod(self, mod):
        if self.slots[mod.type].add_mod(mod):
            self.dispatch_event("on_change")
            return True
        return False
    
    def remove_mod(self, mod):
        if mod.type not in self.slots:
            if mod.parent in self.slots['weapon'].mods: # Then this is a mod_weapon
                return mod.parent.remove_mod(mod)
            return False
        if self.slots[mod.type].remove_mod(mod):
            self.dispatch_event("on_change")
            return True
        return False
        
    def use_boost(self, idx):
        if not self.boost_used:
            self.boosts[idx].use()
            self.boost_used = True
            self.dispatch_event("on_boost_use")
        
    def reset_turn(self):
        self.move_completed = False
        self.attack_completed = False
        self.label.element.text = 'MA'
        for weapon in self.slots['weapon'].mods:
            weapon.reset_turn()
        if self.boost_used:
            [boost.reverse() for boost in self.boosts if boost.used]
            self.boost_used = False
    
    def attack(self, defender):
        weapon = self.weapon
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
        self.inventory = []
    
    def add_ship(self, ship):
        "Add a ship to the fleet"
        ship.player = self
        self.fleet.append(ship)
    
    def destroy_ship(self, ship):
        "Destroys a ship from the fleet"
        self.fleet.remove(ship)
    
    def reset_ships_turn(self):
        """Reset the ships move and attack completed"""
        for ship in self.fleet:
            ship.reset_turn()
    
    def on_end_of_turn(self):
        "Any logic happening when the turns end."
        for ship in self.fleet:
            ship.label.element.text = ''
    
    def add_mod_to_inventory(self, mod):
        """
        Add mod to the inventory. If mod has sub-mods, detach them from the mod
        and add them to the inventory.
        """
        if hasattr(mod, "slots"):
            for slot in mod.slots.itervalues():
                for _mod in slot.mods:
                    slot.remove_mod(_mod)
                    self.add_mod_to_inventory(_mod)
        self.inventory.append(mod)
    
    @staticmethod
    def load():
        "Loads the player from player.json file"
        with open("player.json") as f:
            ships_factory = ShipFactory()
            data = json.load(f)
            player = Player(data['name'])
            for ship_data in data['fleet']:
                    quantity = ship_data.get("count", 1)
                    for i in range(quantity):
                        mods = ship_data.get("mods", [])
                        ship = ships_factory.create_ship(ship_data['type'],
                                                                mods =mods)
                        player.add_ship(ship)
            
            for mod in data['inventory']:
                player.inventory.append(ships_factory.create_mod(mod))
            return player
        return None

class Asteroid(cocos.sprite.Sprite):
    def __init__(self, image, *args, **kwargs):
         super(Asteroid, self).__init__(image, *args, **kwargs)
         frame_num = len(image.frames)
         self._frame_index = random.randint(0, frame_num-1)

class DifficultTerrain(cocos.sprite.Sprite):
    def __init__(self, image, *args, **kwargs):
         super(DifficultTerrain, self).__init__(image, *args, **kwargs)

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
                     v['slots'],
                     v['range'],
                     v['precision'],
                     fractions.Fraction(v['rate of fire']),
                     v['reliability'],
                     # The index of the energy type in the list of energies
                     EnergyType.names.index(v['energy_type']), 
                     v['damage']
                    )
            # Read all the ships
            for v in data['ships']:
                # Read the different shields on the ship
                shields = {}
                for shield in v['shield']:
                    energy_idx = EnergyType.names.index(shield['energy_type'])
                    shields[energy_idx] = shield['pr']
                self.ships[v['ship_type']] = \
                    (v['image'].encode('utf-8'), # cocos.Sprite needs a str, not a unicode
                     v['ship_type'],
                     v['slots'],
                     v['speed'],
                     v['hull'],
                     shields,
                     v['weapons']
                    )
        # And load the different mods classes
        self.ModKlasses = [ModSpeed, ModShield, ModHull, ModWeapon]
    
    def create_ship(self, ship_type, mods=[]):
        "Create a new ship of type ship_type with its mods"
        # Only if there are no mods, we equip the ship with the default weapons
        if not mods:
            # The last element in the ship definition is the list of weapons
            mods = self.ships[ship_type][-1]
        # Take all args except the last
        ship = Ship(*self.ships[ship_type][:-1])
        # Apply mods
        for mod in mods or []: # If mods is None, we pass an empty list
            mod_instance = self.create_mod(mod)
            ship.add_mod(mod_instance)
        return ship
    
    def create_mod(self, mod):
        "Creates a mod which could be a weapon"
        mod = collections.deque(mod) #Need a copy as we alter the list
        mod_name = mod.popleft()
        for ModKlass in self.ModKlasses:
            if ModKlass.__name__ == mod_name:
                mod_instance = ModKlass(*mod, sf=self)
                return mod_instance
        # Mod name not found in ModKlass, so it should be a weapon
        if mod_name in self.weapons:
            weapon = self.create_weapon(mod_name)
            # The remainder of the list might contain mod_weapons
            for _mod in mod:
                weapon.add_mod(self.create_mod(_mod))
            return weapon
    
    def create_weapon(self, weapon_type):
        weapon_args = self.weapons[weapon_type]
        return Weapon(*weapon_args)
    
if __name__ == '__main__':
    from cocos.director import director
    
    director.init(width = 1600, height=900)
    main.load_resource()
    ships_factory = ShipFactory()

    for ship_type in ships_factory.ships.iterkeys():
        print ships_factory.create_ship(ship_type)
