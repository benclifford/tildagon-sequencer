from app import App
from app_components import clear_background, Menu
from system.eventbus import eventbus
from tildagonos import tildagonos
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.patterndisplay.events import PatternDisable, PatternEnable
from system.scheduler.events import RequestForegroundPushEvent
import asyncio
import math
import random
import sys
import time

from .steps.base import BlockStep, Step, EndStep, WhenStep
from .steps.button import WhenButtonPushedStep
from .steps.count import CountLoopsStep
from .steps.forever import RepeatForeverStep
from .steps.imu import WhenIMUUpright
from .steps.led import LEDStep, InsertLEDStepUI
from .steps.pause import PauseStep, InsertPauseStepUI
from .steps.whenplay import WhenPlayStep

from .const import LIVE_SIZE, PLAY_MODE, EDIT_MODE, MENU_MODE, INSERT_STEP_MODE

import platform
if platform.python_implementation() == 'CPython':
    from typing import Any, Optional

from .pickers.colour import ColourPicker

OTHER_SIZE = 20

STEP_PERIOD_MS = 100

class ScripterApp(App):
  def __init__(self):
   try:
    self.sequence = [WhenButtonPushedStep(self),
                       LEDStep(255,255,255),
                       PauseStep(500),
                       LEDStep(0,0,255),
                       PauseStep(500),
                     EndStep(),

                     WhenPlayStep(),
                       RepeatForeverStep(),
                         LEDStep(255,0,0),
                         PauseStep(500),
                         LEDStep(0,0,0),
                         PauseStep(500),
                       EndStep(),
                     EndStep(),

                     WhenIMUUpright(),
                       LEDStep(0,255,0),
                     EndStep(),
                     ]

    # sequence_pos can be positive or negative.
    # when it is negative, it represents something about the code being
    # displayed at a position while also not executing at that position
    # but I'm unsure of how that meaning has turned out... it might be
    # an out-dated idea now? (for example, there's no negative 0
    # representable)
    self.sequence_pos = 0  # don't run anything

    self._mode = EDIT_MODE
    self._reset_steps()

    # so that two different polling loops can run
    # a poll for step
    self._last_step_time_ms = 0

    # TODO: not an Any, it's a "ui delegate", however that
    # should be typed (what calls am I making on it? it's like
    # Menu, for example, or my various similar classes)
    self.ui_delegate: Optional[Any] = None

    self._maximised()
    eventbus.on(RequestForegroundPushEvent, self._handle_foreground_push, self)
   except Exception as e:

    # ignore type error here: cpython doesn't have print_exception, but sim and badge do.
    sys.print_exception(e) # type: ignore

  def _reset_steps(self):
    end_stack: list[BlockStep] = []
    n = 0
    for step in self.sequence:
      step.reset()

      step._step_number = n
 
      if isinstance(step, BlockStep):
        print(f"Appending to block stack for step {n}, {step}")
        print(f"Stack: {end_stack}")
        end_stack.append(step)
      if isinstance(step, EndStep):
        print(f"Popping from block stack for step {n}, {step}")
        step._start_step = end_stack.pop()
        print(f"Stack: {end_stack}")

      n += 1

    # TODO: the UI needs to enforce this too, because otherwise users will
    # easily violate this.
    assert end_stack == [], f"end stack is not empty after step reset: {end_stack}"

  def _handle_foreground_push(self, event):
    if event.app == self:
      print("Foreground push for scripter app - restoring foreground state")
      self._maximised()
    else:
      print("Foreground push for other app - ignoring")
      # TODO: we could actually trigger a when block on this?
      # "do something when a different app/some specific other app comes to foreground"

  def _maximised(self):
    eventbus.on(ButtonDownEvent, self._handle_buttondown, self)
    print("Scripter is disabling pattern in update")
    eventbus.emit(PatternDisable())

  def update(self, delta):
    # print(f"Update, mode is {self._mode}")

    if self._mode == PLAY_MODE:
      self.either_update_PLAY(delta)
    elif self._mode == MENU_MODE:
      # print("main menu update")
      if self.ui_delegate is None:
          self.ui_delegate = Menu(self, ["Insert step above", "Delete step", "Play", "Play in background"], select_handler=self._handle_menu_select, back_handler=self._handle_menu_back)
          # TODO: Edit step
          # TODO: Play in background
          # TODO: Choose difficulty
      return self.ui_delegate.update(delta)
    elif self._mode == INSERT_STEP_MODE:
      if self.ui_delegate is None:
        self.ui_delegate = InsertStepUI(self)
      return self.ui_delegate.update(delta)

  def background_update(self, delta):
    if self._mode == PLAY_MODE:
      self.either_update_PLAY(delta)

  # this can be called as often as you like from as many tasks as
  # you like - specifically intended to be called from both update
  # and the background_update call.
  def either_update_PLAY(self, delta):
    now = time.ticks_ms()
    delta_ticks = time.ticks_diff(now, self._last_step_time_ms)
    if delta_ticks >= STEP_PERIOD_MS and self._mode == PLAY_MODE:
      self.do_update_PLAY(delta)
      self._last_step_time_ms = now

  def do_update_PLAY(self, delta):

    if self.sequence_pos < 0:
      # nothing to run
      pass

    else:
      do_next = self.sequence[self.sequence_pos].progress_step()

      # n.b. this is not the same as "if do_next:" because do_next
      # is richer than a bool
      if do_next is True:
        old_pos = self.sequence_pos
        self.sequence_pos = (self.sequence_pos + 1)
        if self.sequence_pos >= len(self.sequence):
          self.sequence_pos = -old_pos
        else: 
          assert self.sequence_pos >= 0
          assert self.sequence_pos < len(self.sequence)

          self.sequence[self.sequence_pos].enter_step()
      elif do_next is False:
        pass # do nothing
      else:
        assert isinstance(do_next, int), f"do_next not an int: {do_next}"
        self.sequence_pos = do_next
        self.sequence[self.sequence_pos].enter_step()

    for sn in range(0, len(self.sequence)):
      if self.sequence[sn].poll_for_when():
        # guard for the when being the last statement, so there
        # is no sn+1
        if sn+1 < len(self.sequence):
          # TODO: stack-style management to be able to return
          # to main program. maybe fits in with a more nested
          # data structure then a list of steps? to go along
          # with ifs and repeats?
          self.sequence_pos = sn+1
          self.sequence[self.sequence_pos].enter_step()
          # so now we have multiple steps that we have entered

          # break to avoid handling any other when blocks in
          # the same iteration
          break
        else:
          # ignore this when block as it does nothing.
          pass
 
  def render_step(self, ctx, render_base, offset):
    if offset == 0:
      text_colour = (255,255,0)
      y = 0 
      ctx.font_size = LIVE_SIZE
    else:
      text_colour = (128,128,128)
      y = LIVE_SIZE/2 + offset * (OTHER_SIZE) - (OTHER_SIZE/2)
      ctx.font_size = OTHER_SIZE

    render_step = render_base + offset

    if render_step >= 0 and render_step < len(self.sequence):
      assert render_step >= 0
      assert render_step < len(self.sequence)

      ctx.text_align = ctx.LEFT

      step=self.sequence[render_step]

      step.render(self._mode, ctx, render_step, y, text_colour)

 
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
      render_base = self.sequence_pos
    else:
      render_base = -self.sequence_pos

    assert render_base >= 0
    assert render_base < len(self.sequence)
    self.render_step(ctx, render_base, 0)

    for n in range(1,8):
      self.render_step(ctx, render_base, n)
      self.render_step(ctx, render_base, -n)

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
      self._reset_steps()
      self.sequence_pos = abs(self.sequence_pos)
    elif self._mode == EDIT_MODE and BUTTON_TYPES["CANCEL"] in event.button: 
      eventbus.remove(ButtonDownEvent, self._handle_buttondown, self)
      eventbus.emit(PatternEnable())
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
      print(f"Unknown button event - ignoring - mode {self._mode}, event {event}")

  def _handle_menu_back(self):
    # back should back the menu go away and then go to EDIT mode (because
    # is where we came from before the menu)
    print("BACK from Scripter App menu")
    assert self._mode == MENU_MODE, "should be in menu mode"
    assert isinstance(self.ui_delegate, Menu), "in menu mode, the UI delegate should be Menu"
    self.ui_delegate._cleanup()
    self.ui_delegate = None
    self._mode = EDIT_MODE

  def _handle_menu_select(self, item, idx):
    print(f"SELECT from Scripter App menu: item={item} idx={idx}")
    assert self._mode == MENU_MODE, "should be in menu mode"
    assert isinstance(self.ui_delegate, Menu), "in menu mode, the UI delegate should be Menu"

    if item == "Play":
      # switch back to play mode 
      self.ui_delegate._cleanup()
      self.ui_delegate = None
      self.sequence_pos = -1
      self._mode = PLAY_MODE
    elif item == "Play in background":
      # start playing...
      self.ui_delegate._cleanup()
      self.ui_delegate = None
      self.sequence_pos = -1
      self._mode = PLAY_MODE
      # but also minimise, without restoring a bunch of state
      # like patterns or other events, so that things still play.
      eventbus.remove(ButtonDownEvent, self._handle_buttondown, self)
      self.minimise()
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
    elif item == "Insert step above":
      self.ui_delegate._cleanup()
      self.ui_delegate = None
      self._mode = INSERT_STEP_MODE
    else:
      print("Selected menu item is unhandled - ignoring")

__app_export__ = ScripterApp


class InsertStepUI:
  def __init__(self, app):
    self.app = app

    # TODO: types of UI delegate
    self.ui_delegate: Any

    self.ui_delegate = Menu(self.app, ["Set LEDs", "Pause", "Count loops", "When button pushed"], select_handler=self._handle_menu_select, back_handler=self._handle_menu_back)

  def update(self, delta):
    self.ui_delegate.update(delta)

  def draw(self, ctx):
    self.ui_delegate.draw(ctx)

  def _handle_menu_select(self, item, idx):
    # I think there might be problems here with this
    # being called inside an event handler?
    # but it seems to be working right now. expect
    # breakage...

    print(f"Insert step type: {item}")
    # clean up our downstream delegate
    self.ui_delegate._cleanup()

    if item == "Set LEDs":
      self.ui_delegate = InsertLEDStepUI(self.app)
    elif item == "Pause":
      self.ui_delegate = InsertPauseStepUI(self.app)
    elif item == "Count loops":
      self.ui_delegate = InsertCountLoopsUI(self.app)
    elif item == "When button pushed":
      self.ui_delegate = InsertWhenButtonPushedUI(self.app)
    else:
      assert False, "No UI to create this step type"

  def _handle_menu_back(self):
    # clean up our downstream delegate
    self.ui_delegate._cleanup()

    # and remove ourselves from the app
    self.app.ui_delegate = None
    self.app._mode = EDIT_MODE

class InsertWhenButtonPushedUI:
  def __init__(self, app):
    self.app = app

  def update(self, delta):
    self.app.sequence.insert(self.app.sequence_pos, WhenButtonPushedStep(self.app))
    self.app.sequence_pos += 1

    assert self.app.sequence_pos >= 0
    assert self.app.sequence_pos < len(self.app.sequence)

    # and remove ourselves from the app
    self.app.ui_delegate = None
    self.app._mode = EDIT_MODE


  def draw(self, ctx):
    pass


class InsertCountLoopsUI:
  def __init__(self, app):
    self.app = app

  def update(self, delta):
    self.app.sequence.insert(self.app.sequence_pos, CountLoopsStep())
    self.app.sequence_pos += 1

    assert self.app.sequence_pos >= 0
    assert self.app.sequence_pos < len(self.app.sequence)

    # and remove ourselves from the app
    self.app.ui_delegate = None
    self.app._mode = EDIT_MODE


  def draw(self, ctx):
    pass
