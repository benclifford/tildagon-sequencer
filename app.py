from app import App
from app_components import clear_background, Menu
from system.eventbus import eventbus
from tildagonos import tildagonos
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.patterndisplay.events import PatternDisable, PatternEnable
from system.scheduler.events import RequestForegroundPushEvent
import asyncio
import imu
import math
import random
import sys
import time

PLAY_MODE = 0
EDIT_MODE = 1
MENU_MODE = 2
INSERT_STEP_MODE = 3

LIVE_SIZE = 20
OTHER_SIZE = 20

STEP_PERIOD_MS = 100

class SequencerApp(App):
  def __init__(self):
   try:
    self.sequence = [WhenButtonPushedStep(self),
                     LEDStep(255,255,255),
                     PauseStep(500),
                     LEDStep(0,0,255),
                     PauseStep(500),
                     EndStep(),
                     WhenPlayStep(),
                       LEDStep(255,0,255),
                       PauseStep(500),
                       LEDStep(0,0,0),
                       PauseStep(500),
                       LEDStep(0,255,0),
                       PauseStep(500),
                       RepeatForeverStep(),
                         LEDStep(8,8,8),
                         PauseStep(500),
                         LEDStep(0,0,0),
                         PauseStep(500),
                       EndStep(),
                     EndStep(),
                     WhenIMUUpright(),
                       LEDStep(0,255,0),
                     EndStep(),
                     ]

    self.sequence_pos = -1  # don't run anything

    self._mode = PLAY_MODE
    self._reset_steps()

    # so that two different polling loops can run
    # a poll for step
    self._last_step_time_ms = 0

    self.ui_delegate = None

    self._maximised()
    eventbus.on(RequestForegroundPushEvent, self._handle_foreground_push, self)
   except Exception as e:
    sys.print_exception(e)

  def _reset_steps(self):
    end_stack = []
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
      print("Foreground push for sequencer app - restoring foreground state")
      self._maximised()
    else:
      print("Foreground push for other app - ignoring")

  def _maximised(self):
    eventbus.on(ButtonDownEvent, self._handle_buttondown, self)
    print("Sequencer is disabling pattern in update")
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

__app_export__ = SequencerApp


class InsertStepUI:
  def __init__(self, app):
    self.app = app
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

class InsertPauseStepUI:
  def __init__(self, app):
    self.app = app
    self.ui_delegate = Menu(self.app, ["500ms", "1 second", "5 seconds", "30 seconds"], back_handler=self._handle_menu_back, select_handler=self._handle_menu_select)

  def _handle_menu_back(self):
    # this goes back to edit mode when a more consistent flow would be to
    # go back to the previous screen, which is the step type picker.

    # clean up our downstream delegate
    self.ui_delegate._cleanup()

    # and remove ourselves from the app
    self.app.ui_delegate = None
    self.app._mode = EDIT_MODE

  def update(self, delta):
    self.ui_delegate.update(delta)
 
  def draw(self, ctx):
    self.ui_delegate.draw(ctx) 

  def _handle_menu_select(self, item, idx):
    self.ui_delegate._cleanup()

    if idx == 0:
      ms = 500
    elif idx == 1:
      ms = 1000
    elif idx == 2:
      ms = 5000
    elif idx == 3:
      ms = 30000
    else:
      assert False, "invalid duration menu option"

    self.app.sequence.insert(self.app.sequence_pos, PauseStep(ms))
    self.app.sequence_pos += 1

    assert self.app.sequence_pos >= 0
    assert self.app.sequence_pos < len(self.app.sequence)

    # and remove ourselves from the app
    self.app.ui_delegate = None
    self.app._mode = EDIT_MODE


# TODO: the top STEP UI needs to choose both a colour and a set
# of LEDs. So possibly the colour picker now splits out into its
# own UI component, that sits along side a "choose LEDs" picker
# that initially can be "all" or 1,2,3,4,5,6,7,8,9,10,11,12 or a
# subset picker.

# Initialise to the colour picker
# On colour picker select, initalise the LED picker
# On LED picker select, 

class InsertLEDStepUI:
  def __init__(self, app):
    self.app = app
    self.rgb = (0,0,0)
    self.ui_delegate = ColourPicker(app, callback=self.handle_colour_chosen)

  def update(self, delta):
    self.ui_delegate.update(delta)
 
  def draw(self, ctx):
    self.ui_delegate.draw(ctx) 

  def handle_colour_chosen(self, rgb):
    self.ui_delegate._cleanup()
    self.rgb = rgb

    # TODO: move to next state. which until I do LED picking, is
    # to create a step and finish.

    r = self.rgb[0]
    g = self.rgb[1]
    b = self.rgb[2]
    self.app.sequence.insert(self.app.sequence_pos, LEDStep(r, g, b))
    self.app.sequence_pos += 1

    assert self.app.sequence_pos >= 0
    assert self.app.sequence_pos < len(self.app.sequence)

    # TODO: i think this should move into a completed callback on the
    # main app: the modification of app state is a clue.
    self.app._mode = EDIT_MODE
    self.app.ui_delegate = None


class ColourPicker:

  def __init__(self, app, callback):
    self.app = app
    self.chosen_colour = 0
    self.rgb = (0,0,0)
    self._callback = callback
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

  def _cleanup(self):
    eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)

  def _handle_buttondown(self, event):
    if BUTTON_TYPES["UP"] in event.button:
      self.chosen_colour = (self.chosen_colour + 1) % 4
    elif BUTTON_TYPES["DOWN"] in event.button:
      self.chosen_colour = (self.chosen_colour + 1) % 4
    elif BUTTON_TYPES["CONFIRM"] in event.button:
      eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)
      self._callback(self.rgb)

      assert self.app.sequence_pos >= 0
      assert self.app.sequence_pos < len(self.app.sequence)
    else:
      print("unhandled button event in ColourPicker - ignoring")


class Step:
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
class BlockStep(Step): ...


class LEDStep(Step):
  def __init__(self, r, g, b):
    self.rgb = (r, g, b)
    self.leds = list(range(0,12)) # all LEDs

  def enter_step(self):

    colour = self.rgb
    for n in self.leds:
      tildagonos.leds[n+1] = colour
    tildagonos.leds.write()

  def render(self, mode, ctx, render_step, y, text_colour):
    text = f"{render_step}: LEDs "
    tw = ctx.text_width(text)
    tw2 = ctx.text_width("this")
    w = tw + tw2
    ctx.move_to(int(-w/2), y).rgb(*text_colour).text(text)
    ctx.move_to(int(-w/2 + tw), y).rgb(*self.rgb).text("this")


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

    text = f"{render_step}: Pause {duration}ms"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)

  def reset(self):
    self.entered_time = None


class CountLoopsStep(Step):
  def __init__(self):
    self.reset()

  def enter_step(self):
    self.count += 1

  def render(self, mode, ctx, render_step, y, text_colour):
    text = f"{render_step}: Counted {self.count} times"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)

  def reset(self):
    self.count = 0

class WhenButtonPushedStep(BlockStep):

  def __init__(self, app):
    self.app = app

    self.pressed = False
    eventbus.on(ButtonDownEvent, self._handle_buttondown, self.app)

  def _handle_buttondown(self, event):
    # match any button except CANCEL
    if self.app._mode == PLAY_MODE and BUTTON_TYPES["CANCEL"] not in event.button:
      self.pressed = True

  def poll_for_when(self):
    if self.pressed:
      self.pressed = False
      return True
    else:
      return False

  # This is to stop execution if we flow onto this step.
  # This isn't the long term structure of how I want things
  # to be, but it will maybe do for now, until I maybe get
  # some more hierarchical editing implemented.
  def progress_step(self):
    return False

  def render(self, mode, ctx, render_step, y, text_colour):
    text = f"When button pushed"   # : {self.pressed}"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)
    ctx.rgb(255,0,0).begin_path()
    ctx.move_to(-240, y - LIVE_SIZE/2)
    ctx.line_to(240, y - LIVE_SIZE/2)
    ctx.stroke()

  def progress_end_step(self):
    return False


class WhenIMUUpright(BlockStep):
  def __init__(self):
    # when upright, IMU says (approx) (9, 0, 0)
    self.last_state = 0  # 0 = unknown
    self.last_imu_x = 0

  def poll_for_when(self):
    next_imu_acc = imu.acc_read()
    imu_x = next_imu_acc[0]
    self.last_imu_x = imu_x
    if imu_x < 4:
      next_state = -1
    elif imu_x > 9:
      next_state = +1
    else:
      next_state = self.last_state
      # in the middle hysteresis range, don't change state

    if self.last_state == -1 and next_state == 1:
      r = True
    else:
      r = False

    self.last_state = next_state

    return r

  def progress_step(self):
    return False

  def progress_end_step(self):
    return False

  def render(self, mode, ctx, render_step, y, text_colour):
    text = f"When badge goes upright"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)
    ctx.rgb(255,0,0).begin_path()
    ctx.move_to(-240, y - LIVE_SIZE/2)
    ctx.line_to(240, y - LIVE_SIZE/2)
    ctx.stroke()


class WhenPlayStep(BlockStep):

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

class EndStep(Step):
  def __init__(self):
    self._start_step = None
    # this should be set dynamically at start of execution to the
    # executor-detected start step.

  def progress_step(self):
    assert isinstance(self._start_step, BlockStep), f"start step should be a BlockStep: {self._start_step}"
    return self._start_step.progress_end_step()

  def render(self, mode, ctx, render_step, y, text_colour):
    text = "End block"
    tw = ctx.text_width(text)

    # TODO: This line doesn't work nicely when the end block is for an
    # inner block, not an outer-when. What should happen here is part of
    # the bigger question about how to represent nested blocks.
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)
    ctx.rgb(255,0,0).begin_path()
    ctx.move_to(-240, y + LIVE_SIZE/2)
    ctx.line_to(240, y + LIVE_SIZE/2)
    ctx.stroke()

class RepeatForeverStep(BlockStep):
  def progress_end_step(self):
    # continue from the step we were at before
    return self._step_number + 1

  def render(self, mode, ctx, render_step, y, text_colour):
    text = "Repeat forever"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)
