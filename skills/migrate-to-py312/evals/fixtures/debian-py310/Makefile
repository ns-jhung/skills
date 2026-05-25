WHAT                     = "EDR Client"
PYTHON_VERSION           ?= py310
COMPONENT_DIR            = $(NS_BUILD_DIR)/components/edr-client
APP_ENV_YML              = $(COMPONENT_DIR)/app-env-$(PYTHON_VERSION).yaml
SERVICE_NAME             = edr-client
DEB_PKG_NAME             = edr-client
DEVELOP_EDITABLE         = yes

VENV_PIP                 = 24.1.2
VENV_SETUPTOOLS          = 72.1.0

## Do not modify the following vars or include logic ##
MK_DIR            = $(NS_BUILD_DIR)/compile
PYTHONPKG_MK_FILE = $(MK_DIR)/conda-build.mk
HAVE_MK_PYTHONPKG = $(shell test -r $(PYTHONPKG_MK_FILE) && echo yes)

ifeq ($(strip $(HAVE_MK_PYTHONPKG)),yes)
	include $(PYTHONPKG_MK_FILE)
else
$(error Cannot find $(PYTHONPKG_MK_FILE). Make sure you are building from within the project top-level directory.)
endif
