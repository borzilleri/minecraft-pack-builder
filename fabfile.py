import os
import shutil
import pprint

import yaml
from fabric.api import *

import builder


PACK_CONF = {}
DEFAULTS = {
    'config_file': 'config.yml',
    'build_dir': 'build'
}
DEFAULT_PACK_KEY = "_default"
PACK_LIST_FILENAME = ".modpacks.yml"
PACKS = {}

if os.path.exists(PACK_LIST_FILENAME):
    with open(PACK_LIST_FILENAME, "r") as pack_file:
        PACKS.update(yaml.load(pack_file))


# def upload_package(pkg_type):
# local_file = build_zip_name(pkg_type)
#    if os.path.isfile(local_file):
#        print "Uploading %s package..." % pkg_type
#        put(local_file, CONF[pkg_type]['dir'])
class PackageException(Exception):
    pass


@task
def debug():
    _default_pack()
    pp = pprint.PrettyPrinter(indent=2)
    pp.pprint(PACKS)
    pp.pprint(PACK_CONF)


@task(name="add")
def add_pack(pack_name, pack_path, default_pack=False):
    pack_path = os.path.abspath(os.path.expanduser(pack_path))
    # TODO: Improve validation of config file maybe?
    if pack_name in PACKS and PACKS[pack_name] == pack_path:
        print "%s already exists with path %s" % (pack_name, pack_path)
    elif not os.path.isdir(pack_path):
        print "%s is not a directory" % pack_path
    elif not os.path.isfile(pack_path + "/" + DEFAULTS['config_file']):
        print "No %s found in %s" % (DEFAULTS['config_file'], pack_path)
    else:
        PACKS[pack_name] = pack_path
        if default_pack:
            PACKS[DEFAULT_PACK_KEY] = pack_name
        with open(PACK_LIST_FILENAME, 'w') as pf:
            pf.write(yaml.dump(PACKS))
            pf.close()
        print "Added pack %s at %s" % (pack_name, pack_path)


@task(name="remove")
def remove_packs(pack_name):
    if pack_name not in PACKS:
        print "Unknown pack %s" % pack_name
    else:
        if DEFAULT_PACK_KEY in PACKS and PACKS[DEFAULT_PACK_KEY] == pack_name:
            PACKS[DEFAULT_PACK_KEY] = None
        PACKS.pop(pack_name, None)
        with open(PACK_LIST_FILENAME, 'w') as pf:
            pf.write(yaml.dump(PACKS))
            pf.close()
        print "Removed pack %s" % pack_name


@task(name="list")
def list_packs():
    print "Known Packs:"
    for pack_name in PACKS:
        print "%s : %s" % (pack_name, PACKS[pack_name])


def _default_pack():
    if DEFAULT_PACK_KEY in PACKS and PACKS[DEFAULT_PACK_KEY] in PACKS:
        pack(PACKS[DEFAULT_PACK_KEY])


@task
def clean():
    print "Cleaning build directory."
    if os.path.exists(DEFAULTS['build_dir']):
        shutil.rmtree(DEFAULTS['build_dir'])


@task
def pack(name):
    if name not in PACKS:
        raise Exception("Unknown modpack: " + name)
    pack_config_file = PACKS[name] + '/' + DEFAULTS['config_file']
    if not os.path.isfile(pack_config_file):
        raise Exception("Pack '%s' has no config file." % name)
    with open(pack_config_file, "r") as cf:
        PACK_CONF.update(yaml.load(cf))
    env.modpack = name


def _require_pack():
    if DEFAULT_PACK_KEY in PACKS and PACKS[DEFAULT_PACK_KEY] in PACKS:
        pack(PACKS[DEFAULT_PACK_KEY])
    require('modpack', providedBy=[pack])


@task
def build(*packages):
    _require_pack()
    if 'packages' not in PACK_CONF or not PACK_CONF['packages']:
        raise PackageException("Pack config does not define any packages.")
    if not packages:
        packages = PACK_CONF['packages']
    for pkg in packages:
        if pkg not in PACK_CONF['packages']:
            print "Cannot find package definition: " + pkg
        else:
            builder.build(DEFAULTS['build_dir'], PACK_CONF, pkg,
                PACKS[env.modpack])


@task
def deploy(*packages):
    _require_pack()
    if 'packages' not in PACK_CONF or not PACK_CONF['packages']:
        raise PackageException("Pack config does not define any packages.")
    for pkg in packages:
        if pkg not in PACK_CONF['packages']:
            print "Cannot find package definition: " + pkg
        else:
            # Do Upload
