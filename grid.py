
import math
from itertools import cycle
from random import shuffle, randint
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.csgraph import dijkstra

import cocos
from cocos.director import director
from cocos.actions import MoveTo, InstantAction
import pyglet
from pyglet.gl import *

CELL_WIDTH = 50
ROW, COL = 16, 30
DIST = 5


class GridLayer(cocos.layer.Layer):
    def __init__(self, players):
        self.is_event_handler = True
        super( GridLayer, self ).__init__()
        # Just for this demo. Remove when we'll have some scheduled methods.
        self.schedule( lambda x: 0 )
        self.batch = pyglet.graphics.Batch()
        
        # Grid squares and borders
        self.squares = [[None for _ in range(ROW)] for _ in range(COL)]
        self.borders = []
        
        # Obstacle on map
        # self.walls=[(3,4), (5,6), (3,5), (3,6), (4,6), (4,7), (4,8)]
        # Add some random obstacles
        from itertools import product
        coord_gen = product(xrange(COL-1), xrange(ROW-1))
        coords = list(coord_gen)
        # How many walls? They will all be different. So not bigger than grid size!
        # This is a bit slow on start, but won't be part of the game, so who cares?
        shuffle(coords)
        self.walls= coords[:100]
        
        # Background image
        img=pyglet.resource.image("outer-space.jpg")
        self.bg_texture = pyglet.image.TileableTexture.create_for_image(img)

        # We construct the quads and store them for future reference
        for row in range(ROW):
            for col in range(COL):
                self.squares[col][row] = self.batch.add(4, GL_QUADS, pyglet.graphics.OrderedGroup(1),
                            ('v2f', (col*CELL_WIDTH, row*CELL_WIDTH, col*CELL_WIDTH, (row+1)*CELL_WIDTH,
                                     (col+1)*CELL_WIDTH, (row+1)*CELL_WIDTH, (col+1)*CELL_WIDTH, row*CELL_WIDTH)),
                            ('c4B', (128, 128, 128, 0) * 4))
        # We set a different color for the walls
        for x,y in self.walls:
            self.squares[x][y].colors = [0, 0, 128, 150] * 4

        # We build the lines of the grid.
        lines=[]
        # The horizontal lines first
        for row in range(ROW+1):
            lines.extend((0., row*CELL_WIDTH, COL*CELL_WIDTH, row*CELL_WIDTH))
        self.borders.append(self.batch.add((ROW+1)*2, GL_LINES, pyglet.graphics.OrderedGroup(2),
                    ('v2f', lines),
                    ('c4B', (255, 0, 0, 100) * (ROW+1)*2))
                    )
        # And the vertical lines
        lines=[]
        for col in range(COL+1):
            lines.extend((col*CELL_WIDTH, 0., col*CELL_WIDTH, ROW*CELL_WIDTH))
        self.borders.append(self.batch.add((COL+1)*2, GL_LINES, pyglet.graphics.OrderedGroup(2),
                    ('v2f', lines),
                    ('c4B', (255, 0, 0, 100) * (COL+1)*2))
                    )
        
        # We build the distance matrix.
        self.dist_mat = lil_matrix((ROW*COL,ROW*COL))
        def valid_grid(xo, yo):     # Helper function to check if we are in the grid and not in a wall
            in_grid = not xo<0 and not yo<0 and xo<COL and yo<ROW
            in_wall = (xo,yo) in self.walls
            return in_grid and not in_wall
        # Iterate over every square and check the 8 directions. If it's a valid region, add its movement
        # cost to the distance matrix. Straight = 1; Diag = sqrt(2)
        for j in range(ROW):
            for i in range(COL):
                for x_offset in (-1,0,1):
                    for y_offset in (-1,0,1):
                        if valid_grid(i+x_offset, j+y_offset):
                            if x_offset and y_offset:
                                # Allow diag if no obstacle up/down and left/right
                                if not((i+x_offset, j) in self.walls and (i, j+y_offset) in self.walls):
                                    self.dist_mat[ i + j*COL, (i+x_offset) + (j+y_offset) * COL] = math.sqrt(2)
                            elif x_offset or y_offset:
                                self.dist_mat[i + j*COL, (i+x_offset) + (j+y_offset) * COL] = 1
        # And convert this huge matrix to a sparse matrix.
        self.dist_mat = self.dist_mat.tocsc()
        
        # Move a bit the grid, so it doesn't stay stucked at the bottom left of the screen
        self.anchor = (50,50)
        self.position = (50,50)
        
        # Player list
        self.players = cycle(players)
        for player in players:
            self.add_player_fleet(player)
        # Select the first player from the list as the current one
        self.player_turn = next(self.players)
        self.highlight_player(self.player_turn)
        # Selected object from the grid
        self.selected = None
        
    
    def draw(self, *args, **kwargs):
        glPushMatrix()
        self.transform()
        # Draw the background as a tileable texture over the grid.
        grid_width, grid_height = COL*CELL_WIDTH, ROW*CELL_WIDTH
        self.bg_texture.blit_tiled(0, 0, 0, grid_width, grid_height)
        # Draw the rest
        self.batch.draw()
        glPopMatrix()
    
    def from_pixel_to_grid(self, x, y):
        "Compute the cell coords from pixel coords"
        i, j = (int(x // CELL_WIDTH),
            int(y // CELL_WIDTH))
        # Did we click on the grid?
        if self._is_invalid_grid(i, j):
            return (None, None)
        return i, j
    
    def _is_invalid_grid(self, i, j):
        "Check if grid coords are in the grid"
        return i < 0 or j < 0 or not i < COL or not j < ROW
        
    def clear_grid(self):
        "Removes highlights from the grid"
        for row in range(ROW):
            for col in range(COL):
                if (col,row) not in self.walls:
                    self.squares[col][row].colors = [128, 128, 128, 0] * 4
                else:
                    self.squares[col][row].colors = [0, 0, 128, 150] * 4
    
    def move_sprite(self, sprite, i, j):
        "Move sprite to the selected grid location"
        if self._is_invalid_grid(i,j):
            return
        if (i,j) not in self.selected.reachable_cells:
            return
        # Reconstruct the path
        dest = self._from_coord_to_cell_number(i,j)
        origin_cell = self.from_pixel_to_grid(*(sprite.position))
        origin = self._from_coord_to_cell_number(*origin_cell)
        if origin != dest:
            # Path is contructed in reversed order. From dest to origin.
            path=[dest]
            
            while sprite.predecessor[dest] != origin:
                step_grid = sprite.predecessor[dest]
                path.append(step_grid)
                dest = step_grid
            # Initialize the move with an empty action
            move = InstantAction()
            # Sequence moves to the next grid
            for destination in reversed(path):
                move = move + MoveTo(self.from_grid_to_pixel(*self._from_cell_number_to_coord(destination)), 0.3)
            sprite.do(move)
            
        # Delete the reachable cells and deselect the sprite
        self.clear_cells(self.selected.reachable_cells)
        del self.selected.reachable_cells
        del self.selected.predecessor
        self.selected = None
        
    
    def from_grid_to_pixel(self, i, j):
        "Converts grid position to the center position of the cell in pixel"
        return (i*CELL_WIDTH + CELL_WIDTH/2, j*CELL_WIDTH + CELL_WIDTH/2)
        
    def get_reachable_cells(self, origin, distance):
        "Returns all the cells reachable from origin and the predecessor matrix"
        dist, predecessor = dijkstra(self.dist_mat, indices=origin, return_predecessors=True)
        # Only take those where dist is reachable
        return np.argwhere(dist <= DIST).flatten(), predecessor
    
    def get_random_free_cell(self):
        "Returns a cell without obstacle"
        i, j = randint(0, COL-1), randint (0, ROW-1)
        while (i,j) in self.walls:
            i, j = randint(0, COL-1), randint (0, ROW-1)
        return (i,j)
    
    def _from_cell_number_to_coord(self, number):
        """
        Cells are numbered in ascending order starting from 0 at the bottom
        left and increasing by column and then by row.
        -------------
        | 4 | 5 | 6 |
        -------------
        | 0 | 1 | 2 |
        -------------
        This function returns the coordinates from a cell number.
        So cell 5 will return (1,1)
        """
        return (number%COL, number//COL)
    
    def _from_coord_to_cell_number(self, i, j):
        "See _from_cell_number_to_coord. Does the opposite"
        return i + j * COL
    
    def on_mouse_press(self, x, y, button, modifiers):
        # Get the virtual coords, in case window was resized.
        x, y = director.get_virtual_coordinates(x, y)
        i, j = self.from_pixel_to_grid(*self.point_to_local((x, y)) )
        if i is None or j is None: return

        # If we click while something is selected, move it there.
        if self.selected:
            self.selected.turn_completed = True
            self.move_sprite(self.selected, i, j)
            self.end_turn()
            return
        
        # Did we click on the ship?
        # Transform mouse pos in local coord
        x,y = self.point_to_local((x,y))
        for z, child in self.children:
            if child.player == self.player_turn and not child.turn_completed:
                rect = child.get_AABB()
                if rect.contains(x, y):
                    self.selected = child
        
        # We clicked on a ship, so calculate and highlight the reachable cells
        if self.selected:
            # Compute the cell number
            origin = i + j * COL
            reachable_cells, predecessor = self.get_reachable_cells(origin, DIST)
            self.selected.reachable_cells = map(self._from_cell_number_to_coord, reachable_cells)
            self.selected.predecessor = predecessor
            self.highlight_cells(self.selected.reachable_cells, [128, 0, 128, 100])
        
        self.end_turn()
        
    def highlight_cells(self, cells, color):
        """Highlight the cells in the list in the given color."""
        for i, j in cells:
                self.squares[i][j].colors = color * 4
    
    def highlight_player(self, player):
        """Highlight the player ships"""
        cells = []
        for ship in player.fleet:
            cells.append(self.from_pixel_to_grid(*(ship.position)))
        self.highlight_cells(cells, [0, 128, 128, 100])
    
    def clear_cells(self, cells):
        """Remove any highlight from the cells"""
        self.highlight_cells(cells, [0, 0, 0, 0])
    
    def end_turn(self):
        """If all ships played, change player"""
        if self.player_turn.turn_completed():
            self.player_turn.reset_ships_turn()
            self.player_turn = next(self.players)
            self.highlight_player(self.player_turn)
            
    
    def on_key_press(self, symbol, modifiers):
        # Nothing to do for the moment
        pass

    def add_player_fleet(self, player):
        """Add the ships from the layer"""
        for ship in player.fleet:
            i, j = self.get_random_free_cell()
            x, y = self.from_grid_to_pixel(i,j)
            ship.position = (x, y)
            self.add(ship)
