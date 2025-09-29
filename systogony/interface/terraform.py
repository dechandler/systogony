"""



"""
import logging
import os
import re
import sys

from .cli import CliInterface

log = logging.getLogger("systogony")


class TerraformCli(CliInterface):


    def __init__(self, config):

        super().__init__(config)

        self.operations = {
            'plan': {
                'handler': self.plan,
                'help': "Run `terraform plan` in the configured directory"
            },
            'apply': {
                'handler': self.apply,
                'help': "Run `terraform apply` in the configured directory"
            }

        }
        self.no_args_operation = 'help'
        self.no_matching_args_operation = 'run'

    def plan(self, args):

        cmd = ["terraform", "plan"]
        cmd.extend(args)

        self.run_command(cmd, self.config['tf_env_dir'])
