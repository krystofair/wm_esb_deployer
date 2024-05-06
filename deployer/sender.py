"""
Sender module for sending packages to remote servers.
Packages built as zip archive will be sent to inbound directory.
Otherwise, packages will be installed by using IntegrationServer/packages repo
and using is_instance.sh script to copying for specific instance by their name.
"""
import subprocess
from . import settings
from .settings import log


def _send_to_inbound_by_ssh(ssh_host, ssh_port, src_dir, dst_dir):
    """
    Robo
    :param ssh_host:
    :param ssh_port:
    :param src_dir:
    :param dst_dir:
    :return:
    """
    destination_dir = '/app/esb/{}/instances/{instance_name}/replicate/inbound/'
    sent = True
    try:
        args = f'scp -P {ssh_port} {src_dir} {ssh_host}:{dst_dir}'.split(' ')
        result = subprocess.run(args)
    except OSError as e:
        log.exception(e)
        sent = False

    return sent


def send_to_inbound(ref: str = 'HEAD'):
    """
    Send prepared packages in build_{ref} to inbound directory
    per machines in environment.
    :return: True if good, False otherwise.
    """
    # get configuration where to send.

    return None


def send_to_packages_repo():
    path_to_repo = ""
    return None