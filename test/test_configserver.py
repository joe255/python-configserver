from unittest import IsolatedAsyncioTestCase
from unittest.case import TestCase
from unittest.mock import MagicMock
import configserver
import asyncio


def async_return(result):
    f = asyncio.Future()
    f.set_result(result)
    return f


class ConfigserverTest(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        configserver.getFromGithub = MagicMock(
            return_value=async_return({"https://github.com/github/application-test.yaml": {"asd": "bsd"}, "https://github.com/github/application-dev.yaml": {"query": "string"}}))
        configserver.getFromVault = MagicMock(
            return_value=async_return({"vault:test,test": {"secret": "credentials"}, "vault:test,dev": {"secret": "password"}}))
        configserver.configreader.getConfig = MagicMock(
            return_value={"config": {"vault": "secret", "github": "github"}})
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    async def test_retrieve_config(self):
        value = await configserver.allPara(prefix="config", application="test",
                                           profile="test", label="test", x_config_token="token")
        self.assertEqual(len(value['propertySources']), 2)

    async def test_retrieve_config_less_paras(self):
        value = await configserver.appprofile(prefix="config", application="test",
                                              profile="test", x_config_token="token")
        self.assertEqual(len(value['propertySources']), 2)
        self.assertTrue("https://github.com/github/application-test.yaml" in [
                        propertySource['name'] for propertySource in value['propertySources']])
        self.assertTrue("vault:test,test" in [propertySource['name']
                        for propertySource in value['propertySources']])
        self.assertTrue({"asd": "bsd"} in [propertySource['source'] for propertySource in value['propertySources'] if propertySource['name'] == "https://github.com/github/application-test.yaml"])
        self.assertTrue({"secret": "credentials"} in [propertySource['source'] for propertySource in value['propertySources'] if propertySource['name'] == "vault:test,test"])
        value = await configserver.appprofile(prefix="config", application="test",
                                              profile="dev", x_config_token="token")
        self.assertEqual(len(value['propertySources']), 2)
        self.assertTrue("https://github.com/github/application-dev.yaml" in [
                        propertySource['name'] for propertySource in value['propertySources']])
        self.assertTrue("vault:test,dev" in [propertySource['name']
                        for propertySource in value['propertySources']])
        self.assertTrue({"query": "string"} in [propertySource['source'] for propertySource in value['propertySources'] if propertySource['name'] == "https://github.com/github/application-dev.yaml"])
        self.assertTrue({"secret": "password"} in [propertySource['source'] for propertySource in value['propertySources'] if propertySource['name'] == "vault:test,dev"])
        value = await configserver.appprofile(prefix="config", application="test",
                                              profile="prod", x_config_token="token")
        self.assertEqual(len(value['propertySources']), 0)


class FlattenDict(TestCase):
    def test_flattenMethod(self):
        value = configserver.flatten({"asd": {"bsd": {"csd": {"dsd": "esd"}}}})
        self.assertEqual({"asd.bsd.csd.dsd": "esd"}, value)
