
import json
import logging
import os
import sys

from .config import SystogonyConfig
from .interface import MainCli


from .exceptions import (
    BlueprintLoaderError, MissingServiceError, NoSuchEnvironmentError
)

log = logging.getLogger("systogony")


def _main():

    config = SystogonyConfig()
    config.configure_loggers()

    log.info("Starting Systogony")
    log.debug(f"  PID: {os.getpid()}")
    log.debug(f"  Args: {sys.argv[1:]}")

    config.flush_pre_log()

    MainCli(config).handle_args(sys.argv[1:])


def main():

    try:
        _main()
    except BlueprintLoaderError:
        log.error("Exiting due to BlueprintLoaderError")
    except MissingServiceError:
        pass
    except NoSuchEnvironmentError:
        pass

    except KeyboardInterrupt:
        pass
