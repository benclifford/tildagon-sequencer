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

    if self.sequence_pos >= 0:
      assert self.sequence_pos >= 0
      assert self.sequence_pos < len(self.sequence)
      ctx.move_to(0, 0).gray(1).text(f"{self.sequence_pos}: {self.sequence[self.sequence_pos]}")
    else:
      ctx.move_to(0, 0).gray(1).text(f"NO STEP YET")

  def _handle_buttondown(self, event):
    # this will happen on any of the 6 button presses without
    # distinguishing between them - that means you can press any
    # button to minimise.

    eventbus.remove(ButtonDownEvent, self._handle_buttondown, self)
    eventbus.emit(PatternEnable())
    self._foregrounded = False
    self.minimise()

__app_export__ = SequencerApp
