"""Micropython OTA Updates from Github"""
import os
import urequests
import json
import machine
import time
import network
import logging

# Initiate the logging object.
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

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


def pull(fpath: str, raw_url: str, headers: dict) -> None:
    """Pulls a single file."""
    r = urequests.get(raw_url, headers=headers)
    try:
        new_file = open(fpath, "w")
        new_file.write(r.content.decode("utf-8"))
        r.close()
        new_file.close()
        
        logger.info(f"Updated {fpath} on device.")
    except:
        try:
            new_file.close()
        except:
            logger.error(f"Unable to close {fpath} file during raw file decoding.")


def update() -> None:
    """Pulls all the files & overwrites updated files."""
    logger.info("Updating device.")

    # Construct the header used for fetching from github.
    headers = {"User-Agent": "ugit-heytupu"}
    if len(REPO_ACCESS_TOKEN) > 0:
        headers["authorization"] = "bearer %s" % REPO_ACCESS_TOKEN

    if __debug__:
        logger.debug(f"Header used for fetching data : {headers}.")

    # Get the git tree
    tree = parse_git_tree(headers)
    for i in tree:
        fpath = remove_prefix(i["path"])
        gpath = GIT_RAW + i["path"]

        if __debug__:
            logger.debug(f"Pull {fpath} from {gpath} to device.")

        # Pulling the individual file to update.
        pull(fpath, gpath, headers)


def pull_git_tree(headers: dict) -> dict:
    """Pulls the git tree of the repo."""
    if __debug__:
        logger.debug(f"Sending request to fetch git tree : {GIT_TREE_URL}.")
    r = urequests.get(GIT_TREE_URL, headers=headers)
    j = json.loads(r.content.decode("utf-8"))
    r.close()
    return j


def parse_git_tree(headers: dict) -> list:
    """Parsing the git tree for desired files."""
    tree = pull_git_tree(headers)

    # Construct the file list for updating.
    files = list()
    for i in tree["tree"]:
        if i["path"].startswith(GIT_SUBFOLDER) and not i["path"] in IGNORE_FILES:
            files.append(i)

    if __debug__:
        logger.debug(f"Files that should be updated : {files}.")
    return files


def remove_prefix(fpath: str) -> str:
    """Removing the subfolder from path to put the file to root."""
    if fpath.startswith(GIT_SUBFOLDER):
        return fpath[len(GIT_SUBFOLDER) :]
    return fpath

