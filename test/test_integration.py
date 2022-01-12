
import unittest
from unittest.case import TestCase
import subprocess
import os
import time

vaultcommands = [
    "docker exec -it vault vault kv put secret/test foo=world bar=foo",
    "docker exec -it vault vault kv put secret/test,dev foo=world bar=baz",
    "docker exec -it vault vault kv put secret/test,default foo=world2 bar=baz",
    "docker exec -it vault vault kv put secret/application machester=united",
    "docker exec -it vault vault kv put secret/application,dev machester=closed",
    "docker exec -it vault vault secrets enable -path baz -version=2 kv",
    "docker exec -it vault vault kv put baz/test josef=asd",
]

server = {}


def checkForDocker():
    try:
        s = subprocess.check_output('docker ps', shell=True).decode("utf-8")
        return s.find("CONTAINER ID") == -1
    except:
        return True


def checkForMaven():
    try:
        s = subprocess.check_output('mvn -v', shell=True).decode("utf-8")
        return not ("Java version" in s and "Maven home" in s)
    except:
        return True


def spinUp():
    pwd = subprocess.run(["pwd"], capture_output=True).stdout.decode(
        'utf-8').rstrip("\n")
    network = subprocess.run(
        "docker network create test".split(" "), capture_output=True)
    vault = subprocess.run(
        ["docker", "run", "-d", "-p=8200:8200", "-e=VAULT_DEV_ROOT_TOKEN_ID=token", "-e=VAULT_ADDR=http://127.0.0.1:8200", "-e=VAULT_TOKEN=token", "--network=test", "--name=vault", "vault"], capture_output=True)
    configserver = subprocess.run(
        ["docker", "run", "-d", "--name=spring-cloud-config-server", "-p=8888:8888", f"-v={pwd}/springconfig:/config", "-e=LOGGING_LEVEL_WEB=TRACE", "--network=test", "--name=configserver", "hyness/spring-cloud-config-server"], capture_output=True)
    time.sleep(30)
    for command in vaultcommands:
        vaultcmd = subprocess.run(command.split(" "), capture_output=True)
    global server
    server = subprocess.Popen(["uvicorn", "configserver:app"])
    return network.returncode == 0 and vault.returncode == 0 and configserver.returncode == 0 and vaultcmd.returncode == 0


def tearDown():
    print("tearing down")
    vault = subprocess.run(
        "docker container rm vault --force".split(" "), capture_output=True)
    configserver = subprocess.run(
        "docker container rm configserver --force".split(" "), capture_output=True)
    network = subprocess.run(
        "docker network rm test".split(" "), capture_output=True)
    server.terminate()
    return vault.returncode == 0 and network.returncode == 0 and configserver.returncode == 0


class ConfigserverTest(TestCase):
    @unittest.skipIf(checkForDocker(),
                     "docker not found")
    @unittest.skipIf(checkForMaven(),
                     "java and maven not found")
    def test_profile_dev(self):
        try:
            if not spinUp():
                self.fail()
            # run first config client
            my_env = os.environ.copy()
            my_env["SPRING_CONFIG_IMPORT"] = "configserver:http://localhost:8000"
            config1 = subprocess.run(
                ["mvn", "clean", "spring-boot:run", "clean"], cwd="testspring", capture_output=True, env=my_env)
            my_env["SPRING_CONFIG_IMPORT"] = "configserver:http://localhost:8888"
            config2 = subprocess.run(
                ["mvn", "clean", "spring-boot:run", "clean"], cwd="testspring", capture_output=True, env=my_env)
            with open("testspring/8000.log") as c8000, open("testspring/8888.log") as c8888:
                self.assertEqual(c8000.readlines(),
                                 c8888.readlines(), "result was not equals")
        finally:
            tearDown()

    @unittest.skipIf(checkForDocker(),
                     "docker not found")
    @unittest.skipIf(checkForMaven(),
                     "java and maven not found")
    def test_profile_prod(self):
        try:
            if not spinUp():
                self.fail()
            # run first config client
            my_env = os.environ.copy()
            my_env["SPRING_CONFIG_IMPORT"] = "configserver:http://localhost:8000"
            my_env["SPRING_PROFILES_ACTIVE"] = "prod"
            config1 = subprocess.run(
                ["mvn", "clean", "spring-boot:run", "clean"], cwd="testspring", capture_output=True, env=my_env)
            my_env["SPRING_CONFIG_IMPORT"] = "configserver:http://localhost:8888"
            my_env["SPRING_PROFILES_ACTIVE"] = "prod"
            config2 = subprocess.run(
                ["mvn", "clean", "spring-boot:run", "clean"], cwd="testspring", capture_output=True, env=my_env)
            with open("testspring/8000.log") as c8000, open("testspring/8888.log") as c8888:
                self.assertEqual(c8000.readlines(),
                                 c8888.readlines(), "result was not equals")
        finally:
            tearDown()

    @unittest.skipIf(checkForDocker(),
                     "docker not found")
    @unittest.skipIf(checkForMaven(),
                     "java and maven not found")
    def test_profile_dev_label_dev(self):
        try:
            if not spinUp():
                self.fail()
            # run first config client
            my_env = os.environ.copy()
            my_env["SPRING_CONFIG_IMPORT"] = "configserver:http://localhost:8000"
            my_env["SPRING_CLOUD_CONFIG_LABEL"] = "dev"
            config1 = subprocess.run(
                ["mvn", "clean", "spring-boot:run", "clean"], cwd="testspring", capture_output=True, env=my_env)
            my_env["SPRING_CONFIG_IMPORT"] = "configserver:http://localhost:8888"
            config2 = subprocess.run(
                ["mvn", "clean", "spring-boot:run", "clean"], cwd="testspring", capture_output=True, env=my_env)
            with open("testspring/8000.log") as c8000, open("testspring/8888.log") as c8888:
                self.assertEqual(c8000.readlines(),
                                 c8888.readlines(), "result was not equals")
        finally:
            tearDown()
            
    @unittest.skipIf(checkForDocker(),
                     "docker not found")
    @unittest.skipIf(checkForMaven(),
                     "java and maven not found")
    def test_profile_prod_label_dev(self):
        try:
            if not spinUp():
                self.fail()
            # run first config client
            my_env = os.environ.copy()
            my_env["SPRING_CONFIG_IMPORT"] = "configserver:http://localhost:8000"
            my_env["SPRING_CLOUD_CONFIG_LABEL"] = "dev"
            my_env["SPRING_PROFILES_ACTIVE"] = "prod"
            config1 = subprocess.run(
                ["mvn", "clean", "spring-boot:run", "clean"], cwd="testspring", capture_output=True, env=my_env)
            my_env["SPRING_CONFIG_IMPORT"] = "configserver:http://localhost:8888"
            config2 = subprocess.run(
                ["mvn", "clean", "spring-boot:run", "clean"], cwd="testspring", capture_output=True, env=my_env)
            with open("testspring/8000.log") as c8000, open("testspring/8888.log") as c8888:
                self.assertEqual(c8000.readlines(),
                                 c8888.readlines(), "result was not equals")
        finally:
            tearDown()

    @unittest.skipIf(checkForDocker(),
                     "docker not found")
    @unittest.skipIf(checkForMaven(),
                     "java and maven not found")
    def test_profile_prod_label_dev(self):
        try:
            if not spinUp():
                self.fail()
            # run first config client
            my_env = os.environ.copy()
            my_env["SPRING_CONFIG_IMPORT"] = "configserver:http://localhost:8000"
            my_env["SPRING_PROFILES_ACTIVE"] = "prod"
            my_env["SPRING_CLOUD_CONFIG_LABEL"] = "dev"
            config1 = subprocess.run(
                ["mvn", "clean", "spring-boot:run", "clean"], cwd="testspring", capture_output=True, env=my_env)
            my_env["SPRING_CONFIG_IMPORT"] = "configserver:http://localhost:8888"
            my_env["SPRING_PROFILES_ACTIVE"] = "prod"
            config2 = subprocess.run(
                ["mvn", "clean", "spring-boot:run", "clean"], cwd="testspring", capture_output=True, env=my_env)
            with open("testspring/8000.log") as c8000, open("testspring/8888.log") as c8888:
                self.assertEqual(c8000.readlines(),
                                 c8888.readlines(), "result was not equals")
        finally:
            tearDown()
