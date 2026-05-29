from ..const import LIVE_SIZE


class Step:
  def __init__(self):
    # Where the step lives inside the program, for referencing.
    # I'd prefer a more object graph style program structure,
    # which would get rid of this field.
    self._step_number: int

  def enter_step(self):
    pass

  def progress_step(self):
    # by default, step finishes immediately, so that one shot steps only
    # need to override enter_step. 
    # return True for "move to next step", False for "stay in this step",
    # or an integer to jump to that step number.
    return True

  def render(self, mode, ctx, render_step, y, text_colour):
    text = f"{render_step}: No description"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)

  def poll_for_when(self):
    # If this is a When step that has fired (and so wants to run events),
    # return True (once) and the executor will start running at the
    # step after this one.
    return False

  def reset(self):
    # Called to reset the step, for example when play stops or starts
    pass


# kind of step that pairs with an EndStep to scope out a block of steps
class BlockStep(Step):
    def progress_end_step(self):
        """What to do when the corresponding EndStep is reached."""
        ...

    def get_end_name(self) -> str:
        """Return the name used in end blocks"""
        return "block"


class EndStep(Step):
  def __init__(self):
    self._start_step = None
    # this should be set dynamically at start of execution to the
    # executor-detected start step.

  def progress_step(self):
    assert isinstance(self._start_step, BlockStep), f"start step should be a BlockStep: {self._start_step}"
    return self._start_step.progress_end_step()

  def render(self, mode, ctx, render_step, y, text_colour):
    if self._start_step:
        text = "End " + self._start_step.get_end_name()
    else:
        text = "End ... of something?"
        print("consistency error: end step with missing start step")
    tw = ctx.text_width(text)

    # TODO: This line doesn't work nicely when the end block is for an
    # inner block, not an outer-when. What should happen here is part of
    # the bigger question about how to represent nested blocks.
    if isinstance(self._start_step, WhenStep):
        ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)
        ctx.rgb(255,0,0).begin_path()
        ctx.move_to(-240, y + LIVE_SIZE/2)
        ctx.line_to(240, y + LIVE_SIZE/2)
        ctx.stroke()
    else:
        ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)
        ctx.rgb(64,64,255).begin_path()
        ctx.move_to(-tw/2-10, y + LIVE_SIZE/2)
        ctx.line_to(tw/2+10, y + LIVE_SIZE/2)
        ctx.stroke()


class WhenStep(BlockStep):
    """Marker type for When steps."""
    def get_end_name(self):
        return "when"

