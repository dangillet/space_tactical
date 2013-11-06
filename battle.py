import random, gc
from itertools import cycle
import json, collections

import cocos
from cocos.actions import CallFunc, CallFuncS, Show, Hide, Delay
from cocos.director import director

from cocos.scenes import *

from pyglet.window import key
from pyglet.gl import *
import pyglet

import grid, entity, main, gui, game_over, commands, laser

INFO_WIDTH = 350
SHIP_INFO_HEIGHT = 200
MENU_BUTTON_HEIGHT = 50
MARGIN = 10
PROMPT = "{font_name 'Classic Robot'}{font_size 10}{color [255,255,255,255]}>> {margin_left 25}"

class ViewPort(object):
    position = (0, 0)
    width = main.SCREEN_W - INFO_WIDTH - position[0]
    height = main.SCREEN_H

class ActionSequence(object):
    '''
    Pass tuples of (target_cocosnode, actions) and they will execute one
    at a time.
    A callback can be passed. It will be called when there are no more
    target-action pair.
    '''
    def __init__(self, actions, callback=None):
        self.queue = collections.deque()
        self.callback = callback
        for actor, action in actions:
            action = action + CallFunc(self.next_action)
            self.queue.append( (actor, action) )
        self.next_action()
    
    def next_action(self):
        if self.queue:
            actor, action = self.queue.popleft()
            actor.do(action)
        elif self.callback is not None:
            self.callback()
    
class Battle(cocos.layer.Layer):
    def __init__(self):
        self.is_event_handler = True
        super(Battle, self ).__init__()
        self.players = []
        self.ships_factory = entity.ShipFactory()
        self.ship_info = gui.ShipInfoLayer(
            (main.SCREEN_W - INFO_WIDTH + MARGIN, MARGIN),
            INFO_WIDTH - 2*MARGIN, SHIP_INFO_HEIGHT)
        self.add(self.ship_info, z=5)
        self.log_info = gui.ScrollableInfoLayer(
            (main.SCREEN_W - INFO_WIDTH + MARGIN, SHIP_INFO_HEIGHT + 2*MARGIN),
            INFO_WIDTH - 2*MARGIN, main.SCREEN_H - SHIP_INFO_HEIGHT - 3*MARGIN)
        self.add(self.log_info, z=5)
        self.msg = PROMPT
        self.load_player()
        self.load_battlemap()

        # Player list
        self.players_turn = cycle(self.players)
        # Add the ships to the grid
        for i, player in enumerate(self.players):
            self.battle_grid.add_player_fleet(player, i)
        # Select the first player from the list as the current one
        self.current_player = next(self.players_turn)
        self.on_new_turn()
        self.game_phase = collections.deque([Idle(self)])
        self.change_game_phase(Idle(self))
        self.current_player.reset_ships_turn()
        self.battle_grid.highlight_player(self.current_player)

        # Commands list
        self.commands = collections.deque()
        self.command_in_progress = False
        # Selected object from the grid and list of targets in range
        self.selected, self.targets = None, None
        # The reachable cells for a ship and the predecessor list to reconstruct the shortest path
        self.reachable_cells, self.predecessor = None, None

        self.battle_grid.add(laser.LaserBeam(), z=1, name='laser')

    def load_battlemap(self):
        with open("battlemap.json") as f:
            data = json.load(f)
            for player_data in data['players']:
                player = entity.Player(player_data['name'])
                player.set_ia("Albert", self)
                self.players.append(player)
                for ship_data in player_data['fleet']:
                    quantity = ship_data.get("count", 1)
                    for _ in range(quantity):
                        mods = ship_data.get("mods", [])
                        ship = self.ships_factory.create_ship(ship_data['type'],
                                                                mods =mods)
                        ship.scale = float(grid.CELL_WIDTH) / ship.width
                        ship.push_handlers(self)
                        player.add_ship(ship)
            self.battle_grid = grid.GridLayer(data['battlemap'])
            self.scroller = cocos.layer.ScrollingManager(ViewPort())
            self.scroller.add(self.battle_grid)
            self.add(self.scroller)

    def on_enter(self):
        super(Battle, self).on_enter()
        self.schedule(self.process_commands)

    def load_player(self):
        player = entity.Player.load()
        self.players.append(player)
        for ship in player.fleet:
            ship.scale = float(grid.CELL_WIDTH) / ship.width
            ship.push_handlers(self)

    def change_game_phase(self, game_phase):
        "Change the state of the game."
        while self.game_phase:
            self.pop_game_phase()
        self.push_game_phase(game_phase)

    def push_game_phase(self, game_phase):
        "Push a new state to the game."
        self.game_phase.append(game_phase)
        game_phase.on_enter()

    def pop_game_phase(self):
        "Pop the last state of the game."
        self.game_phase.pop().on_exit()

    def submit(self, command):
        "Submit a command to the battle grid"
        self.commands.append(command)

    def process_commands(self, dt):
        "Scheduled function that processes queued commands."
        if self.commands and not self.command_in_progress:
            command = self.commands.popleft()
            self.command_in_progress = True
            command.execute(self)
        if not self.commands and self.current_player.brain:
            self.current_player.brain.think()

    def on_command_finished(self):
        self.command_in_progress = False
        self.game_phase[-1].on_command_finished()

    def on_mouse_release(self, x, y, button, modifiers):
        """
        The game logic happens in the state machine.
        The behaviour of mouse clicks depends on the current game_phase
        """
        # Get the coords from the scrolling manager.
        x, y = self.scroller.pixel_from_screen(x, y)
        # Transform mouse pos in local coord
        x, y = self.scroller.point_to_local((x, y))
        i, j = self.battle_grid.from_pixel_to_grid( (x, y) )
        if i is None or j is None: return

        self.game_phase[-1].on_mouse_release(i, j, x, y)

    def on_mouse_motion(self, x, y, dx, dy):
        # Get the coords from the scrolling manager.
        x, y = self.scroller.pixel_from_screen(x, y)
        # Transform mouse pos in local coord
        x, y = self.scroller.point_to_local((x, y))
        self.game_phase[-1].on_mouse_motion(x, y)

    def on_key_release(self, symbol, modifiers):
        # With Return, end of turn for human players
        return self.game_phase[-1].on_key_release(symbol, modifiers)


    def select_ship(self):
        "Make the entity the selected ship."
        self.battle_grid.highlight_ships([self.selected], grid.SHIP_SELECTED)
        # If ship didn't move yet, calculate and highlight the reachable cells
        self.show_reachable_cells()
        # Get targets in range
        self.show_targets()

    def show_reachable_cells(self):
        "calculate and highlight the reachable cells"
        if not self.selected.move_completed:
            self.get_reachable_cells(self.selected)
            self.battle_grid.highlight_cells(self.reachable_cells, grid.REACHABLE_CELLS)

    def get_reachable_cells(self, ship):
        "Calculate the reachable cells"
        self.reachable_cells, self.predecessor = self.battle_grid.get_reachable_cells(ship)
        return self.reachable_cells

    def show_targets(self):
        "Show targets in range"
        if not self.selected.attack_completed \
           and self.selected.weapon is not None:
            self.targets = self.battle_grid.get_targets(self.selected)
            self.battle_grid.highlight_ships(self.targets, grid.TARGET)

    def deselect_ship(self, ship):
        "Deselect the currently selected ship if in play."
        self.battle_grid.highlight_ships([ship], grid.PLAYER_TURN)

    def clear_reachable_cells(self):
        "Clear the reachable cells if any"
        if self.reachable_cells:
            self.battle_grid.clear_cells(self.reachable_cells)

    def deselect_targets(self):
        "Deselect the targeted ships"
        if self.targets:
            self.battle_grid.clear_ships_highlight(self.targets)
            self.targets = []

    def attack_ship(self, attacker, defender):
        "Attacker attacks the defender"
        ox, oy = self.battle_grid.from_pixel_to_grid(attacker.position)
        m, n = self.battle_grid.from_pixel_to_grid(defender.position)
        
        rotate_action = self.battle_grid.rotate_to_bearing(m, n, ox, oy)
        laser = self.battle_grid.get("laser")
        direction = cocos.euclid.Vector2(x=m-ox, y=n-oy).normalize()
        laser.pos_from = attacker.position + direction * grid.CELL_WIDTH/2.
        laser.pos_to = defender.position
        laser.free() # To update the vertex list
        show_action = Show() + Delay(0.1) + Hide()
        self.action_sequencer = ActionSequence([(attacker, rotate_action),
                        (laser, show_action),
                        (attacker, CallFunc(attacker.attack, defender))],
                        callback=self.on_command_finished)

        #self.msg += _("""{font_name 'Classic Robot'}{font_size 10}{color [255, 0, 0, 255]}
#{bold True}ATTACK{bold False} {}
#{color [0, 255, 0, 255]}%s
#{color [255, 255, 255, 255]} fires at {color [0, 255, 0, 255]}%s{color [255, 255, 255, 255]}'s
#ship.{}
#""") % (attacker.player.name, defender.player.name)

    def on_weapon_change(self):
        self.deselect_targets()
        self.show_targets()

    def on_speed_change(self):
        if not self.selected.move_completed:
            self.clear_reachable_cells()
            self.show_reachable_cells()

    def on_weapon_jammed(self, weapon):
        self.msg += _("Major Failure ! You will need a tech to use {weapon.name} again.{{}}\n").format(weapon=weapon)

    def on_damage(self, ship, dmg):
        if dmg > 0:
            if self.current_player.brain:
                # IA attacks
                msg = [_("Fire in the lower bridge, evacuate this area!{}\n")]
                if 0 < ship.hull < 10:
                    msg.extend([_("Commander, our ship won't hold for long...{}\n"),
                                 _("Breach in the hull ! Perhaps we should think about another approach, Sir.{}\n")])
            else:
                #Player attacks
                msg = [_("Nice shot, those bastards will soon meet the vacuum of space!{}\n"),
                        _("We hit hard our enemy, Commander.{}\n"),
                        _("Well done,boys! Let's keep that fire rate.{}\n"),
                        _("Yeahhh!{}\n") ]

            self.msg += random.choice(msg) + \
                    _("[{{color (200, 100, 0, 255)}}{ship} takes {dmg} points of damage{{color (200, 200, 200, 255)}}]{{}}\n").format(ship=ship.ship_type, dmg=dmg)

        else:
            if self.current_player.brain:
                msg = [_("Shields hold on, Sir.{}\n"),
                        _("Their weapon are painless.{}\n") ]
            else:
                msg = [_("This ship is invulnerable, we should avoid the confrontation.{}\n"),
                        _("Our weapon is badly... ineffective, Commander.{}\n") ]
            self.msg += random.choice(msg)

    def on_destroyed(self, ship, energy_name):
        self.msg += _("""Yeahhh! And one more {energy_name}'s spoon for daddy!{{}}
[{{color (200, 0, 0, 255)}}{ship} is destroyed.{{color (200, 200, 200, 255)}}]{{}}\n""").format(energy_name=energy_name, ship=ship.ship_type)
        explosion = cocos.sprite.Sprite(self.battle_grid.explosion_anim,
                            position=ship.position)
        self.battle_grid.add(explosion, name="explosion")
        @explosion.event
        def on_animation_end():
            self.battle_grid.remove("explosion")
        self.battle_grid.remove(ship)

    def on_missed(self):
        if self.current_player.brain:
            msg = [_("Focus on that enemy before they blast us!{}\n"),
                    _("We are under fire, avoidance maneuver required...{}\n")]
        else:
            msg = [_("Commander, our offensive totally missed.{}\n"),
                    _("Gunnery, focus on our ennemy if you want to see our homeplanet again.{}\n")]
        self.msg += random.choice(msg)

    def on_new_turn(self):
        self.msg += _("{player.name}'s turn begins... {{}}\n").format(player=self.current_player)


    def move_ship(self, ship, i, j):
        self.battle_grid.move_sprite(ship, i, j)
        ship.move_completed = True
        self.reachable_cells = None
        self.predecessor = None



class GamePhase(object):
    def __init__(self, battle):
        self.battle = battle
        self.battle_grid = battle.battle_grid

    def on_enter(self):
        pass

    def on_mouse_release(self, i, j, x, y):
        pass

    def on_mouse_motion(self, x, y):
        pass

    def on_key_release(self, symbol, modifiers):
        pass

    def on_command_finished(self):
        pass

    def on_end_of_turn(self):
        pass

    def on_end_of_round(self):
        pass

    def on_exit(self):
        "All game phase, when they exit, display the buffered message."
        if self.battle.msg != PROMPT:
            self.battle.log_info.prepend_text(self.battle.msg)
            self.battle.msg = PROMPT

class StaticGamePhase(GamePhase):
    """
    A phase of game which is not a transition.
    So it's either idle state or shipselected phase.
    """
    def __init__(self, battle):
        super(StaticGamePhase, self).__init__(battle)

    def on_end_of_round(self):
        player = self.battle.current_player
        self.battle_grid.clear_ships_highlight(player.fleet)
        player.on_end_of_turn()
        self.battle.current_player = next(self.battle.players_turn)
        # If there are no more ships in the fleet, it's game over.
        if not self.battle.current_player.fleet:
            game_over_scene = cocos.scene.Scene(game_over.GameOver())
            director.replace(FadeBLTransition(game_over_scene, duration = 2))
        self.battle.current_player.reset_ships_turn()
        self.battle.on_new_turn()
        if self.battle.current_player.brain is None: # Human player
            self.battle_grid.highlight_player(self.battle.current_player)
            self.battle.change_game_phase(Idle(self.battle))
        else:
            self.battle.change_game_phase(IATurn(self.battle))


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

    def on_mouse_motion(self, x, y):
        entity = self.battle_grid.get_entity(x, y)
        if entity is not None:
            self.battle.ship_info.set_model(entity)
        else:
            self.battle.ship_info.remove_model()

    def on_key_release(self, symbol, modifiers):
        if symbol == key.RETURN:
            self.on_end_of_round()
            return True

class ShipSelected(StaticGamePhase):
    def __init__(self, battle):
        super(ShipSelected, self).__init__(battle)

    def on_enter(self):
        self.battle.select_ship()
        # We keep a reference to the selected ship, so if we change ship
        # We can clear the "old" selected ship in the on_exit method.
        self.selected = self.battle.selected
        self.battle.ship_info.set_model(self.selected)
        ship_menu = gui.MenuLayer(self.battle, self.selected,
                                    main.SCREEN_W - INFO_WIDTH - 2*MARGIN,
                                    MENU_BUTTON_HEIGHT)
        ship_menu.x = MARGIN
        self.battle.add(ship_menu, z=5, name="ship_menu")

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
                weapon = self.selected.weapon
                if weapon.temperature >= 100.:
                    msg = PROMPT + _("""{{font_name 'Classic Robot'}}
{{font_size 10}}{{color [255, 0, 0, 255]}}Overheating, {weapon.name} needs some time before next use.
""") .format(weapon=weapon)
                    self.battle.log_info.prepend_text(msg)
                else:
                    self.battle.push_game_phase(Attack(self.battle, entity))
            # Otherwise display info on this ship
            else:
                self.battle.ship_info.set_model(entity)


        # If we clicked on our selected ship or in an empy cell, deselect the ship.
        else: # entity is self.selected or :
            self.battle.change_game_phase(Idle(self.battle))

    def on_mouse_motion(self, x, y):
        entity = self.battle_grid.get_entity(x, y)
        if entity is not None:
            self.battle.ship_info.set_model(entity)
        else:
            self.battle.ship_info.set_model(self.selected)

    def on_key_release(self, symbol, modifiers):
        if symbol == key.RETURN:
            self.on_end_of_round()
            return True
        return False

    def on_end_of_round(self):
        # Is this needed?
        self.battle.change_game_phase(Idle(self.battle))
        super(ShipSelected, self).on_end_of_round()

    def on_exit(self):
        super(StaticGamePhase, self).on_exit()
        self.battle.deselect_ship(self.selected)
        self.battle.clear_reachable_cells()
        self.battle.deselect_targets()
        self.battle.remove("ship_menu")


class Attack(GamePhase):
    def __init__(self, battle, ennemy):
        super(Attack, self).__init__(battle)
        self.ennemy = ennemy

    def on_enter(self):
        self.battle.submit(commands.AttackCommand(self.battle.selected,
                                                            self.ennemy))
        if not self.battle.selected.boost_used:
            # If no boost yet used, disable the Boost Weapon
            self.battle.get("ship_menu").get("boost_menu").disable(2)

    def on_command_finished(self):
        self.battle.pop_game_phase()

    def on_exit(self):
        super(Attack, self).on_exit()
        self.battle.selected.attack_completed = True
        self.battle.deselect_targets()
        self.battle.clear_reachable_cells()
        self.battle.show_reachable_cells()

class Move(GamePhase):
    def __init__(self, battle, i, j):
        super(Move, self).__init__(battle)
        self.i, self.j = i, j

    def on_enter(self):
        self.battle.submit(commands.MoveCommand(self.battle.selected,
                                                        self.i, self.j))
        self.battle.clear_reachable_cells()
        self.battle.deselect_targets()
        if not self.battle.selected.boost_used:
            # If no boost yet used, disable the Boost Speed
            self.battle.get("ship_menu").get("boost_menu").disable(1)

    def on_command_finished(self):
        self.battle.pop_game_phase()

    def on_exit(self):
        super(Move, self).on_exit()
        self.battle.select_ship()

class IATurn(StaticGamePhase):
    def __init__(self, battle):
        super(IATurn, self).__init__(battle)

    def on_enter(self):
        self.battle.current_player.brain.think()

    def on_command_finished(self):
        if self.battle.msg != PROMPT:
            self.battle.log_info.prepend_text(self.battle.msg)
            self.battle.msg = PROMPT

    def on_exit(self):
        super(IATurn, self).on_exit()
