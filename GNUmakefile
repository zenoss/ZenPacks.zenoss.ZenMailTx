######################################################################
#
# Copyright 2007 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

ZP_DIR=$(PWD)/ZenPacks/zenoss/ZenMailTx
LIB_DIR=$(ZP_DIR)/lib
BIN_DIR=$(ZP_DIR)/bin
PYTHON=$(shell which python2.4)

OPENSSL=$(patsubst src/%.tar.gz,%,$(wildcard src/pyOpenSSL*.tar.gz))

default: egg


egg:
    # setup.py will call 'make build' before creating the egg
	python setup.py bdist_egg


build:
	rm -rf $(OPENSSL)
	mkdir -p build $(LIB_DIR) $(BIN_DIR)
	cd build ; gzip -dc ../src/$(OPENSSL).tar.gz | tar -xf -
	cd build/$(OPENSSL) ; $(PYTHON) setup.py install	\
				--install-lib="$(LIB_DIR)"	\
				--install-scripts="$(BIN_DIR)"


clean:
	rm -rf build dist
	rm -rf *.egg-info
	find . -name *.pyc | xargs rm
	rm -rf $(LIB_DIR) $(BIN_DIR)
