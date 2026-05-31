from .base import EndStep, BlockStep
from ..const import EDIT_MODE

class RepeatForeverStep(BlockStep):
  def progress_end_step(self):
    # continue from the step we were at before
    return self._step_number + 1

  def render(self, mode, ctx, render_step, y, text_colour):
    text = "Repeat forever"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)

  def get_end_name(self):
      return "repeat"


class InsertRepeatForeverStepUI:
  def __init__(self, app):
      self.app = app

  def update(self, delta):
    self.app.sequence.insert(self.app.sequence_pos, RepeatForeverStep())
    self.app.sequence_pos += 1

    self.app.sequence.insert(self.app.sequence_pos, EndStep())

    # advance cursor onto the new end step so that subsequent inserts will insert into the new block
    self.app.sequence_pos += 1

    assert self.app.sequence_pos >= 0
    assert self.app.sequence_pos < len(self.app.sequence)

    # this will make the end step be populated properly
    # which won't happen otherwise.
    self.app._reset_steps()

    # and remove ourselves from the app
    self.app.ui_delegate = None
    self.app._mode = EDIT_MODE

  def draw(self, ctx):
    pass
