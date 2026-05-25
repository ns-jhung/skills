WHAT         = "Client status reporting service"
PYTHON_VERSION          ?= py310
COMPONENT_DIR            = $(NS_BUILD_DIR)/components/stork-debian-py310
APP_ENV_YML              = $(COMPONENT_DIR)/app-env-$(PYTHON_VERSION).yaml
SERVICE_NAME = "clientstatus"
DEB_PKG_NAME = "clientstatus"
REQUIRE_NETSKOPE_COMMON = "no"

PYTHON_LOCAL_BINARY_PATH =

VIRTUALENV_PYPI_TYPE=unbounded

STORK_COMPONENT_NAME = clientstatus
FIRST_LOCAL_COMPONENT_TARGETS = publish
include $(NS_BUILD_DIR)/compile/stork-build.mk

## Do not modify the following vars or include logic ##
MK_DIR             = $(NS_BUILD_DIR)/compile
PYTHONPKG_MK_FILE = $(MK_DIR)/conda-build.mk
HAVE_MK_PYTHONPKG = $(shell test -r $(PYTHONPKG_MK_FILE) && echo yes)

ifeq ($(strip $(HAVE_MK_PYTHONPKG)),yes)
	include $(PYTHONPKG_MK_FILE)
else
$(error Cannot find $(PYTHONPKG_MK_FILE). Make sure you are building from within the project top-level directory.)
endif

deb-install-package-items::
	@echo "(no extra files to install)"
