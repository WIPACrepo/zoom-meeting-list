#!/usr/bin/env python
"""Setup."""

# fmt:off

import glob
import os
import re
import sys
from typing import Any, Dict, List

try:
    # Use setuptools if available, for install_requires (among other things).
    import setuptools  # type: ignore[import]
    from setuptools import setup
except ImportError:
    setuptools = None
    from distutils.core import setup


HERE = os.path.dirname(os.path.realpath(__file__))
REQUIREMENTS_PATH = os.path.join(HERE, "requirements.txt")
REQUIREMENTS = open(REQUIREMENTS_PATH).read().splitlines()
kwargs: Dict[str, Any] = {}


if sys.version_info < (3, 6):
    print('ERROR: ZML requires at least Python 3.6+ to run.')
    sys.exit(1)


# --------------------------------------------------------------------------------------


with open(os.path.join(HERE, 'zml', '__init__.py')) as f:
    for line in f.readlines():
        if '__version__' in line:
            # grab "X.Y.Z" from "__version__ = 'X.Y.Z'" (quote-style insensitive)
            kwargs["version"] = line.replace('"', "'").split("=")[-1].split("'")[1]
            break
    else:
        raise Exception('cannot find __version__')

with open(os.path.join(HERE, 'README.md')) as f:
    kwargs['long_description'] = f.read()


def _get_pypi_requirements() -> List[str]:
    return [
        m.replace("==", ">=")
        for m in REQUIREMENTS
        if ("git+" not in m) and ("pytest" not in m)
    ]


def _get_git_requirements() -> List[str]:
    def valid(req: str) -> bool:
        pat = r"^git\+https://github\.com/[^/]+/[^/]+@(v)?\d+\.\d+\.\d+#egg=\w+$"
        if not re.match(pat, req):
            raise Exception(
                f"from {REQUIREMENTS_PATH}: "
                f"pip-install git-package url is not in standardized format {pat} ({req})"
            )
        return True

    return [m.replace("git+", "") for m in REQUIREMENTS if "git+" in m and valid(m)]


# --------------------------------------------------------------------------------------


if setuptools is not None:
    # If setuptools is not available, you're on your own for dependencies.
    kwargs["install_requires"] = _get_pypi_requirements()
    kwargs["dependency_links"] = _get_git_requirements()
    kwargs['zip_safe'] = False

setup(
    name='zml',
    scripts=glob.glob('bin/*'),
    packages=['zml'],
    package_data={
        # data files need to be listed both here (which determines what gets
        # installed) and in MANIFEST.in (which determines what gets included
        # in the sdist tarball)
        # 'iceprod.server':['data/etc/*','data/www/*','data/www_templates/*'],
    },
    author="IceCube Collaboration",
    author_email="developers@icecube.wisc.edu",
    url="https://github.com/WIPACrepo/zml",
    license="https://github.com/WIPACrepo/zml/blob/master/LICENSE",
    description="zml is the Zoom Meeting List service and related tools, developed for the IceCube Collaboration.",
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        'Operating System :: POSIX :: Linux',
        'Topic :: System :: Distributed Computing',

        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    **kwargs
)
