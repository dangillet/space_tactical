import cocos
from cocos.director import director

import pyglet
import pyglet.text as text
from pyglet.gl import *

BACKGROUND = (50, 50, 50, 255)
PADDING = 10

class DashedLine(pyglet.graphics.OrderedGroup):
    "Ordered Group that puts a dashed line with some width"
    def __init__(self, order, parent=None):
        super(DashedLine, self).__init__(order, parent)
    
    def set_state(self):
        glPushAttrib(GL_LINE_BIT)
        glEnable(GL_LINE_STIPPLE)
        glLineWidth(2.5)
        glLineStipple(1, 0x0F0F)
        
    def unset_state(self):
        glPopAttrib()
        
class InfoLayer(cocos.layer.ColorLayer):
    def __init__(self, position, width, height):
        super( InfoLayer, self ).__init__(*BACKGROUND, width=width, height=height)
        self.info_w, self.info_h = width - PADDING, height - PADDING
        self.position = position
        self.document = text.document.FormattedDocument('')
        self.info_layer = text.layout.IncrementalTextLayout(self.document, width= self.info_w
                                                                    , height = self.info_h
                                                                    , multiline=True)
        self.info_layer.x, self.info_layer.y = PADDING, PADDING

    def on_enter(self):
        super(InfoLayer, self).on_enter()
        # Migrate the vertex list so we can give it an ordered group
        self._batch.migrate(self._vertex_list,
                            pyglet.gl.GL_QUADS,
                            pyglet.graphics.OrderedGroup(0),
                            self._batch)
        x, y = self.width, self.height
        ox, oy = 0, 0
        self._border_vertex_list = self._batch.add(4, pyglet.gl.GL_LINE_LOOP, DashedLine(1),
            ('v2i', ( ox, oy,
                      ox, oy + y,
                      ox+x, oy+y,
                      ox+x, oy)),
            ('c4B', (255, 255, 255, 255)*4 ))
        
    
    def draw(self, *args, **kwargs):
        super(InfoLayer, self).draw(*args, **kwargs)
        glPushMatrix()
        self.transform()
        self.info_layer.draw()
        glPopMatrix()

    def display(self, txt):
        self.document = text.decode_attributed(txt)
        self.info_layer = text.layout.IncrementalTextLayout(self.document, width= self.info_w
                                                                    , height = self.info_h
                                                                    , multiline=True)
        self.info_layer.x, self.info_layer.y = PADDING, PADDING
                                                                    
    def append_text(self, formatted_text):
        "Adds formatted text to the document"
        document = text.decode_attributed("\n" + formatted_text)
        insert_pos = len(self.document.text)
        self.document.insert_text(insert_pos, document.text)

        for attribute, runlist in document._style_runs.iteritems():
            for start, stop, value in runlist:
                self.document.set_style(start + insert_pos, stop + insert_pos, {attribute:value})
        
        if self.info_layer.height < self.info_layer.content_height:
            self.info_layer.view_y = self.info_layer.height - self.info_layer.content_height
    
    def prepend_text(self, formatted_text):
        "Preprends formatted text to the document"
        document = text.decode_attributed(formatted_text + "\n")
        self.document.insert_text(0, document.text)
        
        for attribute, runlist in document._style_runs.iteritems():
            for start, stop, value in runlist:
                self.document.set_style(start, stop, {attribute:value})

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
