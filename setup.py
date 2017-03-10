#!/usr/bin/env python
# coding=utf-8

from setuptools import setup, find_packages

setup(
    name='persist-queue',
    version=__import__('persistqueue').__version__,
    description=(
        'A thread-safe disk based persistent queue in Python.'
    ),
    long_description=open('README.rst').read(),
    author='Peter Wang',
    author_email='wangxu198709@gmail.com',
    maintainer='Peter Wang',
    maintainer_email='wangxu198709@gmail.com',
    license='BSD License',
    packages=find_packages(),
    platforms=["all"],
    url='http://github.com/peter-wangxu/persist-queue',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Operating System :: OS Independent',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Libraries'
    ],
)
