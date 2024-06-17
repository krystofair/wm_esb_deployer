import os
import pathlib
import unittest
import shutil
import subprocess

from deployer import *

import pytest


def _load_config_content(filename):
    lines = list(map(str.strip, """
    HOST=192.168.56.100
    SSH_PORT=2222
    LISTENER_PORT=5555
    USERNAME=krzysztof
    PHONE=732132222
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
            specific_change_cfg.write("USERNAME = krzysztof2")
        settings.CONFIG_DIR_ENV_VAR = 'CONFIG_DIR'
        os.environ['CONFIG_DIR'] = 'config.d'

    def tearDown(self):
        shutil.rmtree('./config.d')

    def test_variables_are_properly_loaded_for_prod_env(self):
        result = config.load_configuration('prod')
        self.assertTrue(result)
        self.assertEqual(os.environ['HOST'], '192.168.56.100')

    def test_variables_are_properly_loaded_for_specific(self):
        result = config.load_configuration('test')
        self.assertTrue(result)
        result = config.load_node_configuration('test', 'server2')
        self.assertTrue(result)
        self.assertEqual(os.environ['HOST'], '192.168.56.100')
        self.assertEqual(os.environ['USERNAME'], 'krzysztof2')

    def test_errors_from_loading_configuration(self):
        os.remove('./config.d/prod/init.cfg')
        result = config.load_configuration('prod')
        self.assertFalse(result)

    def test_raise_exception_in_load_config(self):
        os.remove('./config.d/prod/init.cfg')
        with pytest.raises(errors.LoadingConfigurationError):
            config.load_config('prod', '')

    def test_find_node_configs(self):
        configs = config.find_node_configs('test')
        self.assertIn("server2.cfg", configs)

    def test_remove_configuration(self):
        test_config_dir = config.get_config_dir('test')
        prod_config_dir = config.get_config_dir('prod')
        config.clear_configuration_for_environment('test')
        config.clear_configuration_for_environment('prod')
        with pytest.raises(FileNotFoundError):
            _ = [e.path for e in os.scandir(test_config_dir)]
        with pytest.raises(FileNotFoundError):
            _ = [e.path for e in os.scandir(prod_config_dir)]


class BuildingPackage(unittest.TestCase):
    def test_making_package_zip_archive(self):
        self.skipTest("write new")
        # build.clean_directory_after_deploy()
        # result = build.build_package_for_inbound('TpOssAdapterDms')
        # self.assertTrue(result)


class ConfigAndBuildTC(unittest.TestCase):
    def setUp(self) -> None:
        os.makedirs('./config.d/testing', exist_ok=True)
        _load_config_content("./config.d/testing/init.cfg")
        with open('./config.d/testing/server2.cfg', 'w') as specific_change_cfg:
            specific_change_cfg.write("USERNAME=krzysztof4")
            specific_change_cfg.write("\nCI_REPO_DIR=repository")
        os.environ['CONFIG_DIR'] = './config.d'

    def tearDown(self):
        shutil.rmtree('./config.d')

    def test_set_CI_REPO_DIR_and_use_it_in_making_packages(self):
        ref = 'TEST'
        config.load_configuration('testing')
        config.load_node_configuration('testing', 'server2')
        result = build.build_package_for_inbound('TpOssAdapterDms', ref)
        self.assertTrue(result, "TpOssAdapterDms.zip not created.")
        # configuration change
        os.environ["CI_PROJECT_DIR"] = 'sprawdzam'
        config.load_configuration('testing')
        config.load_node_configuration('testing', 'server2')
        result = build.build_package_for_inbound('TpOssAdapterDms', ref)
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
        self.assertTrue(opts.no_changes_only)
        self.assertEqual(opts.action, "inbound")

    def test_action_build_linking(self):
        # configure.
        self.skipTest("OSError: [WinError 1314] Klient nie ma wymaganych uprawnień: 'packages\\TpOssAdapterDms' -> './build_LINK'")
        os.environ[settings.PIPELINE_REFERENCE] = 'LINK'
        main.action_build(False, False)
        links = [e.name for e in os.scandir("build_LINK") if e.is_symlink()]
        self.assertIn("TpOssAdapterDms", links)

    def test_action_build_inbound(self):
        os.environ[settings.CI_PROJECT_DIR] = '.'  # must be because
        os.environ[settings.PIPELINE_REFERENCE] = 'inbound'
        main.action_build(True, False)
        zips = [e.name for e in os.scandir("build_inbound") if e.is_file() and e.name.endswith('.zip')]
        self.assertIn("TpOssAdapterDms.zip", zips)
        shutil.rmtree("build_inbound")

    def test_action_build_not_inbound_changes_only(self):
        """
        After this test there should be prepared packages as normal (not zip) dirs.
        And this packages MUST contain only changed services.
        """
        os.environ[settings.PIPELINE_REFERENCE] = "NO_INBOUND_CHANGES_ONLY"
        os.environ[settings.CI_MERGE_REQUEST_TARGET_BRANCH_NAME] = "CO"
        ref = os.environ[settings.PIPELINE_REFERENCE]
        main.action_build(False, True)
        build_dir = config.get_build_dir(ref)
        self.assertTrue(os.path.exists(
            build_dir / pathlib.Path("TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processUpdateCFServiceRequest/flow.xml"))
        )
        self.assertTrue(not os.path.exists(
            build_dir / pathlib.Path(
                "TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processUpdateCFServiceResponse/flow.xml"))
        )
        cmd_args = (
            f"diff packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processUpdateCFServiceRequest/flow.xml"
            f" {build_dir}/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/priv/processUpdateCFServiceRequest/flow.xml"
        ).split(' ')
        process = subprocess.run(cmd_args, capture_output=True, encoding='utf-8')
        self.assertEqual(process.stdout.strip(), "")
        self.assertEqual(process.stderr.strip(), "")
        shutil.rmtree("build_NO_INBOUND_CHANGES_ONLY")


class TestBuild(unittest.TestCase):
    def test_extract_svc_name(self):
        diff_line = "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/updateCFService/flow.xml"
        service_name = build.extract_is_style_service_name(diff_line)
        self.assertEqual(service_name, "tp.oss.channel.jazz.order.pub:updateCFService")

    def test_get_services_from_changes(self):
        # TODO: test more cases for this node.ndf etc. and finally implement some more sophisticated.
        diff_line = ["packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/updateWorkOrder/something.frag",
                     "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/updateCFService/flow.xml",
                     "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/updateCFService/node.ndf"
                     "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/node.idf",
                     "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/utils/node.ndf"]
        service_set = build.get_services_from_changes(diff_line)  # get first element from set.
        self.assertIn("packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/updateWorkOrder", service_set)
        self.assertIn("packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/updateCFService", service_set)
        self.assertIn("packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/utils", service_set)
        self.assertNotIn("packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub", service_set)

    def test_build_packages_for_is_instance(self):
        diff_line = ["packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/priv/translateCommonErrors/flow.xml",
                     "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/priv/translateCommonErrors/node.ndf",
                     "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/updateCFService/flow.xml",
                     "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/updateCFService/node.ndf",
                     "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/node.idf",
                     "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/service/pub/handleModifyCFServiceDunningStatusResult/node.ndf",
                     "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/service/pub/handleModifyCFServiceDunningStatusResult/flow.xml"]
        service_set = build.get_services_from_changes(diff_line)  # get first element from set.
        package_set = build.get_packages_from_changes(diff_line)
        build.build_packages_for_is_instance("TEST_IS_INSTANCE_BUILD", package_set, service_set)

    def test_get_packages_from_changes(self):
        # TODO: more tests!
        packages = build.get_packages_from_changes([
            "packages/TpOssChannelJazz/ns/tp/oss/channel/jazz/order/pub/updateCFService/flow.xml",
            "packages/TpOssConnectorChannelJazz/ns/tp/oss/channel/jazz/order/pub/updateCFService/flow.xml"
        ])
        self.assertIn("TpOssChannelJazz", packages)
        self.assertNotIn("TpOssConnectorChannelJazz", packages)

    def test_build_empty_package(self):
        build.create_empty_package("TpOssChannelJazz", "build_EMPTY")
        self.assertFalse(os.path.exists("build_EMPTY/TpOssChannelJazz/ns"))
        shutil.rmtree("build_EMPTY")

    def test_is_package_to_exclude(self):
        self.assertTrue(build.is_package_to_exclude('TpOssConfig'))
        self.assertTrue(build.is_package_to_exclude('TpOssAdministrativeTools'))
        self.assertTrue(build.is_package_to_exclude('TpOssConnectorChannelAtrium'))
        self.assertFalse(build.is_package_to_exclude('TpOssConnectorAtrium'))
        self.assertFalse(build.is_package_to_exclude('TpOssChannelNgnp'))

    def test_is_package_default(self):
        self.assertTrue(build.is_default_package("WmPublic"))
        self.assertFalse(build.is_default_package("TpOssCommonTools"))
        self.assertTrue(build.is_default_package("Default"))

    def test_only_changes_service_copy(self):
        self.skipTest("write new")
        # build.clean_directory_after_deploy()
        # build.prepare_package_only_changes_services_from_last_commit()

    def test_add_file_cicd_version_to_service(self):
        os.makedirs("./sprawdzam/", exist_ok=True)
        os.makedirs("./sprawdzam2/", exist_ok=True)
        build.add_file_cicd_version_to_path("./sprawdzam/")
        os.environ[settings.CI_PROJECT_NAME] = 'esboss'
        os.environ[settings.CI_COMMIT_SHA] = '374ffa03de'
        build.add_file_cicd_version_to_path("./sprawdzam2/")
        # delete this test folders ;)


class TestSender(unittest.TestCase):
    def setUp(self) -> None:
        os.environ[settings.SSH_PORT_ENV_VAR] = '22'
        os.environ[settings.SSH_ADDRESS_ENV_VAR] = '192.168.56.109'
        os.environ[settings.IS_NODE_USERNAME_ENV_VAR] = "admin"
        os.environ[settings.IS_NODE_PRIVKEY_ENV_VAR] = "./admin.privkey"
        os.environ[settings.INBOUND_DIR_ENV_VAR] = ""
        # os.mkdir('./build_TEST')

    def tearDown(self) -> None:
        os.unsetenv(settings.SSH_PORT_ENV_VAR)
        os.unsetenv(settings.SSH_ADDRESS_ENV_VAR)
        os.unsetenv(settings.IS_NODE_USERNAME_ENV_VAR)
        os.unsetenv(settings.IS_NODE_PRIVKEY_ENV_VAR)
        # shutil.rmtree("build_TEST")

    def test_sending_to_remote_directory(self):
        self.skipTest("Take me too long time when trying with key authentication in Windows."
                      "Probably Linux will operate normally with that.") # in gitlab-runner sending works!
        os.environ[settings.INBOUND_DIR_ENV_VAR] = "/home/admin/packages"
        self.assertTrue(sender.send_to_inbound("TEST", "192.168.56.109"))
        os.environ[settings.INBOUND_DIR_ENV_VAR] = ""
        self.assertTrue(sender.send_to_inbound("TEST", "192.168.56.109"))


class TestRemoteCommand(unittest.TestCase):
    def test_simple_ls(self):
        self.skipTest("Loooong for do simple command")
        ssh = remoter.SSHCommand("192.168.56.109", "22", "admin", pathlib.Path("./.ssh/admin.privkey2"))
        try:
            output = ssh.invoke("ls /home/admin")
            self.assertTrue("runner_rsa" in output)
        except errors.RemoteCommandError as e:
            output = str(e)
            self.fail(output)

    def test_connection(self):
        settings.CHECK_CONNECTION_TIMEOUT = 2
        self.assertTrue(remoter.check_start_status("192.168.56.109", "22"))
        self.assertFalse(remoter.check_start_status("192.168.56.109"))  # default port 5555 not open in my VM

    def test_check_stop_status(self):
        self.skipTest("On local virtual machine does not have IS instance.")
        remoter.check_stop_status('192.168.56.109')


class TestSigner(unittest.TestCase):
    HOST = '192.168.56.203'

    def setUp(self) -> None:
        os.mkdir('build_SIGNER')
        self.bd = config.get_build_dir('SIGNER')

    def tearDown(self) -> None:
        shutil.rmtree('build_SIGNER')

    def test_no_stamp_file_yet(self):
        hosts = build.Signer.get_hosts(self.bd)
        self.assertTrue(not hosts)
        self.assertEqual(type(hosts), list)

    def test_host_already_get(self):
        # dependency test - there is a better way to do it
        self.test_write_stamp_and_add_hosts()
        build_dir = config.get_build_dir("SIGNER")
        hosts = build.Signer.get_hosts(build_dir)
        self.assertIn(TestSigner.HOST, hosts)

    def test_write_stamp_and_add_hosts(self):
        os.environ[settings.CI_COMMIT_TAG] = 'TEST_TAG'
        s = build.Signer()
        s.add_host_to_stamp(TestSigner.HOST)
        s.write_stamp(self.bd)
        self.assertTrue(os.path.exists(f"{self.bd}/cicd_version.json"))
        stamp = s.read_stamp(self.bd)
        self.assertEqual(stamp['project'], '-')
        self.assertEqual(stamp['tag name'], 'TEST_TAG')

    def test_add_another_hosts_to_stamp(self):
        self.test_write_stamp_and_add_hosts()
        s = build.Signer.read_stamp(self.bd)
        signer = build.Signer(s)
        signer.add_host_to_stamp("10.0.0.1")
        signer.write_stamp(self.bd) # write stamp where already is.
        self.assertIn("10.0.0.1", build.Signer.get_hosts(self.bd))
