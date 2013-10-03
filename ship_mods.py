import json

import cocos

from cocos.menu import *
from cocos.scenes import *
from cocos.director import director

import battle, gui, entity



class ShipMod(Menu):
    def __init__(self):
        super(ShipMod, self).__init__()
        w, h = director.get_window_size()
        self.title = _("""Ship modifications""")
        
        #
        # Menu font options
        #
        self.font_title = {
            'font_name':'Classic Robot',
            'font_size':36,
            'color':(200, 200, 200, 255),
            'bold':False,
            'italic':False,
            'anchor_y':'top',
            'anchor_x':'center',
            'dpi':96,
            'x':w/2, 'y':h,
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
        self.ships_factory = entity.ShipFactory()
        exit_button = MenuItem("Go to the Battle", self.on_quit)
        self.create_menu([exit_button])
        self.ship_list = gui.ShipList((50, 600), 200, 500)
    
    def on_enter(self):
        super(ShipMod, self).on_enter()
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
        #self.ship_list.set_model(self.player.fleet)
        
    def on_quit(self):
        my_battle = battle.Battle()
        battle_scene = cocos.scene.Scene(my_battle) 
        director.replace(FadeTransition(battle_scene, duration = 3))
        
