# Makefile for Sphinx documentation
#
# NOTE: Best build it in another dir (i.e.: build.sphinx)
#

# You can set these variables from the command line.
SPHINXOPTS       = -a -E -n -t autobuild
SPHINXBUILD      = sphinx-build
SPHINXAPIDOC     = sphinx-apidoc
SPHINXAPIDOCOPTS = --force --separate --private --follow-links
SPHINXPROJ       = isbg
SOURCEDIR        = .
BUILDDIR         = ../build/sphinx
SOURCEPYDIR      = ../isbg

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
	@echo " "
	@echo "  apidoc      to run $(SPHINXAPIDOC)"
	@echo "  clean-all   to clean all generated files"

.PHONY: help Makefile apidoc

# Creates the apidoc
apidoc:
	$(SPHINXAPIDOC) -o "$(SOURCEDIR)" "$(SOURCEPYDIR)" $(SPHINXAPIDOCOPTS)

clean-all:
	@rm -fr "$(BUILDDIR)"

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
