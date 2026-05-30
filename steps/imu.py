import imu

from .base import WhenStep
from ..const import LIVE_SIZE


class WhenIMUUpright(WhenStep):
  def __init__(self):
    super().__init__()
    # when upright, IMU says (approx) (9, 0, 0)
    self.last_state = 0  # 0 = unknown
    self.last_imu_x = 0.0

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

  def render(self, mode, ctx, render_step, y, text_colour):
    text = f"When badge goes upright"
    tw = ctx.text_width(text)
    ctx.move_to(int(-tw/2), y).rgb(*text_colour).text(text)
    ctx.rgb(255,0,0).begin_path()
    ctx.move_to(-240, y - LIVE_SIZE/2)
    ctx.line_to(240, y - LIVE_SIZE/2)
    ctx.stroke()
