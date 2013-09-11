import random
from itertools import cycle
import json

import cocos
from cocos.actions import CallFunc, CallFuncS
import grid, entity, main, gui

class ViewPort(object):
    position = (50, 50)
    width = main.SCREEN_W - gui.WIDTH - position[0]
    height = 800
    
class Battle(cocos.layer.Layer):
    def __init__(self):
        self.is_event_handler = True
        super(Battle, self ).__init__()
        self.players = []
        self.ships_factory = entity.ShipFactory()
        self.ships_type = self.ships_factory.get_ships_type()
        self.ship_info = gui.InfoLayer()
        self.add(self.ship_info, z=5)

        self.load_battlemap()
        

        # Player list
        self.players_turn = cycle(self.players)
        # Add the ships to the grid
        for i, player in enumerate(self.players):
            self.battle_grid.add_player_fleet(player, i)
        # Select the first player from the list as the current one
        self.current_player = next(self.players_turn)
        self.game_phase = Idle(self)
        self.battle_grid.highlight_player(self.current_player)
        
        # Selected object from the grid and list of targets in range
        self.selected, self.targets = None, None
        # The reachable cells for a ship and the predecessor list to reconstruct the shortest path
        self.reachable_cells, self.predecessor = None, None
    
    def load_battlemap(self):
        with open("battlemap.json") as f:
            data = json.load(f)
            for player_data in data['players']:
                player = entity.Player(player_data['name'])
                self.players.append(player)
                for ship_type, quantity in player_data['fleet'].iteritems():
                    for _ in range(quantity):
                        ship = self.ships_factory.create_ship(ship_type)
                        ship.scale = float(grid.CELL_WIDTH) / ship.width
                        player.add_ship(ship)
            self.battle_grid = grid.GridLayer(data['battlemap'])
            self.scroller = cocos.layer.ScrollingManager(ViewPort())
            self.scroller.add(self.battle_grid)
            self.add(self.scroller)
    
    def change_game_phase(self, game_phase):
        "Change the state of the game."
        self.game_phase.on_exit()
        self.game_phase = game_phase
        self.game_phase.on_enter()
    
    def on_mouse_press(self, x, y, button, modifiers):
        """
        The game logic happens in the state machine.
        The behaviour of mouse clicks depends on the current game_phase
        """
        # Get the coords from the scrolling manager.
        x, y = self.scroller.pixel_from_screen(x, y)
        # Transform mouse pos in local coord
        x, y = self.scroller.point_to_local((x, y))
        i, j = self.battle_grid.from_pixel_to_grid(x, y)
        if i is None or j is None: return
        
        self.game_phase.on_mouse_press(i, j, x, y)

    def select_ship(self):
        "Make the entity the selecetd ship."
        self.battle_grid.highlight_ships([self.selected], grid.SHIP_SELECTED)
        # If ship didn't move yet, calculate and highlight the reachable cells
        if not self.selected.move_completed:
            self.show_reachable_cells()
        # Get targets in range if ship didn't attack yet
        if not self.selected.attack_completed:
            self.show_targets()
    
    def show_reachable_cells(self):
        "calculate and highlight the reachable cells"
        i, j = self.battle_grid.from_pixel_to_grid(*(self.selected.position))
        self.reachable_cells, self.predecessor = self.battle_grid.get_reachable_cells(i, j, self.selected.speed)
        self.battle_grid.highlight_cells(self.reachable_cells, grid.REACHABLE_CELLS)
    
    def show_targets(self):
        "Get targets in range"
        self.targets = self.battle_grid.get_targets(self.selected)
        self.battle_grid.highlight_ships(self.targets, grid.TARGET)
        
    def deselect_ship(self):
        "Deselect the currently selected ship if in play."
        if not self.selected.turn_completed:
            self.battle_grid.highlight_ships([self.selected], grid.PLAYER_TURN)
    
    def clear_reachable_cells(self):
        "Clear the reachable cells if any"
        if self.reachable_cells:
            self.battle_grid.clear_cells(self.reachable_cells)
            self.reachable_cells = None
            self.predecessor = None
    
    def deselect_targets(self):
        "Deselect the targeted ships"
        if self.targets:
            self.battle_grid.clear_ships_highlight(self.targets)
            self.targets = []
    
    def end_turn(self):
        """End the turn of the current ship. If all ships played, change player"""
        if self.selected is not None and not self.selected.are_actions_running():
            self.selected.turn_completed = True
            self.battle_grid.clear_cells([self.battle_grid.from_pixel_to_grid(*(self.selected.position))])
            if hasattr(self.selected, "reachable_cells"):
                self.battle_grid.delete_reachable_cells(self.selected)
            # If targets are selected
            if self.targets:
                self.battle_grid.clear_ships_highlight(self.targets)
                self.targets = []
            self.selected = None
            if self.current_player.turn_completed():
                self.current_player.reset_ships_turn()
                self.current_player = next(self.players_turn)
                self.battle_grid.highlight_player(self.current_player)
    
    def attack_ship(self, attacker, defender):
        ox, oy = self.battle_grid.from_pixel_to_grid(*(attacker.position))
        m, n = self.battle_grid.from_pixel_to_grid(*(defender.position))
        attacker.do(self.battle_grid.rotate_to_bearing(m, n, ox, oy))
        print """------
ATTACK
------
[%s]%s is attacking
[%s] %s""" % (attacker.player.name, attacker, defender.player.name, defender)
    
    def move_ship(self, ship, i, j):
        self.battle_grid.move_sprite(ship, i, j)
        self.battle_grid.highlight_cell(i, j, grid.SHIP_SELECTED)


class GamePhase(object):
    def __init__(self, battle):
        self.battle = battle
        self.battle_grid = battle.battle_grid
        
    def on_enter(self):
        pass
    
    def on_mouse_press(self, i, j, x, y):
        pass
    
    def on_end_of_turn(self):
        pass
    
    def on_exit(self):
        pass

class Idle(GamePhase):
    def __init__(self, battle):
        super(Idle, self).__init__(battle)

    def on_enter(self):
        self.selected = None
        self.battle.deselect_targets()
        self.battle.ship_info.display('')
        self.battle.clear_reachable_cells()
    
    def on_mouse_press(self, i, j, x, y):
        entity = self.battle_grid.get_entity(x, y)
        if entity is not None and entity.player == self.battle.current_player \
                and not entity.turn_completed:
            self.battle.selected = entity
            self.battle.change_game_phase(ShipSelected(self.battle))

class ShipSelected(GamePhase):
    def __init__(self, battle):
        super(ShipSelected, self).__init__(battle)
        
    def on_enter(self):
        self.battle.select_ship()
        self.battle.ship_info.display(repr(self.battle.selected))
    
    def on_mouse_press(self, i, j, x, y):
        # If we clicked on our selected ship, deselect it.
        if self.battle.selected.get_AABB().contains(x, y):
            self.battle.change_game_phase(Idle(self.battle))
        # If we clicked on a reachable cell, move the ship there
        elif self.battle.reachable_cells and (i,j) in self.battle.reachable_cells:
            self.battle.change_game_phase(Move(self.battle, i, j))
        # If we clicked on a target, attack it.
        elif self.battle.targets:
            for ship in self.battle.targets:
                if ship.get_AABB().contains(x, y):
                    self.battle.change_game_phase(Attack(self.battle, ship))
        

    
    def on_end_of_turn(self):
        "End the turn of the current ship. If all ships played, change player"
        self.battle.selected.turn_completed = True
        self.battle_grid.clear_ships_highlight([self.battle.selected])
        self.battle.change_game_phase(Idle(self.battle))
        if self.battle.current_player.turn_completed():
            self.battle.current_player.reset_ships_turn()
            self.battle.current_player = next(self.battle.players_turn)
            self.battle_grid.highlight_player(self.battle.current_player)

    def on_exit(self):
        self.battle.deselect_ship()

class Attack(GamePhase):
    def __init__(self, battle, ennemy):
        super(Attack, self).__init__(battle)
        self.ennemy = ennemy
    
    def on_enter(self):
        self.battle.attack_ship(self.battle.selected, self.ennemy)
        self.battle.change_game_phase(ShipSelected(self.battle))
    
    def on_exit(self):
        self.battle.selected.attack_completed = True
        self.battle.deselect_targets()
        self.battle.clear_reachable_cells()
        

class Move(GamePhase):
    def __init__(self, battle, i, j):
        super(Move, self).__init__(battle)
        self.i, self.j = i, j
    
    def on_enter(self):
        self.battle.move_ship(self.battle.selected, self.i, self.j)
        self.battle.clear_reachable_cells()
        self.battle.deselect_targets()
        
    def on_move_finished(self):
        self.battle.change_game_phase(ShipSelected(self.battle))
    
    def on_exit(self):
        self.battle.selected.move_completed = True
        self.battle.deselect_targets()
        self.battle.clear_reachable_cells()
