import cocos
from cocos.director import director

import pyglet.text as text
from pyglet.gl import *

WIDTH = 350
PADDING = 20

class InfoLayer(cocos.layer.Layer):
    def __init__(self):
        super( InfoLayer, self ).__init__()
        self.wx, self.wy = director.get_window_size()
        self.position = (self.wx - WIDTH + PADDING, PADDING)
        self.document = text.decode_attributed('')
        self.info_layer = text.layout.IncrementalTextLayout(self.document, width= WIDTH - 2 * PADDING
                                                                    , height = self.wy - 2 * PADDING
                                                                    , multiline=True)
        
    def draw(self, *args, **kwargs):
        glPushMatrix()
        self.transform()
        self.info_layer.draw()
        glPopMatrix()
        
    def display(self, txt):
        self.document = text.decode_attributed(txt)
        self.info_layer = text.layout.IncrementalTextLayout(self.document, width= WIDTH - 2 * PADDING
                                                                    , height = self.wy - 2 * PADDING
                                                                    , multiline=True)

