"""Micropython OTA Updates from Github"""
import os
import urequests
import json
import machine
import time
import network

if __debug__:
    try:
        import logging
    except ImportError:
        class Logger:
            DEBUG = 10
            def isEnabledFor(self, _):
                return False
            def debug(self, msg, *args):
                pass
            def getLogger(self, name):
                return Logger()
        logging = Logger()

    logger = logging.getLogger(__name__)

global internal_tree

with open("configs/config.json", "r") as json_file:
    CFG = json.load(json_file)

# Repository must be public if no personal access token is supplied
GITHUB_USER = CFG["Github"]["user"]
GITHUB_REPO = CFG["Github"]["repo"]
# REPO_ACCESS_TOKEN = open(CFG["Github"]["secret_access_token"], "r").read()
REPO_ACCESS_TOKEN = ""

# Specify the files that are uneffected by OTA updates.
IGNORE_FILES = [
    "esp32/ugit.py",
    "esp32/configs",
    "esp32/configs/config.json",
    "esp32/cert",
    "esp32/cert/.gitkeep",
    "esp32/cert/AmazonRootCA1.pem",
    "esp32/cert/certificate.pem.crt",
    "esp32/cert/private.pem.key",
]

GIT_SUBFOLDER = "esp32/"
GIT_TREE_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/git/trees/main?recursive=1"
GIT_RAW = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/"


def pull(fpath, raw_url: str) -> None:
    """Pulls a single file."""
    headers = {"User-Agent": "ugit-heytupu"}
    if len(REPO_ACCESS_TOKEN) > 0:
        headers["authorization"] = "bearer %s" % REPO_ACCESS_TOKEN

    if logger and logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"Pulling {fpath} to device.")

    print(f"Pulling {fpath} to device.")
    r = urequests.get(raw_url, headers=headers)
    try:
        new_file = open(fpath, "w")
        new_file.write(r.content.decode("utf-8"))
        r.close()
        new_file.close()
    except:
        try:
            new_file.close()
        except:
            print("Unable to close file during raw file decoding.")


def update() -> None:
    """Pulls all the files & overwrites updated files."""
    print("Updating Device.")
    tree = parse_git_tree()
    for i in tree:
        fpath = remove_prefix(i["path"])
        gpath = GIT_RAW + i["path"]
        # Pulling the individual file to update.
        pull(fpath, gpath)


def pull_git_tree() -> dict:
    """Pulls the git tree of the repo."""
    headers = {"User-Agent": "ugit-heytupu"}
    r = urequests.get(GIT_TREE_URL, headers=headers)
    j = json.loads(r.content.decode("utf-8"))
    r.close()
    return j


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
