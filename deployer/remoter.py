import dataclasses
import pathlib
import subprocess
import os
import socket

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
            process = subprocess.run(cmd_args, capture_output=True, encoding='utf-8')
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


def run_is_instance(host):
    """
    Invoke command /path/to/is_instance -Dinstance.name={} -Dpackage.list={},{} at remote server
    :return:
    """
    invoke = True
    try:
        instance_name = config.get_env_var_or_default(os.environ[settings.INSTANCE_NAME_ENV_VAR], default='default')
        is_dir = os.environ[settings.IS_DIR_ENV_VAR]
        script_path = is_dir / pathlib.Path("instances/is_instance.sh")
        # command = f"{script_path} -Dpackage.list={packages} -Dinstance.name={instance_name}"
        # Without determine package.list, All non-default package will be taken.
        command = f"{script_path} -Dinstance.name={instance_name}"
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
    return invoke


def shutdown_server(host):
    """Invoke remove script for shutdown server"""
    try:

        instance_name = os.environ[settings.INSTANCE_NAME_ENV_VAR]
        is_dir = os.environ[settings.IS_DIR_ENV_VAR]
        script_path = is_dir / pathlib.Path(f"instances/{instance_name}/bin/shutdown.sh")
        ssh = SSHCommand.construct(host)
        # ssh = SSHCommand(ssh_host, ssh_port, is_username, pathlib.Path(is_private_key_filepath))
        output = ssh.invoke(script_path)
        log.info(output)
    except KeyError:
        log.error("Lack of configuration. Used variables: {} {}".format(
            settings.IS_DIR_ENV_VAR, settings.INSTANCE_NAME_ENV_VAR
        ))
        raise


def start_server(host):
    """Start server"""
    invoke = True
    try:
        instance_name = os.environ[settings.INSTANCE_NAME_ENV_VAR]
        is_dir = os.environ[settings.IS_DIR_ENV_VAR]
        script_path = is_dir / pathlib.Path(f"instances/{instance_name}/bin/startup.sh")
        try:
            ssh = SSHCommand.construct(host)  # raises
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
    try:
        log.info(f"checking connection")
        s.connect((host, int(port)))
        s.close()
        return True
    except TimeoutError:
        log.error("Timeout error - server started failed.")
        return False


def check_stop_status(host) -> bool:
    """
    Check if server stoped and possible to invoke is_instance.sh script.
    :param host: at which server check that status
    :return: True if stopped, False otherwise.
    """
    try:
        ssh = SSHCommand.construct(host)
        output = ssh.invoke("ps -ef | grep IS | grep -v grep")
        if not output:
            return True
    except KeyError:
        log.error("There are not a configuration for {} {} {}".format(
            settings.IS_NODE_USERNAME_ENV_VAR,
            settings.IS_NODE_PRIVKEY_ENV_VAR,
            settings.SSH_PORT_ENV_VAR
        ))
    except (Exception, errors.RemoteCommandError, AttributeError) as e:
        log.error(e)
    return False


def clean_package_repo(host):
    """Delete all packages from server package repository."""
    is_dir = os.environ[settings.IS_DIR_ENV_VAR]
    config.get_build_dir(settings.PIPELINE_REFERENCE)
    repo_dir = is_dir / pathlib.Path('packages')
    client = SSHCommand.construct(host)
    client.invoke("rm -rf {}".format(repo_dir))
