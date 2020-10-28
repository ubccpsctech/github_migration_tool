# Github Migration Tool

## Overview

The migration of Github repositories are supported within the application if the repository is migrated from organization to organization within the same Github Enterprise application. A Github migration tool also exists to help admins migrate Github reopsitories (with issues and other repository assets, etc.), but requires site admin permissions.

This Github migration tool is for a use-case where an organization member has owner permissions in each repository and wants to migrate all branches of the Github repository, repository collaborators, and repository teams.

Pre-requisites for a smooth migration:

- Everyone has logged into the destination Github Enterprise instance to ensure that their account user name exists.
- Access token produced under `Developer Settings` within the `User Settings`.
- Ideally, `Owner` permissions of the organization, or `admin` repository permissions (you may not be allowed to create a repo though)

## Supported Operations

- Migrate Users from one Github Enterprise instance repository to another 
  - Prints user list of those who cannot be migrated (ie. they have not created a Github Enterprise user account by logging in)
- Migrate Github repository contents from one Github Enterprise instance to another (copies all branches with --mirror)
  - Copies all branches with --mirror flag
  - Copies permissions from initial repository (this can be built out with include more refined permissions)

## Instructions

Since we are reading and writing to and from two separate Github Enterprise instances, we need two tokens to read/write and access API functions:

- [ ] Create `config.ini` file in root directory.

```
[DEFAULT]
token_source = xyz
token_dest = xyz
```

- [ ] Add source Github Enteprise instance token to `config.ini`
  - To create a token: Login to Github Enterprise --> User Settings --> Developer Settings
  - Note: developed with Owner organization privileges (read repo level could be adequate)
- [ ] Add destination Github Enterprise instance token to `config.ini`
  - To create a token: Login to Github Enterprise --> User Settings --> Developer Settings
  - Note: developed with Owner organization privileges (permissions to create and write repo could be adequate)

