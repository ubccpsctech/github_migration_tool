#!/usr/bin/python
#
# migrate-pl-repos.py
#
# Instructions: Run migrate-pl-repos.py and choose operation selection from menu. Follow input prompts.
#
# A python script to perform migration operations
#
# Andrew Stec <steca@cs.ubc.ca>
# Oct 21 2020
#

# Imports
import sys
import time
import requests
from subprocess import Popen
from urllib.parse import urljoin
from configparser import ConfigParser

TEMP_FILE_PATH = 'temp'

config = ConfigParser()
config.read('config.ini')
config = config['DEFAULT']

repo_address_source = ''
repo_address_dest = ''
token_source = ''
token_dest = ''
headers_source = {}
headers_dest = {}

print('Tips: If you are an admin, lock the source repository so users cannot push to the source repository during the migration. ')

print('A Github migration requires a source and destination repository to work with. Please enter the source and destination repositories in Https format (ie. https://api_token@github.enterprise.instance/org_or_owner/repo_name')
clone_source_url = input('Source repository: ').strip()
# full_dest_url = input('Destination repository: ').strip()
params_source = clone_source_url.split('/')

github_source = params_source[0] + '//' + params_source[2] + '/api/v3/'
repo_source = params_source[4]
org_name_source = params_source[3]
api_token_source = params_source[2].split('@')[0]

# if len(api_token_source) == 0:
#     raise Exception('API token must be defined for source and destination repositories.') 

github_dest = input('Enter github destination mx domain (ie. https://learning.github.ubc.ca): ').strip() + '/api/v3/'
org_name_dest = input('Enter destination organization name or personal repository space (ie. ubccpsctech): ').strip()
repo_dest = input('Enter destination repository address: ').strip()


def main():

    print('This tool assists with common UBC migration tasks. Each operation is disjointed and optional, but all of these operations may be combined if desired. Option selections can be chosen based on a particular use-case in mind.\n\n')

    print('User migration requirements: ')
    print(' - Admin priviledges in source and destination repositories\n')
    print(' - Must have SSH Keys installed to SSH cloning\n')
    print('Repository creation/data transfer requirements: ')
    print(' - Owner priviliges in Organization storing repositories\n\n')

    print('1. Migrate Users')
    print('2. Migrate Repositories')
    print('3. Exit')
    selection = int(input('Select option: ').strip())
    if selection == 1:
        migrate_users()
    elif selection == 2:
        clone_source_repo()
        push_dest_repo()
    elif selection == 3: 
        sys.exit(0)
    else:
        print('Invalid selection.')
        main()

def clone_source_repo():
    # repo_address = input('Enter the source repository address to copy: ').strip()
    print('Removing any pre-existing migration data')
    Popen(['rm', '-rf', TEMP_FILE_PATH])
    Popen(['git', 'clone', '--mirror', clone_source_url, TEMP_FILE_PATH]).wait()

def push_dest_repo():
    headers_source = set_header(config['token_source'])
    headers_dest = set_header(config['token_dest'])

    source_repo = get_repo(github_source, org_name_source, repo_source, headers_source)
    
    clone_dest_url = urljoin(('https://' + config['token_dest'] + '@' + github_dest.replace('/api/v3/', '').replace('https://', 
    '')), (org_name_dest + '/' + repo_dest))
    print('Uploading repository mirror clone to ' + clone_dest_url)

    ## Can customize options to migrate: https://developer.github.com/v3/repos/#create-an-organization-repository
    dest_repo = get_repo(github_source, org_name_dest, repo_dest, headers_dest)
    if dest_repo is not None:
        Popen(['git', 'push', '--mirror', clone_dest_url], cwd=TEMP_FILE_PATH).wait()
    else:
        options = {'private': source_repo['private'], 'description': source_repo['description']}
        create_repo(github_dest, org_name_dest, repo_dest, headers_dest, options)
        time.sleep(2)
        Popen(['git', 'push', '--mirror', clone_dest_url], cwd=TEMP_FILE_PATH).wait()

def get_org(address):
    return repo_address_dest

def migrate_users():
    print('This operation copies the collaborators and their privileges on a repository to a new repository.')

    headers_source = set_header(config['token_source'])
    headers_dest = set_header(config['token_dest'])

    # If repo does not already exist, it should be created with same permissions
    source_repo = get_repo(github_source, org_name_source, repo_source, headers_source)
    dest_repo = get_repo(github_dest, org_name_source, repo_source, headers_dest)
    options = {}
    if dest_repo is not None:
        create_repo(github_source, org_name_dest, repo_dest, headers_dest)

    users_source_list = get_users(github_source, org_name_source, repo_source, headers_source)
    users_dest_list = get_users(github_dest, org_name_dest, repo_dest, headers_dest)

    user_roles_source_list = []
    user_roles_dest_list = []
    user_roles_failed_add_list = []

    for user in users_source_list:
        role = get_user_role(github_source, org_name_source, repo_source, user, headers_source)
        user_roles_source_list.append({'login': user, 'role': role})

    print('Users on Source Repository:', str(user_roles_source_list))
    print('\n')

    for user in user_roles_source_list:
        ## 204 when already added, 201 when newly added
        res = add_user_to_repo(github_dest, org_name_dest, repo_dest, user['login'], user['role'], headers_dest)
        try:
            if res.status_code == 204 or res.status_code == 201:
                user_roles_dest_list.append({'login': user['login'], 'role': user['role']})
        except:
            user_roles_failed_add_list.append({'login': user['login'], 'role': user['role']})

    print('Users on destination repository: ', str(user_roles_dest_list))
    print('\n')
    print('ERROR: Users who could not be added to destination repository: ', str(user_roles_failed_add_list))
    sys.exit(0)

def copy_repo(copy_settings = True):
    source_repo_data = get_repo(github_source, org_name_source, repo_source, headers_source)
    res = create_repo(github_dest, org_name_dest, repo_dest, headers_dest, source_repo_data)

def get_users(github_domain, org_name, repo, headers):
    endpoint_url = urljoin(github_domain, 'repos/{0}/{1}/contributors'.format(org_name, repo))
    json = request(endpoint_url, headers).json()
    users_list = []
    for user in json:
        users_list.append(user['login'])
    return users_list

def get_user_role(github_domain, org_name, repo_name, user, headers):
    endpoint_url = urljoin(github_domain, 'repos/{0}/{1}/collaborators/{2}/permission').format(org_name, repo_name, user)
    role = request(endpoint_url, headers).json()['permission']
    return role

def add_user_to_repo(github_domain, org_name, repo_name, user_login, user_role, headers):
    endpoint_url = urljoin(github_domain, 'repos/{0}/{1}/collaborators/{2}'.format(org_name, repo_name, user_login))
    res = request(endpoint_url, headers, 'PUT', data={'permission': user_role})
    return res

def create_repo(github_domain, org_name, repo_name, headers, options = {}):
    options['name'] = repo_name
    endpoint_url = urljoin(github_domain, 'orgs/{0}/repos'.format(org_name))
    res = request(endpoint_url, headers, 'POST', options)
    return res.json()

def get_repo(github_domain, org_name, repo_name, headers):
    endpoint_url = urljoin(github_domain, 'repos/{0}/{1}').format(org_name, repo_name)
    res = request(endpoint_url, headers)
    if res.status_code == 200:
        return res.json()
    else:
        return None

def set_header(api_token):
	return {'Content-Type': 'application/json',
			'User-Agent': 'UBC-CPSC Department',
            'Authorization': 'token {0}'.format(api_token)}

def request(endpoint_url, headers, verb='get', data={}):
    if verb == 'get':
        time.sleep(1)
    else:
        time.sleep(2)
    return requests.request(verb, endpoint_url, headers=headers, json=data)

main()