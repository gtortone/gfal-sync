#!/usr/bin/env python3

import os
import re
import sys
import gfal2
import argparse
import json
import datetime

def monitor_callback(src, dst, average, instant, transferred, elapsed):
    print("[%4d] %.2fMB (%.2fKB/s)\r" % (elapsed, transferred / 1048576, average / 1024)), sys.stdout.flush()

# parse arguments
parser = argparse.ArgumentParser(description="=== gfal-sync ===")
parser.add_argument('-c', '--conf', dest='conffile', type=str, action='store', help='JSON config file')
parser.add_argument('-r', '--recover', dest='recoverfile', type=str, action='store', help='JSON recover file')

args = parser.parse_args()

if args.conffile is not None:
    try:
        fhand = open(args.conffile, 'r')
    except Exception as e:
        print(f'E: {e}')
        sys.exit(-1)
    else: mode = 'config'
elif args.recoverfile is not None:
    try:
        fhand = open(args.recoverfile, 'r')
    except Exception as e:
        print(f'E: {e}')
        sys.exit(-1)
    else: mode = 'recover'
else:
    print(f'E: specify config file or recover file')
    sys.exit(-1)

try:
    data = json.load(fhand)
except Exception as e:
    print(f'E: JSON parse error - {e}')
    sys.exit(-1)

# extract data
srcBaseDir = data.get('srcBaseDir', None)
if srcBaseDir is None:
    print(f'E: specify srcBaseDir in JSON file')
    sys.exit(-1)

destEndpoint = data.get('destEndpoint', None)
if destEndpoint is None:
    print(f'E: specify destEndpoint in JSON file')
    sys.exit(-1)

destBaseDir = data.get('destBaseDir', None)
if destBaseDir is None:
    print(f'E: specify destBaseDir in JSON file')
    sys.exit(-1)

if mode == 'config':
    srcItems = data.get('srcItems', None)
    if srcItems is None:
        print(f'E: specify srcItems in JSON file')
        sys.exit(-1)
elif mode == 'recover':
    srcDir = data.get('srcDir', None)
    if srcDir is None:
        print(f'E: specify srcDir in JSON file')
        sys.exit(-1)
    srcItems = [srcDir]

# init gfal2
try:
    ctx = gfal2.creat_context()
except Exception as e:
    print(f'E: GFAL2 creat_context() error - {e}')
    sys.exit(-1)

params = ctx.transfer_parameters()
params.monitor_callback = monitor_callback
params.nbstreams = 2
#params.checksum_check = False

try:
    for ldir in srcItems:

        # check local directory
        localDir = f'{srcBaseDir}/{ldir}'
        
        if os.path.isdir(localDir) == False:
            print(f'E: local directory {localDir} not present - skipped')
            continue

        # check remote directory
        destGfalDir = f'{destEndpoint}{destBaseDir}/{ldir}'
        createGfalDir = False
        try:
            ctx.lstat(destGfalDir)
        except gfal2.GError as gerror:
            if gerror.code != 2:           # code=2: directory does not exist
                print(f'E: GFAL2 error lstat() - {gerror}')
                sys.exit(-1)
            else: createGfalDir = True

        if createGfalDir:
            try:
                ctx.mkdir(destGfalDir, 755)
            except gfal2.GError as gerror:
                print(f'E: GFAL2 error mkdir() - {gerror}')
                sys.exit(-1)

        if mode == 'config':
            # init JSON status file
            jdoc = {}
            jdoc['date'] = str(datetime.datetime.now())
            jdoc['srcBaseDir'] = f'{srcBaseDir}'
            jdoc['srcDir'] = f'{ldir}'
            jdoc['destEndpoint'] = f'{destEndpoint}'
            jdoc['destBaseDir'] = f'{destBaseDir}'

            fld = {}
            for lfile in sorted(os.listdir(localDir)):
                fld[str(lfile)] = dict({ 'status': 'idle' })
            jdoc['files'] = fld

            fmode = 'w'
            statusFile = f'{ldir}.recover'
            if os.path.exists(statusFile):      # recover file exists
                while True:
                    res = input(f'=> recover file {statusFile} found - do you want to use it to recover transfers (Y) or init (N) ')
                    if res.lower() == 'y':
                        fmode = 'r+'
                        break
                    elif res.lower() == 'n':
                        fmode = 'w'
                        break
            try:
                fhand = open(statusFile, fmode)
            except Exception as e:
                print(f'E: recovery file open error - {e}')
                sys.exit(-1)

            if fmode == 'w':
                print(f'I: init recovery file {statusFile}')
                fhand.write(json.dumps(jdoc, indent=4))
                fhand.flush()
            elif fmode == 'r+':
                print(f'I: read recovery file {statusFile}')
                jdoc = json.load(fhand)
                
        elif mode == 'recover':
            statusFile = args.recoverfile
            fhand = open(statusFile, 'r+')
            jdoc = json.load(fhand)

        flist = sorted(os.listdir(localDir))
        fdone = ffailed = 0
        # loop on local directory
        for lfile in flist:

            srcFile = f'{localDir}/{lfile}'
            destGfalFile = f'{destGfalDir}/{lfile}'

            if jdoc['files'][lfile]['status'] == 'done':
                print(f'I: recover file reports {srcFile} already copied on remote')
                fdone += 1
                continue

            copyFile = False
            try:
                ctx.lstat(destGfalFile)
            except:
                copyFile = True

            if copyFile:                            # local file does not exist on remote => copy file
                print(srcFile, destGfalFile)
                try:
                    ctx.filecopy(params, f'file://{srcFile}', destGfalFile)
                except gfal2.GError as gerror:
                    # log to status file
                    print(f'E: GFAL2 filecopy() error - {gerror}')
                    jdoc['files'][lfile]['status'] = 'failed'
                    ffailed += 1
                else:
                    jdoc['files'][lfile]['status'] = 'done'
                    fdone += 1

            else:                                   # local file exists on remote => check hash
                srcHash = ctx.checksum(f'file://{srcFile}', 'ADLER32', 0, 0)
                dstHash = ctx.checksum(destGfalFile, 'ADLER32', 0, 0)
                if srcHash == dstHash:                  # hash is the same => skip file
                    print(f'I: file {srcFile} already exists on remote and hash is ok - skipped')
                    jdoc['files'][lfile]['status'] = 'done'
                    fdone += 1
                else:                                   # hash is not the same => overwrite file
                    params.overwrite = True
                    try:
                        ctx.filecopy(params, f'file://{srcFile}', destGfalFile)
                    except gfal2.GError as gerror:
                        # log to file
                        print(f'E: GFAL2 filecopy() overwrite error - {gerror}')
                        jdoc['files'][lfile]['status'] = 'failed'
                        ffailed += 1
                    else:
                        jdoc['files'][lfile]['status'] = 'done'
                        fdone += 1
                    params.overwrite = False

            # update screen
            print(f'stats: {fdone} / {ffailed} / {len(flist)} [done / failed / total]\n')

            # update status file
            fhand.truncate(0)
            fhand.seek(0)
            fhand.write(json.dumps(jdoc, indent=4))
            fhand.flush()

        fhand.close()

except KeyboardInterrupt:
    pass

fhand.close()
print('Bye!')

