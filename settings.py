"""
Settings contains names for environment variables which are used in code.
This is one place entry point for set up where deployer to search configs etc.
"""

# if script is running from another context, otherwise it will be current directory (.)
REPO_DIR_ENV_VAR = 'REPO_DIR'

# where to find sources
SRC_DIR = 'repository/packages'  # directory which contains a code, like /src/ in Java

# configuration
"""
Load by searching init.cfg and %name%.cfg files, then load key=value pairs to environment.
Lines which starts with '#' are treates as comments.
example:
    %CONFIG_DIR%
      + /prod
        - init.cfg  # general configuration for environment
        - node001.cfg  # custom config for node001
      + /test
        - init.cfg
"""
CONFIG_DIR_ENV_VAR = 'CONFIG_DIR'