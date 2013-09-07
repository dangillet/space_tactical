import math
from random import shuffle, randint
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.csgraph import dijkstra

import cocos
import cocos.euclid as eu
from cocos.director import director
from cocos.actions import MoveTo, InstantAction, Repeat, RotateBy, RotateTo, CallFunc, CallFuncS

import pyglet
from pyglet.window import key
from pyglet.gl import *

import entity, simplexnoise, library

CELL_WIDTH = 50

PLAYER_TURN = [128, 128, 0, 100]
SHIP_SELECTED = [250, 250, 0, 100]
REACHABLE_CELLS = [128, 0, 128, 100]
TARGET = [255, 0, 0, 100]
CLEAR_CELL = [0, 0, 0, 0]

class GridLayer(cocos.layer.ScrollableLayer):
    def __init__(self, battle, map_kwargs):
        self.is_event_handler = True
        super( GridLayer, self ).__init__()
        # Batch for the grid
        self.grid_batch = pyglet.graphics.Batch()
        # Batch for the asteroids
        self.sprite_batch = cocos.batch.BatchNode()
        self.add(self.sprite_batch)
        
        self.col, self.row = map_kwargs['col'], map_kwargs['row']
        self.px_width = (self.col+2) * CELL_WIDTH
        self.px_height = (self.row+2) * CELL_WIDTH

        # Keep a reference to the battle object
        self.battle = battle
        
        # Grid squares and borders
        self.squares = [[None for _ in range(self.row)] for _ in range(self.col)]
        self.borders = []
        
        self.entities = {'asteroids' : [], 'ships': []}
        
        # Obstacle on map
        noise = np.zeros(shape=(self.col, self.row))
        for x, y in np.ndindex(self.col, self.row):
            v = simplexnoise.scaled_octave_noise_2d(
                map_kwargs['octave'],
                map_kwargs['persistance'],
                map_kwargs['freq'],
                0, 255,
                x + map_kwargs['x_off'],
                y + map_kwargs['y_off'])
            c = v - map_kwargs['sparsity']
            if c<0: c = 0
            noise[x][y] = 255 - (math.pow(map_kwargs['density'], c) * 255)
        self.entities['asteroids']= zip(*np.where(noise> 0.))

        
        # Background image
        img=pyglet.resource.image("outer-space.jpg")
        self.bg_texture = pyglet.image.TileableTexture.create_for_image(img)

        # We construct the quads and store them for future reference
        for row in range(self.row):
            for col in range(self.col):
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
        for row in range(self.row+1):
            lines.extend((0., row*CELL_WIDTH, self.col*CELL_WIDTH, row*CELL_WIDTH))
        self.borders.append(self.grid_batch.add((self.row+1)*2, GL_LINES, pyglet.graphics.OrderedGroup(2),
                    ('v2f', lines),
                    ('c4B', (255, 0, 0, 100) * (self.row+1)*2))
                    )
        # And the vertical lines
        lines=[]
        for col in range(self.col+1):
            lines.extend((col*CELL_WIDTH, 0., col*CELL_WIDTH, self.row*CELL_WIDTH))
        self.borders.append(self.grid_batch.add((self.col+1)*2, GL_LINES, pyglet.graphics.OrderedGroup(2),
                    ('v2f', lines),
                    ('c4B', (255, 0, 0, 100) * (self.col+1)*2))
                    )
        
        # We build the distance matrix.
        self.dist_mat = DistanceMatrix(self.row, self.col)
        for asteroid in self.entities['asteroids']:
            self.dist_mat.add_obstacle(*asteroid)
        
        self.bindings = { #key constant : button name
            key.LEFT:'left',
            key.RIGHT:'right',
            key.UP:'up',
            key.DOWN:'down',
            key.PLUS:'zoomin',
            key.MINUS:'zoomout'
            }
        self.buttons = { #button name : current value, 0 not pressed, 1 pressed
            'left':0,
            'right':0,
            'up':0,
            'down':0,
            'zoomin':0,
            'zoomout':0
            }
        self.schedule(self.step)
        
    def on_enter(self):
        super(GridLayer,self).on_enter()
        self.scroller = self.get_ancestor(cocos.layer.ScrollingManager)
        self.scroller.fastness = 300
        w, h = director.get_window_size()
        self.focus_position = eu.Point2(w/2, h/2)
    
    def draw(self, *args, **kwargs):
        glPushMatrix()
        self.transform()
        # Draw the background as a tileable texture over the grid.
        grid_width, grid_height = self.col*CELL_WIDTH, self.row*CELL_WIDTH
        self.bg_texture.blit_tiled(0, 0, 0, grid_width, grid_height)
        # Draw the rest
        self.grid_batch.draw()
        glPopMatrix()
    
    def step(self, dt):
        buttons = self.buttons
        move_dir = eu.Vector2(buttons['right']-buttons['left'],
                              buttons['up']-buttons['down'])
        changed = False
        if move_dir:
            new_pos = self.focus_position + self.scroller.fastness*dt*move_dir.normalize()
            new_pos = self.clamp(new_pos)
            self.focus_position = new_pos
            changed = True
        
        if changed:
            self.update_focus()
    
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
        return i < 0 or j < 0 or not i < self.col or not j < self.row
        
    def clear_grid(self):
        "Removes highlights from the grid"
        for row in range(self.row):
            for col in range(self.col):
                if (col,row) not in self.entities['asteroids']:
                    self.squares[col][row].colors = [128, 128, 128, 0] * 4
                else:
                    self.squares[col][row].colors = [0, 0, 128, 150] * 4
    
    def rotate_to_bearing(self, m, n ,ox, oy):
        "Returns a RotateTo action from (ox, oy) towards (m, n)"
        # Compute the angle to the next grid.
        angle = math.degrees(math.atan2(n - oy, m - ox))
        # Bearing with 0 for N, 90 for E, 180 for S and 270 for W
        bearing = (90 - angle) % 360
        return RotateTo(bearing, 0.1)
    
    def move_sprite(self, sprite, i, j):
        "Move sprite to the selected grid location"
        if self._is_invalid_grid(i,j):
            return
        
        i0, j0 = self.from_pixel_to_grid(*(sprite.position))
        self.clear_cell(i0, j0)
        # Reconstruct the path
        path = self.dist_mat.reconstruct_path(i0, j0, i, j, self.battle.predecessor)
        
        # Initialize the move with an empty action
        move = InstantAction()
        # Sequence moves to the next grid
        ox, oy = i0, j0
        for m, n in path:
            
            move = ( move + 
                     self.rotate_to_bearing(m, n, ox, oy) +
                     MoveTo(self.from_grid_to_pixel(m, n), 0.3)
                    )
            ox, oy = m, n
        # And after the move, reset the selected ship
        end_of_move = CallFunc(self.battle.game_phase.on_move_finished)
        move = move + end_of_move
        sprite.do(move)
        # Update the position in entities['ships']
        self.entities['ships'].remove( (i0, j0) )
        self.entities['ships'].append( (i, j) )
        
    def delete_reachable_cells(self, sprite):
        "Delete the reachable cells"
        self.clear_cells(sprite.reachable_cells)
        del sprite.reachable_cells
        del sprite.predecessor
        
    def from_grid_to_pixel(self, i, j):
        "Converts grid position to the center position of the cell in pixel"
        return (i*CELL_WIDTH + CELL_WIDTH/2, j*CELL_WIDTH + CELL_WIDTH/2)
        
    def distance(self, objA, objB):
        "Returns the distance between two objects"
        i0, j0 = self.from_pixel_to_grid(*(objA.position))
        i1, j1 = self.from_pixel_to_grid(*(objB.position))
        return math.hypot((i0-i1), (j0-j1))
    
    def clear_los(self, objA, objB):
        "Check if both objects have a clear line of sight"
        i0, j0 = self.from_pixel_to_grid(*(objA.position))
        i1, j1 = self.from_pixel_to_grid(*(objB.position))
        los = library.get_line(i0, j0, i1, j1)
        for cell in los:
            if cell in self.entities['asteroids']:
                return False
        return True
        
    def get_reachable_cells(self, i, j, speed):
        """
        Forward this to the distance matrix. Remove any other ships from
        reachable cells so we can move through ships but not stop on another one.
        """
        r_cells, predecessor = self.dist_mat.get_reachable_cells(i, j, speed)
        r_cells = [cell for cell in r_cells if cell not in self.entities['ships']]
        return r_cells, predecessor
    
    def get_random_free_cells(self, side):
        "Returns a generator giving cells without obstacle in an area close to a border"
        # Left
        if side == 0:
            left, right, top, bottom = 0, 3, self.row*2/3, self.row/3
        # Right
        elif side == 1:
            left, right, top, bottom = self.col-3, self.col-1, self.row*2/3, self.row/3
        # Top
        elif side == 2:
            left, right, top, bottom = self.col/3, self.col*2/3, self.row-1, self.row-3
        # Bottom
        else:
            left, right, top, bottom = self.col/3, self.col*2/3, 3, 0
        coords = [(x, y) for x in range(left, right) for y in range(bottom, top) if (x, y) not in self.entities['asteroids']]
        shuffle(coords)
        return coords

        i, j = randint(0, self.col-1), randint (0, self.row-1)
        while (i,j) in self.entities['asteroids']:
            i, j = randint(0, self.col-1), randint (0, self.row-1)
        return (i,j)

    def get_entity(self, x, y):
        "Return the entity at position x, y"
        for z, child in self.children:
            # Do not look for the sprite_batch which contains only obstacles
            if isinstance(child, cocos.batch.BatchNode): continue
            rect = child.get_AABB()
            if rect.contains(x, y):
                return child
        return None

    def get_targets(self, ship):
        "Returns the list of all ennemy ships in range"
        current_player = ship.player
        targets = []
        for z, child in self.children:
            # Do not look for the sprite_batch which contains only obstacles
            if isinstance(child, cocos.batch.BatchNode): continue
            if child.player != current_player \
            and self.distance(ship, child) <= ship.weapon.range \
            and self.clear_los(ship, child):
                targets.append(child)
        return targets

    def on_mouse_press(self, x, y, button, modifiers):
        # Get the coords from the scrolling manager.
        x, y = self.scroller.pixel_from_screen(x,y)
        # Transform mouse pos in local coord
        x, y = self.scroller.point_to_local((x,y))
        i, j = self.from_pixel_to_grid(x, y)
        if i is None or j is None: return
        self.battle.on_mouse_press(i, j, x, y)
        
    def highlight_cell(self, i, j, color):
        "Highlight the cell in the given color."
        self.squares[i][j].colors = color * 4
        
    def highlight_cells(self, cells, color):
        """Highlight the cells in the list in the given color."""
        for i, j in cells:
            self.highlight_cell(i, j, color)
    
    def highlight_player(self, player):
        """Highlight the player ships"""
        self.highlight_ships(player.fleet, PLAYER_TURN)
    
    def highlight_ships(self, ships, color):
        cells = []
        for ship in ships:
            cells.append(self.from_pixel_to_grid(*(ship.position)))
        self.highlight_cells(cells, color)
    
    def clear_cell(self, i, j):
        """Remove any highlight from the cell"""
        self.highlight_cell(i, j, CLEAR_CELL)
    
    def clear_cells(self, cells):
        """Remove any highlight from the cells"""
        self.highlight_cells(cells, CLEAR_CELL)
    
    def clear_ships_highlight(self, ships):
        """Remove any highlight from the ships"""
        self.highlight_ships(ships, CLEAR_CELL)
            
    def on_key_press(self, symbol, modifiers):
        # With Space bar, end of turn
        if symbol == key.SPACE:
            self.battle.game_phase.on_end_of_turn()
            return True
        
        binds = self.bindings
        if symbol in binds:
            self.buttons[binds[symbol]] = 1
            return True
        return False

    def on_key_release(self, symbol, modifiers ):
            binds = self.bindings
            if symbol in binds:
                self.buttons[binds[symbol]] = 0
                return True
            return False

    def update_focus(self):
        self.scroller.set_focus(*self.focus_position)
        
    def clamp(self, position):
        "Clamp the position within world boundary"
        min_x, min_y = eu.Vector2(*director.get_window_size()) /2
        max_x, max_y = self.px_width - min_x, self.px_height - min_y
        x, y = position
        return eu.Vector2( max(min(x, max_x), min_x), max(min(y, max_y), min_y) )
    
    def add_player_fleet(self, player, side):
        """Add the ships from the player"""
        starting_cells = self.get_random_free_cells(side)
        orientation = [90, -90, 180, 0]
        for a, ship in enumerate(player.fleet):
            i, j = starting_cells[a]
            self.entities['ships'].append((i, j))
            x, y = self.from_grid_to_pixel(i,j)
            ship.position = (x, y)
            ship.rotation = orientation[side]
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
    
    def add_difficult_terrain(self, i, j):
        "Add difficult terrain at position i,j"
        dist_mat = self.dist_mat.tolil()
        
        for x_offset in (-1,0,1):
            for y_offset in (-1,0,1):
                if self.valid_grid(i+x_offset, j+y_offset):
                    if x_offset and y_offset:
                        dist_mat[ (i+x_offset) + (j+y_offset) * self.col, i + j*self.col] = 2*math.sqrt(2)
                    elif x_offset or y_offset:
                        dist_mat[ (i+x_offset) + (j+y_offset) * self.col, i + j*self.col] = 2
        
        self.dist_mat = dist_mat.tocsc()
    
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
    
    def get_reachable_cells(self, i, j, speed):
        "Returns all the cells reachable from (i, j) and the predecessor matrix"
        origin = self.from_coord_to_cell_number(i, j)
        dist, predecessor = dijkstra(self.dist_mat, indices=origin, return_predecessors=True)
        # Only take those where dist is reachable
        dist = np.argwhere(dist <= speed).flatten()
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
                
