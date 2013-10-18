

class Command(object):
    def execute(self, battle):
        raise NotImplementedError

class MoveCommand(Command):
    def __init__(self, ship, i, j):
        super(MoveCommand, self).__init__()
        self.ship = ship
        self.i, self.j = i, j

    def execute(self, battle):
        battle.battle_grid.move_sprite(self.ship, self.i, self.j)

class AttackCommand(Command):
    def __init__(self, ship, ennemy):
        super(AttackCommand, self).__init__()
        self.ship = ship
        self.ennemy = ennemy

    def execute(self, battle):
        battle.attack_ship(self.ship, self.ennemy)

class BoostCommand(Command):
    def __init__(self, ship, boost_idx):
        super(BoostCommand, self).__init__()
        self.ship = ship
        self.boost_idx = boost_idx

    def execute(self, battle):
        self.ship.use_boost(self.boost_idx)
        battle.on_command_finished()

