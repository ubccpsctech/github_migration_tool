# Github Migration Tool

## Supported Operations

- Migrate Users from one Github Enterprise instance repository to another 
  - Prints user list of those who cannot be migrated (ie. they have not created a Github Enterprise user account by logging in)
- Migrate Github repository contents from one Github Enterprise instance to another (copies all branches with --mirror)
  - Copies all branches with --mirror flag
  - Copies permissions from initial repository (this can be built out with include more refined permissions)

## Instructions

Since we are reading and writing to and from two separate Github Enterprise instances, we need two tokens to read/write and access API functions:

- Create `config.ini` file in root directory.

```
[DEFAULT]
token_source = xyz
token_dest = xyz
```

- [] Add source Github Enteprise instance token to `config.ini`
  - To create a token: Login to Github Enterprise --> User Settings --> Developer Settings
  - Note: developed with Owner organization privileges (read repo level could be adequate)
- [] Add destination Github Enterprise instance token to `config.ini`
  - To create a token: Login to Github Enterprise --> User Settings --> Developer Settings
  - Note: developed with Owner organization privileges (permissions to create and write repo could be adequate)

