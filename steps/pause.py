import time

from app_components import Menu

from .base import Step
from ..const import PLAY_MODE, EDIT_MODE

class PauseStep(Step):
  def __init__(self, ms):
    self.ms = ms
    self.reset()

  def enter_step(self):
    self.entered_time = time.ticks_ms()

  def progress_step(self):
    assert self.entered_time is not None, "Step should have been entered before being progressed"
    now = time.ticks_ms()
    delta_ticks = time.ticks_diff(now, self.entered_time)
    b = delta_ticks > self.ms
    if b:
      self.entered_time = None
    return b

  def render(self, mode, ctx, render_step, y, text_colour):

    if self.entered_time is not None and mode == PLAY_MODE:
      now = time.ticks_ms()
      duration = self.ms - time.ticks_diff(now, self.entered_time)
    else:
      duration = self.ms

    duration_s = str(int(duration / 100) / 10)

    text = f"{render_step}: Pause {duration_s}s"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)

  def reset(self):
    self.entered_time = None


class InsertPauseStepUI:
  def __init__(self, app):
    self.app = app
    self.ui_delegate = Menu(self.app, ["500ms", "1 second", "5 seconds", "30 seconds"], back_handler=self._handle_menu_back, select_handler=self._handle_menu_select)

  def _handle_menu_back(self):
    # this goes back to edit mode when a more consistent flow would be to
    # go back to the previous screen, which is the step type picker.

    # clean up our downstream delegate
    self.ui_delegate._cleanup()

    # and remove ourselves from the app
    self.app.ui_delegate = None
    self.app._mode = EDIT_MODE

  def update(self, delta):
    self.ui_delegate.update(delta)
 
  def draw(self, ctx):
    self.ui_delegate.draw(ctx) 

  def _handle_menu_select(self, item, idx):
    self.ui_delegate._cleanup()

    if idx == 0:
      ms = 500
    elif idx == 1:
      ms = 1000
    elif idx == 2:
      ms = 5000
    elif idx == 3:
      ms = 30000
    else:
      assert False, "invalid duration menu option"

    self.app.sequence.insert(self.app.sequence_pos, PauseStep(ms))
    self.app.sequence_pos += 1

    assert self.app.sequence_pos >= 0
    assert self.app.sequence_pos < len(self.app.sequence)

    # and remove ourselves from the app
    self.app.ui_delegate = None
    self.app._mode = EDIT_MODE
