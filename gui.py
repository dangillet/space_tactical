import cocos
from cocos.director import director

import pyglet.text as text
from pyglet.gl import *

class InfoLayer(cocos.layer.Layer):
    def __init__(self, position, width, height):
        super( InfoLayer, self ).__init__()
        self.info_w, self.info_h = width, height
        self.position = position
        self.document = text.decode_attributed('')
        self.info_layer = text.layout.IncrementalTextLayout(self.document, width= self.info_w
                                                                    , height = self.info_h
                                                                    , multiline=True)

    def draw(self, *args, **kwargs):
        glPushMatrix()
        self.transform()
        self.info_layer.draw()
        glPopMatrix()
        
    def display(self, txt):
        self.document = text.decode_attributed(txt)
        self.info_layer = text.layout.IncrementalTextLayout(self.document, width= self.info_w
                                                                    , height = self.info_h
                                                                    , multiline=True)
                                                                    
    def append_text(self, formatted_text):
        "Adds formatted text to the document"
        document = text.decode_attributed(formatted_text)
        insert_pos = len(self.document.text)
        self.document.insert_text(insert_pos, "\n")
        insert_pos += 1
        self.document.insert_text(insert_pos, document.text)

        for attribute, runlist in document._style_runs.iteritems():
            for start, stop, value in runlist:
                self.document.set_style(start + insert_pos, stop + insert_pos, {attribute:value})
        
        if self.info_layer.height < self.info_layer.content_height:
            self.info_layer.anchor_y= 'bottom'
            self.info_layer.y = 0
            self.info_layer.view_y = self.info_layer.height - self.info_layer.content_height

class ScrollableInfoLayer(InfoLayer):
    def __init__(self, position, width, height):
        self.is_event_handler = True
        super( ScrollableInfoLayer, self ).__init__(position, width, height)
        
    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        x, y = director.get_virtual_coordinates(x, y)
        if self.contains(x, y):
            self.info_layer.view_y -= dy
    
    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        x, y = director.get_virtual_coordinates(x, y)
        if self.contains(x, y):
            self.info_layer.view_y += scroll_y * 20
    
    def contains(self, x, y):
        '''Test whether this InfoLayer contains the pixel coordinates
        given.
        '''
        sx, sy = self.position
        if x < sx or x > sx + self.info_w: return False
        if y < sy or y > sy + self.info_h: return False
        return True
