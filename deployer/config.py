"""
Module for manipulation of configuration settings like from some properties build concrete path
for, for example config directory or build directory.
"""
import pathlib
import os
import functools
import shutil
import inspect

from . import errors, settings
from .settings import log


def get_env_var_or_default(name, default=None):
    """
    Get variable from shell environment or if not exists return default value.
    This if for variables whom are not required, and should not raise exception KeyError.
    """
    try:
        return os.environ[name]
    except KeyError:
        return default


@functools.lru_cache(maxsize=1)
def get_config_dir(env: str) -> pathlib.Path:
    """
    Get config directory for environment name and root folder gets from CONFIG_DIR
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
    """
    Load key=values from config to shell environment, so it will be accessible to others.
    Treat line started with '#' as comment line.
    :param env: configuration will be search in config_dir for that environment.
    :param node: name of file (node + ".cfg") to search config or "init.cfg" for general.
    :return: None, throws exception `errors.LoadingConfigurationError` if something goes wrong.
    """
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
    :param env: environment for which configuration will be searched.
    :return: True if loaded, False otherwise.
    """
    try:
        load_config(env, 'init')
    except errors.LoadingConfigurationError as e:
        log.error(e)
        return False
    return True


def load_node_configuration(env: str, node: str) -> bool:
    """
    Loading configuration of environment as Public API function.
    :param env: environment for which configuration will be searched
    :return: True if there is no problem, False otherwise.
    """
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
    :return: True if clearing goes well, False otherwise.
    """
    try:
        config_dir = get_env_var_or_default(settings.CONFIG_DIR_ENV_VAR, default='configs.d')
        shutil.rmtree(pathlib.Path(config_dir) / env)
    except Exception as e:
        log.error(e)
        return False
    return True


def find_node_configs(env: str) -> list:
    """
    Search configuration files for nodes, that is get all '.cfg' but not 'init.cfg'.
    :param env: in which environment to search.
    :return: list of file names.
    """
    cfg_dir = get_config_dir(env)
    nodes_config_list = [entry.name for entry in os.scandir(cfg_dir)
                         if entry.name.endswith('.cfg') and entry.name != "init.cfg"]
    return nodes_config_list


def get_build_dir(ref) -> str:
    """Create if not exists and return name of build dir. Used setting about where all build dir are."""
    ci_project_dir = get_env_var_or_default("CI_PROJECT_DIR", default=".")
    builds_dir = get_env_var_or_default(settings.BUILD_DIR_ENV_VAR, default=ci_project_dir)
    build_dir = "{}/build_{}".format(builds_dir, ref)
    os.makedirs(build_dir, exist_ok=True)  # raise FileExistsError
    return build_dir


def get_source_dir() -> pathlib.Path:
    repository = get_env_var_or_default(settings.REPO_DIR_ENV_VAR, default='.')
    sources_dir_name = settings.SRC_DIR
    return pathlib.Path(repository) / sources_dir_name


def get_list_env_var_from_settings() -> list:
    """
    Listing members of environment variables,
    whose names are in settings like *_ENV_VAR.
    :return: list of (name, value) tuple of variables.
    """
    return [member for member in inspect.getmembers(settings) if member[0].endswith('_ENV_VAR')]
