import cocos
from cocos import text
from cocos.scenes import *
from cocos.director import director

import battle

class GameOver(cocos.layer.Layer):
    def __init__(self):
        super(GameOver, self).__init__()
        self.is_event_handler = True
        w, h = director.get_window_size()
        msg = _("""{.align 'center'}
{font_size 36}{color [255, 0, 0, 255]}Game Over {}
{font_size 14}{color [200, 200, 200, 255]}Press any key to play again.
        """)
        self.add(text.RichLabel(msg,
                                font_name='Classic Robot',
                                anchor_x="center",
                                anchor_y="center",
                                position = (w/2, h/2),
                                width = 400,
                                multiline=True
                                ))
    
    def on_key_release(self, symbol, modifier):
        battle_scene = cocos.scene.Scene(battle.Battle())
        director.replace(FadeTransition(battle_scene, duration = 2))
