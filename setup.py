"""
Setup file for hotdoc.
"""

import os
import errno
import shutil
import subprocess
import tarfile
import unittest
from distutils.command.build import build
from distutils.core import Command

from pkg_resources import parse_version as V
from setuptools import find_packages, setup
from setuptools.command.bdist_egg import bdist_egg
from setuptools.command.develop import develop
from setuptools.command.sdist import sdist
from setuptools.command.test import test

from hotdoc.utils.setup_utils import VersionList, THEME_VERSION

PYGIT2_VERSION = None
try:
    LIBGIT2_VERSION = subprocess.check_output(['pkg-config', '--modversion',
                                               'libgit2']).strip()
    KNOWN_LIBGIT2_VERSIONS = VersionList([V('0.22.0'), V('0.23.0')])
    try:
        KNOWN_LIBGIT2_VERSION = KNOWN_LIBGIT2_VERSIONS.find_le(
            V(LIBGIT2_VERSION))

        if KNOWN_LIBGIT2_VERSION == V('0.22.0'):
            PYGIT2_VERSION = '0.22.1'
        elif KNOWN_LIBGIT2_VERSION == V('0.23.0'):
            PYGIT2_VERSION = '0.23.2'
        else:
            print "WARNING: no compatible pygit version found"
            print "git integration disabled"
    except ValueError:
        print "Warning: too old libgit2 version %s" % LIBGIT2_VERSION
        print "git integration disabled"
except OSError:
    print "Error when trying to figure out the libgit2 version"
    print "pkg-config is probably not installed\n"
    print "git integration disabled"
except subprocess.CalledProcessError:
    print "\nError when trying to figure out the libgit2 version\n"
    print "git integration disabled"

SOURCE_DIR = os.path.abspath('./')


DEFAULT_THEME =\
    'https://people.collabora.com/~meh/hotdoc_bootstrap_theme-%s/dist.tgz' % \
    THEME_VERSION


class DownloadDefaultTemplate(Command):
    """
    This will download the default theme (bootstrap)
    """
    user_options = []
    description = "Download default html template"

    # pylint: disable=missing-docstring
    def initialize_options(self):
        pass

    # pylint: disable=missing-docstring
    def finalize_options(self):
        pass

    # pylint: disable=missing-docstring
    # pylint: disable=no-self-use
    def run(self):
        theme_path = os.path.join(SOURCE_DIR, 'hotdoc', 'default_theme-%s' %
                                  THEME_VERSION)

        if os.path.exists(theme_path):
            return

        # Only installed at setup_requires time, whatever
        # pylint: disable=import-error
        import requests
        response = \
            requests.get(DEFAULT_THEME)

        with open('default_theme.tgz', 'wb') as _:
            _.write(response.content)

        tar = tarfile.open('default_theme.tgz')
        extract_path = os.path.join(SOURCE_DIR, 'hotdoc')
        tar.extractall(extract_path)
        tar.close()

        extract_path = os.path.join(extract_path, 'dist')

        shutil.rmtree(theme_path, ignore_errors=True)

        shutil.move(extract_path, theme_path)

        os.unlink('default_theme.tgz')


def symlink(source, link_name):
    """
    Method to allow creating symlinks on Windows
    """
    os_symlink = getattr(os, "symlink", None)
    if callable(os_symlink):
        os_symlink(source, link_name)
    else:
        import ctypes
        csl = ctypes.windll.kernel32.CreateSymbolicLinkW
        csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        csl.restype = ctypes.c_ubyte
        flags = 1 if os.path.isdir(source) else 0
        if csl(link_name, source, flags) == 0:
            raise ctypes.WinError()


class LinkPreCommitHook(Command):
    """
    This will create links to the pre-commit hook.
    Only called in develop mode.
    """
    user_options = []
    description = "Create links for the style checking pre-commit hooks"

    # pylint: disable=missing-docstring
    def initialize_options(self):
        pass

    # pylint: disable=missing-docstring
    def finalize_options(self):
        pass

    # pylint: disable=missing-docstring
    # pylint: disable=no-self-use
    def run(self):
        try:
            symlink(os.path.join(SOURCE_DIR, 'pre-commit'),
                    os.path.join(SOURCE_DIR, '.git', 'hooks', 'pre-commit'))
        except OSError as error:
            if error.errno != errno.EEXIST:
                raise


# pylint: disable=missing-docstring
# pylint: disable=too-few-public-methods
class CustomDevelop(develop):

    def run(self):
        self.run_command('download_default_template')
        self.run_command('link_pre_commit_hook')
        return develop.run(self)


# pylint: disable=missing-docstring
class CustomBuild(build):

    def run(self):
        self.run_command('download_default_template')
        return build.run(self)


# pylint: disable=missing-docstring
class CustomSDist(sdist):

    def run(self):
        self.run_command('download_default_template')
        return sdist.run(self)


# pylint: disable=missing-docstring
class CustomBDistEgg(bdist_egg):

    def run(self):
        self.run_command('download_default_template')
        return bdist_egg.run(self)


# From http://stackoverflow.com/a/17004263/2931197
def discover_and_run_tests():
    # use the default shared TestLoader instance
    test_loader = unittest.defaultTestLoader

    # use the basic test runner that outputs to sys.stderr
    test_runner = unittest.TextTestRunner()

    # automatically discover all tests
    # NOTE: only works for python 2.7 and later
    test_suite = test_loader.discover(SOURCE_DIR)

    # run the test suite
    test_runner.run(test_suite)


class DiscoverTest(test):
    def __init__(self, *args, **kwargs):
        test.__init__(self, *args, **kwargs)
        self.test_args = []
        self.test_suite = True

    def finalize_options(self):
        test.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        discover_and_run_tests()


INSTALL_REQUIRES = [
    'cffi>=1.1.2,<=1.3.0',
    'pyyaml',
    'wheezy.template==0.1.167',
    'CommonMark==0.6.1',
    'cmarkpy==0.1.3',
    'pygraphviz>=1.3.rc2',
    'sqlalchemy>=1.0.8',
    'ipython>=4.0.0',
    'toposort==1.4']

if PYGIT2_VERSION is not None:
    INSTALL_REQUIRES.append('pygit2==%s' % PYGIT2_VERSION)

EXTRAS_REQUIRE = {
    'dev': ['git-pylint-commit-hook',
            'git-pep8-commit-hook']
}

setup(name='hotdoc',
      version='0.7',
      description='A documentation tool micro-framework',
      keywords='documentation',
      url='https://github.com/hotdoc/hotdoc',
      author='Mathieu Duponchelle',
      author_email='mathieu.duponchelle@opencreed.com',
      license='LGPL',
      packages=find_packages(),

      # Only fancy thing in there now, we want to download a
      # a default theme and bower is shitty.
      cmdclass={'build': CustomBuild,
                'sdist': CustomSDist,
                'develop': CustomDevelop,
                'bdist_egg': CustomBDistEgg,
                'test': DiscoverTest,
                'link_pre_commit_hook': LinkPreCommitHook,
                'download_default_template': DownloadDefaultTemplate},
      scripts=['hotdoc/hotdoc'],
      package_data={
          'hotdoc.formatters': ['html_templates/*', 'html_assets/*'],
          'hotdoc': ['default_theme-%s/templates/*' % THEME_VERSION,
                     'default_theme-%s/js/*' % THEME_VERSION,
                     'default_theme-%s/css/*' % THEME_VERSION,
                     'default_theme-%s/fonts/*' % THEME_VERSION],
      },
      install_requires=INSTALL_REQUIRES,
      extras_require=EXTRAS_REQUIRE,
      setup_requires=['cffi>=1.1.2,<=1.3.0',
                      'requests'])
