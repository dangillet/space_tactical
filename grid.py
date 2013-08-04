# This code is so you can run the samples without installing the package
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
#


import math
import numpy as np
from scipy.sparse import lil_matrix
from scipy.sparse.csgraph import shortest_path

import cocos
from cocos.director import director
import pyglet
from pyglet.gl import *

CELL_WIDTH = 20
ROW, COL = 40, 70
DIST = 3

class TestLayer(cocos.layer.Layer):
    
    def __init__(self):
        self.is_event_handler = True
        super( TestLayer, self ).__init__()
        self.schedule( lambda x: 0 )
        self.batch = pyglet.graphics.Batch()
        
        # list of grid empty squares
        self.squares = [[None for _ in range(ROW)] for _ in range(COL)]
        # list of borders
        #self.borders = []
        self.walls=[(13,14), (15,16), (13,15), (13,16), (14,16), (14,17), (14,18)]
        
        for row in range(ROW):
            for col in range(COL):

                self.squares[col][row] = self.batch.add(4, GL_QUADS, pyglet.graphics.OrderedGroup(0),
                            ('v2f', (col*CELL_WIDTH, row*CELL_WIDTH, col*CELL_WIDTH, (row+1)*CELL_WIDTH,
                                     (col+1)*CELL_WIDTH, (row+1)*CELL_WIDTH, (col+1)*CELL_WIDTH, row*CELL_WIDTH)),
                            ('c4B', (128, 128, 128, 255) * 4))
        for x,y in self.walls:
            self.squares[x][y].colors = [0, 0, 128, 255] * 4
        #lines=[]
        #for row in range(ROW+1):
            #lines.extend((0., row*CELL_WIDTH, COL*CELL_WIDTH, row*CELL_WIDTH))
        #self.borders.append(self.batch.add((ROW+1)*2, GL_LINES, pyglet.graphics.OrderedGroup(1),
                    #('v2f', lines),
                    #('c4B', (255, 0, 0, 255) * (ROW+1)*2))
                    #)
        #lines=[]
        #for col in range(COL+1):
            #lines.extend((col*CELL_WIDTH, 0., col*CELL_WIDTH, ROW*CELL_WIDTH))
        #self.borders.append(self.batch.add((COL+1)*2, GL_LINES, pyglet.graphics.OrderedGroup(1),
                    #('v2f', lines),
                    #('c4B', (255, 0, 0, 255) * (COL+1)*2))
                    #)
                    
        self.anchor = (50,50)
        self.position = (50,50)
        
    
    def draw(self, *args, **kwargs):
        glPushMatrix()
        self.transform()
        self.batch.draw()
        glPopMatrix()
    
    def on_mouse_press(self, x, y, button, modifiers):
        x, y = director.get_virtual_coordinates(x, y)
        # square pressed
        o_x, o_y = (int((x - self.x) // CELL_WIDTH),
            int((y - self.y) // CELL_WIDTH))
        # check if we are in the grid
        if o_x < 0 or o_y < 0:
            return
        try:
            square = self.squares[o_x][o_y]
        except IndexError:
            return
        
        # we only compute shortest path in a smaller portion of grid.
        # it's a square of length twice the distance reachable
        largest_range = DIST*2 + 1
        # number of the square in the middle of the sub-grid
        origin = (largest_range // 2) * (largest_range + 1)
        # calculate the offset to go from sub_grid to the real grid
        offset_x, offset_y = o_x - largest_range//2, o_y - largest_range//2
        # create empty distance matrix
        dist_mat = lil_matrix((largest_range*largest_range, largest_range*largest_range))
        
        # check if we are in the grid. Will be called later
        def valid_grid(xo, yo):
            # first check if we stay within the sub-grid
            in_grid = not xo<0 and not yo<0 and xo<largest_range and yo<largest_range
            # then test if this places us in a valid place on the larger grid
            xo += offset_x
            yo += offset_y
            in_grid = in_grid and not xo<0 and not yo<0 and xo<COL and yo<ROW
            # check for walls
            in_wall = (xo,yo) in self.walls
            return in_grid and not in_wall
        
        # for each square in the sub-grid, insert distance in matrix
        for j in range(largest_range):
            for i in range(largest_range):
                for x_offset in (-1,0,1):
                    for y_offset in (-1,0,1):
                        if valid_grid(i+x_offset, j+y_offset):
                            if x_offset and y_offset:
                                dist_mat[ i + j*largest_range, (i+x_offset) + (j+y_offset) * largest_range] = math.sqrt(2)
                            elif x_offset or y_offset:
                                dist_mat[i + j*largest_range, (i+x_offset) + (j+y_offset) * largest_range] = 1
        dist_mat = dist_mat.tocsr()
        dist = shortest_path(dist_mat)
        # all cells from middle of sub-grid (=origin) we can reach with DIST movement
        reachable_cells = np.argwhere(dist[origin] <= DIST).flatten()
        for cell in reachable_cells:
            self.squares[cell%largest_range + offset_x][cell//largest_range + offset_y].colors = [128, 0, 128, 255] * 4
        
    
    def on_key_press(self, symbol, modifiers):
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
