"""


"""
import json
import logging
import os
import socket
import sys


from .cli import CliInterface

from ..environment import SystogonyEnvironment


log = logging.getLogger("systogony")


class PrintCli(CliInterface):

    def __init__(self, config):

        log.debug("Initializing PrintCli")

        self.config = config

        self.operations = {
            'ansible': {
                'aliases': [
                    'a', 'ans', 'abl',
                    '-l', '--list',
                    'inv', 'inventory'
                ],
                'handler': self.ansible_inventory
            }

        }
        self.no_args_operation = 'ansible'
        self.no_matching_args_operation = 'help'

    def ansible_inventory(self, args):
        """

        """
        env = SystogonyEnvironment(self.config)

        env.hostvars['localhost'] = {'ansible_connection': "local"}
        inventory = {
            '_meta': {'hostvars': env.hostvars},
            'all': {'hosts': [host for host in env.hostvars]}
        }
        inventory['_meta']['hostvars']['localhost'] = {
            'ansible_connection': "local"
        }
        local_hostname = socket.gethostname().split('.')[0]
        log.debug(f"Local hostname: {local_hostname}")
        if local_hostname in env.hostvars:
            env.hostvars[local_hostname]['ansible_connection'] = "local"

        inventory['all']['vars'] = env.blueprint['vars'] or {}
        inventory.update({
            name: {'hosts': members}
            for name, members in env.groups.items()
        })

        print(json.dumps(inventory, indent=4))
