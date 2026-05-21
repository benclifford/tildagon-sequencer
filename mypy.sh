cd ~/src/badge-2024-software/sim/apps

source ~/src/badge-2024-software/venv-testing/bin/activate

export PYTHONPATH=/home/benc/src/badge-2024-software/sim/fakes/:/home/benc/src/badge-2024-software/modules

mypy tildagon_sequencer/app.py ../../modules/system/eventbus.py ../fakes/imu.py
