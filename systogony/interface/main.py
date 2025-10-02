"""


"""
import json
import logging
import os
import sys


from .cli import CliInterface

from .print import PrintCli
from .ansible import AnsibleCli
from .terraform import TerraformCli


log = logging.getLogger("systogony")


class MainCli(CliInterface):
    """
    In the main run of systogony, config is a custom class that
    gives a quasai-dict interface, but a normal dict can be passed
    in here. Necessary keys depends on the chosen operation.

    """

    def __init__(self, config):

        super().__init__(config)

        self.operations = {
            'print': {
                'aliases': ['list', 'ls', '--list', '-l'],
                'handler': lambda: PrintCli(self.config).handle_args
            },
            'ansible': {
                'aliases': ['a', 'ans', 'abl'],
                'handler': lambda: AnsibleCli(self.config).handle_args
            },
            'terraform': {
                'aliases': ['tf'],
                'handler': lambda: TerraformCli(self.config).handle_args
            }

        }
        self.no_args_operation = 'print'
        self.no_matching_args_operation = 'ansible'
