import logging
import time

from enum import IntEnum

import mido

logging.basicConfig(level='INFO')

class Button(IntEnum):
  BANK_LEFT = 25
  BANK_RIGHT = 26
  SOLO = 27

CURRENT_CHANNEL = 0
LIGHTS = {k: 0 for k in list(range(1, 23)) + [Button.BANK_LEFT, Button.BANK_RIGHT]}

def _send(message, port):
  logging.debug(f"{message} to {port}")
  port.send(message)


def running_lights(port):
  while True:
    for b in range(1, 27):
      _send(mido.Message('note_on', velocity=1, note=b), port)
      time.sleep(0.1)
      _send(mido.Message('note_on', velocity=0, note=b), port)


def ensure_lights(port):
  global CURRENT_CHANNEL
  global LIGHTS
  logging.info(f"ensuring lights")
  match CURRENT_CHANNEL:
    case 0:
      LIGHTS[Button.BANK_LEFT] = 0
      LIGHTS[Button.BANK_RIGHT] = 0
    case 1:
      LIGHTS[Button.BANK_LEFT] = 1
      LIGHTS[Button.BANK_RIGHT] = 0
    case 2:
      LIGHTS[Button.BANK_LEFT] = 0
      LIGHTS[Button.BANK_RIGHT] = 1
    case 3:
      LIGHTS[Button.BANK_LEFT] = 1
      LIGHTS[Button.BANK_RIGHT] = 1
    case _:
      logging.error(f"CURRENT_CHANNEL is {CURRENT_CHANNEL}, setting to 0")
      CURRENT_CHANNEL = 0
      ensure_lights(port)

  for l, v in LIGHTS.items():
    _send(mido.Message('note_on', velocity=v, note=l), port)
  

def main(midimix, outport):
  logging.info(outport.name)
  global CURRENT_CHANNEL
  pre_solo_channel = 0
  ensure_lights(midimix)
  while True:
    message = midimix.receive()
    if 'note_' in message.type:
      if message.type == 'note_on':
        match message.note:
          case Button.BANK_LEFT:
            CURRENT_CHANNEL = (CURRENT_CHANNEL - 1) % 4
            logging.info(f"CURRENT_CHANNEL set to {CURRENT_CHANNEL}")
          case Button.BANK_RIGHT:
            CURRENT_CHANNEL = (CURRENT_CHANNEL + 1) % 4
            logging.info(f"CURRENT_CHANNEL set to {CURRENT_CHANNEL}")
          case Button.SOLO:
            pre_solo_channel = CURRENT_CHANNEL
            CURRENT_CHANNEL = 0
            logging.info(f"SOLO is down, forcing channel 0")
      elif message.type == 'note_off':
        match message.note:
          case Button.SOLO:
            CURRENT_CHANNEL = pre_solo_channel
            logging.info(f"SOLO is up, restoring channel to {pre_solo_channel}")
      ensure_lights(midimix)
    message.channel = CURRENT_CHANNEL
    _send(message, outport)


if __name__ == "__main__":
  midimix = next(filter(lambda x: 'MIDI Mix' in x, mido.get_input_names()), None)

  if not midimix:
    logging.critical("Can't find MIDI Mix device")
  
  main(
    mido.open_ioport(midimix),
    mido.open_output('midimixextender', virtual=True)
  )
