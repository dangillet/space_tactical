from itertools import cycle
import grid, entity

class Battle(object):
    def __init__(self):
        self.players = []
        #How many players?
        for i in range(2):
            player = entity.Player("Player %d" % i)
            self.players.append(player)
            # How many ships ?
            for _ in range(2):
                ship = entity.Ship("ship.png")
                ship.scale = float(grid.CELL_WIDTH) / ship.width
                player.add_ship(ship)
        self.grid = grid.GridLayer(self)
        
        # Player list
        self.players_turn = cycle(self.players)
        # Add the ships to the grid
        for player in self.players:
            self.grid.add_player_fleet(player)
        # Select the first player from the list as the current one
        self.current_player = next(self.players_turn)
        self.grid.highlight_player(self.current_player)
        # Selected object from the grid
        self.selected = None
    
    def on_mouse_press(self, i, j, x, y):
        """
        Called by the grid when a grid square is clicked.
        The game logic happens here.
        """
        # If we click while something is selected, move it there.
        if self.selected:
            # If we clicked on our selected ship, deselect it and delete the reachable cells
            if self.selected.get_AABB().contains(x, y):
                # Delete the reachable cells
                self.grid.clear_cells(self.selected.reachable_cells)
                del self.selected.reachable_cells
                del self.selected.predecessor
                self.selected = None
                return
            # If we click outside of the reachable cells, ignore.
            if (i,j) not in self.selected.reachable_cells:
                return
                
            self.selected.turn_completed = True
            self.grid.clear_cells([self.grid.from_pixel_to_grid(*(self.selected.position))])
            self.grid.move_sprite(self.selected, i, j)
            self.end_turn()
            self.selected = None
            return
        
        if self.selected is None:
            entity = self.grid.get_entity(x, y)
            if entity is not None and entity.player == self.current_player \
                    and not entity.turn_completed:
                self.selected = entity
        # We clicked on a ship, so calculate and highlight the reachable cells
        if self.selected:
            # Compute the cell number
            self.selected.reachable_cells, self.selected.predecessor = self.grid.get_reachable_cells(i, j, grid.DIST)
            self.grid.highlight_cells(self.selected.reachable_cells, [128, 0, 128, 100])
        self.end_turn()
    
    def end_turn(self):
        """If all ships played, change player"""
        if self.current_player.turn_completed():
            self.current_player.reset_ships_turn()
            self.current_player = next(self.players_turn)
            self.grid.highlight_player(self.current_player)
