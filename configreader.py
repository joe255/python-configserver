import yaml
readconfig = {}
default_repo = "joe255/testconfig-repo"
vaultaddress = "http://locahost:8200"

def init(configfile='configserver.yaml'):
    # read config from file
    try:
        with open(configfile) as file:
            # The FullLoader parameter handles the conversion from YAML
            # scalar values to Python the dictionary format
            config = yaml.load(file, Loader=yaml.FullLoader)
            for entry in config['config']:
                readconfig[entry['prefix']] = {
                    "github": entry['github'], "vault": entry['vault']}
            global vaultaddress
            vaultaddress = config['vault']
    except Exception as e:
        print(e)
    if not "default" in readconfig:
        raise FileNotFoundError(
            "Was not able to load configuration from configserver.yaml")


def getConfig():
    return readconfig
def getVaultAddress():
    return vaultaddress

def setConfig(conf):
    readconfig = conf
