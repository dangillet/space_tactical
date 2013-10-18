

class Command(object):
    def __init__(self, battle):
        self.battle = battle

    def execute(self):
        raise NotImplementedError

class MoveCommand(Command):
    def __init__(self, battle, ship, i, j):
        super(MoveCommand, self).__init__(battle)
        self.ship = ship
        self.i, self.j = i, j

    def execute(self):
        self.battle.battle_grid.move_sprite(self.ship, self.i, self.j)

class AttackCommand(Command):
    def __init__(self, battle, ship, ennemy):
        super(AttackCommand, self).__init__(battle)
        self.ship = ship
        self.ennemy = ennemy

    def execute(self):
        self.battle.attack_ship(self.ship, self.ennemy)

class BoostCommand(Command):
    def __init__(self, battle, ship, boost_idx):
        super(BoostCommand, self).__init__(battle)
        self.ship = ship
        self.boost_idx = boost_idx

    def execute(self):
        self.ship.use_boost(self.boost_idx)
        self.battle.on_command_finished()

