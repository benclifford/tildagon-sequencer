from .base import Step
from ..const import EDIT_MODE

class CountLoopsStep(Step):
  def __init__(self):
    self.reset()

  def enter_step(self):
    self.count += 1

  def render(self, mode, ctx, render_step, y, text_colour):
    text = f"{render_step}: Counted {self.count} times"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)

  def reset(self):
    self.count = 0


class InsertCountLoopsUI:
  def __init__(self, app):
    self.app = app

  def update(self, delta):
    self.app.sequence.insert(self.app.sequence_pos, CountLoopsStep())
    self.app.sequence_pos += 1

    assert self.app.sequence_pos >= 0
    assert self.app.sequence_pos < len(self.app.sequence)

    # and remove ourselves from the app
    self.app.ui_delegate = None
    self.app._mode = EDIT_MODE


  def draw(self, ctx):
    pass
