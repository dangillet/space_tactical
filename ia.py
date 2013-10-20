import random

import commands

class Brain(object):
    def __init__(self, player, battle):
        self.player = player
        self.battle = battle
        self.ship_iter = iter(self.player.fleet)

    def attack_targets_in_range(self):
        for ship in self.player.fleet:
            if not ship.move_completed:
                
                return ship, targets
        return None, None

    def think(self):
        try:
            ship = self.ship_iter.next()
            targets = self.battle.battle_grid.get_targets(ship)
            if targets:
                target = random.choice(targets)
                self.battle.submit(commands.AttackCommand(ship, target))
            move_options = self.battle.get_reachable_cells(ship)
            i, j = move = random.choice(move_options)
            i0, j0 = self.battle.battle_grid.from_pixel_to_grid(ship.position)
            self.battle.submit(commands.MoveCommand(ship, i, j))
            if not targets:
                targets = self.battle.battle_grid.get_targets(ship)
                if targets:
                    target = random.choice(targets)
                    self.battle.submit(commands.AttackCommand(ship, target))
        except StopIteration:
            self.battle.submit(commands.EndOfRoundCommand())
            self.ship_iter = iter(self.player.fleet)
