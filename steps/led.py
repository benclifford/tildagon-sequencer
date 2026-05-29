from tildagonos import tildagonos

from .base import Step
from ..const import EDIT_MODE
from ..pickers.colour import ColourPicker


class LEDStep(Step):
  def __init__(self, r, g, b):
    self.rgb = (r, g, b)
    self.leds = list(range(0,12)) # all LEDs

  def enter_step(self):

    colour = self.rgb
    for n in self.leds:
      tildagonos.leds[n+1] = colour
    tildagonos.leds.write()

  def render(self, mode, ctx, render_step, y, text_colour):
    text = f"{render_step}: Set LEDs to "
    tw = ctx.text_width(text)
    tw2 = ctx.text_width("this colour")
    w = tw + tw2
    this_colour = (self.rgb[0] / 256, self.rgb[1] / 256, self.rgb[2] / 256)
    ctx.move_to(int(-w/2), y).rgb(*text_colour).text(text)
    ctx.move_to(int(-w/2 + tw), y).rgb(*this_colour).text("this colour")


# TODO: the top STEP UI needs to choose both a colour and a set
# of LEDs. So possibly the colour picker now splits out into its
# own UI component, that sits along side a "choose LEDs" picker
# that initially can be "all" or 1,2,3,4,5,6,7,8,9,10,11,12 or a
# subset picker.

# Initialise to the colour picker
# On colour picker select, initalise the LED picker
# On LED picker select, 

class InsertLEDStepUI:
  def __init__(self, app):
    self.app = app
    self.rgb = (0,0,0)
    self.ui_delegate = ColourPicker(app, callback=self.handle_colour_chosen)

  def update(self, delta):
    self.ui_delegate.update(delta)
 
  def draw(self, ctx):
    self.ui_delegate.draw(ctx) 

  def handle_colour_chosen(self, rgb):
    self.ui_delegate._cleanup()
    self.rgb = rgb

    # TODO: move to next state. which until I do LED picking, is
    # to create a step and finish.

    r = self.rgb[0]
    g = self.rgb[1]
    b = self.rgb[2]
    self.app.sequence.insert(self.app.sequence_pos, LEDStep(r, g, b))
    self.app.sequence_pos += 1

    assert self.app.sequence_pos >= 0
    assert self.app.sequence_pos < len(self.app.sequence)

    # TODO: i think this should move into a completed callback on the
    # main app: the modification of app state is a clue.
    self.app._mode = EDIT_MODE
    self.app.ui_delegate = None
