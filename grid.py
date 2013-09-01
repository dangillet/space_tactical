import math
from random import shuffle, randint
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.csgraph import dijkstra

import cocos
from cocos.director import director
from cocos.actions import MoveTo, InstantAction, Repeat, RotateBy
import pyglet
from pyglet.gl import *

import entity, simplexnoise

CELL_WIDTH = 50
ROW, COL = 18, 30
DIST = 5


class GridLayer(cocos.layer.Layer):
    def __init__(self, battle):
        self.is_event_handler = True
        super( GridLayer, self ).__init__()
        # Batch for the grid
        self.grid_batch = pyglet.graphics.Batch()
        # Batch for the asteroids
        self.sprite_batch = cocos.batch.BatchNode()
        self.add(self.sprite_batch)
        
        # Keep a reference to the battle object
        self.battle = battle
        
        # Grid squares and borders
        self.squares = [[None for _ in range(ROW)] for _ in range(COL)]
        self.borders = []
        
        self.entities = {'asteroids' : [], 'ships': []}
        
        # Obstacle on map
        # self.entities['asteroids']=[(3,4), (5,6), (3,5), (3,6), (4,6), (4,7), (4,8)]
        # Add some random obstacles
        #from itertools import product
        #coord_gen = product(xrange(COL-1), xrange(ROW-1))
        #coords = list(coord_gen)
        # How many walls? They will all be different. So not bigger than grid size!
        # This is a bit slow on start, but won't be part of the game, so who cares?
        #shuffle(coords)
        OCTAVE, PERSISTENCE, FREQ = 4, 0.6, 10
        SPARSITY = 165
        noise = np.zeros(shape=(COL, ROW))
        for x, y in np.ndindex(COL, ROW):
            v = simplexnoise.scaled_octave_noise_2d(OCTAVE, PERSISTENCE, FREQ, 0, 255, x, y)
            c = v - SPARSITY
            if c<0: c = 0
            noise[x][y] = 255 - (math.pow(0.1, c) * 255)
        self.entities['asteroids']= zip(*np.where(noise> 0.))

        
        # Background image
        img=pyglet.resource.image("outer-space.jpg")
        self.bg_texture = pyglet.image.TileableTexture.create_for_image(img)

        # We construct the quads and store them for future reference
        for row in range(ROW):
            for col in range(COL):
                self.squares[col][row] = self.grid_batch.add(4, GL_QUADS, pyglet.graphics.OrderedGroup(1),
                            ('v2f', (col*CELL_WIDTH, row*CELL_WIDTH, col*CELL_WIDTH, (row+1)*CELL_WIDTH,
                                     (col+1)*CELL_WIDTH, (row+1)*CELL_WIDTH, (col+1)*CELL_WIDTH, row*CELL_WIDTH)),
                            ('c4B', (128, 128, 128, 0) * 4))
        # We set a different color for the walls
        for x,y in self.entities['asteroids']:
            #self.squares[x][y].colors = [0, 0, 128, 150] * 4
            asteroid = entity.Asteroid(self.from_grid_to_pixel(x,y))
            asteroid.do(Repeat(RotateBy(randint(-60, 60), 1)))
            self.sprite_batch.add(asteroid)

        # We build the lines of the grid.
        lines=[]
        # The horizontal lines first
        for row in range(ROW+1):
            lines.extend((0., row*CELL_WIDTH, COL*CELL_WIDTH, row*CELL_WIDTH))
        self.borders.append(self.grid_batch.add((ROW+1)*2, GL_LINES, pyglet.graphics.OrderedGroup(2),
                    ('v2f', lines),
                    ('c4B', (255, 0, 0, 100) * (ROW+1)*2))
                    )
        # And the vertical lines
        lines=[]
        for col in range(COL+1):
            lines.extend((col*CELL_WIDTH, 0., col*CELL_WIDTH, ROW*CELL_WIDTH))
        self.borders.append(self.grid_batch.add((COL+1)*2, GL_LINES, pyglet.graphics.OrderedGroup(2),
                    ('v2f', lines),
                    ('c4B', (255, 0, 0, 100) * (COL+1)*2))
                    )
        
        # We build the distance matrix.
        self.dist_mat = DistanceMatrix(ROW, COL)
        for asteroid in self.entities['asteroids']:
            self.dist_mat.add_obstacle(*asteroid)
        
        # Move a bit the grid, so it doesn't stay stucked at the bottom left of the screen
        self.anchor = (50,50)
        self.position = (50,50)
    
    def draw(self, *args, **kwargs):
        glPushMatrix()
        self.transform()
        # Draw the background as a tileable texture over the grid.
        grid_width, grid_height = COL*CELL_WIDTH, ROW*CELL_WIDTH
        self.bg_texture.blit_tiled(0, 0, 0, grid_width, grid_height)
        # Draw the rest
        self.grid_batch.draw()
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
                if (col,row) not in self.entities['asteroids']:
                    self.squares[col][row].colors = [128, 128, 128, 0] * 4
                else:
                    self.squares[col][row].colors = [0, 0, 128, 150] * 4
    
    def move_sprite(self, sprite, i, j):
        "Move sprite to the selected grid location"
        if self._is_invalid_grid(i,j):
            return
        # Reconstruct the path
        i0, j0 = self.from_pixel_to_grid(*(sprite.position))
        path = self.dist_mat.reconstruct_path(i0, j0, i, j, sprite.predecessor)
        
        # Initialize the move with an empty action
        move = InstantAction()
        # Sequence moves to the next grid
        for m, n in path:
            move = move + MoveTo(self.from_grid_to_pixel(m, n), 0.3)
        sprite.do(move)
        # Update the position in entities['ships']
        self.entities['ships'].remove( (i0, j0) )
        self.entities['ships'].append( (i, j) )
            
        # Delete the reachable cells
        self.clear_cells(sprite.reachable_cells)
        del sprite.reachable_cells
        del sprite.predecessor
        
    def from_grid_to_pixel(self, i, j):
        "Converts grid position to the center position of the cell in pixel"
        return (i*CELL_WIDTH + CELL_WIDTH/2, j*CELL_WIDTH + CELL_WIDTH/2)
        
    def get_reachable_cells(self, i, j, distance):
        """
        Forward this to the distance matrix. Remove any other ships from
        reachable cells so we can move through ships but not stop on another one.
        """
        r_cells, predecessor = self.dist_mat.get_reachable_cells(i, j, distance)
        r_cells = [cell for cell in r_cells if cell not in self.entities['ships']]
        return r_cells, predecessor
    
    def get_random_free_cells(self, side):
        "Returns a generator giving cells without obstacle in an area close to a border"
        if side == 0:
            left, right, top, bottom = 0, 3, ROW*2/3, ROW/3
        elif side == 1:
            left, right, top, bottom = COL-3, COL-1, ROW*2/3, ROW/3
        elif side == 2:
            left, right, top, bottom = COL/3, COL*2/3, ROW-1, ROW-3
        else:
            left, right, top, bottom = COL/3, COL*2/3, 3, 0
        coords = [(x, y) for x in range(left, right) for y in range(bottom, top) if (x, y) not in self.entities['asteroids']]
        shuffle(coords)
        return coords



        i, j = randint(0, COL-1), randint (0, ROW-1)
        while (i,j) in self.entities['asteroids']:
            i, j = randint(0, COL-1), randint (0, ROW-1)
        return (i,j)
    
    def from_cell_number_to_coord(self, number):
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
    
    def from_coord_to_cell_number(self, i, j):
        "See _from_cell_number_to_coord. Does the opposite"
        return i + j * COL
    
    def get_entity(self, x, y):
        "Return the entity at position x, y"
        for z, child in self.children:
            # Do not look for the sprite_batch which contains only obstacles
            if isinstance(child, cocos.batch.BatchNode): continue
            rect = child.get_AABB()
            if rect.contains(x, y):
                return child
        return None
                    
    def on_mouse_press(self, x, y, button, modifiers):
        # Get the virtual coords, in case window was resized.
        x, y = director.get_virtual_coordinates(x, y)
        # Transform mouse pos in local coord
        x, y = self.point_to_local((x,y))
        i, j = self.from_pixel_to_grid(x, y)
        if i is None or j is None: return
        self.battle.on_mouse_press(i, j, x, y)
        
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
            
    def on_key_press(self, symbol, modifiers):
        # Nothing to do for the moment
        pass

    def add_player_fleet(self, player, side):
        """Add the ships from the player"""
        starting_cells = self.get_random_free_cells(side)
        for a, ship in enumerate(player.fleet):
            i, j = starting_cells[a]
            self.entities['ships'].append((i, j))
            x, y = self.from_grid_to_pixel(i,j)
            ship.position = (x, y)
            self.add(ship)

class DistanceMatrix(object):
    """
    Distance matrix where we can add obstacles.
    Can also be used to recontruct a shortest path, giving the predecessor matrix.
    """
    def __init__(self, row, col):
        self.row, self.col = row, col
        self.dist_mat = lil_matrix((self.row*self.col, self.row*self.col))
        # Construct distance matrix for an empty grid
        # cost to the distance matrix. Straight = 1; Diag = sqrt(2)
        for j in range(self.row):
            for i in range(self.col):
                for x_offset in (-1,0,1):
                    for y_offset in (-1,0,1):
                        if self.valid_grid(i+x_offset, j+y_offset):
                            if x_offset and y_offset:
                                self.dist_mat[ i + j*self.col, (i+x_offset) + (j+y_offset) * self.col] = math.sqrt(2)
                            elif x_offset or y_offset:
                                self.dist_mat[i + j*self.col, (i+x_offset) + (j+y_offset) * self.col] = 1

        # And convert this huge matrix to a sparse matrix.
        self.dist_mat = self.dist_mat.tocsc()
    
    def valid_grid(self, xo, yo):     
        "Helper function to check if we are in the grid and not in a wall."
        in_grid = not xo<0 and not yo<0 and xo<self.col and yo<self.row
        return in_grid
    
    def add_obstacle(self, i, j):
        "Add obstacle at position i,j"
        dist_mat = self.dist_mat.tolil()
        grid_number = self.from_coord_to_cell_number(i, j)

        # Check if the new obstacle is set at a diagonal from another obstacle.
        # Example: we add an obstacle at 4 and there was already an obstacle at 8:
        # -------------
        # | 6 | 7 | X |
        # -------------
        # | 3 | X | 5 |
        # -------------
        # | 0 | 1 | 2 |
        # -------------
        # Deny movements between 5 and 7.
        for x in (-1, 1):
            for y in (-1, 1):
                if self.valid_grid(i+x, j+y) and dist_mat[grid_number, self.from_coord_to_cell_number(i+x, j+y)] == 0:
                    dist_mat[self.from_coord_to_cell_number(i, j+y), self.from_coord_to_cell_number(i+x, j)] = 0
                    dist_mat[self.from_coord_to_cell_number(i+x, j), self.from_coord_to_cell_number(i, j+y)] = 0
                    
        # Set to 0 the whole col at grid_num as we cannot move into this position.
        dist_mat[: ,grid_number] = 0
        
        # Set to 0 the whole row at grid_num as this is an obstacle and we cannot move
        # from this position.
        dist_mat[grid_number, :] = 0    
   
        # And update the distance matrix in csc format
        self.dist_mat = dist_mat.tocsc()
        
    def from_cell_number_to_coord(self, number):
        """
        Cells are numbered in ascending order starting from 0 at the bottom
        left and increasing by column and then by row.
        -------------
        | 3 | 4 | 5 |
        -------------
        | 0 | 1 | 2 |
        -------------
        This function returns the coordinates from a cell number.
        So cell 5 will return (1,1)
        """
        return (number%self.col, number//self.col)
    
    def from_coord_to_cell_number(self, i, j):
        "See _from_cell_number_to_coord. Does the opposite"
        return i + j * self.col
    
    def get_reachable_cells(self, i, j, distance):
        "Returns all the cells reachable from (i, j) and the predecessor matrix"
        origin = self.from_coord_to_cell_number(i, j)
        dist, predecessor = dijkstra(self.dist_mat, indices=origin, return_predecessors=True)
        # Only take those where dist is reachable
        dist = np.argwhere(dist <= distance).flatten()
        # And convert it to a list of grid coordinates
        dist = map(self.from_cell_number_to_coord, dist)
        return dist, predecessor

    def reconstruct_path(self, i0, j0, i, j, predecessor):
        "Reconstruct the shortest path going from (i0, j0) to (i, j)."
        origin = self.from_coord_to_cell_number(i0, j0)
        dest = self.from_coord_to_cell_number(i,j)
        path = None
        if origin != dest:
            # Path is contructed in reversed order. From dest to origin.
            path=[(i, j)]
            
            while predecessor[dest] != origin:
                step_grid = predecessor[dest]
                path.append(self.from_cell_number_to_coord(step_grid))
                dest = step_grid
        return reversed(path)
                
