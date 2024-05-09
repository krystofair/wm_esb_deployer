"""Set of git operations"""
import subprocess

from . import errors, settings
from .settings import log


class GitOperation:
    # def __init__(self):
    #     """Set up credentials for runner."""
    #     self.login = "esb-runner"
    #     self.access_token = config.get_env_var_or_default(os.environ[settings.PERSONAL_ACCESS_TOKEN], default="")
    @staticmethod
    def diff_branches(target_branch, source_branch) -> list:
        """
        Compare changes between merging branches.
        :param target_branch: where source will be merged,
        :param source_branch: with new changes.
        :return: list of paths whose changed.
        """
        changes = []
        command_args = 'git diff --name-only {} {}'.format(target_branch, source_branch).split(' ')
        try:
            pc = subprocess.run(command_args, capture_output=True, encoding='utf-8')
            if pc.returncode != 0:
                log.info(pc.stdout)
                log.error(pc.stderr)
            output_lines = pc.stdout.split('\n')
            # how filter works: https://docs.python.org/3/library/functions.html#filter
            changes = list(filter(None, output_lines))
        except Exception as e:
            log.exception(e)
            raise errors.GitOperationError(e) from None
        return changes

    @staticmethod
    def check_current_branch():
        cmd_args = "git branch --show-current".split(' ')
        result = subprocess.run(cmd_args, capture_output=True, encoding='utf-8')
        if result.returncode != 0:
            raise errors.GitOperationError('checkout')
        return list(filter(None, filter(str.strip, result.stdout.split('\n')))).pop()  # should be one

    @staticmethod
    def git_checkout(branch) -> bool:
        cmd_args = "git checkout {}".format(branch).split(' ')
        result = subprocess.run(cmd_args)
        if result.returncode != 0:
            raise errors.GitOperationError('checkout')
        return True

    def pull_changes(self, branch):
        if self.check_current_branch() != branch:
            self.git_checkout(branch)
        cmd_args = "git pull".split(' ')
        if subprocess.run(cmd_args).returncode != 0:
            raise errors.GitOperationError('pull')
