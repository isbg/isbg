#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from setuptools import setup
import os

ldesc = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()

setup(
	name='isbg',
	version='1.0',
	description=('a script that makes it easy to scan an IMAP inbox for spam using SpamAssassin and get your spam moved to another folder.'),
	long_description=ldesc,
	keywords='email imap spamassasin filter',
	author='Thomas Lecavelier',
	author_email='thomas@lecavelier.name',
	license='See LICENCE file.',
	packages=['isbg'],
	entry_points={
		'console_scripts': [
			'isbg = isbg.isbg:isbg_run',
			'sa_unwrap = isbg.sa_unwrap:run',
		]
	},
	install_requires = ['docopt'],
	url='https://github.com/isbg/isbg',
	classifiers=[
		'Development Status :: 5 - Production/Stable',
		'Environment :: Console',
		'Intended Audience :: System Administrators',
		'Intended Audience :: End Users/Desktop',
		'License :: OSI Approved',
		'Programming Language :: Python :: 2 :: Only',
		'Topic :: Communications :: Email :: Post-Office :: IMAP',
		'Topic :: Communications :: Email :: Filters',
		'Topic :: Utilities',
	]
)
