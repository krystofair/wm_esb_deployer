import os
import unittest
import shutil

import errors
import config

import pytest


def _load_config_content(filename):
    lines = list(map(str.strip, """
    HOST=192.168.56.100
    SSH_PORT=2222
    LISTENER_PORT=5555
    USERNAME=klapykrz
    PHONE=732132227
    """.split('\n')))
    with open(filename, 'w') as configfile:
        for line in lines:
            print(line, file=configfile)


class LoadingConfigurationTest(unittest.TestCase):

    def setUp(self) -> None:
        os.makedirs('./config.d/TEST', exist_ok=True)
        os.makedirs('./config.d/PROD', exist_ok=True)
        _load_config_content("./config.d/PROD/init.sh")
        _load_config_content("./config.d/TEST/init.sh")
        with open('./config.d/TEST/server2.sh', 'w') as specific_change_cfg:
            specific_change_cfg.write("USERNAME=klapykrz_changed")
        os.environ['CONFIG_DIR'] = './config.d'

    def tearDown(self):
        shutil.rmtree('./config.d')

    def test_variables_are_properly_loaded_for_prod_env(self):
        result = config.load_configuration('prod')
        self.assertTrue(result)
        self.assertEqual(os.environ['HOST'], '192.168.56.100')

    def test_variables_are_properly_loaded_for_specific(self):
        result = config.load_configuration('test', 'server2')
        self.assertTrue(result)
        self.assertEqual(os.environ['HOST'], '192.168.56.100')
        self.assertEqual(os.environ['USERNAME'], 'klapykrz_changed')

    def test_errors_from_loading_configuration(self):
        os.remove('./config.d/PROD/init.sh')
        result = config.load_configuration('prod')
        self.assertFalse(result)

    def test_raise_exception_in_load_config(self):
        os.remove('./config.d/PROD/init.sh')
        with pytest.raises(errors.LoadingConfigurationError):
            config.load_config('prod', '')
