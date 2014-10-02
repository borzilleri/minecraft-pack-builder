import os
import shutil
import sys
import urllib
import yaml
import zipfile
import zlib
from fabric.api import *

DEFAULT_PACKAGE_NAME="modpack"
DEFAULT_PACKAGE_VERSION="1.0"
CONFIG_FILE="config.yml"
CONF = {}
with open(CONFIG_FILE, "r") as configFile:
    CONF = yaml.load(configFile)


def zip_name(pkg_type):
    base_name = env.conf.get('base_name', DEFAULT_PACKAGE_NAME)
    version = env.conf.get('version', DEFAULT_PACKAGE_VERSION)
    return '%s-%s-%s.zip' % (base_name, version, pkg_type)


def zip_dir(zipf, path):
    prefix = len(path)
    for root, dirs, files in os.walk(path):
        for f in files:
            if not f.startswith('.'):
                fp = os.path.join(root,f)
                zipf.write(fp, fp[prefix:], compress_type=zipfile.ZIP_DEFLATED)


def build_zip(zip_name, base_dir, pkg_style, additional={}):
    base_dir = '%s/%s' % (CONF['modpacks_dir'], env.modpack)
    filename = '%s/%s' % (CONF['build_dir'], zip_name)
    zipf = zipfile.ZipFile(filename, 'w')
    # add common files
    zip_dir(zipf, base_dir+'/common')
    # add package-style specific files (server vs client)
    zip_dir(zipf, base_dir+'/'+pkg_style)
    for f in additional:
        if os.path.isfile(additional[f]):
            zipf.write(additional[f], f, compress_type=zipfile.ZIP_DEFLATED)
    zipf.close()


def add_files_noop():
    return {}


def add_files_technic():
    adds = {}
    forge_version = env.conf['technic']['forge_version']
    forge_jar = CONF['forge']['jar_pattern'] % forge_version
    forge_dir = CONF['build_dir'] +'/'+ CONF['forge']['cache_dir']
    forge_file = forge_dir+'/'+forge_jar
    if not os.path.isfile(forge_file):
        if not os.path.exists(forge_dir):
            os.makedirs(forge_dir)
        forge_url = CONF['forge']['url_pattern'] % (forge_version, forge_jar)
        urllib.urlretrieve(forge_url, forge_file)
    adds[env.conf['technic']['forge_zipfile']] = forge_file
    return adds


@task
def pack(name):
    if name in CONF['modpacks']:
        env.modpack = name
        env.conf = CONF['modpacks'][name]
        for pkgType in CONF['package_types']:
            if pkgType not in env.conf:
                env.conf[pkgType] = {}
            env.conf[pkgType] = dict(CONF['package_defaults'].items()+env.conf[pkgType].items())
    else:
        raise Exception("Unknown modpack: "+name)


@task
def clean():
    print "Cleaning up build dir."
    if os.path.exists(CONF['build_dir']):
        shutil.rmtree(CONF['build_dir'])


@task
def build(*package_types):
    require('modpack', providedBy=[pack])
    if not package_types:
        package_types = list(CONF['package_types'].keys())
    if not os.path.exists(CONF['build_dir']):
        os.makedirs(CONF['build_dir'])
    for pkg in package_types:
        print "Building %s package." % pkg
        path = CONF['modpacks_dir'] +'/'+ env.modpack
        build_zip(zip_name(pkg), path, CONF['package_types'][pkg],
                getattr(sys.modules[__name__], "add_files_"+pkg, add_files_noop)())


@task
def deploy(*package_types):
    require('modpack', providedBy=[pack])
    if not package_types:
        package_types = list(CONF['package_types'].keys())
    for pkg in package_types:
        execute(upload_package, host=env.conf[pkg]['host'], pkg_type=pkg)


def upload_package(pkg_type):
    local_file = '%s/%s' % (CONF['build_dir'], zip_name(pkg_type))
    if os.path.isfile(local_file):
        print "Uploading %s package..." % pkg_type
        put(local_file, env.conf[pkg_type]['dir'])


@task
def debug():
    require('modpack', providedBy=[pack])
    print "Config file: "
    print CONF
    print "Selected modpack: "+env.modpack
    print "Modpack Config: "
    print env.conf
