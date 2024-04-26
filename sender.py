"""
Sender module for sending packages to remote servers.
Packages built as zip archive will be sent to inbound directory.
Otherwise, packages will be installed by using IntegrationServer/packages repo
and using is_instance.sh script to copying for specific instance by their name.
"""
import subprocess
import settings
from settings import log


def _send_to_inbound_by_ssh(ssh_host, ssh_port, src_dir, dst_dir):
    """
    Robo
    :param ssh_host:
    :param ssh_port:
    :param src_dir:
    :param dst_dir:
    :return:
    """
    sent = True
    try:
        args = f'scp -P {ssh_port} {src_dir} {ssh_host}:{dst_dir}'.split(' ')
        result = subprocess.run(args)
    except OSError as e:
        log.exception(e)
        sent = False

    return sent

