from .base import WhenStep
from ..const import LIVE_SIZE

class WhenPlayStep(WhenStep):

  def __init__(self):
    self._start = False

  def poll_for_when(self):
    if self._start:
      self._start = False
      return True
    else:
      return False

  def progress_step(self):
    return False

  def render(self, mode, ctx, render_step, y, text_colour):
    text = f"When play starts"  # : {self._start}"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)
    ctx.rgb(255,0,0).begin_path()
    ctx.move_to(-240, y - LIVE_SIZE/2)
    ctx.line_to(240, y - LIVE_SIZE/2)
    ctx.stroke()

  def reset(self):
    self._start = True

  def progress_end_step(self):
    # block here.
    return False
