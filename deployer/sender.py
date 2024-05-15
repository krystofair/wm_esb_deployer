"""
Sender module for sending packages to remote servers.
Packages built as zip archive will be sent to inbound directory.
Otherwise, packages will be installed by using IntegrationServer/packages repo
and using is_instance.sh script to copying for specific instance by their name.
"""
import os
import pathlib
import subprocess
import dataclasses as dc

from . import settings, config
from .settings import log


@dc.dataclass
class SCPCommand:
    ip: str
    port: str
    username: str
    private_key_filename: pathlib.Path

    def send_files(self, from_dir, to_dir) -> bool:
        """
        Sending files like i.e. *.zip.
        :param from_dir: where the files are located,
        :param to_dir: absolute path for remote directory or relative from authorized user.
        :return: True if all good, False otherwise.
        """
        str_files = ' '.join([e.path for e in os.scandir(from_dir) if e.is_file()])
        args = f"scp -p -i {self.private_key_filename} -P {self.port} {str_files} {self.username}@{self.ip}:{to_dir}/"
        command_args = args.split(' ')
        sent = True
        try:
            process_completed = subprocess.run(command_args, timeout=settings.SUBPROCESS_CMD_TIMEOUT)
            if process_completed.returncode != 0:
                self.error_handling_hook(process_completed)
                sent = False
        except OSError as e:
            log.error(e)
            sent = False
        except subprocess.SubprocessError as e:
            log.error(e)
            sent = False
        except Exception as e:
            log.exception(e)
            sent = False
        return sent

    def send_dir(self, name, to_dir) -> bool:
        """
        Send dir in recursive style.
        :param name: folder to send,
        :param to_dir: when that folder should be placed.
        :return: True if sent, False otherwise.
        """
        args = f"scp -p -i {self.private_key_filename} -P {self.port} -r {name} {self.username}@{self.ip}:{to_dir}/"
        command_args = args.split(' ')
        sent = True
        try:
            process_completed = subprocess.run(command_args, timeout=settings.SUBPROCESS_CMD_TIMEOUT)
            if process_completed.returncode != 0:
                self.error_handling_hook(process_completed)
                sent = False
        except OSError as e:
            log.error(e)
            sent = False
        except subprocess.SubprocessError as e:
            log.error(e)
            sent = False
        except Exception as e:
            log.exception(e)
            sent = False
        return sent

    def error_handling_hook(self, pc):
        log.info(pc.stdout)
        log.error(pc.stderr)
        log.info(self)


def send_to_inbound(ref: str, host: str) -> bool:
    """
    For now this used `scp` command to send ZIP-s.
    :param: ref Commit from which Directory of current build will be named.
    :return: True if sending process goes well, otherwise, False.
    """
    sent = True
    try:
        dst_dir = os.environ[settings.INBOUND_DIR_ENV_VAR]
        ssh_host = host
        ssh_port = os.environ[settings.SSH_PORT_ENV_VAR]
        is_username = os.environ[settings.IS_NODE_USERNAME_ENV_VAR]
        is_private_key_filepath = os.environ[settings.IS_NODE_PRIVKEY_ENV_VAR]
        scp = SCPCommand(ssh_host, ssh_port, is_username, pathlib.Path(is_private_key_filepath))
        src_dir = config.get_build_dir(ref)
        if not scp.send_files(src_dir, dst_dir):
            sent = False
    except KeyError:
        sent = False
        log.error("Lack of configuration for inbound folder. Used variables: {} {} {} {}"
                  .format(settings.INBOUND_DIR_ENV_VAR,
                          settings.SSH_ADDRESS_ENV_VAR,
                          settings.SSH_PORT_ENV_VAR,
                          settings.IS_NODE_USERNAME_ENV_VAR,
                          settings.IS_NODE_PRIVKEY_ENV_VAR))
    return sent

def send_to_packages_repo():
    path_to_repo = ""
    return None