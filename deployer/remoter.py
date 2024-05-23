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


def run_is_instance(host, package_list):
    """
    Invoke command /path/to/is_instance -Dinstance.name={} -Dpackage.list={},{} at remote server
    :return:
    """
    invoke = True
    try:
        ssh_host = host
        ssh_port = config.get_env_var_or_default(os.environ[settings.SSH_PORT_ENV_VAR], default='22')
        is_username = os.environ[settings.IS_NODE_USERNAME_ENV_VAR]
        is_private_key_filepath = os.environ[settings.IS_NODE_PRIVKEY_ENV_VAR]
        instance_name = config.get_env_var_or_default(os.environ[settings.INSTANCE_NAME_ENV_VAR], default='default')
        is_dir = os.environ[settings.IS_DIR_ENV_VAR]
        script_path = is_dir / pathlib.Path("/instances/is_instance.sh")
        packages = ','.join(package_list)
        command = f"{script_path} -Dpackage.list={packages} -Dinstance.name={instance_name}"
        ssh = SSHCommand(ssh_host, ssh_port, is_username, pathlib.Path(is_private_key_filepath))
        try:
            ssh.invoke(command)
        except errors.RemoteCommandError as e:  # normal error handling
            log.error(e)
            invoke = False
        except Exception as e:
            log.error(e)
            invoke = False
    except KeyError:
        invoke = False
        log.error("Lack of configuration. Used variables: {} {} {} {}"
                  .format(settings.IS_DIR_ENV_VAR,
                          settings.SSH_PORT_ENV_VAR,
                          settings.IS_NODE_USERNAME_ENV_VAR,
                          settings.IS_NODE_PRIVKEY_ENV_VAR))
    return invoke


def shutdown_server(host):
    """Invoke remove script for shutdown server"""
    try:
        ssh_host = host
        ssh_port = os.environ[settings.SSH_PORT_ENV_VAR]
        is_username = os.environ[settings.IS_NODE_USERNAME_ENV_VAR]
        is_private_key_filepath = os.environ[settings.IS_NODE_PRIVKEY_ENV_VAR]
        instance_name = os.environ[settings.INSTANCE_NAME_ENV_VAR]
        is_dir = os.environ[settings.IS_DIR_ENV_VAR]
        script_path = is_dir / pathlib.Path(f"/instances/{instance_name}/bin/shutdown.sh")
        ssh = SSHCommand(ssh_host, ssh_port, is_username, pathlib.Path(is_private_key_filepath))
        output = ssh.invoke(script_path)
        log.info(output)
    except KeyError:
        log.error("Lack of configuration. Used variables: {} {} {} {} {}"
                  .format(settings.IS_DIR_ENV_VAR,
                          settings.SSH_PORT_ENV_VAR,
                          settings.IS_NODE_USERNAME_ENV_VAR,
                          settings.IS_NODE_PRIVKEY_ENV_VAR,
                          settings.INSTANCE_NAME_ENV_VAR))
        raise


def start_server(host):
    """Start server"""
    invoke = True
    try:
        ssh_host = host
        ssh_port = os.environ[settings.SSH_PORT_ENV_VAR]
        is_username = os.environ[settings.IS_NODE_USERNAME_ENV_VAR]
        is_private_key_filepath = os.environ[settings.IS_NODE_PRIVKEY_ENV_VAR]
        instance_name = os.environ[settings.INSTANCE_NAME_ENV_VAR]
        is_dir = os.environ[settings.IS_DIR_ENV_VAR]
        script_path = is_dir / pathlib.Path(f"/instances/{instance_name}/bin/startup.sh")
        ssh = SSHCommand(ssh_host, ssh_port, is_username, pathlib.Path(is_private_key_filepath))
        try:
            ssh.invoke(f"{script_path}")
        except errors.RemoteCommandError as e:  # normal error handling
            log.error(e)
            invoke = False
        except Exception as e:
            log.error(e)
            invoke = False
    except KeyError:
        invoke = False
        log.error("Lack of configuration. Used variables: {} {} {} {} {}"
                  .format(settings.IS_DIR_ENV_VAR,
                          settings.SSH_ADDRESS_ENV_VAR,
                          settings.SSH_PORT_ENV_VAR,
                          settings.IS_NODE_USERNAME_ENV_VAR,
                          settings.IS_NODE_PRIVKEY_ENV_VAR))
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
        username = os.environ[settings.IS_NODE_USERNAME_ENV_VAR]
        keyfile = os.environ[settings.IS_NODE_PRIVKEY_ENV_VAR]
        port = os.environ[settings.SSH_PORT_ENV_VAR]
        ssh = SSHCommand(host, port, username, pathlib.Path(keyfile))
        output = ssh.invoke("ps -ef | grep IS | grep -v grep")
        if not output:
            return True
    except KeyError:
        log.error("There are not a configuration for {} {} {}".format(
            settings.IS_NODE_USERNAME_ENV_VAR,
            settings.IS_NODE_PRIVKEY_ENV_VAR,
            settings.SSH_PORT_ENV_VAR
        ))
    except (Exception, errors.RemoteCommandError) as e:
        log.error(e)
    return False
