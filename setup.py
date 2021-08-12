# Copyright (c) 2021 Julien Peloton
#
# This file is part of TOM Toolkit
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
from setuptools import setup, find_packages
from os import path

from tom_fink import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='tom-fink',
    version=__version__,
    description='Fink broker module for the TOM Toolkit',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/TOMToolkit/tom_fink',
    author='JulienPeloton',
    author_email='peloton@lal.in2p3.fr',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering :: Astronomy',
        'Topic :: Scientific/Engineering :: Physics'
    ],
    keywords=[
        'tomtoolkit',
        'astronomy',
        'astrophysics',
        'cosmology',
        'science',
        'observatory',
        'alert',
        'broker',
        'fink'
    ],
    packages=find_packages(),
    use_scm_version=False,
    setup_requires=['setuptools_scm', 'wheel'],
    install_requires=[
        'tomtoolkit~=2.7.0',
        'elasticsearch-dsl~=7.3.0',
        'markdown'
    ],
    extras_require={
        'test': ['factory_boy>=3.1,<3.3']
    },
    include_package_data=True,
)
