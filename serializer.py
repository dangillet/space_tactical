import json, entity

class SpaceEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, entity.Player):
            return {'name':o.name, 'fleet':o.fleet, 'inventory':o.inventory}
        elif isinstance(o, entity.Ship):
            mods = []
            for slot_type, slot in o.slots.iteritems():
                mods.extend(self.default(slot) )
            return {'type':o.ship_type, 'mods':mods}
        elif isinstance(o, entity.Slot):
            return o.mods
        elif isinstance(o, entity.Weapon):
            return o.name
        elif isinstance(o, entity.ModSpeed):
            return ['ModSpeed', o.level]
        elif isinstance(o, entity.ModShield):
            return ['ModShield', o.level, entity.EnergyType.names[o.energy_type], o.pr]
        
        else:
            return super(SpaceEncoder, self).default(o)
