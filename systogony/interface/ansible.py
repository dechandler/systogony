"""



"""
import logging
import os
import re
import sys

from .cli import CliInterface

log = logging.getLogger("systogony")


class AnsibleCli(CliInterface):


    def __init__(self, config):

        super().__init__(config)

        self.operations = {
            'ansible-playbook': {
                'aliases': ['run'],
                'handler': self.run_playbook,
                'help': "Run ansible-playbook with the configured context"
            }

        }
        self.no_args_operation = 'help'
        self.no_matching_args_operation = 'run'

    def run_playbook(self, args):

        cmd = [
            "ansible-playbook", "-i", os.path.abspath(sys.argv[0])
        ]

        if self.config['ask_become_pass']:
            cmd.append('-K')

        if self.config['ask_vault_pass']:
            cmd.append('--ask-vault-pass')

        cmd.extend(args)

        self.run_command(cmd, self.config['ansible_dir'])
