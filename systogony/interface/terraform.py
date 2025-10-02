"""



"""
import logging
import os
import re
import sys

from jinja2 import Template

from .cli import CliInterface

log = logging.getLogger("systogony")


class TerraformCli(CliInterface):


    def __init__(self, config):
        """
        In the main run of systogony, config is a custom class that
        gives a quasai-dict interface, but a normal dict can be passed
        in here. The following keys are needed:
        - tf_env_dir (str)
        - environments (dict of dicts)
        - default_env (str)

        """
        super().__init__(config)


        self.operations = {
            'generate': {
                'handler': self.generate,
                'help': "Generate terraform environment"
            },
            'init': {
                'handler': self.init,
                'help': "Run `terraform init` in the tfenv directory"
            },
            'plan': {
                'handler': self.plan,
                'help': "Run `terraform plan` in the tfenv directory"
            },
            'apply': {
                'handler': self.apply,
                'help': "Run `terraform apply` in the tfenv directory"
            },
            'destroy': {
                'handler': self.destroy,
                'help': "Run `terraform destroy` in the tfenv directory"
            }

        }
        self.no_args_operation = 'help'
        self.no_matching_args_operation = 'run'

    def _generic_tf_operation(self, operation, args):

        cmd = ["terraform", operation]
        cmd.extend(args)

        self.run_command(cmd, self.config['tf_env_dir'])


    def generate(self, args):

        os.makedirs(self.config['tf_env_dir'], exist_ok=True)

        env = SystogonyEnvironment(self.config)
        template_env = (
            env.blueprint['vars'].get('template_env')
            or self.config['env_name']
        )
        tf_env_template_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            "../../terraform/templates",
            template_env
        ))

        try:
            tmpl_files = os.listdir(tf_env_template_dir)
        except FileNotFoundError:
            NoSuchEnvironmentError(
                f"No terraform env template at {tf_env_template_dir}"
            )

        tmpl_vars = {}
        tmpl_vars.update(self.config)
        #tmpl_vars.update()

        for fname in tmpl_files:
            if os.path.splitext(fname)[1] not in [".tf", ".tfvars"]:
                continue
            src_path = os.path.join(tf_env_template_dir, fname)
            dest_path = os.path.join(self.config['tf_env_dir'], fname)
            with open(src_path) as fh:
                tmpl = Template(fh)



            out = tmpl.render()



    def init(self, args):
        self._generic_tf_operation("init", args)

        
    def plan(self, args):
        self._generic_tf_operation("plan", args)


    def apply(self, args):
        self._generic_tf_operation("apply", args)

        
    def destroy(self, args):
        self._generic_tf_operation("destroy", args)
