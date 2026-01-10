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
INSERT_STEP_MODE = 3

LIVE_SIZE = 20
OTHER_SIZE = 20

class SequencerApp(App):
  def __init__(self):

    self.sequence = [AllLEDStep(255,0,255),
                     PauseStep(500),
                     AllLEDStep(0,0,0),
                     PauseStep(500),
                     AllLEDStep(0,255,0),
                     PauseStep(500),
                     AllLEDStep(0,0,0),
                     PauseStep(5000),
                     ]

    self.sequence_pos = -1  # -1 means next step should be first
    self._foregrounded = False

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
          self.ui_delegate = Menu(self, ["Insert step", "Delete step", "Play"], select_handler=self._handle_menu_select, back_handler=self._handle_menu_back)
          # TODO: Edit step
          # TODO: Play in background
          # TODO: Choose difficulty
      return self.ui_delegate.update(delta)
    elif self._mode == INSERT_STEP_MODE:
      if self.ui_delegate is None:
        self.ui_delegate = InsertStepUI(self)
      return self.ui_delegate.update(delta)

  def update_PLAY(self, delta):

    if self.sequence_pos == -1:
      self.sequence_pos = 0
      self.sequence[self.sequence_pos].enter_step()

    do_next = self.sequence[self.sequence_pos].progress_step()

    if do_next:
      self.sequence_pos = (self.sequence_pos + 1) % len(self.sequence)

      assert self.sequence_pos >= 0
      assert self.sequence_pos < len(self.sequence)

      self.sequence[self.sequence_pos].enter_step()


 
  def render_step(self, ctx, offset):
    if offset == 0:
      text_colour = (255,255,0)
      y = 0 
      ctx.font_size = LIVE_SIZE
    else:
      text_colour = (128,128,128)
      y = LIVE_SIZE/2 + offset * (OTHER_SIZE) - (OTHER_SIZE/2)
      ctx.font_size = OTHER_SIZE

    render_step = self.sequence_pos + offset

    if render_step >= 0 and render_step < len(self.sequence):
      assert render_step >= 0
      assert render_step < len(self.sequence)

      ctx.text_align = ctx.LEFT

      step=self.sequence[render_step]

      step.render(self._mode, ctx,render_step, y, text_colour)


 
  def draw(self, ctx):

    clear_background(ctx)

    # delegate drawing completely if a UI delegate is active
    if self.ui_delegate is not None:
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

    ctx.text_baseline = ctx.MIDDLE


    if self.sequence_pos >= 0:
      assert self.sequence_pos >= 0
      assert self.sequence_pos < len(self.sequence)
      self.render_step(ctx, 0)

      for n in range(1,8):
        self.render_step(ctx, n)
        self.render_step(ctx, -n)
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
    self.ui_delegate = None
    self._mode = EDIT_MODE

  def _handle_menu_select(self, item, idx):
    print(f"SELECT from Sequencer App menu: item={item} idx={idx}")
    assert self._mode == MENU_MODE, "should be in menu mode"
    assert isinstance(self.ui_delegate, Menu), "in menu mode, the UI delegate should be Menu"

    if item == "Play":
      # switch back to play mode 
      self.ui_delegate._cleanup()
      self.ui_delegate = None
      self.sequence_pos = -1
      self._mode = PLAY_MODE
    elif item == "Delete step":
      # delete current step then switch back to edit mode
      assert self.sequence_pos >= 0
      assert self.sequence_pos < len(self.sequence)

      del self.sequence[self.sequence_pos]

      # BUG: this is going to break when deleting all steps so that
      # the sequence list is empty. Probably other bits of the
      # app will break too, and maybe it should be the case that there
      # is always one step?
      if self.sequence_pos >= len(self.sequence):
          self.sequence_pos = len(self.sequence) - 1

      assert self.sequence_pos >= 0
      assert self.sequence_pos < len(self.sequence)

      self.ui_delegate._cleanup()
      self.ui_delegate = None
      self._mode = EDIT_MODE
    elif item == "Insert step":
      self.ui_delegate._cleanup()
      self.ui_delegate = None
      self._mode = INSERT_STEP_MODE
    else:
      print("Selected menu item is unhandled - ignoring")

__app_export__ = SequencerApp


class InsertStepUI:
  def __init__(self, app):
    self.app = app
    self.chosen_colour = 0
    self.rgb = (0,0,0)
    eventbus.on(ButtonDownEvent, self._handle_buttondown, self.app)

  def update(self, delta):
    if self.chosen_colour == 0:
      self.rgb = (255,0,0)
    elif self.chosen_colour == 1:
      self.rgb = (0,255,0)
    elif self.chosen_colour == 2:
      self.rgb = (0,0,255)
    elif self.chosen_colour == 3:
      self.rgb = (0,0,0)
    else:
      self.rgb = (0,0,0)

    for n in range(0,12):
      tildagonos.leds[n+1] = self.rgb
    tildagonos.leds.write()

  def draw(self, ctx):

    ctx.arc(0, 0, 60, 0, 2 * math.pi, True)
    ctx.rgb(*self.rgb).fill()

  def _cleanup():
    eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)

  def _handle_buttondown(self, event):
    if BUTTON_TYPES["UP"] in event.button:
      self.chosen_colour = (self.chosen_colour + 1) % 4
    elif BUTTON_TYPES["DOWN"] in event.button:
      self.chosen_colour = (self.chosen_colour + 1) % 4
    elif BUTTON_TYPES["CONFIRM"] in event.button:
      assert self.app.sequence_pos >= 0
      assert self.app.sequence_pos < len(self.app.sequence)

      r = self.rgb[0]
      g = self.rgb[1]
      b = self.rgb[2]
      self.app.sequence.insert(self.app.sequence_pos, AllLEDStep(r, g, b))
      self.app.sequence_pos += 1

      assert self.app.sequence_pos >= 0
      assert self.app.sequence_pos < len(self.app.sequence)

      eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)
      self.app._mode = EDIT_MODE
      self.app.ui_delegate = None
    else:
      print("unhandled button event in InsertStepUI - ignoring")


class Step:
  def enter_step(self):
    pass

  def progress_step(self):
    # by default, step finishes immediately, so that one shot steps only
    # need to override enter_step
    return True

  def render(self, mode, ctx, render_step, y, text_colour):
    text = f"{render_step}: No description"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)


class AllLEDStep(Step):
  def __init__(self, r, g, b):
    self.rgb = (r, g, b)

  def enter_step(self):

    colour = self.rgb
    for n in range(0,12):
      tildagonos.leds[n+1] = colour
    tildagonos.leds.write()

  def render(self, mode, ctx, render_step, y, text_colour):
    text = f"{render_step}: All LEDs "
    tw = ctx.text_width(text)
    tw2 = ctx.text_width("this")
    w = tw + tw2
    ctx.move_to(int(-w/2), y).rgb(*text_colour).text(text)
    ctx.move_to(int(-w/2 + tw), y).rgb(*self.rgb).text("this")


class PauseStep(Step):
  def __init__(self, ms):
    self.ms = ms
    self.entered_time = None

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

    text = f"{render_step}: Pause {duration}ms"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)
