from .base import BlockStep

class RepeatForeverStep(BlockStep):
  def progress_end_step(self):
    # continue from the step we were at before
    return self._step_number + 1

  def render(self, mode, ctx, render_step, y, text_colour):
    text = "Repeat forever"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)
