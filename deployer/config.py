import pathlib
import os
import functools

from . import errors, settings
from .settings import log


def get_env_var_or_default(name, default=None):
    try:
        return os.environ[name]
    except KeyError:
        return default


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
    config_path = pathlib.Path(config_dir) / env
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


def load_configuration(env: str) -> bool:
    """
    Loading configuration of environment as Public API function.
    :param env: environment for which configuration will be searched
    :return: True if loaded, False otherwise
    """
    try:
        load_config(env, 'init')
    except errors.LoadingConfigurationError as e:
        log.error(e)
        return False
    return True


def load_node_configuration(env: str, node: str) -> bool:
    try:
        if node:
            load_config(env, node)
    except errors.LoadingConfigurationError as e:
        log.error(e)
        return False
    return True


def clear_configuration_for_environment(env: str) -> bool:
    """
    Delete whole folder of environment from $CONFIG_DIR.
    :param env: environment name defined in Gitlab JOB.
    :return: None
    """
    try:
        config_dir = get_env_var_or_default(settings.CONFIG_DIR_ENV_VAR, default='configs.d')
        os.remove(pathlib.Path(config_dir) / env)
    except Exception as e:
        log.error(e)
        return False
    return True


def find_node_configs(env: str) -> list:
    cfg_dir = get_config_dir(env)
    nodes_config_list = [entry.name for entry in os.scandir(cfg_dir)
                         if entry.name.endswith('.cfg') and entry.name != "init.cfg"]
    return nodes_config_list


def get_build_dir(ref) -> str:
    """Create if not exists and return name of build dir. Used setting about where all build dir are."""
    ci_project_dir = get_env_var_or_default("CI_PROJECT_DIR", default=".")
    builds_dir = get_env_var_or_default(settings.BUILD_DIR_ENV_VAR, default=ci_project_dir)
    build_dir = "{}/build_{}".format(builds_dir, ref)
    os.makedirs(builds_dir, exist_ok=True)
    return build_dir
