# Sequencer

![Screenshot of sequencer UI](imgs/screenshot.jpg)

## Install

```
mpremote fs mkdir /apps/sequencer
mpremote fs cp app.py :/apps/sequencer/
```

## The default program

The default program will trigger a sequence of LED flashes. Then it will
wait for:

* any button (except CANCEL) to be pressed and do some more flashing every time
  that happens.

* the badge to be turned upright (from e.g. flat on a table) and turn the
  LEDs green


## Play mode

When you first load the app, it will load a default program and start
playing.

Play mode is indicated by a green ring around the edge of the screen.

Press CANCEL (top left) button to stop the program and go into edit mode.

## Edit mode

Edit mode is indicated by a blue ring around the edge of the screen.

CANCEL will exit the app.

UP/DOWN will scroll through the default program.

CONFIRM will bring up a menu of things you can do, either to the current
step or to the program as a whole.

You can:

* delete steps
* add steps
* play the program

## Step creators

When you add a step, you will get an editor specific to the kind of step.
Some steps need no editor, but:

The colour picker: scroll UP and DOWN to choose from a very limited palette:
red, green, blue, off/black. choose CONFIRM to select that colour.

The delay picker: use the menu to pick one of several preconfigured delays.
