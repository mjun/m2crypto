#!/usr/bin/env python

"""
setuptools based installer for M2Crypto.

Copyright (c) 1999-2004, Ng Pheng Siong. All rights reserved.

Portions created by Open Source Applications Foundation (OSAF) are
Copyright (C) 2004-2007 OSAF. All Rights Reserved.

Copyright 2008-2011 Heikki Toivonen. All rights reserved.

Copyright 2018 Daniel Wozniak. All rights reserved.
"""
import glob
import logging
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import setuptools

from typing import Dict, List

if sys.version_info[:2] < (3, 10):
    from distutils.command import build
    from distutils.dir_util import mkpath
else:
    from setuptools.command import build

from setuptools.command import build_ext

logging.basicConfig(format='%(levelname)s:%(funcName)s:%(message)s',
                    stream=sys.stdout, level=logging.INFO)
log = logging.getLogger('setup')

requires_list = []


def _get_additional_includes():
    if os.name == 'nt':
        globmask = os.path.join('C:', os.sep, 'Program Files*',
                                '*Visual*', 'VC', 'include')
        err = glob.glob(globmask)
    else:
        cpp = shlex.split(os.environ.get('CPP', 'cpp'))
        pid = subprocess.Popen(cpp + ['-Wp,-v', '-'],
                               stdin=open(os.devnull, 'r'),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        _, err = pid.communicate()
        err = [line.lstrip() for line in err.decode('utf8').split('\n')
               if line and line.startswith(' /')]

    log.debug('additional includes:\n%s', err)
    return err


def openssl_version(ossldir, req_ver, required=False):
    # type: (str, int, bool) -> bool
    """
    Compare version of the installed OpenSSL with the maximum required version.

    :param ossldir: the directory where OpenSSL is installed
    :param req_ver: required version as integer (e.g. 0x10100000)
    :param required: whether we want bigger-or-equal or less-than
    :return: Boolean indicating whether the satisfying version of
             OpenSSL has been installed.
    """
    try:
        import ctypes
        libssl = ctypes.cdll.LoadLibrary("libssl.so")
        ver = libssl.OpenSSL_version_num()
        log.debug("ctypes: ver = %s", hex(ver))
    # for OpenSSL < 1.1.0
    except (AttributeError, FileNotFoundError):
        ver = None
        file = os.path.join(ossldir, 'include', 'openssl', 'opensslv.h')

        with open(file) as origin_file:
            for line in origin_file:
                m = re.match(
                    r'^# *define  *OPENSSL_VERSION_NUMBER  *(0x[0-9a-fA-F]*)',
                    line)
                if m:
                    log.debug('found version number: %s\n', m.group(1))
                    ver = int(m.group(1), base=16)
                    break

        log.debug("parsing header file: ver = %s", hex(ver))

        if ver is None:
            raise OSError('Unknown format of file %s\n' % file)

    if required:
        return ver >= req_ver
    else:
        return ver < req_ver


class _M2CryptoBuild(build.build):
    """Enable swig_opts to inherit any include_dirs settings made elsewhere."""

    user_options = build.build.user_options + \
        [('openssl=', 'o', 'Prefix for openssl installation location')] + \
        [('bundledlls', 'b', 'Bundle DLLs (win32 only)')]

    def initialize_options(self):
        """Overload to enable custom openssl settings to be picked up."""
        build.build.initialize_options(self)
        self.openssl = None
        self.bundledlls = None


class _M2CryptoBuildExt(build_ext.build_ext):
    """Enable swig_opts to inherit any include_dirs settings made elsewhere."""

    user_options = build_ext.build_ext.user_options + \
        [('openssl=', 'o', 'Prefix for openssl installation location')] + \
        [('bundledlls', 'b', 'Bundle DLLs (win32 only)')]

    def initialize_options(self):
        """Overload to enable custom openssl settings to be picked up."""
        build_ext.build_ext.initialize_options(self)
        self.openssl = None
        self.bundledlls = None

    def finalize_options(self):
        # type: (None) -> None
        """Append custom openssl include file and library linking options."""
        build_ext.build_ext.finalize_options(self)
        self.openssl_default = None
        self.set_undefined_options('build', ('openssl', 'openssl'))
        if self.openssl is None:
            self.openssl = self.openssl_default
        self.set_undefined_options('build', ('bundledlls', 'bundledlls'))

        self.libraries = ['ssl', 'crypto']
        if sys.platform == 'win32':
            self.libraries = ['ssleay32', 'libeay32']
            if self.openssl and openssl_version(self.openssl,
                                                0x10100000, True):
                self.libraries = ['libssl', 'libcrypto']
                self.swig_opts.append('-D_WIN32')
                # Swig doesn't know the version of MSVC, which causes
                # errors in e_os2.h trying to import stdint.h. Since
                # python 2.7 is intimately tied to MSVC 2008, it's
                # harmless for now to define this. Will come back to
                # this shortly to come up with a better fix.
                self.swig_opts.append('-D_MSC_VER=1500')

        self.swig_opts.append('-py3')

        # swig seems to need the default header file directories
        self.swig_opts.extend(['-I%s' % i for i in _get_additional_includes()])

        log.debug('self.include_dirs = %s', self.include_dirs)
        log.debug('self.library_dirs = %s', self.library_dirs)

        if self.openssl is not None:
            log.debug('self.openssl = %s', self.openssl)
            openssl_library_dir = os.path.join(self.openssl, 'lib')
            openssl_include_dir = os.path.join(self.openssl, 'include')

            self.library_dirs.append(openssl_library_dir)
            self.include_dirs.append(openssl_include_dir)

            log.debug('self.include_dirs = %s', self.include_dirs)
            log.debug('self.library_dirs = %s', self.library_dirs)

        if platform.system() == "Linux":
            # For RedHat-based distros, the '-D__{arch}__' option for
            # Swig needs to be normalized, particularly on i386.
            mach = platform.machine().lower()
            if mach in ('i386', 'i486', 'i586', 'i686'):
                arch = '__i386__'
            elif mach in ('ppc64', 'powerpc64', 'ppc64le', 'ppc64el'):
                arch = '__powerpc64__'
            elif mach in ('ppc', 'powerpc'):
                arch = '__powerpc__'
            else:
                arch = '__%s__' % mach
            self.swig_opts.append('-D%s' % arch)
            if mach in ('ppc64le', 'ppc64el'):
                self.swig_opts.append('-D_CALL_ELF=2')
            if mach in ('arm64_be'):
                self.swig_opts.append('-D__AARCH64EB__')

        self.swig_opts.extend(['-I%s' % i for i in self.include_dirs])

        # Some Linux distributor has added the following line in
        # /usr/include/openssl/opensslconf.h:
        #
        #     #include "openssl-x85_64.h"
        #
        # This is fine with C compilers, because they are smart enough to
        # handle 'local inclusion' correctly.  Swig, on the other hand, is
        # not as smart, and needs to be told where to find this file...
        #
        # Note that this is risky workaround, since it takes away the
        # namespace that OpenSSL uses.  If someone else has similarly
        # named header files in /usr/include, there will be clashes.
        if self.openssl is None:
            self.swig_opts.append('-I/usr/include/openssl')
        else:
            self.swig_opts.append(
                '-I' + os.path.join(openssl_include_dir, 'openssl'))

        self.swig_opts.append('-includeall')
        self.swig_opts.append('-modern')
        self.swig_opts.append('-builtin')

        build_dir = os.path.join(self.build_lib, 'M2Crypto')
        os.makedirs(build_dir, exist_ok=True)

        # These two lines are a workaround for
        # http://bugs.python.org/issue2624 , hard-coding that we are only
        # building a single extension with a known path; a proper patch to
        # distutils would be in the run phase, when extension name and path are
        # known.
        self.swig_opts.extend(['-outdir', build_dir])
        self.include_dirs.append(os.path.join(os.getcwd(), 'src', 'SWIG'))

        if sys.platform == 'cygwin' and self.openssl is not None:
            # Cygwin SHOULD work (there's code in distutils), but
            # if one first starts a Windows command prompt, then bash,
            # the distutils code does not seem to work. If you start
            # Cygwin directly, then it would work even without this change.
            # Someday distutils will be fixed and this won't be needed.
            self.library_dirs += [os.path.join(self.openssl, 'bin')]

        os.makedirs(os.path.join(self.build_lib, 'M2Crypto'), exist_ok=True)

    def run(self):
        """
        On Win32 platforms include the openssl dll's in the binary packages
        """

        # Win32 bdist builds must use --openssl in the builds step.
        if not self.bundledlls:
            build_ext.build_ext.run(self)
            return

        if sys.platform == 'win32':
            ver_part = ''
            if self.openssl and openssl_version(self.openssl,
                                                0x10100000, True):
                ver_part += '-1_1'
            if sys.maxsize > 2**32:
                ver_part += '-x64'
            search = list(self.library_dirs)
            if self.openssl:
                search = search + [self.openssl,
                                   os.path.join(self.openssl, 'bin')]
            libs = list(self.libraries)
            for libname in list(libs):
                for search_path in search:
                    dll_name = '{0}{1}.dll'.format(libname, ver_part)
                    dll_path = os.path.join(search_path, dll_name)
                    if os.path.exists(dll_path):
                        shutil.copy(dll_path, 'M2Crypto')
                        libs.remove(libname)
                        break
            if libs:
                raise Exception("Libs not found {}".format(','.join(libs)))
        build_ext.build_ext.run(self)


x_comp_args = set()

# We take care of deprecated functions in OpenSSL with our code, no need
# to spam compiler output with it.
if sys.platform == 'win32':
    x_comp_args.update(['-DTHREADING', '-D_CRT_SECURE_NO_WARNINGS'])
else:
    x_comp_args.update(['-DTHREADING', '-Wno-deprecated-declarations'])

m2crypto = setuptools.Extension(name='M2Crypto._m2crypto',
                                sources=['src/SWIG/_m2crypto.i'],
                                extra_compile_args=list(x_comp_args),
                                # Uncomment to build Universal Mac binaries
                                # extra_link_args =
                                #     ['-Wl,-search_paths_first'],
                                )


setuptools.setup(
    ext_modules=[m2crypto],
    cmdclass={
        'build_ext': _M2CryptoBuildExt,
        'build': _M2CryptoBuild
    }
)
