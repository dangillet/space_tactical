import json, entity

class SpaceEncoder(json.JSONEncoder):
    "JSON encoder for the player class"
    def default(self, o):
        if isinstance(o, entity.Player):
            return {'name':o.name, 'fleet':o.fleet, 'inventory':o.inventory}
        elif isinstance(o, entity.Ship):
            mods = []
            for slot in o.slots.itervalues():
                mods.extend(self.default(slot) )
            return {'type':o.ship_type, 'mods':mods}
        elif isinstance(o, entity.Slot):
            return o.mods
        elif isinstance(o, entity.Weapon):
            mods = [o.name]
            for slot in o.slots.itervalues():
                mods.extend(self.default(slot) )
            return mods
        elif isinstance(o, entity.ModSpeed):
            return ['ModSpeed', o.level]
        elif isinstance(o, entity.ModShield):
            return ['ModShield', o.level, entity.EnergyType.names[o.energy_type]]
        elif isinstance(o, entity.ModHull):
            return ['ModHull', o.level]
        elif isinstance(o, entity.ModWeapon):
            return ['ModWeapon', o.level]
        else:
            return super(SpaceEncoder, self).default(o)
