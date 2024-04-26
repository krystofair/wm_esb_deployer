import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('package_list', 'count', '+', help="A list of packages to build archives for.")
parser.add_argument('tag_name','store_value', help='Tag name or commit from Git repository')
parser.add_argument('--inbound')
arguments = parser.parse_args(sys.argv[1:])

for package in arguments.package_list.split(','):
    import build
    build.build_package(package, arguments.tag_name, True)
