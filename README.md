# gfal-sync
GFAL sync utility to copy a list of subdirectories that contain files (no recursion) to remote storage.

```
usage: gfal-sync.py [-h] [-c CONFFILE] [-r RECOVERFILE]

=== gfal-sync ===

optional arguments:
  -h, --help            show this help message and exit
  -c CONFFILE, --conf CONFFILE
                        JSON config file
  -r RECOVERFILE, --recover RECOVERFILE
                        JSON recover file
```

## Config file (JSON)

This file must be created by user. An example is in conf/ directory.

- **destEndpoint**: SRM (or other) base endpoint
- **destBaseDir**: base directory where script will create subdirectories
- **srcBaseDir**: source base directory where script will loop on srcItems
- **srcItems**: list of subdirectories

## Recover file (JSON)

This file is generated for each srcItems and updated on each transfer by gfal-sync.

- **date**: file creation date
- **destEndpoint**: (same as config file)
- **destBaseDir**: (same as config file)
- **srcBaseDir**: (same as config file)
- **files**: list of files entries with 'name' as key and 'status' as value
(status can be: 'done', 'failed', 'idle')

## Operating mode

In **config mode** (-c option) gfal-sync loop on 'srcItems' list and for each directory:
- check if local directory exists
- if recovery file exists apply **recovery mode** else create a new recovery file
- check if remote directory exists (create it if needed)
- for each file in local directory:
    - check if remote file exists
        - if remote file does not exist copy local file to remote
        - if remote file exists compare hash values and if values differ copy local file to remote
- update recovery file

In **recovery mode** (-r option) gfal-sync open passed recovery file:
- for each filename
    - skip if status is 'done'
    - try to copy if status is 'failed' or 'idle'




