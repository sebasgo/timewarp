#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst', encoding='utf-8') as readme_file:
    readme = readme_file.read()

with open('CHANGES.rst', encoding='utf-8') as history_file:
    changes = history_file.read()

REQUIREMENTS = [
    'textual',
]

DEV_REQUIREMENTS = [
    'check-manifest',
    'docutils<0.19',
    'pylint',
    'pytest',
    'pytest-cov',
    'pytest-mock',
    'textual-dev',
    'wheel',
]

setup(
    name='timewarp',
    author='Sebastian Gottfried',
    version='0.1.0',
    description="Return to days begone.",
    long_description=readme + '\n\n' + changes,
    python_requires='>=3.8',
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=REQUIREMENTS,
    extras_require={
        'dev': DEV_REQUIREMENTS,
    },
    entry_points={
        'console_scripts': [
            'timewarp=timewarp.__main__:main',
        ],
    },
)
