import json

import cocos

from cocos.menu import *
from cocos.scenes import *
from cocos.director import director

import battle, gui, entity

class ShipMod(cocos.layer.Layer):
    def __init__(self):
        super(ShipMod, self).__init__()
        self.add(ShipList(), "ship_list")
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
        self.ship_info = gui.ShipInfoLayer((300, 200), 400, 300, show_all_weapons=True)
        self.add(self.ship_info, "ship_info")
        
        self.add(SlotMenu())

class SlotMenu(Menu):
    def __init__(self):
        super(SlotMenu, self).__init__()
        l = [MenuItem("Test 1", None), MenuItem("Test 2", None)]
        self.create_menu(l)

class ShipList(gui.SubMenu):
    def __init__(self):
        super(ShipList, self).__init__()
        
        self.title = _("""Fleet""")
        self.menu_halign = LEFT
        self.menu_valign = TOP
        self.menu_hmargin = 20
        self.menu_vmargin = 100
        #
        # Menu font options
        #
        self.font_title = {
            'font_name':'Classic Robot',
            'font_size':28,
            'color':(200, 200, 200, 255)
        }
        self.font_item= {
            'font_name':'Classic Robot',
            'font_size':16,
            'bold':False,
            'italic':False,
            'anchor_y':'center',
            'anchor_x':'left',
            'color':(192,192,192,255),
            'dpi':96,
        }
        self.font_item_selected = {
            'font_name':'Classic Robot',
            'font_size':16,
            'bold':False,
            'italic':False,
            'anchor_y':'center',
            'anchor_x':'left',
            'color':(192,192,0,255),
            'dpi':96,
        }
        self.ships_factory = entity.ShipFactory()
    
    def on_enter(self):
        super(ShipList, self).on_enter()
        self.buttons = []
        with open("player.json") as f:
            data = json.load(f)
            self.player = entity.Player(data['name'])
            for ship_data in data['fleet']:
                    quantity = ship_data.get("count", 1)
                    for i in range(quantity):
                        mods = ship_data.get("mods")
                        ship = self.ships_factory.create_ship(ship_data['type'],
                                                                mods =mods)
                        self.player.add_ship(ship)
                        ship_button = MenuItem(ship.ship_type, self.show, ship)
                        self.buttons.append(ship_button)
        self.buttons.append( MenuItem("Go to the Battle", self.on_quit) )
        self.create_menu(self.buttons, selected_effect=zoom_in(),
                          unselected_effect=zoom_out())
        # Reposition the menu title as default is in the middle of the page
        #self.title_label.x = self.menu_hmargin
        #self.title_label.y -= self.menu_vmargin - 20
        
    def on_exit(self):
        super(ShipList, self).on_exit()
        map(self.remove, (child for z,child in self.children) )
        
    def on_quit(self):
        my_battle = battle.Battle()
        battle_scene = cocos.scene.Scene(my_battle) 
        director.replace(FadeTransition(battle_scene, duration = 3))
        
    def show(self, ship):
        self.parent.ship_info.set_model( ship )
