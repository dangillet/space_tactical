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

CELL_WIDTH = 25
ROW, COL = 20, 28
DIST = 5

class TestLayer(cocos.layer.Layer):
    
    def __init__(self):
        self.is_event_handler = True
        super( TestLayer, self ).__init__()
        self.schedule( lambda x: 0 )
        self.batch = pyglet.graphics.Batch()
        
        self.squares = [[None for _ in range(ROW)] for _ in range(COL)]
        self.borders = []
        self.walls=[(13,4), (15,6), (13,5), (13,6), (14,6), (14,7), (14,8)]
        
        for row in range(ROW):
            for col in range(COL):

                self.squares[col][row] = self.batch.add(4, GL_QUADS, pyglet.graphics.OrderedGroup(0),
                            ('v2f', (col*CELL_WIDTH, row*CELL_WIDTH, col*CELL_WIDTH, (row+1)*CELL_WIDTH,
                                     (col+1)*CELL_WIDTH, (row+1)*CELL_WIDTH, (col+1)*CELL_WIDTH, row*CELL_WIDTH)),
                            ('c4B', (128, 128, 128, 255) * 4))
        for x,y in self.walls:
            self.squares[x][y].colors = [0, 0, 128, 255] * 4
        lines=[]
        for row in range(ROW+1):
            lines.extend((0., row*CELL_WIDTH, COL*CELL_WIDTH, row*CELL_WIDTH))
        self.borders.append(self.batch.add((ROW+1)*2, GL_LINES, pyglet.graphics.OrderedGroup(1),
                    ('v2f', lines),
                    ('c4B', (255, 0, 0, 255) * (ROW+1)*2))
                    )
        lines=[]
        for col in range(COL+1):
            lines.extend((col*CELL_WIDTH, 0., col*CELL_WIDTH, ROW*CELL_WIDTH))
        self.borders.append(self.batch.add((COL+1)*2, GL_LINES, pyglet.graphics.OrderedGroup(1),
                    ('v2f', lines),
                    ('c4B', (255, 0, 0, 255) * (COL+1)*2))
                    )
        
        self.dist_mat = lil_matrix((ROW*COL,ROW*COL))
        def valid_grid(xo, yo):
            in_grid = not xo<0 and not yo<0 and xo<COL and yo<ROW
            in_wall = (xo,yo) in self.walls
            return in_grid and not in_wall
        for j in range(ROW):
            for i in range(COL):
                for x_offset in (-1,0,1):
                    for y_offset in (-1,0,1):
                        if valid_grid(i+x_offset, j+y_offset):
                            if x_offset and y_offset:
                                self.dist_mat[ i + j*COL, (i+x_offset) + (j+y_offset) * COL] = math.sqrt(2)
                            elif x_offset or y_offset:
                                self.dist_mat[i + j*COL, (i+x_offset) + (j+y_offset) * COL] = 1
        self.dist_mat = self.dist_mat.tocsc()
        self.dist = shortest_path(self.dist_mat)
        self.anchor = (50,50)
        self.position = (50,50)
        
    
    def draw(self, *args, **kwargs):
        glPushMatrix()
        self.transform()
        self.batch.draw()
        glPopMatrix()
    
    def on_mouse_press(self, x, y, button, modifiers):
        i,j = (int((x - self.x) // CELL_WIDTH),
            int((y - self.y) // CELL_WIDTH))
        if i < 0 or j < 0:
            return
        try:
            square = self.squares[i][j]
            origin = i + j * COL
            
            reachable_cells = np.argwhere(self.dist[origin] <= DIST).flatten()
            for cell in reachable_cells:
                self.squares[cell%COL][cell//COL].colors = [128, 0, 128, 255] * 4
        except IndexError:
            pass
    
    def on_key_press(self, symbol, modifiers):
        for row in range(ROW):
            for col in range(COL):
                if (col,row) not in self.walls:
                    self.squares[col][row].colors = [128, 128, 128, 255] * 4
                else:
                    self.squares[col][row].colors = [0, 0, 128, 255] * 4

def main():
    director.init(width = 800, height=600)
    test_layer = TestLayer ()
    main_scene = cocos.scene.Scene (test_layer)
    director.show_FPS = True
    director.run (main_scene)

if __name__ == '__main__':
    main()
