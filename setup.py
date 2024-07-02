#!/usr/bin/env python
# coding=utf-8

from setuptools import setup, find_packages


def get_extras():
    return {
        "extra": open("extra-requirements.txt").read().splitlines()
    }


setup(
    name='persist-queue',
    version=__import__('persistqueue').__version__,
    description=(
        'A thread-safe disk based persistent queue in Python.'
    ),
    long_description=open('README.rst').read(),
    long_description_content_type='text/x-rst',
    author=__import__('persistqueue').__author__,
    author_email='wangxu198709@gmail.com',
    maintainer=__import__('persistqueue').__author__,
    maintainer_email='wangxu198709@gmail.com',
    license=__import__('persistqueue').__license__,
    packages=find_packages(),
    extras_require=get_extras(),
    platforms=["all"],
    url='http://github.com/peter-wangxu/persist-queue',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Software Development :: Libraries'
    ],
    package_date={'persistqueue': ['py.typed']}
)
