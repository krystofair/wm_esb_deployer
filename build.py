import argparse
import functools
import shutil
import pathlib
import os
import subprocess
import itertools

import settings
from settings import log


def clean_directory_for_new_build(directory='.'):
    """
    Delete all build_* directories whose were created by deployer
    :param directory: directory where to find such a build_*-s.
    """
    for entry in os.scandir(directory):
        if entry.is_dir() and entry.name.startswith("build_"):
            shutil.rmtree(entry.path)


def build_package(name: str, ref: str = 'HEAD', skip_check_archive_exist = False) -> bool:
    """
    Building ZIP from package and left it in working dir.
    :param skip_check_archive_exist: if you should do things quickly
    :param name: name of package
    :param ref: name of GIT commit
    :return: True if builded, False otherwise
    """
    error = False
    try:
        repository_dir = '.'
        try:
            repository_dir = os.environ[settings.REPO_DIR_ENV_VAR]
        except KeyError:
            pass
        os.mkdir(f"build_{ref}")
        # before this 'git reset' runner pull the repo
        arguments = f"git reset --hard {ref}".split(' ')
        result = subprocess.run(arguments)
        if result.returncode == 0:
            if 'zip' in [n for n, _ in shutil.get_archive_formats()]:
                shutil.make_archive(f"build_{ref}/{name}", 'zip', root_dir=f"{repository_dir}/{settings.SRC_DIR}/{name}")
                if not skip_check_archive_exist:
                    try:
                        if not [file for file in os.scandir(f"build_{ref}") if file.name == f"{name}.zip"]:
                            log.error('Making archive process failed.')
                            error = True
                    except Exception as e:
                        log.error(e)
                        error = True
            else:
                log.error("There is no 'zip' format to create archive.")
                error = True
    except Exception as e:
        log.error(e)
        error = True
    return not error

def prepare_package_only_changes_services_from_last_commit(ref: str = 'HEAD') -> bool:
    """
    Prepare directory with metadata and services from ns/
    which were changed across ref commit and previous one.
    :return: True if operation succeed, False otherwise.
    """
    arguments = "git log --oneline".split(' ')
    gitlog_output = subprocess.run(arguments, capture_output=True, encoding='utf-8')
    log_lines = gitlog_output.stdout.split('\n')
    commits = list(map(lambda x: ''.join(itertools.takewhile(lambda y: y != ' ', x)), log_lines))
    if ref == 'HEAD':
        idx = 0
    else:
        idx = commits.index(ref)
    previous_commit = commits[idx+1]
    arguments = "git diff {} --name-only".format(previous_commit)
    # !hint encoding.
    diff = subprocess.run(arguments, capture_output=True, encoding='utf-8')
    diff_lines = diff.stdout.split('\n')
    log.info("Changed packages: {}".format(list(map(extract_service_name, diff_lines))))
    # packages = set(p for p in [line for line in diff_lines.split('/')[0])
    packages = set(p[0] for p in [line.split('/') for line in diff_lines])
    for package in packages:
        if is_package_to_exclude(package):
            continue
        if settings.REPO_DIR_ENV_VAR in os.environ:
            repo_dir = os.environ[settings.REPO_DIR_ENV_VAR]
        else:
            repo_dir = '.'

        path = '/'.join([repo_dir, settings.SRC_DIR, package])
        # if path.startswith('./'):
        #     path = ''.join(path[1:])
        shutil.copytree(path, f"build_{ref}/", ignore=shutil.ignore_patterns("ns"))
    for diff in diff_lines:
        shutil.copytree(diff, f"build_{ref}/", dirs_exist_ok=True)

@functools.cache
def is_package_to_exclude(package_name):
    for exclude in settings.PACKAGES_TO_EXCLUDE:
        if exclude.endswith('*') and exclude[:-1] in package_name:
            return True
        elif exclude == package_name:
            return True
    return False


def extract_service_name(diff_line):
    parts = diff_line.split('/')
    _ = parts.pop()
    index = parts.index('tp')
    return '.'.join(parts[index:-1]) + ':' + parts[-1]