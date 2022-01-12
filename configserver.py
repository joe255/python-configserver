import getopt
import os
import sys
from collections.abc import MutableMapping
from typing import Optional

import github
import hvac
import yaml
from fastapi import FastAPI, Header, Response
from github import Github

import configreader

githubtoken = "" if not "GITHUB_TOKEN" in os.environ else os.environ["VAULT_TOKEN"]
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
async def endpoint_application_profile_label(
    application: str,
    profile: str,
    label: str,
    prefix: Optional[str] = Header("default"),
    x_config_token: Optional[str] = Header(None),
):
    """
    The offered endpoint implements the basic feature of the spring cloud config server with an added label field. The label reflects in case of git/github the source of a ref/branch.
    :param application: The name of the application which needs the application configuration.
    :param profile: The profile (comma separated) that should be loaded from git and vault.
    :param label: The label (comma separated) that should be loaded from git. Vault does not support multiple labels.
    :param prefix: This is a multi profile implementation of the configserver. Depending on this value a different profile from the configuration file is loaded.
    :param x_config_token: In case of the requirement to load values from vault, a header field is added to the http request which has access permissions to the secrets in vault.
    :return: The results contain an ordered set of source configurations from git and vault.
    """
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
async def endpoint_application_profile(
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
async def endpoint_application_profile_fileending(
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
    content = {
        key: value for res in reversed(results) for key, value in res["source"].items()
    }
    if fileending == "properties":
        c = [f"{key}={value}" for key, value in content.items()]
        return Response(content="\n".join(c), media_type="application/text")
    elif fileending == "yml" or fileending == "yaml":
        return Response(
            content=yaml.dump(generateWideMap(content)), media_type="application/x-yaml"
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
async def endpoint_application_fileending(
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
