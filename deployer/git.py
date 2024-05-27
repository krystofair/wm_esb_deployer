"""Set of git operations"""
import dataclasses
import subprocess

from . import errors, settings
from .settings import log


class GitOperation:
    # def __init__(self):
    #     """Set up credentials for runner."""
    #     self.login = "esb-runner"
    #     self.access_token = config.get_env_var_or_default(os.environ[settings.PERSONAL_ACCESS_TOKEN], default="")

    @staticmethod
    def diff_to_target_branch(target_branch_name) -> list:
        """
        Compare changes between merging branches - new (detached commit) and target.
        :param target_branch_name: where source will be merged,
        :return: list of paths whose changed.
        """
        changes = []
        command_args = 'git diff --name-only remotes/origin/{}'.format(target_branch_name).split(' ')
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


# import http.client as client
# import http
# @dataclasses.dataclass
# class GitLabOperation:
#     project_id: str
#     private_token: str
#
#     def tag(self, ref, name, msg=""):
#         """tagowanie"""
#         con = client.HTTPConnection("192.168.56.109", 43211)
#         con.putheader("PRIVATE_TOKEN", self.private_token)
#         con.request("POST", f"/projects/{self.project_id}/repository/tags/?tag_name={name}&ref={ref}")