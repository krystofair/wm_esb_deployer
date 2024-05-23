"""Errors which can be thrown in processing"""


class BaseDeployerError(Exception):
    pass


class LoadingConfigurationError(BaseDeployerError):
    pass


class GitOperationError(BaseDeployerError):
    pass


class LackRequiredConfiguration(BaseDeployerError):
    pass


class RemoteCommandError(BaseDeployerError):
    pass
