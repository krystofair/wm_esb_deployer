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

from . import (config, errors, sender, settings, build, remoter)
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
    parser.add_argument("--with-restart", action='store_true', help="Use if you want to restart server in deploy")

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
    try:
        log.info("Make|get dir for build")
        build_dir = config.get_build_dir(ref)
    except FileExistsError:
        log.error("Build for this merge request has already done.")
        return True
    if inbound:
        if changes_only:
            changes = build.get_changes_from_git_diff(mock=settings.mock)
            if not changes:
                log.info("There were not changes")
                return False
            packages = build.get_packages_from_changes(changes)
        else:
            log.info("Get all packages from repository without this excluded from settings")
            packages = build.get_all_package()
        for package in packages:
            if build.build_package_for_inbound(package, ref):
                log.info("Built {} successfully".format(package))
            else:
                log.error("Built {} failed".format(package))
                return False
    elif not changes_only:
        packages = build.get_all_package()
        sources_dir = config.get_source_dir()
        for package in packages:
            source_dir = sources_dir / pathlib.Path(package)
            destination_dir = build_dir / pathlib.Path(package)
            os.symlink(source_dir, destination_dir, target_is_directory=True)
    else:
        log.info("Set up build for is_instance script deploying.")
        changes = build.get_changes_from_git_diff(settings.mock)
        if not changes:
            log.info("There were not changes")
            return False
        services = build.get_services_from_changes(changes)
        packages = build.get_packages_from_changes(changes)
        try:
            build.build_packages_for_is_instance(build_dir, packages, services)
        except Exception as e:
            log.error(e)
            return False
    return True


def action_deploy(inbound=False, with_restart=False) -> bool:
    """
    Sending packages built in build stage and run script is_instance.
    If you have configuration for specific node it MUST have SSH_ADDRESS_ENV_VAR set, cause there have to be correlation
    which config matches to which host.
    Hosts which has different configuration NOT MUST be written down in NODES for environment config,
    but there will be WARNING log.
    :param inbound: determine if packages are ZIP-s and will be sent to inbound directory,
    :param with_restart: determine if there will be restart after execute is_instance.sh script.
    :return: True if it goes well, False otherwise.
    """
    ref = os.environ[settings.PIPELINE_REFERENCE]
    env = os.environ[settings.CI_ENVIRONMENT_NAME]
    try:
        deploy_zone = config.get_env_var_or_default(settings.ZONE_ENV_VAR, default=None)
        if deploy_zone:
            del os.environ[settings.ZONE_ENV_VAR]
        hosts = set()
        configured_hosts = {}
        filenames_node_cfg = config.find_node_configs(env)
        for nf in filenames_node_cfg:
            node_name = nf.rstrip('.cfg')
            config.load_node_configuration(env, node_name)
            addr = os.environ[settings.SSH_ADDRESS_ENV_VAR]
            if deploy_zone:
                log.info("Zone was set - selecting hosts")
                zone = config.get_env_var_or_default(settings.ZONE_ENV_VAR,
                                                     default='kokianowy_rbaon_astoarnuta')
                if zone == deploy_zone:
                    hosts.add(addr)
            if addr in configured_hosts:
                log.error("The same address for two nodes.")
                return False
            configured_hosts[addr] = node_name
        if not deploy_zone:
            hosts = set()
            nodes = config.get_env_var_or_default(settings.NODES_ENV_VAR, default=None)
            if nodes:
                hosts |= set(filter(None, nodes.split(',')))
            hosts |= configured_hosts.keys()
            if not hosts:
                log.error("Any host was configured")
                return False
    except KeyError as e:
        log.error(e)
        return False
    except errors.LoadingConfigurationError as e:
        log.error(e)
        return False
    signer = build.Signer()
    for host in hosts:
        build_dir = config.get_build_dir(ref)
        hosts_already_get = build.Signer.get_hosts(build_dir)
        if host in hosts_already_get:
            log.info(f"For this host {host} packages already sent.")
            continue
        log.info("Load global configuration of {}".format(env))
        config.load_configuration(env)
        try:
            log.info("Load configuration of {}".format(host))
            config.load_node_configuration(env, configured_hosts[host])
        except KeyError:
            # supress this cause this means that host are loaded from spliting by comma
            pass
        if inbound:
            log.info("Sending packages to inbound at host {}".format(host))
            if not sender.send_to_inbound(ref, host):
                log.error(f"Sending packages for host {host} to inbound for environment {env} failed")
                return False
            signer.add_host_to_stamp(host)
            signer.write_stamp(build_dir)
            log.info("Host {} get packages".format(host))
        else:
            log.info("Sending packages to repository dir at host {}".format(host))
            if not sender.send_to_packages_repo(ref, host):
                log.error(f"Sending packages for host {host} to repository dir for environment {env} failed")
                return False
            if with_restart:
                log.info("Shutdown server.")
                if not remoter.shutdown_server(host):
                    log.error("Shutdown server command timeout. Check it.")
                    return False
            log.info("Run is_instance script")
            if not remoter.run_is_instance(host):
                return False
            if with_restart:
                log.info("Start server.")
                if not remoter.start_server(host):
                    log.error("Start server command failed.")
                    return False
                log.info("Check start status.")
                if not remoter.check_start_status(host):
                    return False
    return True


def clean_repo_after_instance_script_done():
    """
    Delete non-core, deployed packages from $IS_DIR/packages.
    To be prepared for another deployment.
    """
    env = os.environ[settings.CI_ENVIRONMENT_NAME]
    loader = config.CfgLoader(env)
    config.load_configuration(env)
    hosts_from_nodes = config.get_env_var_or_default(settings.NODES_ENV_VAR, default=None)
    hosts = set()
    if hosts_from_nodes:
        hosts = set(hosts_from_nodes.split(','))
    for node_loaded_config_in_background in loader:
        with loader:
            ip_address = os.environ[settings.SSH_ADDRESS_ENV_VAR]
            if ip_address in hosts:
                hosts.remove(ip_address)
            log.info("Clear packages repository for %s" % (ip_address,))
            invoker = remoter.SSHCommand.construct(ip_address)
            integration_server_dir = os.environ[settings.IS_DIR_ENV_VAR]
            invoker.invoke(f"rm -rf {integration_server_dir}/packages/*")
        if loader.error:
            exit(-1)
    for host in hosts:
        config.load_configuration(env)
        invoker = remoter.SSHCommand.construct(host)
        integration_server_dir = os.environ[settings.IS_DIR_ENV_VAR]
        invoker.invoke(f"rm -rf {integration_server_dir}/packages/*")
    exit(0)


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
            raise ValueError("Reference to MERGE_REQUEST_IID not set,"
                             "so pipeline is not configured properly.")
        if args.action == "build":
            if not action_build(args.inbound, args.no_changes_only):
                exit(-1)
        elif args.action == "deploy":
            if not action_deploy(args.inbound, args.with_restart):
                exit(-1)
        elif args.action == "test":
            exit(0)
        else:
            log.error("Entered unknown action.")
    except Exception as e:
        log.error(e)
        log.info("Error occured. Ending...")
        exit(-1)
    exit(0)


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
        if os.path.exists(path / filename):
            log.info("Configuration for %s changed - overridden." % filename)
        with open(path / filename, 'w', encoding='utf-8') as cfg:
            for key in keys:
                try:
                    cfg.write(f"{key} = {os.environ[key]}\n")
                except KeyError:
                    continue
    except FileExistsError:
        log.error("Configuration already exists, but should be overridden and this error not show up.")
        exit(-1)
    exit(0)


def clean_configuration() -> None:
    """
    Script to clean configuration per environment. This should not be a problem,
    because there will be configuration loaded in yaml files. Otherwise, do not use
    a job with this script in your pipeline.
    """
    environ = os.environ[settings.CI_ENVIRONMENT_NAME]
    config.clear_configuration_for_environment(environ)
