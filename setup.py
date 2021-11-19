#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name='BandCamp Extractor',
    version='0.1.0',
    entry_points={
        'console_scripts': [
            'bcextr = src.extract:extract'
        ]
    },
    install_requires=['click', 'tinytag'],
    python_requires=">=3.6",
    description=('Extract BandCamp .zip album folders to their appropriate '
                 'place'),
    author='Jonathan Montgomery',
    author_email='jonathan.montgo@gmail.com',
    url='https://github.com/JonMontgo/bandcamp_extract',
    packages=find_packages(),
    include_package_data=True,
)
