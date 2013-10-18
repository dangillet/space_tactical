import math
from random import shuffle, randint, uniform, choice
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.csgraph import dijkstra

import cocos
import cocos.euclid as eu
from cocos.director import director
from cocos.actions import (
    MoveTo, InstantAction, Repeat, RotateBy, RotateTo, Delay,
    CallFunc, CallFuncS, ScaleTo, AccelDeccel)

import pyglet
from pyglet.window import key
from pyglet.gl import *

import entity, simplexnoise, library, battle

CELL_WIDTH = 50

PLAYER_TURN = [128, 128, 0, 100]
SHIP_SELECTED = [250, 250, 0, 100]
REACHABLE_CELLS = [128, 0, 128, 100]
TARGET = [255, 0, 0, 100]
CLEAR_CELL = [0, 0, 0, 0]

class GridLayer(cocos.layer.ScrollableLayer):
    def __init__(self, map_kwargs):
        """
        map_kwargs is a dictionary of keywords arguments to define the battlemap.
        See battlemap.json for the different objects that can be set.
        """
        self.is_event_handler = True
        super( GridLayer, self ).__init__()
        # Batch for the grid
        self.grid_batch = pyglet.graphics.Batch()
        # Batch for the asteroids
        self.sprite_batch = cocos.batch.BatchNode()
        self.add(self.sprite_batch)

        # Size of the grid
        self.col, self.row = map_kwargs['col'], map_kwargs['row']
        # Max size of the showable area.
        self.px_width = (self.col) * CELL_WIDTH
        self.px_height = (self.row) * CELL_WIDTH

        # Grid squares and borders
        self.squares = [[None for _ in range(self.row)] for _ in range(self.col)]
        self.borders = []

        # Each entity type has a dict {(i, j): entity}
        self.entities = {'asteroids' : {}, 'diff_terrain' : {}, 'ships': {}}

        # We build the obstacles and difficult terrains
        # We get a set of coordinates for each type of terrain. We don't want
        # obstacles on the same place as difficult terrains. So we take the difference
        # between both sets to get the terrain.
        diff_terrain_pos = self.generate_noise_terrain(map_kwargs['difficult terrain'])
        asteroids_pos = self.generate_noise_terrain(map_kwargs['obstacle']) - diff_terrain_pos

        # Create the asteroids animated sprites
        raw = pyglet.resource.image('aster3.png')
        raw_seq = pyglet.image.ImageGrid(raw, 6, 5)
        texture_seq = pyglet.image.TextureGrid(raw_seq)

        for x, y in asteroids_pos:
            rotation_speed = uniform(0.07, 0.15)
            anim = pyglet.image.Animation.from_image_sequence(texture_seq, rotation_speed, True)
            asteroid = entity.Asteroid(anim, position=self.from_grid_to_pixel(x,y),
                                                         rotation = uniform(0, 360))
            self.sprite_batch.add(asteroid)
            self.entities['asteroids'][(x, y)] = asteroid

        # Create the difficult terrain sprites
        raw = pyglet.resource.image('nebulaes.png')
        raw_grid = pyglet.image.ImageGrid(raw, 3, 3, row_padding=1, column_padding=1)
        texture_grid = pyglet.image.TextureGrid(raw_grid)
        # max_len = len(texture_grid)

        for x, y in diff_terrain_pos:
            diff_terrain = entity.DifficultTerrain(choice(texture_grid),
                            position=self.from_grid_to_pixel(x,y))
            self.sprite_batch.add(diff_terrain)
            self.entities['diff_terrain'][(x, y)] = diff_terrain

        # We build the distance matrix.
        self.dist_mat = DistanceMatrix(self.row, self.col)
        self.dist_mat.add_obstacles( self.entities['asteroids'].keys() )
        self.dist_mat.add_difficult_terrains(map_kwargs['difficult terrain']['cost factor'],
                                        self.entities['diff_terrain'].keys())

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
        self.grid_visible = True

        # We store key state
        self.bindings = { #key constant : button name
            key.LEFT:'left',
            key.RIGHT:'right',
            key.UP:'up',
            key.DOWN:'down',
            key.NUM_ADD:'zoomin',
            key.NUM_SUBTRACT:'zoomout'
            }
        self.buttons = { #button name : current value, 0 not pressed, 1 pressed
            'left':0,
            'right':0,
            'up':0,
            'down':0,
            'zoomin':0,
            'zoomout':0
            }
        # We want to call step every frame to scroll the map
        self.schedule(self.step)

    def on_enter(self):
        "Called when the grid is displayed for the first time"
        super(GridLayer,self).on_enter()
        # Keep a reference to the battle layer
        self.battle = self.get_ancestor(battle.Battle)
        self.scroller = self.get_ancestor(cocos.layer.ScrollingManager)
        # How fast we can scroll
        self.scroller.fastness = 700

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
        "Called every frame to check if buttons were pressed and move the map."
        buttons = self.buttons
        move_dir = eu.Vector2(buttons['right']-buttons['left'],
                              buttons['up']-buttons['down'])
        changed = False
        if move_dir:
            new_pos = eu.Vector2(self.scroller.restricted_fx, self.scroller.restricted_fy)
            new_pos = new_pos + self.scroller.fastness*dt*move_dir.normalize()
            changed = True

        if changed:
            self.update_focus(new_pos)

    def generate_noise_terrain(self, params):
        """
        Given the params to generate a simplex noise, returns a set of
        the coords above the defined threshold in the parameters.
        Returns: set of tuples {(i,j), ...}
        """
        noise = np.zeros(shape=(self.col, self.row))
        for x, y in np.ndindex(self.col, self.row):
            v = simplexnoise.scaled_octave_noise_2d(
                params['octave'],
                params['persistance'],
                params['freq'],
                0, 255,
                x + params['x_off'],
                y + params['y_off'])
            c = v - params['sparsity']
            if c<0: c = 0
            noise[x][y] = 255 - (math.pow(params['density'], c) * 255)
        return set(zip(*np.where(noise> 0.)))

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

    def rotate_to_bearing(self, m, n ,ox, oy):
        """
        Returns a RotateTo action from (ox, oy) towards (m, n).
        We add some delay in order to synchronize the turns with the movements.
        """
        # Compute the angle to the next grid.
        angle = math.degrees(math.atan2(n - oy, m - ox))
        # Bearing with 0 for N, 90 for E, 180 for S and 270 for W
        bearing = (90 - angle) % 360
        return RotateTo(bearing, 0.1) + Delay(0.2)

    def move_sprite(self, sprite, i, j):
        "Move sprite to the selected grid location"
        if self._is_invalid_grid(i,j):
            return

        i0, j0 = self.from_pixel_to_grid(*(sprite.position))
        self.clear_cell(i0, j0)
        # Reconstruct the path
        path = self.dist_mat.reconstruct_path(i0, j0, i, j, self.battle.predecessor)

        # Initialize the move and rotate with an empty action
        move = rotate = InstantAction()
        # Sequence moves to the next grid
        ox, oy = i0, j0
        for m, n in path:
            # We move in 0.3s to the next grid location
            move = ( move +
                     MoveTo(self.from_grid_to_pixel(m, n), 0.3)
                    )
            # We rotate towards the next grid location in 0.1s and wait for 0.2s
            rotate = ( rotate +
                       self.rotate_to_bearing(m, n, ox, oy)
                    )
            ox, oy = m, n
        # And after the move, reset the selected ship
        # end_of_move = CallFunc(self.battle.game_phase[-1].on_move_finished)
        end_of_move = CallFunc(self.battle.on_command_finished)
        move = move + end_of_move
        sprite.do(move)
        sprite.do(rotate)
        # Update the position in entities['ships']
        self.entities['ships'][(i, j)] = self.entities['ships'].pop( (i0, j0) )

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
        other_ships = {pos:ship for pos, ship in self.entities['ships'].iteritems()
                        if (ship is not objA and ship is not objB)}
        for cell in los:
            if cell in self.entities['asteroids'] or \
                cell in self.entities['ships'] and \
                cell != (i0, j0) and cell != (i1, j1):
                return False
        return True

    def get_reachable_cells(self, ship):
        """
        Forward this to the distance matrix. Remove any other ships from
        reachable cells so we can move through ships but not stop on another one.
        """
        i, j = self.from_pixel_to_grid(*(ship.position))
        r_cells, predecessor = self.dist_mat.get_reachable_cells(i, j, ship.speed)
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
        i, j = self.from_pixel_to_grid(x, y)
        return self.entities['ships'].get( (i, j) )

    def get_targets(self, ship):
        "Returns the list of all ennemy ships in range"
        current_player = ship.player
        targets = []
        for entity in self.entities['ships'].itervalues():
            if entity.player != current_player \
                    and self.distance(ship, entity) <= ship.weapon.range \
                    and self.clear_los(ship, entity):
                targets.append(entity)
        return targets

    def highlight_cell(self, i, j, color):
        "Highlight the cell in the given color."
        self.squares[i][j].colors = color * 4

    def highlight_cells(self, cells, color):
        """Highlight the cells in the list in the given color."""
        for i, j in cells:
            self.highlight_cell(i, j, color)

    def highlight_player(self, player):
        """Highlight the player' ships"""
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
        # Check for key pressed in our key bindings
        binds = self.bindings
        if symbol in binds:
            self.buttons[binds[symbol]] = 1
            return True
        return False

    def on_key_release(self, symbol, modifiers):
        # Check for key released in our key bindings
        if symbol == key.F1:
            self.scroller.do(AccelDeccel(ScaleTo(0.75, 1)))
            return True
        elif symbol == key.F2:
            self.scroller.do(AccelDeccel(ScaleTo(1., 1)))
            return True
        elif symbol == key.F3:
            self.scroller.do(AccelDeccel(ScaleTo(1.25, 1)))
            return True
        elif symbol == key.G:
            self.toggle_grid_lines()

        binds = self.bindings
        if symbol in binds:
            self.buttons[binds[symbol]] = 0
            return True
        return False

    def toggle_grid_lines(self):
        if self.grid_visible:
            color = [255, 0, 0, 0]
        else:
            color = [255, 0, 0, 100]

        self.borders[0].colors = color * (self.row+1)*2
        self.borders[1].colors = color * (self.col+1)*2

        self.grid_visible = not self.grid_visible


    def update_focus(self, position):
        "Move the grid to the focus_position."
        self.scroller.set_focus(*position)

    def add_player_fleet(self, player, side):
        """Add the ships from the player"""
        starting_cells = self.get_random_free_cells(side)
        orientation = [90, -90, 180, 0]
        for a, ship in enumerate(player.fleet):
            i, j = starting_cells[a]
            self.entities['ships'][(i, j)] = ship
            x, y = self.from_grid_to_pixel(i,j)
            ship.position = (x, y)
            ship.rotation = orientation[side]
            self.add(ship)

    def remove(self, entity):
        "Removes the entity both from the Layer and from the dict entities"
        super(GridLayer, self).remove(entity)
        for grid_pos, ship in self.entities['ships'].items():
            if ship is entity:
                del self.entities['ships'][grid_pos]



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

    def _add_difficult_terrain(self, cf, i, j):
        "Add difficult terrain at position i,j. Cost factor is cf"
        for x_offset in (-1,0,1):
            for y_offset in (-1,0,1):
                if self.valid_grid(i+x_offset, j+y_offset):
                    if x_offset and y_offset:
                        self.dist_mat[ (i+x_offset) + (j+y_offset) * self.col, i + j*self.col] = cf*math.sqrt(2)
                    elif x_offset or y_offset:
                        self.dist_mat[ (i+x_offset) + (j+y_offset) * self.col, i + j*self.col] = cf

    def add_difficult_terrains(self, cf, diff_terrains):
        "Add list of difficult terrains at position (i,j). Cost factor is cf"
        self.dist_mat = self.dist_mat.tolil()
        for diff_terrain in diff_terrains:
            self._add_difficult_terrain(cf, *diff_terrain)
        self.dist_mat = self.dist_mat.tocsc()

    def add_obstacles(self, obstacles):
        "Add obstacles at position (i, j)"
        # Change the distance matrix to lil format
        self.dist_mat = self.dist_mat.tolil()
        for obstacle in obstacles:
            self._add_obstacle(*obstacle)
        # Update the distance matrix in csc format
        self.dist_mat = self.dist_mat.tocsc()

    def _add_obstacle(self, i, j):
        "Add obstacle at position i,j"
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
        ctc = self.from_coord_to_cell_number
        for x in (-1, 1):
            for y in (-1, 1):
                if self.valid_grid(i+x, j+y) \
                   and self.dist_mat[grid_number, ctc(i+x, j+y)] == 0:
                    self.dist_mat[ctc(i, j+y), ctc(i+x, j)] = 0
                    self.dist_mat[ctc(i+x, j), ctc(i, j+y)] = 0

        # Set to 0 the whole col at grid_num as we cannot move into this position.
        self.dist_mat[: ,grid_number] = 0

        # Set to 0 the whole row at grid_num as this is an obstacle and we cannot move
        # from this position.
        self.dist_mat[grid_number, :] = 0

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

