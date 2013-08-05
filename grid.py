# This code is so you can run the samples without installing the package
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
#


import math
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.csgraph import dijkstra

import cocos
from cocos.director import director
import pyglet
from pyglet.gl import *

CELL_WIDTH = 15
ROW, COL = 50, 100
DIST = 15

class TestLayer(cocos.layer.Layer):
    
    def __init__(self):
        self.is_event_handler = True
        super( TestLayer, self ).__init__()
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
        from random import sample, shuffle
        coord_gen = product(xrange(COL-1), xrange(ROW-1))
        coords = list(coord_gen)
        # How many walls? They will all be different. So not bigger than grid size!
        # This is a bit slow on start, but won't be part of the game, so who cares?
        shuffle(coords)
        self.walls=coords[:2000]

        # We construct the quads and store them for future reference
        for row in range(ROW):
            for col in range(COL):

                self.squares[col][row] = self.batch.add(4, GL_QUADS, pyglet.graphics.OrderedGroup(0),
                            ('v2f', (col*CELL_WIDTH, row*CELL_WIDTH, col*CELL_WIDTH, (row+1)*CELL_WIDTH,
                                     (col+1)*CELL_WIDTH, (row+1)*CELL_WIDTH, (col+1)*CELL_WIDTH, row*CELL_WIDTH)),
                            ('c4B', (128, 128, 128, 255) * 4))
        # We set a different color for the walls
        for x,y in self.walls:
            self.squares[x][y].colors = [0, 0, 128, 255] * 4

        # We build the lines of the grid.
        lines=[]
        # The horizontal lines first
        for row in range(ROW+1):
            lines.extend((0., row*CELL_WIDTH, COL*CELL_WIDTH, row*CELL_WIDTH))
        self.borders.append(self.batch.add((ROW+1)*2, GL_LINES, pyglet.graphics.OrderedGroup(1),
                    ('v2f', lines),
                    ('c4B', (255, 0, 0, 100) * (ROW+1)*2))
                    )
        # And the vertical lines
        lines=[]
        for col in range(COL+1):
            lines.extend((col*CELL_WIDTH, 0., col*CELL_WIDTH, ROW*CELL_WIDTH))
        self.borders.append(self.batch.add((COL+1)*2, GL_LINES, pyglet.graphics.OrderedGroup(1),
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
                                if (i+x_offset, j) not in self.walls and (i, j+y_offset):
                                    self.dist_mat[ i + j*COL, (i+x_offset) + (j+y_offset) * COL] = math.sqrt(2)
                            elif x_offset or y_offset:
                                self.dist_mat[i + j*COL, (i+x_offset) + (j+y_offset) * COL] = 1
        # And convert this huge matrix to a sparse matrix.
        self.dist_mat = self.dist_mat.tocsc()
        
        # Move a bit the grid, so it doesn't stay stucked at the bottom left of the screen
        self.anchor = (50,50)
        self.position = (50,50)
        
    
    def draw(self, *args, **kwargs):
        glPushMatrix()
        self.transform()
        self.batch.draw()
        glPopMatrix()
    
    def on_mouse_press(self, x, y, button, modifiers):
        # Get the virtual coords, in case window was resized.
        x, y = director.get_virtual_coordinates(x, y)
        # Compute the cell coords
        i,j = (int((x - self.x) // CELL_WIDTH),
            int((y - self.y) // CELL_WIDTH))
        # Did we click on the grid?
        if i < 0 or j < 0 or not i < COL or not j < ROW:
            return
        # The cell number
        origin = i + j * COL
        # Create the shortest distance from origin
        dist = dijkstra(self.dist_mat, indices=origin)
        # Only take those where dist is reachable
        reachable_cells = np.argwhere(dist <= DIST).flatten()
        # Highlight the reachable cells
        for cell in reachable_cells:
            self.squares[cell%COL][cell//COL].colors = [128, 0, 128, 255] * 4
    
    def on_key_press(self, symbol, modifiers):
        # Reset the grid
        for row in range(ROW):
            for col in range(COL):
                if (col,row) not in self.walls:
                    self.squares[col][row].colors = [128, 128, 128, 255] * 4
                else:
                    self.squares[col][row].colors = [0, 0, 128, 255] * 4

def main():
    director.init(width = 1600, height=900)
    test_layer = TestLayer ()
    main_scene = cocos.scene.Scene (test_layer)
    director.show_FPS = True
    director.run (main_scene)

if __name__ == '__main__':
    main()
