"""
General module to make actions.
'test' - do nothing, should do some tests by means IntegrationServer and catch developers mistakes;
'deploy' - prepare backup and packages in packages/ directory of IS in environment and run 'is_instance update' script;
'backup' - not implemented yet, revert changes by use created backup;
'build' - only prepare packages in 'packages/' directory on IS-es or in inbound if flag is set.
'stop' - not implemented, stop all instance from environment;
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
    parser.add_argument('--no-changes-only', action='store_false',
                        help="Use this flag if you want to deploy all* packages\n*Without excluded packages {}"
                        .format(settings.PACKAGES_TO_EXCLUDE))
    parser.add_argument('--inbound', action='store_true', help="Use it if you want to load package from inbound.")

    # this below arg should be fetched from environment variable set by runner
    # parser.add_argument('tag_name', 'store_value', help='Tag name or commit from Git repository')

    return parser.parse_args(args)


def action_build(inbound=False, changes_only=True):
    merge_iid = os.environ[settings.CI_MERGE_REQUEST_IID]
    if inbound:
        if changes_only:  # experimental
            changes = build.get_changes_from_git_diff(mock=settings.mock)
            packages = build.get_packages_from_changes(changes)
        else:
            packages = build.get_all_package()
            try:
                os.makedirs(config.get_build_dir(merge_iid))
            except FileExistsError:
                log.error("Build for this merge request has already done.")
                exit(-1)
        for package in packages:
            if build.build_package_for_inbound(package, merge_iid):
                log.info("Built {} successfully".format(package))
            else:
                log.error("Built {} failed".format(package))
                break
    elif not changes_only:
        packages = build.get_all_package()
        build_dir = config.get_build_dir(merge_iid)
        for package in packages:
            source_dir = settings.SRC_DIR / pathlib.Path(package)
            os.symlink(source_dir, build_dir, target_is_directory=True)
    else:
        pass


def action_deploy(inbound=False):
    """
    Sending packages built in build stage and run script is_instance.
    If you have configuration for specific node it MUST have SSH_ADDRESS_ENV_VAR set, cause there have to be correlation
    which config matches to which host.
    Hosts which has different configuration NOT MUST be written down in NODES for environment config,
    but there will be WARNING log.
    :param inbound:
    :return:
    """
    merge_iid = os.environ[settings.CI_MERGE_REQUEST_IID]
    env = os.environ[settings.CI_ENVIRONMENT_NAME]
    hosts = os.environ[settings.NODES_ENV_VAR].split(',')
    nodes_names = config.find_node_configs(env)
    if inbound:
        for node in nodes_names:
            log.info("Sending packages for node {}".format(node))
            config.load_node_configuration(env, node)
            host = os.environ[settings.SSH_ADDRESS_ENV_VAR]  # changed by last loaded config
            try:
                hosts.remove(host)
            except ValueError:
                log.warn("Node {} has IP not defined in NODES config for environment {}".format(node, env))
            sender.send_to_inbound(merge_iid, host)
        for host in hosts:
            log.info("Sending packages to host {}".format(host))
            sender.send_to_inbound(merge_iid, host)
        # invoke endpoint to install and log.
        # this probably use only IP's.
    else:
        # sender.send_to_packages_repo()
        # run is_instance on machines from environment
        log.info("not implemented yet.")


def main():
    # parse arguments
    args = build_arguments()
    # configure
    ref = ""
    try:
        ref = os.environ[settings.CI_MERGE_REQUEST_IID]
        env_name = os.environ[settings.CI_ENVIRONMENT_NAME]
        log.info("Loading configuration for environment {}".format(env_name))
        config.load_configuration(env_name)
    except (ValueError, KeyError, errors.LoadingConfigurationError) as e:
        log.error(e)
        log.info("Error occured. Ending...")
        exit(-1)
    # run actions
    try:
        if not ref:
            raise ValueError("Reference to MERGE_REQUEST_IID not set, so pipeline is not configured properly.")
        if args.action == "build":
            changes_only = not args.no_changes_only  # reversed logic
            action_build(args.inbound, changes_only)
        if args.action == "deploy":
            action_deploy(args.inbound)
        elif args.action == "test":
            exit(0)
        else:
            log.error("Entered unknown action.")
    except errors.GitOperationError as e:
        log.error(e)
        log.info("Error occured. Ending...")
        exit(-1)


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
            # save additionally environment name for config
            cfg.write(f"{[settings.CI_ENVIRONMENT_NAME]} = {os.environ[settings.CI_ENVIRONMENT_NAME]}")
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
