import cocos
from cocos.director import director
from cocos.menu import *

import pyglet
import pyglet.text as text
from pyglet.gl import *
from pyglet import font

import entity, commands

BACKGROUND = (50, 50, 50, 200)
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
        self.model = None

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

    def on_exit(self):
        super(InfoLayer, self).on_exit()
        self._border_vertex_list.delete()
        self._border_vertex_list = None

    def draw(self, *args, **kwargs):
        super(InfoLayer, self).draw(*args, **kwargs)
        glPushMatrix()
        self.transform()
        self.info_layer.draw()
        glPopMatrix()

    def update(self):
        self.info_layer.begin_update()
        if self.model is None:
            self.info_layer.document = text.decode_attributed('')
        else:
            self.info_layer.document = text.decode_attributed(self.display_model())
        self.info_layer.end_update()

    def display_model(self):
        raise NotImplementedError

    def set_model(self, model):
        if self.model is not None:
            self.model.pop_handlers()
        self.model = model
        if self.model is not None:
            model.push_handlers(self)
        self.update()

    def remove_model(self):
        if self.model is not None:
            self.model.pop_handlers()
            self.model = None
            self.update()

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
        formatted_text += "{}\n"
        document = text.decode_attributed(formatted_text)
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

class ShipInfoLayer(InfoLayer):
    def __init__(self, position, width, height, show_all_weapons=False):
        super(ShipInfoLayer, self).__init__(position, width, height)
        self.show_all_weapons = show_all_weapons


    def display_model(self):
        "Display the ship and its weapons in the formatted text style"
        model = self.model
        shield = " - ".join(["{pr}/{energy_name}".format(pr=pr,
                                    energy_name= entity.EnergyType.name(en_idx))
                        for en_idx, pr in model.shield.iteritems() if pr != 0])
        s =  _("""{{font_name 'Classic Robot'}}{{font_size 16}}
{{color [255, 0, 0, 255]}}{{italic True}}{m.ship_type}{{italic False}}{{}}
{{font_size 12}}{{.tab_stops [90, 170]}}{{color [255, 255, 255, 255]}}Speed: {m.speed}{{#x09}}Hull: {m.hull}{{#x09}}Shield: {shield}
""").format(m=model, shield=shield)
        if self.show_all_weapons:
            for weapon in model.slots['weapon'].mods:
                s += self._display_weapon(weapon)
        elif model.weapon is not None:
            s += self._display_weapon(model.weapon)
        return s

    def _display_weapon(self, weapon):
        return _("""
{{color [255, 0, 0, 255]}}{w.name} {{color [255, 255, 255, 255]}} {{}}
{{.tab_stops [150]}}
Energy type: {energy_name}{{#x09}}Range: {w.range}{{}}
Precision: {w.precision:.0%}{{#x09}}Damage: {w.damage} {{}}
Temperature: {color_heating}{w.temperature:.0f}{color_normal}{{#x09}}Heating: {w.heating:.0f} {{}}
Reliability: {w.reliability:.0%}{{}}
""").format(w=weapon, energy_name=entity.EnergyType.name(weapon.energy_type),
        color_heating="{color (255, 0, 0, 255)}" if weapon.temperature >= 100 else "",
        color_normal="{color (255, 255, 255, 255)}")

    def on_change(self):
        self.update()

    def on_weapon_change(self):
        self.update()

    def on_speed_change(self):
        self.update()

    def on_weapon_jammed(self, weapon):
        self.update()

class SubMenu(Menu):
    def __init__(self, title = ''):
        super(SubMenu, self).__init__(title)

    def _generate_title(self):
        width, height = director.get_window_size()
        fo = font.load(self.font_item['font_name'], self.font_item['font_size'])
        fo_height = int( (fo.ascent - fo.descent) * 0.9 )

        if self.menu_halign == CENTER:
            self.font_title['x'] = width // 2
        elif self.menu_halign == RIGHT:
            self.font_title['x'] = width - self.menu_hmargin
        elif self.menu_halign == LEFT:
            self.font_title['x'] = self.menu_hmargin
        else:
            raise Exception("Invalid anchor_x value for menu")

        self.font_title['anchor_x'] = self.menu_halign
        self.font_title['anchor_y'] = "center"
        self.font_title['text'] = self.title
        self.title_label = pyglet.text.Label( **self.font_title )
        self.title_height = self.title_label.content_height

        if self.menu_valign == CENTER:
            self.title_label.y = (height + len(self.children) * fo_height +
                         self.title_height) * 0.5
        elif self.menu_valign == TOP:
            self.title_label.y = (height - self.menu_vmargin - self.title_height //2)
        elif self.menu_valign == BOTTOM:
            self.title_label.y = (0 + fo_height * (len(self.children)) +
                         self.title_height + self.menu_vmargin)

class MenuLayer(cocos.layer.ColorLayer):
    def __init__(self, battle, ship, width, height):
        super(MenuLayer, self).__init__(*BACKGROUND, width=width, height=height)
        self.battle = battle
        self.ship = ship
        weapon_menu = WeaponMenu(ship)
        self.add(weapon_menu, z=5, name="weapon_menu")
        boost_menu = BoostMenu(battle, ship)
        x_offset = 20
        for z, item in weapon_menu.children:
            x_offset += item.get_item_width() + 20
        boost_menu.x = x_offset
        self.add(boost_menu, z=5, name="boost_menu")

class MenuItemDisableable (MenuItem):
    "Menu Item which can be disabled"
    def __init__(self, label, callback_func, *args, **kwargs):
        # Get the disable status from the kwargs
        self.is_disabled = kwargs.get("disabled", False)
        # If there was a disabled key, delete it
        kwargs.pop("disabled", None)
        super(MenuItemDisableable, self).__init__(label, callback_func, *args, **kwargs)


    def generateWidgets (self, pos_x, pos_y, font_item, font_item_selected, font_item_disabled):
        super(MenuItemDisableable, self).generateWidgets(pos_x, pos_y, font_item, font_item_selected)
        font_item_disabled['x'] = int(pos_x)
        font_item_disabled['y'] = int(pos_y)
        font_item_disabled['text'] = self.label
        self.item_disabled = pyglet.text.Label(**font_item_disabled )

    def draw( self ):
        glPushMatrix()
        self.transform()
        if self.is_disabled:
            self.item_disabled.draw()
        elif self.is_selected:
            self.item_selected.draw()
        else:
            self.item.draw()
        glPopMatrix()

class ShipMenu(Menu):
    "Base class for the menu of ship actions"
    def __init__(self, ship):
        super(ShipMenu, self).__init__()

        self.menu_halign = LEFT
        self.menu_valign = CENTER

        #
        # Menu font options
        #
        self.font_title = {
            'text':'title',
            'font_name':'Classic Robot',
            'font_size':14,
            'color':(192,192,192,255),
            'bold':False,
            'italic':False,
            'anchor_y':'center',
            'anchor_x':'center',
            'dpi':96,
            'x':0, 'y':0,
        }
        self.font_item= {
            'font_name':'Classic Robot',
            'font_size':12,
            'bold':False,
            'italic':False,
            'anchor_y':'center',
            'anchor_x':'left',
            'color':(192,192,192,255),
            'dpi':96,
        }
        self.font_item_selected = {
            'font_name':'Classic Robot',
            'font_size':12,
            'bold':False,
            'italic':False,
            'anchor_y':'center',
            'anchor_x':'left',
            'color':(192,192,0,255),
            'dpi':96,
        }
        self.font_item_disabled = {
            'font_name':'Classic Robot',
            'font_size':12,
            'bold':False,
            'italic':False,
            'anchor_y':'center',
            'anchor_x':'left',
            'color':(20,20,20,255),
            'dpi':96,
        }
        self.ship = ship

    def on_enter(self):
        super(ShipMenu, self).on_enter()
        self.ship.push_handlers(self)

    def on_exit(self):
        super(ShipMenu, self).on_exit()
        self.ship.pop_handlers()

    def on_key_press(self, symbol, modifiers):
        return False

    def on_mouse_release( self, x, y, buttons, modifiers ):
        (x,y) = director.get_virtual_coordinates(x,y)
        if self.children[ self.selected_index ][1].is_inside_box(x,y):
            self._activate_item()
            return True
        return False

    def disable(self, idx):
        self.children[idx][1].is_disabled = True

    def on_mouse_motion( self, x, y, dx, dy ):
        (x,y) = director.get_virtual_coordinates(x,y)
        for idx,i in enumerate( self.children):
            item = i[1]
            if item.is_inside_box( x, y) and not item.is_disabled:
                self._select_item( idx )
                break

class WeaponMenu(ShipMenu):
    "Menu for selecting the current weapon"
    def __init__(self, ship):
        super(WeaponMenu, self).__init__(ship)
        weapons = ship.slots['weapon'].mods
        l = []
        for idx, weapon in enumerate(weapons):
            l.append(MenuItemDisableable(weapon.name, ship.change_weapon, idx,
                    disabled = weapon.is_inop))
        self.create_menu(l, layout_strategy=horizontalMenuLayout)
        if self.ship.weapon is not None:
            self._select_item(self.ship.weapon_idx)

    def on_key_press(self, symbol, modifiers):
        return False

    def on_weapon_jammed(self, weapon):
        idx = self.ship.weapons.index(weapon)
        self.children[idx][1].is_disabled = True
        return True

class BoostMenu(ShipMenu):
    "Menu for selecting the boost"
    def __init__(self, battle, ship):
        super(BoostMenu, self).__init__(ship)
        boosts = ship.boosts
        l = []
        for idx, boost in enumerate(boosts):
            item = MenuItemDisableable(boost.name, battle.submit,
                    commands.BoostCommand(battle, self.ship, idx),
                    disabled=ship.boost_used)
            l.append(item)
        self.create_menu(l, layout_strategy=horizontalMenuLayout)
        if ship.move_completed:
            self.disable(1) # Disable Boost Speed
        if ship.attack_completed:
            self.disable(2) # Disabel Boost Weapon

    def on_boost_use(self):
        for _, item in self.children:
            item.is_disabled = True
        return True

def horizontalMenuLayout (menu):
    pos_x = 20
    pos_y = 25
    for idx,i in enumerate( menu.children):
        item = i[1]
        item.transform_anchor_x = 0
        item.generateWidgets (pos_x, pos_y, menu.font_item,
                              menu.font_item_selected,
                              menu.font_item_disabled)
        pos_x += item.get_item_width() + 20



