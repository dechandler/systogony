
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

def main():

    config = SystogonyConfig()
    config.configure_loggers()

    log.info("Starting Systogony")
    log.debug(f"  PID: {os.getpid()}")
    log.debug(f"  Args: {sys.argv[1:]}")
    #log.debug(f"  Config: {json.dumps(config.config)}")

    config.flush_pre_log()


    try:
        MainCli(config).handle_args(sys.argv[1:])

    except BlueprintLoaderError:
        log.error("Exiting due to BlueprintLoaderError")
    except MissingServiceError:
        pass
    except NoSuchEnvironmentError:
        pass

    except KeyboardInterrupt:
        pass
