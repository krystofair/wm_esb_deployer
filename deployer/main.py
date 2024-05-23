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
import copy

from . import (config, errors, sender, settings, build)
from .settings import log


def build_arguments(args=None):
    """
    Parse arguments from command line.
    :param args: None, prepared to do tests.
    :return:
    """
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


def action_build(inbound=False, changes_only=True) -> bool:
    """
    Build packages or link to directory build_$settings.PIPELINE_REFERENCE for deploy.
    :param inbound: flag whether packages should be packed in zip archive,
    :param changes_only: flag for determine if only packages with changes should be taken into account.
    :return: True if good, False otherwise.
    """
    ref = os.environ[settings.PIPELINE_REFERENCE]
    if inbound:
        if changes_only:
            changes = build.get_changes_from_git_diff(mock=settings.mock)
            if not changes:
                return False
            packages = build.get_packages_from_changes(changes)
        else:
            packages = build.get_all_package()
            try:
                os.makedirs(config.get_build_dir(ref))
            except FileExistsError:
                log.error("Build for this merge request has already done.")
                return False
        for package in packages:
            if build.build_package_for_inbound(package, ref):
                log.info("Built {} successfully".format(package))
            else:
                log.error("Built {} failed".format(package))
                return False
    elif not changes_only:
        packages = build.get_all_package()
        build_dir = config.get_build_dir(ref)
        for package in packages:
            source_dir = settings.SRC_DIR / pathlib.Path(package)
            os.symlink(source_dir, build_dir, target_is_directory=True)
    else:
        return False  # not implemented.
    return True


def action_deploy(inbound=False) -> bool:
    """
    Sending packages built in build stage and run script is_instance.
    If you have configuration for specific node it MUST have SSH_ADDRESS_ENV_VAR set, cause there have to be correlation
    which config matches to which host.
    Hosts which has different configuration NOT MUST be written down in NODES for environment config,
    but there will be WARNING log.
    :param inbound:
    :return: True if it goes well, False otherwise.
    """
    ref = os.environ[settings.PIPELINE_REFERENCE]
    env = os.environ[settings.CI_ENVIRONMENT_NAME]
    global_config = copy.deepcopy(os.environ)
    node_configs = list()
    try:
        deploy_zone = config.get_env_var_or_default(settings.ZONE_ENV_VAR, default=None)
        if deploy_zone:
            del os.environ[settings.ZONE_ENV_VAR]
        filenames_node_cfg = config.find_node_configs(env)
        for nf in filenames_node_cfg:
            node_name = nf.rstrip('.cfg')
            log.info("Load configuration for node {}".format(node_name))
            config.load_node_configuration(env, node_name)
            zone = config.get_env_var_or_default(settings.ZONE_ENV_VAR, default='kokianowy_rbaon_astoarnuta')
            os.environ[settings.ZONE_ENV_VAR] = zone
            node_configs.append(copy.deepcopy(os.environ))
    except KeyError as e:
        log.error(e)
        return False
    except errors.LoadingConfigurationError as e:
        log.error(e)
        return False
    configured_hosts = map(lambda x: x[settings.SSH_ADDRESS_ENV_VAR], node_configs)
    if not deploy_zone:  # not specified zone
        hosts = set(os.environ[settings.NODES_ENV_VAR].split(','))
        _ = [hosts.add(ch) for ch in configured_hosts]  # add configured hosts even there are not included in NODES var
    else:
        hosts = set()
        for cfg in node_configs:
            addr = cfg[settings.SSH_ADDRESS_ENV_VAR]
            zone = cfg[settings.ZONE_ENV_VAR]
            if zone == deploy_zone:
                hosts.add(addr)
    log.info("sending part...")
    for host in hosts:
        os.environ = global_config
        try:
            os.environ.update([cfg for cfg in node_configs if cfg[settings.SSH_ADDRESS_ENV_VAR] == host][0])
        except IndexError:
            if deploy_zone:
                log.error("Not load SSH_ADDRESS for host {}".format(host))
                return False
            else:
                pass
        if inbound:
            log.info("Sending packages to inbound at host {}".format(host))
            if not sender.send_to_inbound(ref, host):
                log.error(f"Sending packages for host {host} to inbound for environment {env} failed")
                return False
        else:
            log.info("Sending packages to repository dir at host {}".format(host))
            if not sender.send_to_packages_repo(ref, host):
                log.error(f"Sending packages for host {host} to repository dir for environment {env} failed")
                return False


def main():
    # parse arguments
    args = build_arguments()
    # configure
    ref = ""
    try:
        ref = os.environ[settings.PIPELINE_REFERENCE]
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
            if not action_build(args.inbound, args.no_changes_only):
                exit(-1)
        elif args.action == "deploy":
            if not action_deploy(args.inbound):
                exit(-1)
        elif args.action == "test":
            exit(0)
        else:
            log.error("Entered unknown action.")
    except Exception as e:
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
    keys = [key for name, key in config.get_list_env_var_from_settings() if 'CONFIG_DIR' not in name]
    config_dir = config.get_env_var_or_default(settings.CONFIG_DIR_ENV_VAR, default='configs.d')
    path = config_dir / pathlib.Path(env_name)
    os.makedirs(path, exist_ok=True)
    try:
        with open(path / filename, 'x', encoding='utf-8') as cfg:
            for key in keys:
                try:
                    cfg.write(f"{key} = {os.environ[key]}\n")
                except KeyError:
                    continue
    except FileExistsError:
        log.error("Configuration already exists. You have to manually clean it up and retry if it changed.")
        exit(-1)


def clean_configuration() -> None:
    """
    Script to clean configuration per environment. This should not be a problem,
    because there will be configuration loaded in yaml files. Otherwise, do not use
    a job with this script in your pipeline.
    """
    environ = os.environ[settings.CI_ENVIRONMENT_NAME]
    config.clear_configuration_for_environment(environ)
