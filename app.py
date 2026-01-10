from app import App
from app_components import clear_background, Menu
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
MENU_MODE = 2

class SequencerApp(App):
  def __init__(self):

    # This sequence is "commands". Right now a "command" is an RGB tuple
    # meaning "set all LEDs to this then wait 333ms".
    self.sequence = [(0,0,0), (255, 0, 255), (0, 255, 0), (0,0,0), (0, 255, 0), (0,0,0)]

    self.sequence_pos = -1  # -1 means next step should be first
    self._foregrounded = False
    self._last_step_time = 0

    self._mode = PLAY_MODE

    self.ui_delegate = None

  def update(self, delta):
    # print(f"Update, mode is {self._mode}")
    if not self._foregrounded:
        # we maybe just regained focus, so (re-)register UI events.
        # I'm not clear on the favoured way to do that?
        eventbus.on(ButtonDownEvent, self._handle_buttondown, self)
        eventbus.emit(PatternDisable())
        self._foregrounded = True

    if self._mode == PLAY_MODE:
      self.update_PLAY(delta)
    elif self._mode == MENU_MODE:
      # print("main menu update")
      if self.ui_delegate is None:
          self.ui_delegate = Menu(self, ["Insert step", "Edit step", "Delete step", "Run", "Run in background", "Choose difficulty"], select_handler=self._handle_menu_select, back_handler=self._handle_menu_back)
      return self.ui_delegate.update(delta)

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

    # delegate drawing completely to the menu if it is active
    if self._mode == MENU_MODE:
      # print("main menu draw")
      return self.ui_delegate.draw(ctx)

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
      ctx.font_size = LIVE_SIZE
      ctx.move_to(0, 0).gray(1).text(f"NO EXECUTION YET")

  def _handle_buttondown(self, event):
    # Button behaviours:
    #   In PLAY mode:
    #     CANCEL button will switch to edit mode (so to exit, CANCEL twice).
    #     Other buttons I would like to be available later for user events,
    #     so ignore them here.
    #   In EDIT mode, CANCEL exits. UP and DOWN move through the program.
    #     CONFIRM triggers activity menu.

    if self._mode == PLAY_MODE and BUTTON_TYPES["CANCEL"] in event.button:
      self._mode = EDIT_MODE
    elif self._mode == EDIT_MODE and BUTTON_TYPES["CANCEL"] in event.button: 
      eventbus.remove(ButtonDownEvent, self._handle_buttondown, self)
      eventbus.emit(PatternEnable())
      self._foregrounded = False
      self.minimise()
    elif self._mode == EDIT_MODE and BUTTON_TYPES["UP"] in event.button: 
      if self.sequence_pos > 0:
        self.sequence_pos = (self.sequence_pos - 1)
      # else ignore, because we're at the start of the list
    elif self._mode == EDIT_MODE and BUTTON_TYPES["DOWN"] in event.button: 
      if self.sequence_pos < len(self.sequence)-1:
        self.sequence_pos = (self.sequence_pos + 1)
      # else ignore because we're at the end of the list
    elif self._mode == EDIT_MODE and BUTTON_TYPES["CONFIRM"] in event.button: 
      pass # NOTIMPL: edit menu ... time to learn about how to use menu UI component.
      self._mode = MENU_MODE
      self.ui_delegate = None
      # this will be populated in update(), outside of the eventbus handler, because
      # otherwise Menu() can see the in-progress button press event and select
      # an option spuriously/immediately.
      print("Switching to MENU mode")
    elif self._mode == MENU_MODE:
      pass # menu will handle its own button events, we should stay out of the way
    else:
      print("Unknown button event - ignoring - mode {self._mode}, event {event}")

  def _handle_menu_back(self):
    # back should back the menu go away and then go to EDIT mode (because
    # is where we came from before the menu)
    print("BACK from Sequencer App menu")
    assert self._mode == MENU_MODE, "should be in menu mode"
    assert isinstance(self.ui_delegate, Menu), "in menu mode, the UI delegate should be Menu"
    self.ui_delegate._cleanup()
    self._mode = EDIT_MODE

  def _handle_menu_select(self, item, idx):
    print(f"SELECT from Sequencer App menu: item={item} idx={idx}")
    assert self._mode == MENU_MODE, "should be in menu mode"
    assert isinstance(self.ui_delegate, Menu), "in menu mode, the UI delegate should be Menu"


__app_export__ = SequencerApp
