"""
Settings contains names for environment variables which are used in code.
This is one place entry point for set up where deployer to search configs etc.
"""
# set logger globally
import logging
logging.basicConfig(level=logging.INFO, format="%(created)f |%(levelname)s| %(name)s %(lineno)d %(message)s -_-")
log = logging.getLogger(__name__)

mock = True  # helping flag to using mocks.

# if script is running from another context, otherwise it will be current directory (.)
REPO_DIR_ENV_VAR = 'REPO_DIR'

# where to find sources
SRC_DIR = 'packages'  # directory which contains a code, like /src/ in Java

# configuration
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
"""
CONFIG_DIR_ENV_VAR = 'CONFIG_DIR'

# gitlab predefined variables used.
CI_ENVIRONMENT_NAME = 'CI_ENVIRONMENT_NAME'
CI_COMMIT_SHA = 'CI_COMMIT_SHA'
CI_COMMIT_TAG = 'CI_COMMIT_TAG'
CI_PROJECT_NAME = 'CI_PROJECT_NAME'

PACKAGES_TO_EXCLUDE = ["TpOssAdministrativeTools", "TpOssConfig", "TpOssConnectorChannel*"]

# how to find special node config name in environment.
NODE_ENV_VAR = "NODE_NAME"
