#!/usr/bin/env python3
"""



"""
import json
import logging
import sys

from functools import cached_property

#from ansible.plugins.inventory import BaseInventoryPlugin

from systogony import SystogonyEnvironment

log = logging.getLogger("systogony-inventory")

class InventoryModule:  #(BaseInventoryPlugin):

    NAME = 'dechandler.systogony.inventory'



    def __init__(self):

        self.env = SystogonyEnvironment()

    @cached_property
    def ansible_inventory(self):
        """

        """
        self.env.hostvars['localhost'] = {'ansible_inventory': "local"}
        inventory = {
            '_meta': {'hostvars': self.env.hostvars},
            'all': {'hosts': [host for host in self.env.hostvars]}
        }
        inventory['_meta']['hostvars']['localhost'] = {
            'ansible_inventory': "local"
        }
        inventory.update({
            name: {'hosts': members}
            for name, members in self.env.groups.items()
        })

        return inventory


def configure_loggers():

    datefmt = "%Y-%m-%d_%H:%M:%S"

    log.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)-7s %(message)s', datefmt=datefmt
    ))
    log.addHandler(handler)


if __name__ == "__main__":

    configure_loggers()
    inventory = InventoryModule().ansible_inventory
    print(json.dumps(inventory, indent=4))
