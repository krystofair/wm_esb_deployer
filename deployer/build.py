"""Building - preparing changes to deploy"""

import functools
import shutil
import pathlib
import os
import itertools
import typing
from datetime import datetime

from . import settings, config
from .settings import log
from .git import GitOperation


def build_packages_for_is_instance(build_dir, packages, services):
    for package in packages:
        create_empty_package(package, build_dir)
        services_to_copy = list(filter(lambda x: package in x.split('/'), services))
        common_names_svc = map(extract_is_style_service_name, services_to_copy)
        log.info("In package {}; Copying services: {}".format(package, ', '.join(common_names_svc)))
        copy_services(build_dir, package, services_to_copy)


def build_package_for_inbound(name: str, ref: str, skip_check_archive_exist=False) -> bool:
    """
    Building one ZIP from one package
    :param skip_check_archive_exist: if you should do things quickly,
    :param name: name of package,
    :param ref: name of merge_iid.
    :return: True if built, False otherwise.
    """
    error = False
    try:
        # initialize variables
        build_dir = config.get_build_dir(ref)
        source_dir = config.get_source_dir()
        os.makedirs(build_dir, exist_ok=True)
        if 'zip' in [n for n, _ in shutil.get_archive_formats()]:
            shutil.make_archive(str(pathlib.Path(build_dir) / name),
                                'zip', root_dir=str(source_dir/name))
            if not skip_check_archive_exist:
                try:
                    if not [file for file in os.scandir(build_dir) if file.name == f"{name}.zip"]:
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

@functools.cache
def is_default_package(name) -> bool:
    """
    Determine if package from vendor. Names are listed in settings.
    :return: True if name is on the list, False otherwise.
    """
    for package in settings.DEFAULT_PACKAGES:
        if package.endswith('*') and name.startswith(package[:-1]):
            return True
        elif package == name:
            return True
    return False

@functools.cache
def is_package_to_exclude(package_name) -> bool:
    """
    Determine whether package_name should be skipped or not.
    Implementation of logic with asterisk (*) to exclude by 'starts with' pattern.
    :param package_name: name to check.
    :return: True if should, False otherwise.
    """
    for exclude in settings.PACKAGES_TO_EXCLUDE:
        if exclude.endswith('*') and exclude[:-1] in package_name:
            return True
        elif exclude == package_name:
            return True
    return False


@functools.cache
def is_package(p: str) -> bool:
    """
    Determine whether package name p is package in our understanding.
    :param p: package name to check
    :return: True if it is a packages name, False otherwise.
    """
    if p.startswith("TpOss") or p.startswith("CaOss") or p.startswith("Wm") or p.startswith("Default"):
        return True
    return False


def get_changes_from_git_diff(mock=False):
    """
    Returns list of paths which changed between merge_request source branch and target branch.
    Mocked list shows an example of data which are returned here.
    Flag 'mock' default to False, can be set in settings.py - it was used for testing.
    """
    if mock:
        return [
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processHandleConfigureCFServiceResultRequest/flow.xml",
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processHandleConfigureCFServiceResultRequest/node.ndf",
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processUpdateCFServiceRequest/flow.xml",
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processUpdateCFServiceRequest/node.ndf",
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/handleConfigureCFServiceResult/flow.xml",
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/handleConfigureCFServiceResult/node.ndf",
            "packages/TpOssChannelJazz2/ns/tp/oss/channel/jazz/resource/priv/processGetDeviceParametersRequest/flow.xml",
            "packages/TpOssChannelJazz2/ns/tp/oss/channel/jazz/resource/priv/processGetDeviceParametersRequest/node.ndf"
        ]
    else:
        return GitOperation.diff_to_target_branch(os.environ[settings.CI_MERGE_REQUEST_TARGET_BRANCH_NAME])


def get_all_package() -> list:
    """
    Collecting all packages from repository directory, which is default '.' and can be set in settings.
    Default '.' is where GitLab runner cloned repository, but this can be specified in GitLab settings too,
    so if you change that value you should change REPO_DIR variable for this deployer too.
    :return: list of package names.
    """
    repo_dir = config.get_env_var_or_default(settings.REPO_DIR_ENV_VAR, default='.')
    return [p.name for p in os.scandir(repo_dir / pathlib.Path(settings.SRC_DIR))
            if is_package(p.name) and not is_package_to_exclude(p.name)]


def extract_is_style_service_name(diff_line: str, first_parts=None) -> str:
    """
    From diff line of changes from git this function produce name for service in Java style.
    Like this: PackageName/ns/com/example/service => com.example:service.
    :param diff_line: line for split and change
    :param first_parts: parts to search as begin, default None like ['tp'].
    :return: changed name or empty string if cant process line.
    """
    try:
        if not first_parts:
            first_parts = ['tp']
        parts = diff_line.split('/')
        _ = parts.pop()
        index = None
        for first_part in first_parts:
            try:
                index = parts.index(first_part)
            except ValueError:
                pass
        if index is None:
            raise ValueError()
        return '.'.join(parts[index:-1]) + ':' + parts[-1]
    except ValueError:
        log.warn(f"This line {diff_line} cannot be parsed as a service name.")
    except Exception as e:
        log.exception(e)
    return ""


def add_file_cicd_version_to_path(path):
    """Add to `path` cicd version in format {project_name};{commit_sha};{dt_stamp}"""
    project_name = os.environ[settings.CI_PROJECT_NAME] if settings.CI_PROJECT_NAME in os.environ else '-'
    commit_sha = os.environ[settings.CI_COMMIT_SHA] if settings.CI_COMMIT_SHA in os.environ else '-'
    tag_name = os.environ[settings.CI_COMMIT_TAG] if settings.CI_COMMIT_TAG in os.environ else '-'
    dt_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(f"{path}/cicd.version", 'w', encoding='utf-8') as cicd_version_file:
        cicd_version_file.write(f"{project_name};{commit_sha};{tag_name};{dt_stamp}")


def get_packages_from_changes(changes) -> set:
    """
    Collect whole packages (TpOss*, etc.) from changes line produced by `git diff` command.
    :param changes:
    :return: set - unique list of packages name
    """
    return set(
        itertools.filterfalse(
            is_package_to_exclude,
            set(filter(is_package, itertools.chain(*[p for p in (line.split('/') for line in changes)])))
        ))


def get_services_from_changes(changes) -> set:
    """
    Collect only services dir - the folders which has specific files changed.
    :param changes: list from `git diff` operation.
    :return: list of path to folders.
    """
    services = set()
    for change in changes:
        if not change.endswith(settings.SOURCE_CODE_EXT):
            continue
        svc = '/'.join(s for s in change.split('/')[:-1])  # exclude last (file) part.
        services.add(svc)
    return services


def clean_directory_after_deploy():
    """Delete build_{settings.PIPELINE_REFERENCE} directory which was created by deployer."""
    ref = settings.PIPELINE_REFERENCE
    directory = config.get_build_dir(ref)
    for entry in os.scandir(directory):
        if entry.is_dir() and entry.name == f"build_{ref}":
            shutil.rmtree(entry.path)


def create_empty_package(name, where) -> bool:
    """
    Build package from exists already, but with ns/ folder empty.
    Then there will be added only changed services.
    :param name: name of package
    :param where: in which folder create that empty package
    :return: True if good and new package was added to build_* dir. False otherwise.
    """
    try:
        shutil.copytree(f'packages/{name}', f'{where}/{name}', ignore=shutil.ignore_patterns("ns"))
    except Exception as e:
        log.error(e)
        return False
    return True


def copy_services(build_dir: str, package: str, service_dir_list: typing.Iterable):
    """
    :param package: package from which services are,
    :param service_dir_list: list of absolute paths to where files flow.xml etc. are,
    :param build_dir: is buiding directory where new package are created and to that package services are copied.
    :return: True if copy all service well, False otherwise.
    """
    source_dir = config.get_source_dir() / package  # $REPO_DIR/packages/$package
    service_dirs = [x.split(package)[1][1:] for x in service_dir_list]  # /ns/* # and get rid of '/'
    for service_dir in service_dirs:
        try:
            src = pathlib.Path(source_dir) / pathlib.Path(service_dir)
            dst = pathlib.Path(build_dir) / package / service_dir
            shutil.copytree(src, dst)
        except Exception as e:
            log.exception(e)
            raise
