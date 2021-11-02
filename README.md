# gfal-sync
GFAL sync utility

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

