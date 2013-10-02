import cocos

from cocos.menu import *
from cocos.scenes import *
from cocos.director import director

import battle, gui



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
        
        self.exit_button = MenuItem("Go to the Battle", None)
        self.create_menu([self.exit_button])
    
    def on_enter(self):
        super(ShipMod, self).on_enter()
        my_battle = battle.Battle()
        battle_scene = cocos.scene.Scene(my_battle)
        transition = FadeTransition(battle_scene, duration = 5, color=(0,0,0), src=director.scene)
        self.exit_button.callback_func = director.replace
        self.exit_button.callback_args = (transition,)
        
        
    def on_exit(self):
        super(ShipMod, self).on_exit()
        #self.remove([child self.children])
        
