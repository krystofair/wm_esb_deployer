"""
General module to make actions.
'test' - not implemented, should do some tests by means IntegrationServer and catch developers mistakes;
'deploy' - prepare backup and packages in packages/ directory of IS in environment and run 'is_instance update' script;
'backup' - not implemented yet, revert changes by use created backup;
'build' - only prepare packages in 'packages/' directory on IS-es or in inbound if flag is set.
'stop' - not implemented, stop all instance from environment;
'test' - only try run main, so there will be invoke imports, and add some else;
"""
import os
import pathlib
import sys
import argparse
import inspect

from . import (config, errors, sender, settings, build)
from .settings import log


def build_arguments(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument('action',
                        help="possible options for action are: 'test', 'inbound', 'build', 'deploy', 'backup'"
                             ", 'stop'")
    parser.add_argument('--package', nargs='+', action='extend', help="A list of packages to build archives for.")
    parser.add_argument('--changes-only', action='store_false',
                        help="Use this flag if you want to deploy all* packages\n*Without excluded packages {}"
                        .format(settings.PACKAGES_TO_EXCLUDE))
    parser.add_argument('--inbound', action='store_true', help="Use it if you want to load package from inbound.")

    # this below arg should be fetched from environment variable set by runner
    # parser.add_argument('tag_name', 'store_value', help='Tag name or commit from Git repository')

    return parser.parse_args(args)


def action_build(inbound=False, changes_only=True):
    commit_deploy = os.environ[settings.CI_COMMIT_SHA] or "HEAD"
    build.clean_directory_for_new_build()
    if inbound:
        if changes_only:
            packages = build.get_changes_from_git_diff(mock=settings.mock)
        for package in packages:
            if build.build_package_for_inbound(package, commit_deploy):
                log.info("Built {} successfully".format(package))
            else:
                log.error("Built {} failed".format(package))
                break
    elif changes_only:
        build.prepare_package_only_changes_services_from_last_commit(commit_deploy)
        sender.send_to_packages_repo()
    else:
        pass
    if inbound:
        sender.send_to_inbound()


def action_deploy():
    pass




def main():
    # parse arguments
    args = build_arguments()
    # configure
    special_config = config.get_env_var_or_default(settings.NODE_ENV_VAR)
    commit_ref = os.environ[settings.CI_COMMIT_SHA]
    try:
        if special_config:
            log.info("Loading configuration with special config for node.")
            config.load_configuration(os.environ[settings.CI_ENVIRONMENT_NAME], special_config)
        else:
            log.info(f"There was no special config for node."
                     f"Loading only for environment({os.environ[settings.CI_ENVIRONMENT_NAME]}).")
            config.load_configuration(os.environ[settings.CI_ENVIRONMENT_NAME])
    except (KeyError, errors.LoadingConfigurationError) as e:
        log.error(e)
        log.info("Error occured. Ending...")
        exit(-1)
    try:
        # run specified action
        if args.action == "build":
            if args.changes_only:
                pass
            if args.inbound:  # and args.only_changes - not implemented don't know if this is works. D:
                packages = set(p[1] for p in [line.split('/') for line in build.get_changes_from_git_diff()] if p[1])
                for package in packages:
                    build.build_package_for_inbound(package, commit_ref)
        if args.action == "deploy":
            action_build(args.package)
            if not args.inbound:
                action_deploy(args.package, changes=False)
        elif args.action == "test":
            exit(0)
        else:
            log.error("Entered unknown action.")
    except errors.GitOperationError as e:
        log.error(e)
        log.info("Error occured. Ending...")
        exit(-1)


def build_arguments_save_yaml(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--filename")
    parser.add_argument("--configdir")
    return parser.parse_args(args)


def save_config_from_yaml() -> None:
    """
    Function as a scripts (see pyproject.toml),
    that's why it has one own parser for arguments from stdin.
    Save all environments variable defined by settings as useful,
    which has been set in gitlab job.
    :return: None
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("filename")
    args = parser.parse_args(sys.argv[1:])
    filename = args.filename
    env_name = os.environ[settings.CI_ENVIRONMENT_NAME]
    members = [member for member in inspect.getmembers(settings)
               if member[0].endswith('ENV_VAR') and 'CONFIG_DIR' not in member[0]]
    config_dir = config.get_env_var_or_default(settings.CONFIG_DIR_ENV_VAR, default='configs.d')
    path = config_dir / pathlib.Path(env_name)
    os.makedirs(path, exist_ok=True)
    try:
        with open(path / filename, 'x', encoding='utf-8') as cfg:
            for _, key in members:
                try:
                    cfg.write(f"{key} = {os.environ[key]}\n")
                except KeyError:
                    continue
    except FileExistsError:
        log.info("Configuration already exists. You have to manually clean it up and retry if it changed.")


def clean_configuration() -> None:
    """
    Script to clean configuration per environment. This should not be a problem,
    because there will be configuration loaded in yaml files. Otherwise, do not use
    a job with this script in your pipeline.
    """
    environ = os.environ[settings.CI_ENVIRONMENT_NAME]
    config.clear_configuration_for_environment(environ)
