import json

import pyglet

import cocos

from cocos.menu import *
from cocos.scenes import *
from cocos.director import director

import battle, gui, entity

def set_fonts(menu):
    #
    # Menu font options
    #
    menu.font_title = {
        'font_name':'Classic Robot',
        'font_size':28,
        'color':(200, 200, 200, 255)
    }
    menu.font_item= {
        'font_name':'Classic Robot',
        'font_size':16,
        'bold':False,
        'italic':False,
        'anchor_y':'center',
        'anchor_x':'left',
        'color':(192,192,192,255),
        'dpi':96,
    }
    menu.font_item_selected = {
        'font_name':'Classic Robot',
        'font_size':16,
        'bold':False,
        'italic':False,
        'anchor_y':'center',
        'anchor_x':'left',
        'color':(192,192,0,255),
        'dpi':96,
    }

class ShipMod(cocos.layer.Layer):
    def __init__(self):
        super(ShipMod, self).__init__()
        self.ships_factory = entity.ShipFactory()
        self.mods = []
        with open("player.json") as f:
            data = json.load(f)
            self.player = entity.Player(data['name'])
            for ship_data in data['fleet']:
                    quantity = ship_data.get("count", 1)
                    for i in range(quantity):
                        mods = ship_data.get("mods", [])
                        ship = self.ships_factory.create_ship(ship_data['type'],
                                                                mods =mods)
                        self.player.add_ship(ship)
            for mod in data['inventory']:
                self.mods.append(self.ships_factory.create_mod(mod))
        self.add(ShipList(), name="ship_list")
        w, h = director.get_window_size()
        self.add(cocos.text.Label("Ship Modifications",
                                font_name = "Classic Robot",
                                font_size = 36,
                                color = (200, 200, 200, 255),
                                anchor_y = "top",
                                anchor_x = "center",
                                x=w//2,
                                y=h)
                )
        self.ship_info = gui.ShipInfoLayer((250, h-400 ), 550, 300, show_all_weapons=True)
        self.add(self.ship_info, name="ship_info")
        self.add(ModList())
        
    
    def on_enter(self):
        super(ShipMod, self).on_enter()
        self.get("ship_list").push_handlers(self)
    
    def on_exit(self):
        super(ShipMod, self).on_exit()
        self.get("ship_list").pop_handlers()
        
    def on_selected(self, ship):
        self.ship_info.set_model( ship )
        try:
            self.remove("slot_menu_mob")
            self.remove("slot_menu_def")
            self.remove("slot_menu_wea")
        except Exception:
            pass
        slot_menu = SlotMenu(ship.slots['mobility'], 250)
        self.add(slot_menu, name="slot_menu_mob")
        slot_menu = SlotMenu(ship.slots['defense'], 450)
        self.add(slot_menu, name="slot_menu_def")
        slot_menu = SlotMenu(ship.slots['weapon'], 650)
        self.add(slot_menu, name="slot_menu_wea")
    
    def on_mod_selected(self, mod):
        ship_list = self.get("ship_list")
        self.player.fleet[ship_list.selected_index].add_mod(mod)

class SlotMenu(gui.SubMenu):
    def __init__(self, slot, hmargin):
        super(SlotMenu, self).__init__(slot.type)
        w, h = director.get_window_size()
        set_fonts(self)
        self.font_item['font_size'] = self.font_item_selected ['font_size'] = 12
        self.menu_halign = LEFT
        self.menu_valign = TOP
        self.menu_hmargin = hmargin
        self.menu_vmargin = 400
        
        self.slot = slot
        
        l = [MenuItem(mod.name, None) for mod in self.slot.mods]
        if not l:
            l = [MenuItem("None", None)]
        self.create_menu(l)
    
    def on_enter(self):
        super(SlotMenu, self).on_enter()
        self.slot.ship.push_handlers(self)
        
    def on_exit(self):
        super(SlotMenu, self).on_exit()
        self.slot.ship.pop_handlers()
        
    def on_key_press(self, s, m):
        return False
    
    def on_change(self):
        map(self.remove, (child for z,child in self.children) )
        l = [MenuItem(mod.name, None) for mod in self.slot.mods]
        if not l:
            l = [MenuItem("None", None)]
        self.create_menu(l)

class ShipList(gui.SubMenu, pyglet.event.EventDispatcher):
    def __init__(self):
        super(ShipList, self).__init__()
        self.title = _("""Fleet""")
        self.menu_halign = LEFT
        self.menu_valign = TOP
        self.menu_hmargin = 20
        self.menu_vmargin = 100
        set_fonts(self)
    
    def on_enter(self):
        super(ShipList, self).on_enter()
        self.buttons = []
        for ship in self.parent.player.fleet:
            ship_button = MenuItem(ship.ship_type, self.dispatch_event, "on_selected", ship)
            self.buttons.append(ship_button)
        self.buttons.append( MenuItem("Go to the Battle", self.on_quit) )
        self.create_menu(self.buttons, selected_effect=zoom_in(),
                          unselected_effect=zoom_out())

    def on_exit(self):
        super(ShipList, self).on_exit()
        map(self.remove, (child for z,child in self.children) )
        
    def on_quit(self):
        my_battle = battle.Battle()
        battle_scene = cocos.scene.Scene(my_battle) 
        director.replace(FadeTransition(battle_scene, duration = 3))
        
    def show(self, ship):
        self.parent.ship_info.set_model( ship )

ShipList.register_event_type("on_selected")

class ModList(gui.SubMenu):
    def __init__(self):
        super(ModList, self).__init__()
        self.title = _("""Modifications""")
        self.menu_halign = RIGHT
        self.menu_valign = TOP
        self.menu_hmargin = 20
        self.menu_vmargin = 100
        set_fonts(self)

    def on_enter(self):
        super(ModList, self).on_enter()
        l = [MenuItem(mod.name, self.parent.on_mod_selected, mod) for mod in self.parent.mods]
        if not l:
            l = [MenuItem("None", None)]
        self.create_menu(l)
    
    def on_exit(self):
        super(ModList, self).on_exit()
        map(self.remove, (child for z,child in self.children) )
    
    def on_key_press(self, s, m):
        return False

