import random
from itertools import cycle
import json

import cocos
from cocos.actions import CallFunc, CallFuncS
from cocos.director import director

from cocos.scenes import *

from pyglet.window import key
from pyglet.gl import *
import pyglet

import grid, entity, main, gui, game_over

INFO_WIDTH = 350
SHIP_INFO_HEIGHT = 200
MENU_BUTTON_HEIGHT = 50
MARGIN = 10

class ViewPort(object):
    position = (0, MENU_BUTTON_HEIGHT)
    width = main.SCREEN_W - INFO_WIDTH - position[0]
    height = main.SCREEN_H-MENU_BUTTON_HEIGHT
    
class Battle(cocos.layer.Layer):
    def __init__(self):
        self.is_event_handler = True
        super(Battle, self ).__init__()
        self.players = []
        self.ships_factory = entity.ShipFactory()
        self.ship_info = gui.InfoLayer(
            (main.SCREEN_W - INFO_WIDTH + MARGIN, MARGIN),
            INFO_WIDTH - 2*MARGIN, SHIP_INFO_HEIGHT)
        self.add(self.ship_info, z=5)
        self.log_info = gui.ScrollableInfoLayer(
            (main.SCREEN_W - INFO_WIDTH + MARGIN, SHIP_INFO_HEIGHT + 2*MARGIN),
            INFO_WIDTH - 2*MARGIN, main.SCREEN_H - SHIP_INFO_HEIGHT - 3*MARGIN)
        self.add(self.log_info, z=5)
        self.msg = ''
        self.load_battlemap()

        # Player list
        self.players_turn = cycle(self.players)
        # Add the ships to the grid
        for i, player in enumerate(self.players):
            self.battle_grid.add_player_fleet(player, i)
        # Select the first player from the list as the current one
        self.current_player = next(self.players_turn)
        self.game_phase = [Idle(self)]
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
                        ship.push_handlers(self)
                        player.add_ship(ship)
            self.battle_grid = grid.GridLayer(data['battlemap'])
            self.scroller = cocos.layer.ScrollingManager(ViewPort())
            self.scroller.add(self.battle_grid)
            self.add(self.scroller)
    
    def change_game_phase(self, game_phase):
        "Change the state of the game."
        self.pop_game_phase()
        self.push_game_phase(game_phase)
    
    def push_game_phase(self, game_phase):
        "Push a new state to the game."
        self.game_phase.append(game_phase)
        game_phase.on_enter()
    
    def pop_game_phase(self):
        "Pop the last state of the game."
        self.game_phase.pop().on_exit()
        
    def on_mouse_release(self, x, y, button, modifiers):
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
        
        self.game_phase[-1].on_mouse_release(i, j, x, y)

    def on_key_release(self, symbol, modifiers):
        # With Space bar, end of turn
        if symbol == key.SPACE:
            self.game_phase[-1].on_end_of_turn()
            return True
        
        if symbol == key.RETURN:
            self.game_phase[-1].on_end_of_round()
            return True
    
    def select_ship(self):
        "Make the entity the selecetd ship."
        self.battle_grid.highlight_ships([self.selected], grid.SHIP_SELECTED)
        # If ship didn't move yet, calculate and highlight the reachable cells
        if not self.selected.move_completed:
            self.show_reachable_cells()
        # Get targets in range if ship didn't attack yet
        if not self.selected.attack_completed and self.selected.weapon_idx is not None:
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
        
    def deselect_ship(self, ship):
        "Deselect the currently selected ship if in play."
        self.battle_grid.highlight_ships([ship], grid.PLAYER_TURN)
    
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
    
    def attack_ship(self, attacker, defender):
        "Attacker attacks the defender"
        ox, oy = self.battle_grid.from_pixel_to_grid(*(attacker.position))
        m, n = self.battle_grid.from_pixel_to_grid(*(defender.position))
        attacker.do(self.battle_grid.rotate_to_bearing(m, n, ox, oy))
        self.msg += _("""{font_name 'Classic Robot'}{font_size 10}{color [255, 0, 0, 255]}
{bold True}ATTACK{bold False} {}
{color [0, 255, 0, 255]}%s
{color [255, 255, 255, 255]} fires at {color [0, 255, 0, 255]}%s{color [255, 255, 255, 255]}'s
ship.{}
""") % (attacker.player.name, defender.player.name)
        
        attacker.attack(defender)
    
    def on_change(self):
        self.ship_info.update()
    
    def on_weapon_change(self):
        self.ship_info.update()
        self.deselect_targets()
        self.show_targets()
    
    def on_weapon_jammed(self, weapon):
        self.msg += _("%s jammed! It's now inoperative.{}\n") % (weapon.weapon_type)
        self.ship_info.update()
    
    def on_damage(self, ship, dmg):
        self.msg += _("HIT! %s took %d points of damage. {}\n") % (ship.ship_type, dmg)
    
    def on_destroyed(self, ship):
        self.msg += _("%s is destroyed.{}\n") %(ship.ship_type)
        self.battle_grid.remove(ship)
            
    def on_missed(self):
        self.msg += _("Missed!{}\n")
    
    def move_ship(self, ship, i, j):
        self.battle_grid.move_sprite(ship, i, j)
        self.battle_grid.highlight_cell(i, j, grid.SHIP_SELECTED)


class GamePhase(object):
    def __init__(self, battle):
        self.battle = battle
        self.battle_grid = battle.battle_grid
        
    def on_enter(self):
        pass
    
    def on_mouse_release(self, i, j, x, y):
        pass
    
    def on_end_of_turn(self):
        pass
    
    def on_end_of_round(self):
        pass
        
    def on_exit(self):
        "All game phase, when they exit, display the buffered message."
        if self.battle.msg:
            self.battle.log_info.prepend_text(self.battle.msg)
            self.battle.msg = ""

class StaticGamePhase(GamePhase):
    """
    A phase of game which is not a transition.
    So it's either idle state or shipselected phase.
    """
    def __init__(self, battle):
        super(StaticGamePhase, self).__init__(battle)
    
    def on_end_of_round(self):
        player = self.battle.current_player
        ships_in_play = [ship for ship in player.fleet if not ship.turn_completed]
        for ship in ships_in_play:
            ship.turn_completed = True
        self.battle_grid.clear_ships_highlight(ships_in_play)
        self.check_end_of_round()
        
    def check_end_of_round(self):
        "Check at the end of a turn if all ships have played. If so, change player."
        if self.battle.current_player.turn_completed():
            self.battle.current_player = next(self.battle.players_turn)
            # If there are no more ships in the fleet, it's game over.
            if not self.battle.current_player.fleet:
                game_over_scene = cocos.scene.Scene(game_over.GameOver())
                director.replace(FadeBLTransition(game_over_scene, duration = 2))
            self.battle.current_player.reset_ships_turn()
            self.battle_grid.highlight_player(self.battle.current_player)

class Idle(StaticGamePhase):
    def __init__(self, battle):
        super(Idle, self).__init__(battle)
    
    def on_enter(self):
        self.battle.ship_info.remove_model()
        
    def on_mouse_release(self, i, j, x, y):
        entity = self.battle_grid.get_entity(x, y)
        if entity is not None:
            if entity.player == self.battle.current_player:
                self.battle.selected = entity
                self.battle.change_game_phase(ShipSelected(self.battle))
            else:
                self.battle.ship_info.set_model(entity)

class ShipSelected(StaticGamePhase):
    def __init__(self, battle):
        super(ShipSelected, self).__init__(battle)
        
    def on_enter(self):
        self.battle.select_ship()
        # We keep a reference to the selected ship, so if we change ship
        # We can clear the "old" selected ship in the on_exit method.
        self.selected = self.battle.selected
        self.battle.ship_info.set_model(self.selected)
        self.battle.add(gui.WeaponMenu(self.selected), z=5, name="weapon_menu")
        
    def on_mouse_release(self, i, j, x, y):
        entity = self.battle_grid.get_entity(x, y)
        # If we clicked on a reachable cell, move the ship there
        if self.battle.reachable_cells and (i,j) in self.battle.reachable_cells:
            self.battle.push_game_phase(Move(self.battle, i, j))
        # If we clicked on another ship
        elif entity is not None:
            # If it belongs to the player, select it
            if entity.player == self.battle.current_player:
                if entity is not self.battle.selected:
                    self.battle.selected = entity
                    self.battle.change_game_phase(ShipSelected(self.battle))
                # If we clicked on our selected ship, deselect it
                else:
                    self.battle.change_game_phase(Idle(self.battle))
            # If we clicked on a target, attack it.
            elif self.battle.targets is not None and entity in self.battle.targets:
                weapon = self.selected.weapons[self.selected.weapon_idx]
                if weapon.temperature + weapon.heating > 100:
                    msg = _("""{color [255, 0, 0, 255]}
Cannot fire with %s. It's overheating.
""") % (weapon.weapon_type)
                    self.battle.log_info.prepend_text(msg)
                else:
                    self.battle.push_game_phase(Attack(self.battle, entity))
            # Otherwise display info on this ship
            else:
                self.battle.ship_info.set_model(entity)
        

        # If we clicked on our selected ship or in an empy cell, deselect the ship.
        else: # entity is self.selected or :
            self.battle.change_game_phase(Idle(self.battle))
        
    def on_end_of_round(self):
        self.battle.change_game_phase(Idle(self.battle))
        super(ShipSelected, self).on_end_of_round()

    def on_exit(self):
        super(StaticGamePhase, self).on_exit()
        self.battle.deselect_ship(self.selected)
        self.battle.clear_reachable_cells()
        self.battle.deselect_targets()
        self.battle.remove("weapon_menu")
        

class Attack(GamePhase):
    def __init__(self, battle, ennemy):
        super(Attack, self).__init__(battle)
        self.ennemy = ennemy
    
    def on_enter(self):
        self.battle.attack_ship(self.battle.selected, self.ennemy)
        self.battle.pop_game_phase()
    
    def on_exit(self):
        super(Attack, self).on_exit()
        self.battle.selected.attack_completed = True
        self.battle.deselect_targets()

class Move(GamePhase):
    def __init__(self, battle, i, j):
        super(Move, self).__init__(battle)
        self.i, self.j = i, j
    
    def on_enter(self):
        self.battle.move_ship(self.battle.selected, self.i, self.j)
        self.battle.clear_reachable_cells()
        self.battle.deselect_targets()
        
    def on_move_finished(self):
        self.battle.pop_game_phase()
    
    def on_exit(self):
        super(Move, self).on_exit()
        self.battle.selected.move_completed = True
        self.battle.select_ship()
