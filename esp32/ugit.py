"""Micropython OTA Updates from Github"""
import os
import urequests
import json
import hashlib
import binascii
import machine
import time
import network

global internal_tree

SSID = CFG["Network"]["SSID"]
PASS = CFG["Network"]["PASS"]

# Repository must be public if no personal access token is supplied
GITHUB_USER = CFG["Github"]["user"]
GITHUB_REPO = CFG["Github"]["repo"]
REPO_ACCESS_TOKEN = open(CFG["Github"]["secret_access_token"], "r").read()

# Specify the files that are uneffected by OTA updates.
IGNORE_FILES = ['/ugit.py', 'configs/config.json', 'cert/AmazonRootCA1.pem', 'cert/certificate.pem.crt', 'cert/private.pem.key']

giturl = f'https://github.com/{GITHUB_USER}/{GITHUB_REPO}'
git_destination = 'iot/esp32'
GIT_TREE_URL = f'https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/git/trees/main?recursive=1'
raw = f'https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/'


def pull(f_path: str, raw_url: str):
    # headers = {'User-Agent': 'ugit-turfptax'} 
    headers = {}
    if len(REPO_ACCESS_TOKEN) > 0:
        headers['authorization'] = "bearer %s" % REPO_ACCESS_TOKEN 
    
    r = urequests.get(raw_url, headers=headers)
    try:
        new_file = open(f_path, 'w')
        new_file.write(r.content.decode('utf-8'))
        new_file.close()
    except:
        try:
            new_file.close()
        except:
            print('Unable to close file during raw file decoding.')
      

def pull_all() -> None:
    """Pulls all the files & overwrites updated files."""
    tree = pull_git_tree()
    
    # Restart the machine after the update
    machine.reset()


# def pull_all(tree=call_trees_url, raw: str = raw, isconnected=False):
#     os.chdir('/')
#     tree = pull_git_tree()
#     internal_tree = build_internal_tree()
#     internal_tree = remove_ignore(internal_tree)
#     print(internal_tree)
    
#     log = []
#     # download and save all files
#     for i in tree['tree']:
#         if i['type'] == 'tree':
#             try:
#                 os.mkdir(i['path'])
#             except:
#                 print(f'failed to {i["path"]} dir may already exist.')
#         elif i['path'] not in ignore:
#             try:
#                 os.remove(i['path'])
#                 log.append(f'{i["path"]} file removed from int mem.')
#                 internal_tree = remove_item(i['path'], internal_tree)
#             except:
#                 log.append(f'{i["path"]} del failed from int mem.')
#                 print('failed to delete old file.')
#             try:
#                 pull(i['path'], raw + i['path'])
#                 log.append(i['path'] + ' updated.')
#             except:
#                 log.append(i['path'] + ' failed to pull')

#     # delete files not in Github tree
#     if len(internal_tree) > 0:
#         print(internal_tree, ' leftover!')
#         for i in internal_tree:
#             os.remove(i)
#             log.append(i + ' removed from int mem')
#     logfile = open('ugit_log.py','w')
#     logfile.write(str(log))
#     logfile.close()

#     time.sleep(10)
#     machine.reset()



def build_internal_tree():
    """."""
    global internal_tree
    internal_tree = []
    os.chdir('/')

    for i in os.listdir():
        add_to_tree(i)
    return(internal_tree)


def add_to_tree(dir_item):
    global internal_tree
    if is_directory(dir_item) and len(os.listdir(dir_item)) >= 1:
        os.chdir(dir_item)
        for i in os.listdir():
            add_to_tree(i)
        os.chdir('..')
    else:
        print(dir_item)
        if os.getcwd() != '/':
            subfile_path = os.getcwd() + '/' + dir_item
        else:
            subfile_path = os.getcwd() + dir_item
        try:
            internal_tree.append([subfile_path, get_hash(subfile_path)])
        except OSError:
            print(f'{dir_item} could not be added to tree.')


def get_hash(file):
    """Computes the hash of a specific file."""
    o_file = open(file)
    r_file = o_file.read()
    sha1obj = hashlib.sha1(r_file)
    hash = sha1obj.digest()
    return(binascii.hexlify(hash))


def is_directory(file) -> bool:
    try:
        return (os.stat(file)[8] == 0)
    except:
        return False

    
def pull_git_tree() -> dict:
    """Pulls the git tree of the repo."""
    headers = {}

    if len(REPO_ACCESS_TOKEN) > 0:
        headers['authorization'] = "bearer %s" % REPO_ACCESS_TOKEN 
    r = urequests.get(GIT_TREE_URL, headers=headers)
    return json.loads(r.content.decode('utf-8'))
  

def parse_git_tree():
    tree = pull_git_tree()
    dirs = []
    files = []
    for i in tree['tree']:
        if i['type'] == 'tree':
            dirs.append(i['path'])
        if i['type'] == 'blob':
            files.append([i['path'],i['sha'],i['mode']])
   
   
# def check_ignore(tree=call_trees_url,raw = raw):
#     os.chdir('/')
#     tree = pull_git_tree()
#     check = []
    
#     for i in tree['tree']:
#         if i['path'] not in ignore:
#             print(i['path'] + ' not in ignore')
#         if i['path'] in ignore:
#             print(i['path']+ ' is in ignore')
        
        
# def remove_ignore(internal_tree,ignore=ignore):
    # clean_tree = []
    # int_tree = []
    # for i in internal_tree:
        # int_tree.append(i[0])
    # for i in int_tree:
        # if i not in ignore:
        #     clean_tree.append(i)
    # return(clean_tree)
        

# def remove_item(item,tree):
    # culled = []
    # for i in tree:
        # if item not in i:
        #     culled.append(i)
    # return(culled)
