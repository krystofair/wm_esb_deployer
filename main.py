"""
General module to make actions.
'test' - not implemented, should do some tests by means IntegrationServer and catch developers mistakes;
'deploy' - prepare backup and packages in packages/ directory of IS in environment and run 'is_instance update' script;
'backup' - not implemented yet, revert changes by use created backup;
'build' - only prepare packages in 'packages/' directory on IS-es or in inbound if flag is set.
'stop' - not implemented, stop all instance from environment;
"""
import os
import sys
import argparse
import subprocess

import config
import settings
from settings import log
import build


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




def action_build(packages, inbound=False, changes_only=True):
    SOURCE_DIR = settings.SRC_DIR
    if inbound:
        for package in packages:
            if build.build_package(package):
                log.info("Built {} successfully".format(package))
            else:
                log.error("Built {} failed".format(package))
                break
    else:
        if changes_only:
            pass




def action_deploy(packages, changes):
    pass


if __name__ == "__main__":
    # parse arguments
    args = build_arguments()
    # configure
    special_config = os.environ[settings.NODE_ENV_VAR]
    if special_config:
        config.load_configuration(os.environ[settings.CI_ENVIRONMENT_NAME], special_config)
    else:
        config.load_configuration(os.environ[settings.CI_ENVIRONMENT_NAME])
    # run specified action
    if args.action == "build":
        action_build(args.package,inbound=args.inbound)
    if args.action == "deploy":
        action_build(args.package)
        if not args.inbound:
            action_deploy(args.package, changes=False)
    elif args.action == "":
        pass
    else:
        log.error("Entered unknown action.")

