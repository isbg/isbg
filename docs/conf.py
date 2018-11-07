# -*- coding: utf-8 -*-
#
"""Conf file for isbg docs using sphinx."""

import re
from ast import literal_eval
import os
import sys
import recommonmark


# -- Custom variables -----------------------------------------------------

cvar_github_base_uri = 'https://github.com/'
cvar_github_prj = 'isbg'
cvar_github_usr = 'isbg'
cvar_github_uri = cvar_github_base_uri + cvar_github_prj + '/' + \
    cvar_github_usr
cvar_pypi_uri = 'https://pypi.python.org/pypi/isbg'

master_doc = 'index'  # The master toctree document.

project = u'isbg'
copyright = u'''License GPLv3: GNU GPL version 3 https://gnu.org/licenses/gpl.html

This is free software: you are free to change and redistribute it. There is
NO WARRANTY, to the extent permitted by law.'''

author = u'''See the CONTRIBUTORS file in the git repository for more
information on who wrote and maintains this software'''

# We get the version from isbg/isbg.py
_VERSION_RE = re.compile(r'__version__\s+=\s+(.*)')
with open('../isbg/isbg.py', 'rb') as f:
    _VERSION = str(literal_eval(_VERSION_RE.search(
        f.read().decode('utf-8')).group(1)))

sys.path.insert(0, os.path.abspath('..'))


# -- Extensions -----------------------------------------------------------

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.doctest',
              'sphinx.ext.intersphinx',
              'sphinx.ext.napoleon',
              'sphinx.ext.coverage',
              'sphinx.ext.mathjax',
              'sphinx.ext.ifconfig',
              'sphinx.ext.extlinks',
              'sphinx.ext.githubpages',
              'sphinx.ext.autosummary',
              'sphinx.ext.todo'
              ]

source_suffix = ['.rst']

version = _VERSION
release = _VERSION

pygments_style = 'sphinx'


# -- Options for todo extension -------------------------------------------

todo_include_todos = True


# -- Options for autodoc extension ----------------------------------------

autodoc_member_order = 'bysource'
autodoc_default_flags = ['members']

autodoc_docstring_signature = False
autodoc_mock_imports = []
autodoc_warningiserror = True

# Enable nitpicky mode - which ensures that all references in the docs
# resolve.

nitpicky = True
nitpick_ignore = []

for line in open('nitpick-exceptions'):
    if line.strip() == "" or line.startswith("#"):
        continue
    dtype, target = line.split(None, 1)
    target = target.strip()
    nitpick_ignore.append((dtype, target))


# -- Options for napoleon extension ---------------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True


# -- Options for extlinks extension ---------------------------------------

extlinks = {
    'issue': (cvar_github_uri + '/issues/%s', 'issue '),  # e.g. :issue:`12`
    'pull': (cvar_github_uri + '/pull/%s', 'pull ')      # e.g. :pull:`11`
}


# -- Options for HTML output ----------------------------------------------

html_theme = 'sphinx_rtd_theme'

# For theme 'sphinx_rtd_theme':
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'collapse_navigation': False,
    'sticky_navigation': True,
    'navigation_depth': 3,
}

html_sidebars = {
    '**': [
        'about.html',
        'navigation.html',
        'searchbox.html',
        'relations.html',
    ]
}


# -- Options for HTMLHelp output ------------------------------------------

htmlhelp_basename = 'isbgdoc'


# -- Options for manual page output ---------------------------------------

man_pages = [
    ('manpage.isbg', 'isbg', u'scans an IMAP Inbox and runs every entry ' +
     u'against SpamAssassin.',
     [author], 1),
    ('manpage.isbg_sa_unwrap', 'isbg_sa_unwrap', u'unwraps a email bundeled ' +
     u'by SpamAssassin.',
     [author], 1),
]

intersphinx_mapping = {'https://docs.python.org/': None}


# -- Read the Docs integration: generate the documentation from sources -----

def run_apidoc(_):
    """Run apidoc."""
    try:
        from sphinx.ext.apidoc import main  # sphinx => 1.7.0b1
    except ImportError:
        from sphinx.apidoc import main
    import os
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    module = os.path.join(cur_dir, "..", project)
    params = ['-e', '--force', '--separate', '--private', '--follow-links',
              '-o', cur_dir, module]
    main(params)


def import_rsts(_):
    """Copy rst files from base dir to cur dir."""
    import glob
    import shutil
    import os
    import sys
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    for file in glob.glob('../*.rst'):
        shutil.copy2(file, cur_dir)


def import_mds(_):
    """Copy md files from base dir to cur dir."""
    import glob
    import shutil
    import os
    import sys
    cur_dir = os.path.abspath(os.path.dirname(__file__))
    for file in glob.glob('../*.md'):
        shutil.copy2(file, cur_dir)


def setup(app):
    """Configure sphinx."""
    app.connect('builder-inited', run_apidoc)
    app.connect('builder-inited', import_rsts)
