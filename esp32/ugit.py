"""Micropython OTA Updates from Github"""
import os
import urequests
import json
import hashlib
import binascii
import machine
import time
import network

from boot import CFG
global internal_tree


SSID = CFG["Network"]["SSID"]
PASS = CFG["Network"]["PASS"]

# Repository must be public if no personal access token is supplied
GITHUB_USER = CFG["Github"]["user"]
GITHUB_REPO = CFG["Github"]["repo"]
REPO_ACCESS_TOKEN = open(CFG["Github"]["secret_access_token"], "r").read()

# Specify the files that are uneffected by OTA updates.
IGNORE_FILES = [
    "esp32/ugit.py",
    "esp32/configs/config.json",
    "esp32/cert/AmazonRootCA1.pem",
    "esp32/cert/certificate.pem.crt",
    "esp32/cert/private.pem.key",
]

GIT_SUBFOLDER = "esp32/"
GIT_TREE_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/git/trees/main?recursive=1"
GIT_RAW = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/"


def pull(fpath, raw_url: str) -> None:
    """Pulls a single file."""
    headers = {}
    if len(REPO_ACCESS_TOKEN) > 0:
        headers["authorization"] = "bearer %s" % REPO_ACCESS_TOKEN

    r = urequests.get(raw_url, headers=headers)
    try:
        new_file = open(fpath, "w")
        new_file.write(r.content.decode("utf-8"))
        new_file.close()
    except:
        try:
            new_file.close()
        except:
            print("Unable to close file during raw file decoding.")


def update() -> None:
    """Pulls all the files & overwrites updated files."""
    tree = parse_git_tree()
    for i in tree:
        fpath = remove_prefix(i["path"])
        pull(os.path.join(GIT_RAW, i["path"]))

    # Restart the machine after the update
    machine.reset()


def pull_git_tree() -> dict:
    """Pulls the git tree of the repo."""
    headers = {}
    if len(REPO_ACCESS_TOKEN) > 0:
        headers["authorization"] = "bearer %s" % REPO_ACCESS_TOKEN

    r = urequests.get(GIT_TREE_URL, headers=headers)
    return json.loads(r.content.decode("utf-8"))


def parse_git_tree() -> list:
    """Parsing the git tree for desired files."""
    tree = pull_git_tree()

    files = list()
    for i in tree["tree"]:
        if i["path"].startswith(GIT_SUBFOLDER) and not i["path"] in IGNORE_FILES:
            files.append(i)
    return files


def remove_prefix(fpath: str) -> str:
    """Removing the subfolder from path to put the file to root."""
    if fpath.startswith(GIT_SUBFOLDER):
        return fpath[len(GIT_SUBFOLDER) :]
    return fpath
