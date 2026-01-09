from app import App
from app_components import clear_background
from system.eventbus import eventbus
from tildagonos import tildagonos
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.patterndisplay.events import PatternDisable, PatternEnable
import asyncio
import math
import random
import time

PLAY_MODE = 0
EDIT_MODE = 1

class SequencerApp(App):
  def __init__(self):

    # This sequence is "commands". Right now a "command" is an RGB tuple
    # meaning "set all LEDs to this then wait 333ms".
    self.sequence = [(0,0,0), (255, 0, 255), (0, 255, 0), (0,0,0), (0, 255, 0), (0,0,0)]

    self.sequence_pos = -1  # -1 means next step should be first
    self._foregrounded = False
    self._last_step_time = 0

    self._mode = PLAY_MODE

  def update(self, delta):
    if not self._foregrounded:
        # we maybe just regained focus, so (re-)register UI events.
        # I'm not clear on the favoured way to do that?
        eventbus.on(ButtonDownEvent, self._handle_buttondown, self)
        eventbus.emit(PatternDisable())
        self._foregrounded = True

    if self._mode == PLAY_MODE:
      self.update_PLAY(delta)

  def update_PLAY(self, delta):

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

    if self._mode == PLAY_MODE:
        mode_colour = (0, 255, 0)
    elif self._mode == EDIT_MODE:
        mode_colour = (0, 0, 255)
    else:  # indicate bad mode
        mode_colour = (255, 0, 0)

    # max radius is 120, but I like the visual effect of being slightly
    # inset.
    ctx.arc(0, 0, 115, 0, 2 * math.pi, True)
    ctx.rgb(*mode_colour).fill()

    ctx.arc(0, 0, 105, 0, 2 * math.pi, True)
    ctx.rgb(0, 0, 0).fill()

    ctx.text_align = ctx.CENTER
    ctx.text_baseline = ctx.MIDDLE

    LIVE_SIZE = 20
    OTHER_SIZE = 20

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
    # Button behaviours:
    #   In play mode:
    #     CANCEL button will switch to edit mode (so to exit, CANCEL twice).
    #     Other buttons I would like to be available later for user events,
    #     so ignore them here.

    if self._mode == PLAY_MODE and BUTTON_TYPES["CANCEL"] in event.button:
      self._mode = EDIT_MODE
    elif self._mode == EDIT_MODE and BUTTON_TYPES["CANCEL"] in event.button: 
      eventbus.remove(ButtonDownEvent, self._handle_buttondown, self)
      eventbus.emit(PatternEnable())
      self._foregrounded = False
      self.minimise()
    else:
      print("button event in unknown mode - ignoring")

__app_export__ = SequencerApp
