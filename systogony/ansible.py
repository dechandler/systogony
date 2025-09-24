#!/usr/bin/env python3
"""



"""
import json
import logging
import os
import socket
import sys

from functools import cached_property

from .environment import SystogonyEnvironment

log = logging.getLogger("systogony")


class SystogonyAnsibleInventory:  #(BaseInventoryPlugin):

    NAME = 'dechandler.systogony.inventory'



    def __init__(self, subdir):

        self.env = SystogonyEnvironment(subdir)

    def __str__(self):

        log.debug(str(self.ansible_inventory))
        return json.dumps(self.ansible_inventory, indent=4)

    @cached_property
    def ansible_inventory(self):
        """

        """
        self.env.hostvars['localhost'] = {'ansible_connection': "local"}
        inventory = {
            '_meta': {'hostvars': self.env.hostvars},
            'all': {'hosts': [host for host in self.env.hostvars]}
        }
        inventory['_meta']['hostvars']['localhost'] = {
            'ansible_connection': "local"
        }
        local_hostname = socket.gethostname().split('.')[0]
        log.debug(f"Local hostname: {local_hostname}")
        if local_hostname in self.env.hostvars:
            self.env.hostvars[local_hostname]['ansible_connection'] = "local"

        inventory['all']['vars'] = self.env.blueprint['vars']
        inventory.update({
            name: {'hosts': members}
            for name, members in self.env.groups.items()
        })

        return inventory
