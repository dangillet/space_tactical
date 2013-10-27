from cocos import draw

class LaserBeam(draw.Canvas):
    def __init__(self):
        super(LaserBeam, self).__init__()
        self.pos_from = (0,0)
        self.pos_to = (0,0)
        self.visible = False

    def render(self):
        self.set_endcap( draw.ROUND_CAP )
        self.set_color( (255,0,0,200) )
        self.set_stroke_width( 5 )
        self.move_to(self.pos_from); self.line_to(self.pos_to)
        self.set_color( (255,180,180,200) )
        self.set_stroke_width( 2 )
        self.move_to(self.pos_from); self.line_to(self.pos_to)
