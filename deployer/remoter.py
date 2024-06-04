import dataclasses
import pathlib
import subprocess
import os
import socket
import time

from . import errors, settings, config
from .settings import log


@dataclasses.dataclass
class SSHCommand:
    ip: str
    port: str
    username: str
    private_key_filename: pathlib.Path

    def invoke(self, command):
        cmd_args = "ssh -p {} -i {} {}@{} {}".format(
            self.port,
            self.private_key_filename,
            self.username,
            self.ip,
            command
        ).split(' ')
        try:
            process = subprocess.run(cmd_args, capture_output=True, encoding='utf-8',
                                     timeout=settings.SUBPROCESS_CMD_TIMEOUT)
            if process.returncode != 0:
                raise errors.RemoteCommandError(process.stderr)
            return process.stdout
        except Exception as e:
            log.exception(e)
            raise

    @staticmethod
    def construct(host):
        """
        Pull out from environment basic parameters for SSHCommand client.
        :return: None if cannot construct, SSHCommand object otherwise.
        """
        try:
            ip = host
            port = config.get_env_var_or_default(os.environ[settings.SSH_PORT_ENV_VAR], default='22')
            username = os.environ[settings.IS_NODE_USERNAME_ENV_VAR]
            private_key_filepath = os.environ[settings.IS_NODE_PRIVKEY_ENV_VAR]
            return SSHCommand(ip, port, username, pathlib.Path(private_key_filepath))
        except KeyError:
            log.error("Lack of configuration. Used variables: {} {} {}".format(
                settings.SSH_PORT_ENV_VAR, settings.IS_NODE_USERNAME_ENV_VAR, settings.IS_NODE_PRIVKEY_ENV_VAR
            ))
            return None
        except Exception as e:
            log.exception(e)
            return None


def run_is_instance(host, packages='all') -> bool:
    """
    Invoke command /path/to/is_instance -Dinstance.name={} -Dpackage.list={},{} at remote server
    :return:
    """
    invoke = True
    try:
        instance_name = config.get_env_var_or_default(os.environ[settings.INSTANCE_NAME_ENV_VAR], default='default')
        is_dir = os.environ[settings.IS_DIR_ENV_VAR]
        script_path = is_dir / pathlib.Path("instances/is_instance.sh")
        # command = f"{script_path} update -Dpackage.list={packages} -Dinstance.name={instance_name}"
        # Without determine package.list, All non-default package will be taken.
        if not isinstance(packages, str):
            packages_str = ','.join(packages)
        else:
            packages_str = packages
        command = f"{script_path} update -Dpackage.list={packages_str} -Dinstance.name={instance_name}"
        ssh = SSHCommand.construct(host)
        if not ssh:
            log.error("Cannot construct SSH client.")
            return False
        try:
            output = ssh.invoke(command)
            log.info("SSH invoke output: {}".format(output))
        except errors.RemoteCommandError as e:  # normal error handling
            log.error(e)
            invoke = False
        except Exception as e:
            log.error(e)
            invoke = False
    except KeyError:
        invoke = False
        log.error("Lack of configuration. Used variables: {} {}('default')".format(
            settings.IS_DIR_ENV_VAR, settings.INSTANCE_NAME_ENV_VAR,
        ))
    except Exception as e:
        log.exception(e)
        invoke = False
    return invoke


def shutdown_server(host) -> bool:
    """Invoke remove script for shutdown server"""
    try:

        instance_name = os.environ[settings.INSTANCE_NAME_ENV_VAR]
        is_dir = os.environ[settings.IS_DIR_ENV_VAR]
        script_path = is_dir / pathlib.Path(f"instances/{instance_name}/bin/shutdown.sh")
        ssh = SSHCommand.construct(host)
        # ssh = SSHCommand(ssh_host, ssh_port, is_username, pathlib.Path(is_private_key_filepath))
        output = ssh.invoke(script_path)
        if "Stopped" in output:
            return True
    except KeyError:
        log.error("Lack of configuration. Used variables: {} {}".format(
            settings.IS_DIR_ENV_VAR, settings.INSTANCE_NAME_ENV_VAR
        ))
    except TimeoutError:
        log.error("Shutdown server timeout. Please check status manually.")
    return False


def start_server(host) -> bool:
    """Start server"""
    invoke = True
    try:
        instance_name = os.environ[settings.INSTANCE_NAME_ENV_VAR]
        is_dir = os.environ[settings.IS_DIR_ENV_VAR]
        script_path = is_dir / pathlib.Path(f"instances/{instance_name}/bin/startup.sh")
        try:
            ssh = SSHCommand.construct(host)
            ssh.invoke(f"{script_path}")
        except errors.RemoteCommandError as e:  # normal error handling
            log.error(e)
            invoke = False
        except Exception as e:
            log.error(e)
            invoke = False
    except KeyError:
        invoke = False
        log.error("Lack of configuration. Used variables: {} {}".format(
            settings.IS_DIR_ENV_VAR, settings.INSTANCE_NAME_ENV_VAR
        ))
    return invoke


def check_start_status(host, port=5555) -> bool:
    """
    Check status of server after startup - wait timeout determined in settings
    :param host: host to connect
    :param port: port to connect - default as management port of IntegrationServer
    :return: True if started, False otherwise.
    """
    socket.setdefaulttimeout(settings.CHECK_CONNECTION_TIMEOUT)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for attempt in range(settings.CHECK_START_STATUS_COUNT):
        try:
            log.info(f"Check connection, attempt: {attempt}")
            s.connect((host, int(port)))
            s.close()
            return True
        except TimeoutError:
            log.error("Timeout error - server started failed.")
            return False
        except ConnectionRefusedError:
            log.info(f"Connection refused.")
            time.sleep(settings.CHECK_START_STATUS_TIME)
        except Exception as e:
            log.info(f"Another exception {e} will be supress")
            time.sleep(settings.CHECK_START_STATUS_TIME)
    return False


def clean_package_repo(host):
    """Delete all packages from server package repository."""
    is_dir = os.environ[settings.IS_DIR_ENV_VAR]
    config.get_build_dir(settings.PIPELINE_REFERENCE)
    repo_dir = is_dir / pathlib.Path('packages')
    client = SSHCommand.construct(host)
    client.invoke("rm -rf {}".format(repo_dir))
