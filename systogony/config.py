
import datetime
import json
import logging
import os

import yaml

from .exceptions import NoSuchEnvironmentError, BlueprintLoaderError

log = logging.getLogger("systogony")


class SystogonyConfig:

    def __init__(self):

        self._pre_log = []
        self.log = self.pre_log

        self.log('debug', "Real start of run - SystogonyConfig.__init__")

        self.path, config_file_data = self._get_config_file_data()
        self.config_dir = os.path.dirname(self.path)

        self.config = self._get_defaults()
        self.config.update(config_file_data)

        self._expand_paths()
        if self.config['default_env']:
            self._apply_default_env()

        self.config['service_defaults'] = self._get_service_defaults()


    def configure_loggers(self):

        os.makedirs(self.config['log_dir'], exist_ok=True)

        datefmt = "%Y-%m-%d_%H:%M:%S"
        log.setLevel(getattr(logging, self.config['log_level'].upper()))

        handler = logging.FileHandler(
            os.path.join(self.config['log_dir'], "systogony.log")
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s (%(process)d) %(levelname)-7s: %(message)s', datefmt=datefmt
        ))
        log.addHandler(handler)

        self.log = self.full_log


    def pre_log(self, level, message):
        """
        Since this object is created and begins generating logs
        before logging is configured, stash log messages for
        later replay into the correct log

        """
        # Prepend timestamp to message, since this will be replayed later
        message = f"{datetime.datetime.now().strftime("%H:%M:%S")} {message}"

        self._pre_log.append((level, message))

    def full_log(self, level, message):
        """
        This is a passthrough method to fit the pre_log interface
        but write directly to the log, so that the log interface
        can be consistent in this class

        """
        log.log(logging.__dict__[level.upper()], message)

    def flush_pre_log(self):

        # Refuse to flush if log has not been configured
        if self.log is self.pre_log:
            return

        # Empty self._pre_log into the updated log method
        for level, message in self._pre_log:
            self.log(level, message)
        self._pre_log = []


    def __getitem__(self, key):
        return self.config[key]

    def get(self, key, default):
        return self.config.get(key, default)


    def items(self):
        return self.config.items()

    def keys(self):
        return self.config.keys()

    def values(self):
        return self.config.values()


    def __setitem__(self, key, value):
        self.config[key] = value

    def update(self, update_data):
        self.config.update(update_data)


    def _get_config_file_data(self):
        """
        The priority order is:
            Environment variable: SYSTOGONY_CONFIG (~ accepted)
            $HOME/.config/systogony/config.yaml

        """
        search_paths = [
            os.environ.get("SYSTOGONY_CONFIG", ""),
            "~/.config/systogony/config.yaml"
        ]
        for path_var in search_paths:
            path = os.path.expanduser(path_var)
            try:
                with open(path) as fh:
                    config_file_data = yaml.safe_load(fh)
                    self.log('info', f"Config Path: {path}")
                self.path = path
                break
            except FileNotFoundError:
                pass
            except yaml.scanner.ScannerError:
                self.log('error', f"File exists at {path} but is not YAML parseable, aborting...")
                sys.exit(1)
            except Exception as e:
                self.log('debug', ' '.join([
                    "Unexpected exception while loading",
                    f"yaml at {path}: ({e.__class__}) {e}"
                ]))
        else:
            config_file_data = {}
            self.path = path

        return path, config_file_data

    def _get_defaults(self):

        return {
            'environments': {},
            'default_env': None,
            'env_name': "default",
            'blueprint_path': os.path.join(self.config_dir, "blueprint"),
            'use_cache': False,

            'tf_env_dir': os.path.join(self.config_dir, "terraform"),

            'ansible_dir': os.path.abspath(
                os.path.join(os.path.dirname(__file__), "../ansible")
            ),
            'ask_become_pass': True,
            'ask_vault_pass': False,

            'log_dir': os.path.join(self.config_dir, "log"),
            'log_level': "warning",

        }

    def _expand_paths(self):

        def resolve_path(path, default_dir):

            # Resolve ~ to home dir
            path = os.path.expanduser(path)

            # Assume path is relative to default_dir if not abolute
            if not os.path.isabs(path):
                path = os.path.join(self.config_dir, path)

            return path

        path_opts = [
            'blueprint_path', 'tf_env_dir', 'ansible_dir', 'log_dir'
        ]
        for opt in path_opts:
            self.config[opt] = resolve_path(self.config[opt], self.config_dir)
        for name, env in self.config['environments'].items():
            for key, value in env.items():
                if key in path_opts:
                    env[key] = resolve_path(value, self.config_dir)
            env['env_name'] = name

    def _apply_default_env(self):

        default_env = self.config['default_env']
        if default_env not in self.config['environments']:
            raise NoSuchEnvironmentError(
                f"default_env defined ({default_env}) "
                + "but no matching name under environments"
            )
        self.config.update(self.config['environments'][default_env])

    def _get_service_defaults(self):
        """
        Since services can reference other services to inherit from,
        there is no way to know which order to load the files,
        so we're looping over it a few times until they've
        all resolved.

        """
        raw_defaults = {}
        defaults = {}
        resolved = []

        defaults_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "services.d"
        )
        self.log('info', f"Svc defaults directory: {defaults_dir}")
        for root, dirs, files in os.walk(defaults_dir):
            for f in files:
                svc_name, extension = os.path.splitext(f)
                if extension != ".yaml":
                    continue
                path = os.path.join(root, f)

                try:
                    with open(path) as fh:
                        svc_vars = yaml.safe_load(fh)
                    self.log('debug', f"Loaded svc defaults: {path}")

                except yaml.scanner.ScannerError:
                    self.log('warning', f"File with .yaml extension at {path} is not YAML parseable, aborting...")
                    continue
                except Exception as e:
                    self.log('debug', ' '.join([
                        "Unexpected exception while loading",
                        f"yaml at {path}: ({e.__class__}) {e}"
                    ]))

                # If a parent service isn't specified, mark as fully loaded
                if svc_vars.get('service') in [svc_name, None]:
                    svc_vars['service'] = svc_name
                    defaults[svc_name] = svc_vars
                    resolved.append(svc_name)
                raw_defaults[svc_name] = svc_vars

        self.log('debug', f"Resolved service defaults: {resolved}")

        # Resolve services iteratively until complete or unchanged
        prev_resolved_len = -1
        while (
            len(resolved) < len(raw_defaults)
            and len(resolved) != prev_resolved_len
        ):
            prev_resolved_len = len(defaults)

            for svc_name, svc_vars in defaults.items():
                if svc_name in defaults:
                    continue

                # Load defaults from parent service
                parent_svc_name = svc_vars['service']
                try:
                    parent_vars = {**defaults[parent_svc_name]}
                except KeyError:
                    raise MissingServiceError(f"Missing from service.d: {parent_service} ({svc_name}.yaml)")

                # Update service vars with parent defaults
                del svc_vars['service']
                parent_vars.update(svc_vars)
                defaults[svc_name] = parent_vars

                # Mark complete if resolved
                if parent_vars['service'] == parent_svc_name:
                    resolved.append(parent_svc_name)

        if len(resolved) < len(raw_defaults):
            self.log('warning', f"Unresolved services: {set(defaults) - set(resolved)}")

        return defaults
