"""
Settings contains names for environment variables which are used in code.
This is one place entry point for set up where deployer to search configs etc.
"""
# set logger globally
import logging
logging.basicConfig(level=logging.INFO, format="%(created)f |%(levelname)s| %(module)s %(lineno)d %(message)s -_-")
log = logging.getLogger()

mock = False  # helping flag to using mocks.

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
# name of variable from what create builds directories aka build_$VARIABLE
PIPELINE_REFERENCE = "CI_MERGE_REQUEST_IID"
ZONE = "ZONE"  # support for zones.
BUILD_DIR_ENV_VAR = 'BUILD_DIR'  # repository where archives are created.
CONFIG_DIR_ENV_VAR = 'CONFIG_DIR'
# variables to use in configuration of environments
INBOUND_DIR_ENV_VAR = 'INBOUND_DIR'
SSH_ADDRESS_ENV_VAR = 'SSH_ADDRESS'
SSH_PORT_ENV_VAR = 'SSH_PORT'
IS_NODE_USERNAME_ENV_VAR = 'IS_NODE_USERNAME'
IS_NODE_PRIVKEY_ENV_VAR = 'IS_NODE_PRIVKEY'
IS_INSTANCE_PATH_ENV_VAR = 'IS_INSTANCE_PATH'
IS_PACKAGE_REPO_PATH_ENV_VAR = 'IS_PACKAGE_REPO_DIR_PATH'
NODES_ENV_VAR = "NODES"  # IPv4 separated by comma (,) - hosts where to send files
# Environment - set below from gitlab pipeline.
# Git tag name - set from gitlab pipeline
# gitlab_user? - needed?
REPO_DIR_ENV_VAR = 'REPO_DIR'  # not required.

# gitlab predefined variables used.
CI_ENVIRONMENT_NAME = 'CI_ENVIRONMENT_NAME'
CI_COMMIT_SHA = 'CI_COMMIT_SHA'
CI_COMMIT_TAG = 'CI_COMMIT_TAG'
CI_PROJECT_NAME = 'CI_PROJECT_NAME'
CI_PROJECT_DIR = "CI_PROJECT_DIR"  # default folder for builds when no set BUILD_DIR_ENV_VAR
CI_MERGE_REQUEST_SOURCE_BRANCH_SHA = "CI_MERGE_REQUEST_SOURCE_BRANCH_SHA"  # for create tag for latest version at env.
CI_MERGE_REQUEST_TARGET_BRANCH_NAME = "CI_MERGE_REQUEST_TARGET_BRANCH_NAME"  # for git diff.

# where to find sources
SRC_DIR = 'packages'  # directory which contains a code, like /src/ in Java
SOURCE_CODE_EXT = ("xml", "java", "frag", "ndf")  # edit this if something missing
SUBPROCESS_CMD_TIMEOUT = 90  # timeout in seconds.

PACKAGES_TO_EXCLUDE = ["TpOssAdministrativeTools", "TpOssConfig", "TpOssConnectorChannel*"]
