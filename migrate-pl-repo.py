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
params_source = clone_source_url.split('/')

github_source = params_source[0] + '//' + params_source[2] + '/api/v3/'
repo_source = params_source[4]
org_name_source = params_source[3]
api_token_source = params_source[2].split('@')[0]

github_dest = 'github_dest' in config and config['github_dest']
org_name_dest = 'org_name_dest' in config and config['org_name_dest']

# if len(api_token_source) == 0:
#     raise Exception('API token must be defined for source and destination repositories.')

if github_dest is None:
    github_dest = input('Enter github destination mx domain (ie. https://learning.github.ubc.ca): ').strip() + '/api/v3/'
if org_name_dest is None:
    org_name_dest = input('Enter destination organization name or personal repository space (ie. ubccpsctech): ').strip()

# Want to always ask for the repo destination
repo_dest = input('Enter destination repository address: ').strip()


def main():

    print('This tool assists with common UBC migration tasks. Each operation is disjointed and optional, but all of these operations may be combined if desired. Option selections can be chosen based on a particular use-case in mind.\n\n')

    print('User migration requirements: ')
    print(' - Admin priviledges in source and destination repositories\n')
    print(' - Must have SSH Keys installed to SSH cloning\n')
    print('Repository creation/data transfer requirements: ')
    print(' - Owner priviliges in Organization storing repositories\n\n')

    print('1. Migrate Users and Teams')
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

# LDAP functionality has not been considered or implemented. This is native Github user migration logic
def migrate_users():
    print('This operation copies the collaborators and their privileges on a repository to a new repository.')

    headers_source = set_header(config['token_source'])
    headers_dest = set_header(config['token_dest'])

    # If repo does not already exist, it should be created with same permissions
    source_repo = get_repo(github_source, org_name_source, repo_source, headers_source)
    dest_repo = get_repo(github_dest, org_name_source, repo_source, headers_dest)

    options = {'private': source_repo['private'], 'description': source_repo['description']}
    if dest_repo is None:
        create_repo(github_dest, org_name_dest, repo_dest, headers_dest, options)

    users_source_list = get_repo_users(github_source, org_name_source, repo_source, headers_source)
    teams_source_list = get_repo_teams(github_source, org_name_source, repo_source, headers_source)
    
    for team in teams_source_list:
        team_members = get_team_members(github_source, org_name_dest, team['slug'], headers_source)
        team_options = {'name': team['name'], 'description': team['description'], 'permission': team['permission'], 'maintainers': team_members}
        create_team(github_dest, org_name_dest, team_options, headers_dest)
        add_team_to_repo(github_dest, org_name_source, team['slug'], repo_dest, headers_dest)

        # remove these so we do not add them as collaborators when they are already on a team
        for team_member_login in team_members:
            index = users_source_list.index(team_member_login)
            if index >= 0:
                users_source_list.pop(index)

    users_dest_list = get_repo_users(github_dest, org_name_dest, repo_dest, headers_dest)
    users_no_profile = []
    users_with_profile = []

    for user_login in users_source_list:
        user_profile = get_user_profile(github_dest, user_login, headers_dest)
        if user_profile is None:
            users_no_profile.append(user_login)

    user_roles_source_list = []
    user_roles_dest_list = []
    user_roles_failed_add_list = []

    for user in users_source_list:
        role = get_user_role(github_source, org_name_source, repo_source, user, headers_source)
        user_roles_source_list.append({'login': user, 'role': role})

    ## Warning. May not want to proceed until all users are active on new Github Enterprise respository
    if len(user_roles_dest_list) > 0:
        print('Warning: These users cannot be added to the destination repository, as they do not exist on the destination Github Enterprise instance.')
        proceed = input('Are you sure you want to proceed? y/n ')
        if proceed != 'yes' and proceed != 'y':
            sys.exit(0)

    print('Users on Source Repository:', str(user_roles_source_list))
    print('\n')

    for user in user_roles_source_list:
        ## 204 when already added, 201 when newly added
        res = add_user_to_repo(github_dest, org_name_dest, repo_dest, user['login'], user['role'], headers_dest)
        if res.status_code == 204 or res.status_code == 201:
            user_roles_dest_list.append({'login': user['login'], 'role': user['role']})
        else:
            user_roles_failed_add_list.append({'login': user['login'], 'role': user['role']})

    print('Users on destination repository: ', str(user_roles_dest_list))
    print('\n')
    print('Users who could not be added to destination repository: ', str(user_roles_failed_add_list))
    sys.exit(0)

def get_repo_users(github_domain, org_name, repo, headers):
    endpoint_url = urljoin(github_domain, 'repos/{0}/{1}/collaborators'.format(org_name, repo))
    # GITHUB BUG: this option does not work. All users are retrieved.
    options = {'affiliation': 'outside'}
    res = request(endpoint_url, headers, 'GET', options)
    json = res.json()
    users_list = []

    # Filters out Anth and myself because we always show up as collaborators even though we are not
    # Might want to fill out a bug report for Github's collaborator endpoint
    for user in json:
        if user['site_admin'] == False and user['login'] != 'steca':
            users_list.append(user['login'])
    return users_list

def get_repo_teams(github_domain, org_name, repo, headers):
    endpoint_url = urljoin(github_domain, 'repos/{0}/{1}/teams'.format(org_name, repo))
    res = request(endpoint_url, headers, 'GET')
    json = res.json()
    return json

def get_team_members(github_domain, org_name, team_slug, headers):
    endpoint_url = urljoin(github_domain, 'orgs/{0}/teams/{1}/members'.format(org_name, team_slug))
    res = request(endpoint_url, headers, 'GET')
    json = res.json()
    team_members = []
    for team_member in json:
        team_members.append(team_member['login'])
    return team_members

# duplciate?
# def get_team_members(github_domain, org_name, team_slug, headers):
#     endpoint_url = urljoin(github_domain, 'orgs/{0}/teams/{1}}'.format(org_name, team_slug))
#     res = request(endpoint_url, headers, 'GET')
#     json = res.json()
#     team_members = []
#     for team_member in json:
#         team_members.append({'login': team_member['login']})
#     return team_members

# https://developer.github.com/v3/teams/#create-a-team
def create_team(github_domain, org_name, team_options, headers):
    endpoint_url = urljoin(github_domain, 'orgs/{0}/teams'.format(org_name))
    res = request(endpoint_url, headers, 'GET', team_options)
    json = res
    if res.status_code == 201:
        return res.json()
    return None

# https://developer.github.com/v3/teams/#add-or-update-team-repository-permissions
def add_team_to_repo(github_name, org_name, team_slug, repo_name, headers):
    endpoint_url = urljoin(github_name, 'orgs/{0}/teams/{1}/repos/{0}/{2}'.format(org_name, team_slug, repo_name))
    res = request(endpoint_url, headers, 'PUT')
    if res.status_code == 204:
        return res
    return None
    
def get_user_role(github_domain, org_name, repo_name, user, headers):
    endpoint_url = urljoin(github_domain, 'repos/{0}/{1}/collaborators/{2}/permission'.format(org_name, repo_name, user))
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

def get_user_profile(github_domain, user_login, headers):
    endpoint_url = urljoin(github_domain, 'users/{0}'.format(user_login))
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