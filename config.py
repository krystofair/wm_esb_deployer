import subprocess
import pathlib
import os
import logging as log
import functools

import errors


@functools.lru_cache(maxsize=1)
def get_config_dir(env: str) -> pathlib.Path:
    """
    Get config directory for environment name (in upper case) and root folder gets from CONFIG_DIR
    environment variable.
    """
    # this log should appear only once, because this is cached by environment name
    # if this appeared more than one and not because upperCase - that is something wrong
    log.info(f"getting config dir for environment: {env}") #FIXME: this log doesnt appear in console
    config_dir = os.environ["CONFIG_DIR"]
    config_path = pathlib.Path(config_dir) / env.upper()
    if not config_path.exists() or not config_path.is_dir():
        raise errors.LoadingConfigurationError("Config directory `%s` doesn't exists"
                                               " or there is some file with that name"
                                               % config_path)
    return config_path


def load_config(env: str, node: str) -> None:
    config = get_config_dir(env) / pathlib.Path(node + '.sh')
    arguments = f"source {config}".split(' ')
    try:
        result = subprocess.run(arguments)  # throws FileNotFoundError for binary to run (source)
        if result.returncode != 0:
            raise FileNotFoundError
    except FileNotFoundError:
        try:
            with open(config, 'r') as cfg:
                for line in filter(None, map(str.strip, cfg.readlines())):
                    key, value = line.split('=')
                    os.environ[key] = value
        except (ValueError, OSError, FileNotFoundError) as e:
            log.exception(e)
            raise errors.LoadingConfigurationError(env, node) from None


def load_configuration(env: str, node: str = '') -> bool:
    """
    Loading configuration as Public API function.
    :param env: environment for which configuration will be searched
    :param node: optional argument for configurate specific node
    :return: True if loaded, False otherwise
    """
    environment = env.upper()
    try:
        load_config(environment, 'init')
        if node:
            load_config(environment, node)
    except errors.LoadingConfigurationError as e:
        log.error(e)
        return False
    return True
