"""
General module to make actions.
'test' - not implemented, should do some tests by means IntegrationServer and catch developers mistakes;
'inbound' - prepare packages in inbound directory on specific environment;
'deploy' - prepare backup and packages in packages/ directory of IS in environment and run 'is_instance update' script;
'backup' - revert changes by use created backup;
'prepare' - only prepare packages in 'packages/' directory on IS-es;
'stop' - not implemented, stop all instance from environment;
"""
import sys
import argparse

import settings


def build_arguments(args=None):
    if args is None:
        args = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument('action',
                        help="possible options for action are: 'test', 'inbound', 'prepare', 'deploy', 'backup'"
                             ", 'stop'")
    parser.add_argument('--package', nargs='+', action='extend', help="A list of packages to build archives for.")
    parser.add_argument('--changes-only', action='store_false',
                        help="Use this flag if you want to deploy all* packages\n*Without excluded packages {}"
                        .format(settings.PACKAGES_TO_EXCLUDE))

    # this below arg should be fetched from environment variable set by runner
    # parser.add_argument('tag_name', 'store_value', help='Tag name or commit from Git repository')

    return parser.parse_args(args)


if __name__ == "__main__":
    args = build_arguments()
    for package in args.package_list.split(','):
        import build

        build.build_package(package, args.tag_name, True)
