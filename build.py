import argparse
import shutil
import pathlib
import os
import subprocess
import logging

import settings


logging.basicConfig(level=logging.INFO, format="%(created)f |%(levelname)s| %(name)s %(lineno)d %(message)s -_-")
log = logging.getLogger(__name__)


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
