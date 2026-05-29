import time

from .base import Step
from ..const import PLAY_MODE

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
