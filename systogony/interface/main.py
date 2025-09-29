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

    def __init__(self, config):

        log.info(
            f"Starting Systogony; PID: {os.getpid()}; Args: {sys.argv[1:]}"
        )
        log.debug(f"Run config: {json.dumps(dict(config.items()))}")

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
