#!/usr/bin/env python3
"""



"""
import json
import logging
import os
import sys

from functools import cached_property

#from ansible.plugins.inventory import BaseInventoryPlugin

from systogony import SystogonyAnsibleInventory

log = logging.getLogger("systogony")


def configure_loggers(log_level):

    datefmt = "%Y-%m-%d_%H:%M:%S"

    log.setLevel(log_level)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)-7s %(message)s', datefmt=datefmt
    ))
    log.addHandler(handler)


if __name__ == "__main__":

    blueprint = os.environ.get('SYSTOGONY_BP_SUBDIR', "blueprints")
    log_level = logging.WARN


    configure_loggers(log_level)
    print(SystogonyAnsibleInventory(subdir=blueprint))
