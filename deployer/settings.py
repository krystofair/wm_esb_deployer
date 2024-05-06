"""
Settings contains names for environment variables which are used in code.
This is one place entry point for set up where deployer to search configs etc.
"""
# set logger globally
import logging
logging.basicConfig(level=logging.INFO, format="%(created)f |%(levelname)s| %(module)s %(lineno)d %(message)s -_-")
log = logging.getLogger()

mock = True  # helping flag to using mocks.

# if script is running from another context, otherwise it will be current directory (.)

###### configuration
"""
Load by searching init.cfg and %name%.cfg files, then load key=value pairs to environment.
Lines which starts with '#' are treates as comments.
example:
    %CONFIG_DIR%
      + /%CI_ENVIRONMENT_NAME%
        - init.cfg  # general configuration for environment
        - node001.cfg  # custom config for node001
      + /test
        - init.cfg

variables which should be loaded for node or per environments in config files.

settings only determine that name in `'` will be search in Environment Variables after
loads configuration. So dont thing that names on the left side of the '=' sign
is meaningful in `*.cfg` files.
"""
CONFIG_DIR_ENV_VAR = 'CONFIG_DIR'
INBOUND_DIR_ENV_VAR = 'INBOUND_DIR'
SSH_ADDRESS_ENV_VAR = 'SSH_ADDRESS'
SSH_PORT_ENV_VAR = 'SSH_PORT'
IS_NODE_USERNAME_ENV_VAR = 'IS_NODE_USERNAME'
IS_INSTANCE_PATH_ENV_VAR = 'IS_INSTANCE_PATH'
IS_PACKAGE_REPO_PATH_ENV_VAR = 'IS_PACKAGE_REPO_DIR_PATH'
# how to find special node config name in environment.
NODE_ENV_VAR = "NODE_NAME"
# Environment - set below from gitlab pipeline.
# Git tag name - set from gitlab pipeline
# gitlab_user? - needed?
REPO_DIR_ENV_VAR = 'REPO_DIR'  # not required.

# gitlab predefined variables used.
CI_ENVIRONMENT_NAME = 'CI_ENVIRONMENT_NAME'
CI_COMMIT_SHA = 'CI_COMMIT_SHA'
CI_COMMIT_TAG = 'CI_COMMIT_TAG'
CI_PROJECT_NAME = 'CI_PROJECT_NAME'

# where to find sources
SRC_DIR = 'packages'  # directory which contains a code, like /src/ in Java
BUILD_DIR = 'build_{}'


PACKAGES_TO_EXCLUDE = ["TpOssAdministrativeTools", "TpOssConfig", "TpOssConnectorChannel*"]


