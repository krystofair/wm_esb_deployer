import argparse
import shutil
import pathlib
import os
import subprocess

SRC_DIR = 'packages'  # directory which contains a code, like /src/ in Java

def build_package(name: str, ref: str = 'HEAD') -> bool:
    """
    Building ZIP from package and left it in working dir.
    :param name: name of package
    :param ref: name of GIT commit
    :return: True if builded, False otherwise
    """
    cwd = os.curdir
    os.mkdir(f"build_{ref}")
    # o1s.chdir(SRC_DIR)
    # In short git can create archive from it's ref name, but it will be from whole files
    arguments = f"git archive --format=zip -o build_{ref}.zip {ref}".split(' ')
    subprocess.run()





    shutil.make_archive(f"{name}", 'zip', f'{SRC_DIR}/{name}', )
