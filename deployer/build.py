import functools
import shutil
import pathlib
import os
import itertools
from datetime import datetime

from . import errors, settings, config
from .settings import log
from .git import GitOperation


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
        repository_dir = config.get_env_var_or_default(settings.REPO_DIR_ENV_VAR, default='.')
        build_dir = config.get_build_dir(ref)
        os.makedirs(build_dir, exist_ok=True)
        if 'zip' in [n for n, _ in shutil.get_archive_formats()]:
            shutil.make_archive(f"{build_dir}/{name}",
                                'zip', root_dir=f"{repository_dir}/{settings.SRC_DIR}/{name}")
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
def is_package_to_exclude(package_name):
    for exclude in settings.PACKAGES_TO_EXCLUDE:
        if exclude.endswith('*') and exclude[:-1] in package_name:
            return True
        elif exclude == package_name:
            return True
    return False


@functools.cache
def is_package(p: str) -> bool:
    if p.startswith("TpOss") or p.startswith("CaOss") or p.startswith("Wm") or p.startswith("Default"):
        return True
    return False


def get_changes_from_git_diff(mock=False):
    if mock:
        return [
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processHandleConfigureCFServiceResultRequest/flow.xml",
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processHandleConfigureCFServiceResultRequest/node.ndf",
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processUpdateCFServiceRequest/flow.xml",
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processUpdateCFServiceRequest/node.ndf",
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processUpdateCFServiceResponse/flow.xml",
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processUpdateCFServiceResponse/node.ndf",
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/handleConfigureCFServiceResult/flow.xml",
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/handleConfigureCFServiceResult/node.ndf"
        ]
    else:
        return GitOperation.diff_to_HEAD(os.environ[settings.CI_COMMIT_SHA])


def get_all_package():
    repo_dir = config.get_env_var_or_default(settings.REPO_DIR_ENV_VAR, default='.')
    return [p.name for p in os.scandir(repo_dir / pathlib.Path(settings.SRC_DIR))
            if is_package(p.name) and not is_package_to_exclude(p.name)]


def extract_is_style_service_name(diff_line: str) -> str:
    try:
        parts = diff_line.split('/')
        _ = parts.pop()
        index = parts.index('tp')
        return '.'.join(parts[index:-1]) + ':' + parts[-1]
    except ValueError:
        log.warn(f"This line {diff_line} cannot be parsed as a service name.")
        return ""
    except Exception as e:
        log.exception(e)
        return ""


def add_file_cicd_version_to_path(path):
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


def clean_directory_after_deploy(ref, directory='.'):
    """
    Delete build_{ref} directory whose were created by deployer.
    :param directory: directory where to search that build_{ref}.
    :param ref: reference to merge_iid
    """
    for entry in os.scandir(directory):
        if entry.is_dir() and entry.name == ref:
            shutil.rmtree(entry.path)
