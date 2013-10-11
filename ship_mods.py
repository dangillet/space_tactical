import json

import pyglet

import cocos

from cocos.menu import *
from cocos.scenes import *
from cocos.director import director

import battle, gui, entity, serializer

def set_fonts(menu):
    "Called from a menu to set the default fonts used"
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
    "Layer containing the different menu elements"
    def __init__(self):
        super(ShipMod, self).__init__()
        self.player = entity.Player.load()
        self.inventory = self.player.inventory

        w, h = director.get_window_size()
        # The fleet list
        self.add(ShipList(), name="ship_list")
        self.selected = None
        
        # Page title
        self.add(cocos.text.Label("Ship Modifications",
                                font_name = "Classic Robot",
                                font_size = 36,
                                color = (200, 200, 200, 255),
                                anchor_y = "top",
                                anchor_x = "center",
                                x=w//2,
                                y=h)
                )
        # The ship display window
        self.ship_info = gui.ShipInfoLayer((250, h-400 ), 550, 300, show_all_weapons=True)
        self.add(self.ship_info, name="ship_info")
        # The list of modifications in inventory
        self.add(ModList(), name="mod_list")
        
    
    def on_enter(self):
        super(ShipMod, self).on_enter()
        self.get("ship_list").push_handlers(self)
    
    def on_exit(self):
        super(ShipMod, self).on_exit()
        self.get("ship_list").pop_handlers()
        
    def on_selected(self, ship):
        self.selected = ship
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
        if not self.selected:
            return
        slot_weapon = self.get("slot_menu_wea")
        selected_weapon = slot_weapon.selected_mod
        i=1
        while selected_weapon.type != "weapon":
            selected_weapon = slot_weapon.mod_at_index(slot_weapon.selected_index - i)
            i += 1
        if mod.type in self.selected.slots and \
                self.selected.add_mod(mod):
            self.inventory.remove(mod)
            self.get("mod_list").on_change()
        elif mod.type in selected_weapon.slots and \
                selected_weapon.add_mod(mod):
            self.inventory.remove(mod)
            self.get("mod_list").on_change()
    
    def on_mod_deselected(self, mod):
        if self.selected.remove_mod(mod):
            self.player.add_mod_to_inventory(mod)
            self.get("mod_list").on_change()

class SlotMenu(gui.SubMenu):
    def __init__(self, slot, hmargin):
        self.slot = slot
        super(SlotMenu, self).__init__()
        w, h = director.get_window_size()
        set_fonts(self)
        self.font_title['font_size'] = 20
        self.font_item['font_size'] = self.font_item_selected ['font_size'] = 12
        self.menu_halign = LEFT
        self.menu_valign = TOP
        self.menu_hmargin = hmargin
        self.menu_vmargin = 400
        
    def on_enter(self):
        super(SlotMenu, self).on_enter()
        self.slot.parent.push_handlers(self)
        self._create_menu_items()
    
    def _create_menu_items(self):
        l = []
        self._append_mod_menu_item(l, self.slot, 0) 
        if not l:
            l = [MenuItem("None", None)]
        self.title = self.slot.type + " (%d/%d)" % (len(self.slot.mods), 
                                                self.slot.max_count)
        self.create_menu(l)
    
    def _append_mod_menu_item(self, l, slot, level):
        for mod in slot.mods:
            l.append(MenuItem("  "*level + mod.name,
                     self.parent.on_mod_deselected, mod))
            if hasattr(mod, "slots"):
                for slot in mod.slots.itervalues():
                    self._append_mod_menu_item(l, slot, level+1)
    
    def on_exit(self):
        super(SlotMenu, self).on_exit()
        self.slot.parent.pop_handlers()
        map(self.remove, (child for z,child in self.children) )
        
    def on_key_press(self, s, m):
        return False
    
    def on_change(self):
        old_selected_mod = self.selected_mod
        map(self.remove, (child for z,child in self.children) )
        self._create_menu_items()
        if old_selected_mod is not None:
            new_idx = self.index_of_mod(old_selected_mod)
            self._select_item(new_idx)
    
    def on_mouse_motion( self, x, y, dx, dy ):
        "Do not select item when hovering over them."
        pass
    
    def on_mouse_release( self, x, y, buttons, modifiers ):
        "Only select items when clicking them."
        super(SlotMenu, self).on_mouse_motion(x, y, 0, 0)
        if buttons == pyglet.window.mouse.LEFT:
            return super(SlotMenu, self).on_mouse_release(x, y, buttons, modifiers)
            
    @property
    def selected_mod(self):
        "Returns the selected mod in this slot."
        # If list is empty, there is only one child which is a MenuItem("None", None)
        if self.children[ self.selected_index][1].callback_func is None:
            return None
        # ItemMenu contains a callback passing the mod as first argument.
        return self.children[ self.selected_index][1].callback_args[0]
    
    @property
    def mod_at_index(self, idx):
        "Returns the mod at the given index"
        return self.children[idx][1].callback_args[0]
    
    def index_of_mod(self, mod):
        "Finds the index of the MenuItem displaying this mod."
        for idx, (z, child) in enumerate(self.children):
            if child.callback_args[0] is mod:
                return idx
        return 0
    
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
        self.buttons.append( MenuItem("Save...", self.on_save) )
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
    
    def on_save(self):
        with open("player.json", "w") as fp:
            json.dump(self.parent.player, fp, cls=serializer.SpaceEncoder, indent=2)
        
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
        l = [MenuItem(mod.name, self.parent.on_mod_selected, mod) for mod in self.parent.inventory]
        if not l:
            l = [MenuItem("None", None)]
        self.create_menu(l)
    
    def on_exit(self):
        super(ModList, self).on_exit()
        map(self.remove, (child for z,child in self.children) )
    
    def on_key_press(self, s, m):
        return False

    def on_change(self):
        self.on_exit()
        self.on_enter()
