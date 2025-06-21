#!/usr/bin/env python3
# spin_wheel_mode.py  –  MX-106T/R • Protocol 1.0 • 57 600 бод

import time, signal, sys
from dynamixel_sdk import PortHandler, PacketHandler
import logging
import pytest

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Starting test_dynamixel.py")

DEV      = "/dev/ttyUSB0"
BAUD     = 57600
PROTO    = 1.0
DXL_IDS  = [2, 7, 8, 9]

ADDR_CW_LIMIT   = 6    
ADDR_CCW_LIMIT  = 8
ADDR_TORQUE     = 24
ADDR_SPEED      = 32

SPD_FWD = 300
SPD_REV = 1024 + 30
PAUSE   = 2.0

port  = PortHandler(DEV)
pkt   = PacketHandler(PROTO)
if not (port.openPort() and port.setBaudRate(BAUD)):
    logger.error("Failed to open port")
    sys.exit("❌ Не могу открыть порт")

def write2bytes(id_, addr, val):
    pkt.write2ByteTxRx(port, id_, addr, val)

def write1bytes(id_, addr, val):
    pkt.write1ByteTxRx(port, id_, addr, val)

def clean_exit(sig, frame):
    for i in DXL_IDS:
        write1bytes(i, ADDR_TORQUE, 0)
    port.closePort()
    print("\nTorque OFF, порт закрыт")
    sys.exit(0)
signal.signal(signal.SIGINT, clean_exit)

for i in DXL_IDS:
    try:
        write1bytes(i, ADDR_TORQUE, 0)
        write2bytes(i, ADDR_CW_LIMIT,  0)
        write2bytes(i, ADDR_CCW_LIMIT, 0)
        write1bytes(i, ADDR_TORQUE, 1)
    except Exception as e:
        logger.error(f"Error setting up dynamixel {i}: {e}")
        sys.exit(1)

logger.info("▶  Wheel-mode активен, начинаю вращение…")

logger.info("▶  Forward rotation")
for i in DXL_IDS:
    try:
        write2bytes(i, ADDR_SPEED, SPD_FWD)
    except Exception as e:
        logger.error(f"Error setting speed for dynamixel {i}: {e}")
        sys.exit(1)
time.sleep(PAUSE)

logger.info("▶  Reverse rotation")
for i in DXL_IDS:
    try:
        write2bytes(i, ADDR_SPEED, SPD_REV)
    except Exception as e:
        logger.error(f"Error setting speed for dynamixel {i}: {e}")
        sys.exit(1)
time.sleep(PAUSE)
