import os
import shutil
import sys
import yaml
import zipfile
import zlib
from fabric.api import *

config = {}
with open("config.yml", "r") as configFile:
    config = yaml.load(configFile)


def get_host(pack_type):
    c = env.conf
    if pack_type in c and 'host' in c[pack_type]:
        return c[pack_type]['host']
    return config['deploy']['host']


def zip_dir(zipFile, path):
    pathLen = len(path)
    for root, dirs, files in os.walk(path):
        for f in files:
            filePath = os.path.join(root,f)
            zipFile.write(filePath, filePath[pathLen:], compress_type=zipfile.ZIP_DEFLATED)


def zip_name(zip_type):
    return '%s-%s-%s.zip' % (env.conf['base_name'], env.conf['version'], zip_type)


def build_zip(zip_name, base_dir, pack_type, additional={}):
    base_dir = 'packs/%s' % env.pack
    filename = '%s/%s' % (config['build_dir'], zip_name)
    zipf = zipfile.ZipFile(filename, 'w')
    # add common files
    zip_dir(zipf, base_dir+'/common')
    # add client files
    zip_dir(zipf, base_dir+'/'+pack_type)

    for f in additional:
        if os.path.isfile(additional[f]):
            zipf.write(additional[f], f, compress_type=zipfile.ZIP_DEFLATED)

    zipf.close()


def add_files_server():
    return {}

def add_files_vanilla():
    return {}

def add_files_technic():
    return {
            "bin/modpack.jar": '%s/%s' % (config['forge_dir'], env.conf['technic']['forge'])
    }



@task
def pack(name):
    if name in config['packs']:
        env.pack = name
        env.conf = config['packs'][name]
    else:
        raise Exception("Unknown pack: "+name)


@task
def clean():
    print "Cleaning."
    if os.path.isdir(config['build_dir']):
        shutil.rmtree(config['build_dir'])


@task
def build(*pack_types):
    require('pack', providedBy=[pack])
    if not pack_types:
        pack_types = list(config['pack_types'].keys())
    if not os.path.isdir(config['build_dir']):
        os.mkdir(config['build_dir'])
    for kind in pack_types:
        print "Building %s pack." % kind
        pack_path = '%s/%s' % (config['packs_dir'], env.pack)
        adds = getattr(sys.modules[__name__], "add_files_"+kind)()
        build_zip(zip_name(kind), pack_path, config['pack_types'][kind], adds)


@task
def deploy(*pack_types):
    require('pack', providedBy=[pack])
    print "Deploying zips for pack: "+env.pack
    if not pack_types:
        pack_types = list(config['pack_types'].keys())
    for kind in pack_types:
        execute(upload_pack, host=get_host(kind), pack_type=kind)

def upload_pack(pack_type):
    c = env.conf
    local_file = '%s/%s' % (config['build_dir'], zip_name(pack_type))
    remote_dir = config['deploy']['dir']
    if pack_type in c and 'dir' in c[pack_type]:
        remote_dir = c[pack_type]['dir']
    if os.path.isfile(local_file):
        print "Uploading %s pack..." % pack_type
        put(local_file, remote_dir)

