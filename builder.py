__author__ = 'jonathan'

import os
import urllib
import zipfile

PACKAGE_PATTERN = "%(pack)s-%(version)s-%(package)s"
TECHNIC_DEFAULTS = {
    'forge_cache_dir': '.forge-cache',
    'forge_jar_pattern': 'forge-%(version)s-universal.jar',
    'forge_url_pattern': 'http://files.minecraftforge.net/maven/net/minecraftforge/forge/%(version)s/%(jar)s',
    'forge_package_path': 'bin/modpack.jar'
}


class BuilderException(Exception):
    pass


def _setup(build_dir):
    if not os.path.isdir(build_dir):
        os.makedirs(build_dir)
    if not os.access(build_dir, os.W_OK):
        raise BuilderException("Build Directory is not writable.")


def _pkg_name(config, package_type):
    return config.get('package_pattern', PACKAGE_PATTERN) % {
        'pack': config.get('package_name', 'unknown-modpack'),
        'version': config.get('version', '0.0'),
        'package': package_type
    }


def _zip_directory(zf, path):
    print "Zipping: " + path
    path_len = len(path)
    for root, dirs, files in os.walk(path):
        for f in files:
            if not f.startswith('.'):
                fp = os.path.join(root, f)
                zf.write(fp, fp[path_len:])


def _get_forge(version):
    cache_dir = TECHNIC_DEFAULTS['forge_cache_dir']
    if not os.path.isdir(cache_dir):
        os.makedirs(cache_dir)
    jar_name = TECHNIC_DEFAULTS['forge_jar_pattern'] % version
    jar_file = cache_dir + '/' + jar_name
    if not os.path.isfile(jar_file):
        jar_url = TECHNIC_DEFAULTS['forge_url_pattern'] % {
            'version': version,
            'jar': jar_name
        }
        urllib.urlretrieve(jar_url, jar_file)
    return jar_file


def _build_vanilla(build_dir, package_name, pack_basedir, conf):
    print "Buliding vanilla package '%s'" % package_name
    zip_name = build_dir + '/' + package_name + '.zip'
    dirs = []
    if 'directories' in conf:
        dirs.extend(conf['directories'])
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zf:
        for dir_ in dirs:
            _zip_directory(zf, pack_basedir + '/' + dir_)
        zf.close()
    return zip_name


def _build_technic(build_dir, package_name, pack_basedir, conf):
    pkg = _build_vanilla(build_dir, package_name, pack_basedir, conf)
    with zipfile.ZipFile(pkg, 'a', zipfile.ZIP_DEFLATED) as zf:
        forge_jar = _get_forge(conf['forge_version'])
        zf.write(forge_jar, TECHNIC_DEFAULTS['forge_package_path'])
        zf.close()
    return pkg


BUILDERS = {
    'vanilla': _build_vanilla,
    'technic': _build_technic
}


def build(build_dir, config, package_type, pack_basedir):
    _setup(build_dir)
    pkg_config = config['packages'][package_type]
    builder = 'vanilla'
    if 'builder' in pkg_config:
        builder = pkg_config['builder']
    if builder not in BUILDERS:
        raise BuilderException("Unknown builder type" + builder)
    package_name = _pkg_name(config, package_type)
    return BUILDERS[builder](
        build_dir, package_name, pack_basedir, pkg_config)

