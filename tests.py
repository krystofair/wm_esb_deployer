import os
import unittest
import shutil

import errors
import config
import build
import main

import pytest

import settings


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
        os.makedirs('./config.d/test', exist_ok=True)
        os.makedirs('./config.d/prod', exist_ok=True)
        _load_config_content("./config.d/prod/init.cfg")
        _load_config_content("./config.d/test/init.cfg")
        with open('./config.d/test/server2.cfg', 'w') as specific_change_cfg:
            specific_change_cfg.write("USERNAME = klapykrz_changed")
        settings.CONFIG_DIR_ENV_VAR = 'CONFIG_DIR'
        os.environ['CONFIG_DIR'] = 'config.d'

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
        os.remove('./config.d/prod/init.cfg')
        result = config.load_configuration('prod')
        self.assertFalse(result)

    def test_raise_exception_in_load_config(self):
        os.remove('./config.d/prod/init.cfg')
        with pytest.raises(errors.LoadingConfigurationError):
            config.load_config('prod', '')


class BuildingPackage(unittest.TestCase):
    def test_making_package_zip_archive(self):
        build.clean_directory_for_new_build()
        result = build.build_package('TpOssAdapterDms')
        self.assertTrue(result)


class ConfigAndBuildTC(unittest.TestCase):
    def setUp(self) -> None:
        os.makedirs('./config.d/testing', exist_ok=True)
        _load_config_content("./config.d/testing/init.cfg")
        with open('./config.d/testing/server2.cfg', 'w') as specific_change_cfg:
            specific_change_cfg.write("USERNAME=klapykrz_changed")
            specific_change_cfg.write("\nCI_REPO_DIR=repository")
        os.environ['CONFIG_DIR'] = './config.d'

    def tearDown(self):
        shutil.rmtree('./config.d')

    def test_set_CI_REPO_DIR_and_use_it_in_making_packages(self):
        config.load_configuration('testing', 'server2')
        build.clean_directory_for_new_build()
        result = build.build_package('TpOssAdapterDms')
        self.assertTrue(result, "TpOssAdapterDms.zip not created.")


class TestMainRun(unittest.TestCase):
    def test_parsing_arguments(self):
        opts = main.build_arguments([
            "inbound",
            "--package",
            "TpOssAdministrativeTools",
            "CaOssMock",
            "TpOssDocument"
        ])
        self.assertListEqual(opts.package, ["TpOssAdministrativeTools", "CaOssMock", "TpOssDocument"])
        self.assertTrue(opts.changes_only)
        self.assertEqual(opts.action, "inbound")


class TestBuild(unittest.TestCase):
    def test_extract_svc_name(self):
        diff_line = "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/updateCFService/flow.xml"
        service_name = build.extract_service_name(diff_line)
        self.assertEqual(service_name, "tp.oss.channel.jazz.order.pub:updateCFService")

    def test_ignoring_namespace(self):
        build.clean_directory_for_new_build()
        shutil.copytree('repository/packages/TpOssAdapterDms', 'build_test0123/TpOssAdapterDms',
                        ignore=shutil.ignore_patterns("ns"))
        try:
            with open('build_test0123/TpOssAdapterDms/manifest.v3', 'r'):
                pass
        except FileNotFoundError:
            self.fail("File should exist.")
        try:
            with open('build_test0123/TpOssAdapterDms/ns/tp/node.idf', 'r'):
                self.fail("File should not exist.")
        except FileNotFoundError:
            pass

    def test_is_package_to_exclude(self):
        self.assertTrue(build.is_package_to_exclude('TpOssConfig'))
        self.assertTrue(build.is_package_to_exclude('TpOssAdministrativeTools'))
        self.assertTrue(build.is_package_to_exclude('TpOssConnectorChannelAtrium'))
        self.assertFalse(build.is_package_to_exclude('TpOssConnectorAtrium'))
        self.assertFalse(build.is_package_to_exclude('TpOssChannelNgnp'))

    def test_only_changes_service_copy(self):
        build.clean_directory_for_new_build()
        build.prepare_package_only_changes_services_from_last_commit()
