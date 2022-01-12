from typing import Optional
from fastapi import FastAPI, Header, Response
from github import Github
import github
import hvac
import os
import yaml
from collections.abc import MutableMapping
import configreader
import sys
import getopt

synopsis = "configserver.py -c <configfile>"
githubtoken = (
    "REPLACE FOR LOCAL TESTING"
    if not "GITHUB_TOKEN" in os.environ
    else os.environ["GITHUB_TOKEN"]
)
g = Github(login_or_token=githubtoken)
fileendings = ["yaml", "yml", "properties"]


def main(argv):
    configfile = (
        "configserver.yaml"
        if not "CONFIGFILE" in os.environ
        else os.environ["CONFIGFILE"]
    )
    configreader.init(configfile=configfile)


if __name__ == "__main__" or __name__ == "configserver":
    main(sys.argv[1:])
app = FastAPI()


@app.get("/{application}/{profile}/{label}")
async def allPara(
    application: str,
    profile: str,
    label: str,
    prefix: Optional[str] = Header("default"),
    x_config_token: Optional[str] = Header(None),
):
    results = await combine(
        applications=[application, "application"],
        profiles=profile.split(","),
        labels=label.split(","),
        x_config_token=x_config_token,
        github=configreader.getConfig()[prefix]["github"],
        vault=configreader.getConfig()[prefix]["vault"],
    )
    return {
        "name": application,
        "profiles": profile.split(","),
        "label": label,
        "version": None,
        "state": None,
        "propertySources": results,
    }


@app.get("/{application}/{profile}")
async def appprofile(
    application: str,
    profile: str,
    prefix: Optional[str] = Header("default"),
    x_config_token: Optional[str] = Header(None),
):
    results = await combine(
        applications=[application, "application"],
        profiles=profile.split(","),
        labels=["main"],
        x_config_token=x_config_token,
        github=configreader.getConfig()[prefix]["github"],
        vault=configreader.getConfig()[prefix]["vault"],
    )
    return {
        "name": application,
        "profiles": profile.split(","),
        "label": "main",
        "version": None,
        "state": None,
        "propertySources": results,
    }


@app.get("/{application}-{profile}.{fileending}")
async def appprofile_file(
    application: str,
    profile: str,
    fileending: str,
    prefix: Optional[str] = Header("default"),
    x_config_token: Optional[str] = Header(None),
):
    results = await combine(
        applications=[application, "application"],
        profiles=profile.split(","),
        labels=["main"],
        x_config_token=x_config_token,
        github=configreader.getConfig()[prefix]["github"],
        vault=configreader.getConfig()[prefix]["vault"],
    )
    if fileending == "properties":
        # content = [f"{key}={value} ({res['name']})" for res in results for key, value in res['source'].items()]
        content = {
            key: value
            for res in reversed(results)
            for key, value in res["source"].items()
        }
        c = [f"{key}={value}" for key, value in content.items()]
        return Response(content="\n".join(c), media_type="application/text")
    elif fileending == "yml" or fileending == "yaml":
        c = {
            key: value
            for res in reversed(results)
            for key, value in res["source"].items()
        }
        return Response(
            content=yaml.dump(generateWideMap(c)), media_type="application/x-yaml"
        )
    elif fileending == "json":
        c = {
            key: value
            for res in reversed(results)
            for key, value in res["source"].items()
        }
        return c
    return {
        "name": application,
        "profiles": profile.split(","),
        "label": "main",
        "version": None,
        "state": None,
        "propertySources": results,
    }


@app.get("/{application}.{fileending}")
async def appprofile_file(
    application: str,
    fileending: str,
    prefix: Optional[str] = Header("default"),
    x_config_token: Optional[str] = Header(None),
):
    results = await combine(
        applications=[application, "application"],
        profiles=[],
        labels=["main"],
        x_config_token=x_config_token,
        github=configreader.getConfig()[prefix]["github"],
        vault=configreader.getConfig()[prefix]["vault"],
    )
    return {
        "name": application,
        "profiles": [],
        "label": "main",
        "version": None,
        "state": None,
        "propertySources": results,
    }


def flatten(d, parent_key="", sep="."):
    if not d:
        return {}
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def merge(prio, weak):
    for key in weak:
        if key not in prio:
            prio[key] = weak[key]
    return prio


async def getFromGithub(label, searchedFiles, repository=configreader.default_repo):
    results = {}
    try:
        repo = g.get_repo(repository)
        contents = repo.get_contents(path="", ref=label)
        for content in contents:
            if content.path in searchedFiles:
                if ".yaml" in content.path or ".yml" in content.path:
                    results[
                        f"https://github.com/{repository}/{content.path}"
                    ] = flatten(yaml.safe_load(content.decoded_content))
                else:
                    results[f"https://github.com/{repository}/{content.path}"] = {
                        line[0 : line.find("=")]: line[line.find("=") + 1 :]
                        for line in content.decoded_content.decode("utf-8")
                        .strip()
                        .split("\n")
                    }
    except github.GithubException:
        print(f"ref: {label} not found")
    return results


async def getFromVault(searchedNames, secretpath="secret", vaulttoken="token"):
    vault = hvac.Client(
        url=configreader.getVaultAddress(),
        token=vaulttoken if vaulttoken else os.environ["VAULT_TOKEN"],
        verify=False,
    )
    results = {}
    for searchedName in searchedNames:
        try:
            secret = vault.secrets.kv.read_secret_version(
                path=searchedName, mount_point=secretpath
            )
            results[f"vault:{searchedName}"] = flatten(secret["data"]["data"])
        except:
            pass
    return results


async def combine(
    applications,
    profiles,
    labels,
    x_config_token,
    github="joe255/testconfig-repo",
    vault="secret",
):
    results = []
    tasks = []
    searchedFiles, searchedNames = generateSearchPaths(
        applications, profiles, labels, fileendings
    )
    if x_config_token:
        tasks.append(
            getFromVault(
                searchedNames=searchedNames, vaulttoken=x_config_token, secretpath=vault
            )
        )
    for label in labels:
        tasks.append(
            getFromGithub(label=label, searchedFiles=searchedFiles, repository=github)
        )
    tempres = {}
    for task in tasks:
        res = await task
        for key in res:
            if res[key]:
                tempres[key] = {"name": key, "source": res[key]}
                # results.append({'name': key, 'source': res[key]})
    for sn in searchedNames:
        if f"vault:{sn}" in tempres:
            results.append(tempres[f"vault:{sn}"])
    for sn in searchedFiles:
        if f"https://github.com/{github}/{sn}" in tempres:
            results.append(tempres[f"https://github.com/{github}/{sn}"])
    return results


def generateSearchPaths(applications, profiles, labels, fileendings):
    searchedFiles = []
    searchedNames = []
    for label in labels:
        for application in applications:
            for profile in profiles:
                for fileending in fileendings:
                    searchedFiles.append(
                        f'{application}{"-" + profile if profile else ""}.{fileending}'
                    )
                searchedNames.append(f'{application}{"," + profile if profile else ""}')
        for application in applications:
            for fileending in fileendings:
                searchedFiles.append(f"{application}.{fileending}")
            searchedNames.append(f"{application}")
    return searchedFiles, searchedNames


# asyncio.run(combine())


def generateWideMap(map, sep="."):
    rval = {}
    for key, value in map.items():
        trval = rval
        for item in key.split(sep):
            if not item in trval and item == key.split(sep)[-1]:
                trval[item] = value
            elif not item in trval:
                trval[item] = {}
            trval = trval[item]
    return rval
