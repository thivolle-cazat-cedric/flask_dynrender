# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
setup(

    name='flask_dynrender',

    # la version du code
    version='0.0.0',
    packages=find_packages(),
    author="THIVOLLE-CAZAT Cédric",
    description="Flask project to render static jinja files with context",
    # long_description=open('README.md').read(),
    include_package_data=True,
    url='https://github.com/thivolle-cazat-cedric/flask_dynrender',
    classifiers=[
    ],
    install_requires=[
        'Flask',
        'Flask-WTF',
        'Flask-Assets',
        'Flask-Mail',
        'Babel',
        'webassets',
        'PyYAML',
        'validate-email'
    ],
    entry_points={
        'console_scripts': [
        ],
    },
    license="MIT",
)
