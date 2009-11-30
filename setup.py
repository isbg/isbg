#!/usr/bin/env python
#coding=utf8

from setuptools import setup
import os

ldesc = open(os.path.join(os.path.dirname(__file__), 'README')).read()

setup(
	name='isbg',
	version='0.98',
	description=('a script that makes it easy to scan an IMAP inbox for spam using SpamAssassin and get your spam moved to another folder.'),
	long_description=ldesc,
	keywords='email imap spamassasin filter',
	author='Thomas Lecavelier',
	author_email='thomas@lecavelier.name',
	license='See LICENCE file.',
	scripts=['isbg.py'],
	url='http://redmine.ookook.fr/projects/isbg',
	classifiers=[
		'Development Status :: 5 - Production/Stable',
		'Environment :: Console',
		'Intended Audience :: System Administrators',
		'Intended Audience :: End Users/Desktop',
		'License :: OSI Approved',
		'Programming Language :: Python',
		'Topic :: Communications :: Email :: Post-Office :: IMAP',
		'Topic :: Communications :: Email :: Filters',
		'Topic :: Utilities',
	]
)
