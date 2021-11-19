#!/usr/bin/env python3
from setuptools import setup, find_packages

setup(
    name='bandcamp_extract',
    version='0.1.2',
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
    ],
    entry_points={
        'console_scripts': [
            'bcextr = src.extract:extract'
        ]
    },
    install_requires=['click', 'tinytag'],
    python_requires=">=3.6",
    description=('Extract BandCamp .zip album folders to their appropriate '
                 'place'),
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Jonathan Montgomery',
    author_email='jonathan.montgo@gmail.com',
    url='https://github.com/JonMontgo/bandcamp_extract',
    packages=find_packages(),
    include_package_data=True,
)
