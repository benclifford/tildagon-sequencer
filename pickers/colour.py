from system.eventbus import eventbus


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

