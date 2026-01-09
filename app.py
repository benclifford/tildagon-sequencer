from app import App
from app_components import clear_background
from system.eventbus import eventbus
from tildagonos import tildagonos
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.patterndisplay.events import PatternDisable, PatternEnable
import asyncio
import random
import time


class SequencerApp(App):
  def __init__(self):

    # This sequence is "commands". Right now a "command" is an RGB tuple
    # meaning "set all LEDs to this then wait 333ms".
    self.sequence = [(0,0,0), (255, 0, 255), (0, 255, 0), (0,0,0), (0, 255, 0), (0,0,0)]

    self.sequence_pos = -1  # -1 means next step should be first
    self._foregrounded = False
    self._last_step_time = 0

  def update(self, delta):
    if not self._foregrounded:
        # we maybe just regained focus, so (re-)register UI events.
        # I'm not clear on the favoured way to do that?
        eventbus.on(ButtonDownEvent, self._handle_buttondown, self)
        eventbus.emit(PatternDisable())
        self._foregrounded = True

    now = time.ticks_ms()
    delta_ticks = time.ticks_diff(now, self._last_step_time)

    if delta_ticks > 333:
      self._last_step_time = now

      self.sequence_pos = (self.sequence_pos + 1) % len(self.sequence)

      assert self.sequence_pos >= 0
      assert self.sequence_pos < len(self.sequence)
      colour = self.sequence[self.sequence_pos]
      for n in range(0,12):
          tildagonos.leds[n+1] = colour
      tildagonos.leds.write()
 
  def draw(self, ctx):

    clear_background(ctx)
    ctx.text_align = ctx.CENTER
    ctx.text_baseline = ctx.MIDDLE

    LIVE_SIZE = 20
    OTHER_SIZE = 15

    if self.sequence_pos >= 0:
      assert self.sequence_pos >= 0
      assert self.sequence_pos < len(self.sequence)
      ctx.font_size = LIVE_SIZE
      ctx.move_to(0, 0).rgb(255,255,0).text(f"{self.sequence_pos}: {self.sequence[self.sequence_pos]}")

      ctx.font_size = OTHER_SIZE
      for n in range(1,8):
        y = LIVE_SIZE/2 + n * (OTHER_SIZE) - (OTHER_SIZE/2)

        render_step = self.sequence_pos - n
        if render_step >= 0:
          assert render_step < len(self.sequence)
          ctx.move_to(0, -y).gray(1).text(f"{render_step}: {self.sequence[render_step]}")

        render_step = self.sequence_pos + n
        if render_step < len(self.sequence):
          assert render_step >= 0
          ctx.move_to(0, y).gray(1).text(f"{render_step}: {self.sequence[render_step]}")
    else:
      ct.font_size = LIVE_SIZE
      ctx.move_to(0, 0).gray(1).text(f"NO EXECUTION YET")

  def _handle_buttondown(self, event):
    # this will happen on any of the 6 button presses without
    # distinguishing between them - that means you can press any
    # button to minimise.

    eventbus.remove(ButtonDownEvent, self._handle_buttondown, self)
    eventbus.emit(PatternEnable())
    self._foregrounded = False
    self.minimise()

__app_export__ = SequencerApp
