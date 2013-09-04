import random
from itertools import cycle

from cocos.actions import CallFunc, CallFuncS

import grid, entity

class Battle(object):
    def __init__(self):
        self.players = []
        #How many players?
        for i in range(4):
            player = entity.Player("Player %d" % i)
            self.players.append(player)
            # How many ships ?
            for _ in range(2):
                ship = entity.Ship("ship.png", distance=random.randint(2,6) +0.5)
                ship.scale = float(grid.CELL_WIDTH) / ship.width
                player.add_ship(ship)
        self.grid = grid.GridLayer(self)
        
        # Player list
        self.players_turn = cycle(self.players)
        # Add the ships to the grid
        for i, player in enumerate(self.players):
            self.grid.add_player_fleet(player, i)
        # Select the first player from the list as the current one
        self.current_player = next(self.players_turn)
        self.grid.highlight_player(self.current_player)
        # Selected object from the grid and list of targets in range
        self.selected, self.targets = None, None
    
    def on_mouse_press(self, i, j, x, y):
        """
        Called by the grid when a grid square is clicked.
        The game logic happens here.
        """
        # If we click while something is selected, either move, attack or deselect.
        if self.selected:
            # If we clicked on our selected ship, deselect it.
            if self.selected.get_AABB().contains(x, y):
                self.deselect_ship()
                return
            # If we clicked on a target, attack it.
            elif self.targets and not self.selected.attack_completed:
                for ship in self.targets:
                    if ship.get_AABB().contains(x, y):
                        print "%s attacks %s" % (self.selected, ship)
                        self.selected.attack_completed = True
                        entity = self.selected
                        self.deselect_ship()
                        self.select_ship(entity)
            
            # If we clicked on a reachable cell, move the ship there
            elif not self.selected.move_completed and (i,j) in self.selected.reachable_cells:
                self.grid.move_sprite(self.selected, i, j)
                self.selected.move_completed = True
            
        else:
            entity = self.grid.get_entity(x, y)
            if entity is not None and entity.player == self.current_player \
                    and not entity.turn_completed:
                self.select_ship(entity)

    def select_ship(self, entity):
        "Make the entity the selecetd ship."
        self.selected = entity
        self.grid.highlight_ships([self.selected], grid.SHIP_SELECTED)
        # If ship didn't move yet, calculate and highlight the reachable cells
        if not self.selected.move_completed:
            i, j = self.grid.from_pixel_to_grid(*(self.selected.position))
            self.selected.reachable_cells, self.selected.predecessor = self.grid.get_reachable_cells(i, j, self.selected.distance)
            self.grid.highlight_cells(self.selected.reachable_cells, grid.REACHABLE_CELLS)
        # Get targets in range if ship didn't attack yet
        if not self.selected.attack_completed:
            self.targets = self.grid.get_targets(self.selected)
            self.grid.highlight_ships(self.targets, grid.TARGET)
    
    def deselect_ship(self):
        "Deselect the currently selected ship."
        # Clear the reachable cells if any
        if hasattr(self.selected, 'reachable_cells'):
            self.grid.clear_cells(self.selected.reachable_cells)
            del self.selected.reachable_cells
            del self.selected.predecessor
        # If targets are selected
        self.deselect_targets()
        # Normal highlight for the ship
        self.grid.highlight_ships([self.selected], grid.PLAYER_TURN)
        self.selected = None
    
    def deselect_targets(self):
        "Deselect the targeted ships"
        if self.targets:
            self.grid.clear_ships_highlight(self.targets)
            self.targets = []
    
    def end_turn(self):
        """End the turn of the current ship. If all ships played, change player"""
        if self.selected is not None and not self.selected.are_actions_running():
            self.selected.turn_completed = True
            self.grid.clear_cells([self.grid.from_pixel_to_grid(*(self.selected.position))])
            if hasattr(self.selected, "reachable_cells"):
                self.grid.delete_reachable_cells(self.selected)
            # If targets are selected
            if self.targets:
                self.grid.clear_ships_highlight(self.targets)
                self.targets = []
            self.selected = None
            if self.current_player.turn_completed():
                self.current_player.reset_ships_turn()
                self.current_player = next(self.players_turn)
                self.grid.highlight_player(self.current_player)

class GamePhase(object):
    def __init__(self, battle, grid):
        self.battle = battle
        self.grid = grid
        
    def on_enter(self, entity):
        pass
    
    def on_mouse_press(self, i, j, x, y):
        pass
    
    def on_exit(self):
        pass

class ShipSelected(GamePhase):
    def __init__(self, battle, grid, entity):
        super(ShipSelected, self).__init__(battle, grid)
        self.selected = entity
        self.actions = []
        
    def on_enter(self, entity):
        self.grid.highlight_ships([self.selected], grid.SHIP_SELECTED)
        # If ship didn't move yet, calculate and highlight the reachable cells
        if not self.selected.move_completed:
            self.actions.append(MoveAction(self))
        # Get targets in range if ship didn't attack yet
        if not self.selected.attack_completed:
            self.actions.append(AttackAction(self))
        for action in self.actions:
            action.on_enter(entity)
    
    def on_mouse_press(self, i, j, x, y):
        # If we clicked on our selected ship, deselect it.
        if self.selected.get_AABB().contains(x, y):
            self.parent.change_game_phase(ShipDeselected(self.battle))
        else:
            for action in self.actions:
                action.on_mouse_press(i, j, x, y)
    
    def on_exit(self):
        for action in self.actions:
            action.on_exit()
        self.grid.highlight_ships([self.selected], grid.PLAYER_TURN)

class MoveAction(GamePhase):
    def __init__(self, battle, grid):
        super(MoveAction, self).__init__(battle, grid)
    
    def on_enter(self, entity):
        i, j = self.grid.from_pixel_to_grid(*(entity.position))
        self.reachable_cells, self.predecessor = self.grid.get_reachable_cells(i, j, entity.distance)
        self.grid.highlight_cells(self.reachable_cells, grid.REACHABLE_CELLS)
    
    def on_mouse_press(self, i, j, x, y):
        if (i,j) in self.selected.reachable_cells:
            self.grid.move_sprite(self.selected, i, j)
            self.selected.move_completed = True
    
class NoSelection(GamePhase):
    def __init__(self, battle, grid):
        super(NoSelection, self).__init__(battle, grid)

    def on_mouse_press(self, i, j, x, y):
        entity = self.grid.get_entity(x, y)
        if entity is not None and entity.player == self.current_player \
                and not entity.turn_completed:
            self.battle.change_game_phase(ShipSelected(self.battle, self.grid, entity))




