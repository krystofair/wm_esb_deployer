"""Errors which can be thrown in processing"""


class BaseDeployerError(Exception):
    pass


class LoadingConfigurationError(BaseDeployerError):
    pass


class GitOperationError(BaseDeployerError):
    pass