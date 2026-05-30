from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus

from .base import WhenStep
from ..const import LIVE_SIZE, PLAY_MODE, EDIT_MODE



class WhenButtonPushedStep(WhenStep):

  def __init__(self, app):
    super().__init__()

    self.app = app
    self.pressed = False
    eventbus.on(ButtonDownEvent, self._handle_buttondown, self.app)

  def _handle_buttondown(self, event):
    # match any button except CANCEL
    if self.app._mode == PLAY_MODE and BUTTON_TYPES["CANCEL"] not in event.button:
      self.pressed = True

  def poll_for_when(self):
    if self.pressed:
      self.pressed = False
      return True
    else:
      return False

  # This is to stop execution if we flow onto this step.
  # This isn't the long term structure of how I want things
  # to be, but it will maybe do for now, until I maybe get
  # some more hierarchical editing implemented.
  def progress_step(self):
    return False

  def render(self, mode, ctx, render_step, y, text_colour):
    text = f"When button pushed"   # : {self.pressed}"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)
    ctx.rgb(255,0,0).begin_path()
    ctx.move_to(-240, y - LIVE_SIZE/2)
    ctx.line_to(240, y - LIVE_SIZE/2)
    ctx.stroke()


class InsertWhenButtonPushedUI:
  def __init__(self, app):
    self.app = app

  def update(self, delta):
    self.app.sequence.insert(self.app.sequence_pos, WhenButtonPushedStep(self.app))
    self.app.sequence_pos += 1

    assert self.app.sequence_pos >= 0
    assert self.app.sequence_pos < len(self.app.sequence)

    # and remove ourselves from the app
    self.app.ui_delegate = None
    self.app._mode = EDIT_MODE


  def draw(self, ctx):
    pass
