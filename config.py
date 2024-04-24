import subprocess
import pathlib
import os
import logging
import functools

import errors
import settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@functools.lru_cache(maxsize=1)
def get_config_dir(env: str) -> pathlib.Path:
    """
    Get config directory for environment name (in upper case) and root folder gets from CONFIG_DIR
    environment variable.
    """
    # this log should appear only once, because this is cached by environment name
    # if this appeared more than one and not because upperCase - that is something wrong
    log.info(f"getting config dir for environment: {env}")
    config_dir = os.environ[settings.CONFIG_DIR_ENV_VAR]
    config_path = pathlib.Path(config_dir) / env.upper()
    if not config_path.exists() or not config_path.is_dir():
        raise errors.LoadingConfigurationError("Config directory `%s` doesn't exists"
                                               " or there is some file with that name"
                                               % config_path)
    return config_path


def load_config(env: str, node: str) -> None:
    try:
        config = get_config_dir(env) / pathlib.Path(node + '.cfg')
        with open(config, 'r') as cfg:
            lines = filter(None, map(str.strip, cfg.readlines()))
            lines = filter(lambda x: not x.startswith('#'), lines)
            for line in lines:
                key, value = line.split('=')
                os.environ[key.strip()] = value.strip()
    except (ValueError, OSError, FileNotFoundError, KeyError) as e:
        log.exception(e)
        raise errors.LoadingConfigurationError(env, node)


def load_configuration(env: str, node: str = '') -> bool:
    """
    Loading configuration as Public API function.
    :param env: environment for which configuration will be searched
    :param node: optional argument for configurate specific node
    :return: True if loaded, False otherwise
    """
    try:
        load_config(env, 'init')
        if node:
            load_config(env, node)
    except errors.LoadingConfigurationError as e:
        log.error(e)
        return False
    return True
