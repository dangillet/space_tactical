import random
from itertools import cycle
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
        # If we click while something is selected, move it there.
        if self.selected:
            # If we clicked on our selected ship, deselect it.
            # Delete the reachable cells and the targets
            if self.selected.get_AABB().contains(x, y):
                # Delete the reachable cells
                self.grid.clear_cells(self.selected.reachable_cells)
                # If targets are selected
                self.deselect_targets()
                del self.selected.reachable_cells
                del self.selected.predecessor
                self.selected = None
                return
            # If we click outside of the reachable cells, ignore.
            if (i,j) not in self.selected.reachable_cells:
                return

            self.grid.move_sprite(self.selected, i, j)
            self.end_turn()
            return
        
        if self.selected is None:
            entity = self.grid.get_entity(x, y)
            if entity is not None and entity.player == self.current_player \
                    and not entity.turn_completed:
                self.selected = entity
                # We clicked on a ship, so calculate and highlight the reachable cells
                # Compute the cell number
                self.selected.reachable_cells, self.selected.predecessor = self.grid.get_reachable_cells(i, j, self.selected.distance)
                self.grid.highlight_cells(self.selected.reachable_cells, [128, 0, 128, 100])
                # Get targets in range
                self.targets = self.grid.get_targets(self.selected)
                self.grid.highlight_ships(self.targets, [255, 0, 0, 100])

    
    def deselect_targets(self):
        "Deselect the targeted ships"
        if self.targets:
            self.grid.clear_ships_highlight(self.targets)
            self.targets = []
    
    def end_turn(self):
        """End the turn of the current ship. If all ships played, change player"""
        if self.selected is not None:
            self.selected.turn_completed = True
            self.grid.clear_cells([self.grid.from_pixel_to_grid(*(self.selected.position))])
            if hasattr(self.selected, "reachable_cells"):
                self.grid.delete_reachable_cells(self.selected)
            # If targets are selected
            self.deselect_targets()
            self.selected = None
        if self.current_player.turn_completed():
            self.current_player.reset_ships_turn()
            self.current_player = next(self.players_turn)
            self.grid.highlight_player(self.current_player)
