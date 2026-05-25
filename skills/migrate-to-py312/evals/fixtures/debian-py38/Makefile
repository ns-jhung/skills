WHAT                     = PDD Upload Service
SERVICE_NAME             = pdd-upload-service
DEB_PKG_NAME             = pdd-upload-service
DEVELOP_EDITABLE         = yes

VENV_PIP                 = 24.1.2
VENV_SETUPTOOLS          = 72.1.0

## Do not modify the following vars or include logic ##
MK_DIR            = $(NS_BUILD_DIR)/compile
PYTHONPKG_MK_FILE = $(MK_DIR)/pythonpkg-py3.mk
HAVE_MK_PYTHONPKG = $(shell test -r $(PYTHONPKG_MK_FILE) && echo yes)

ifeq ($(strip $(HAVE_MK_PYTHONPKG)),yes)
	include $(PYTHONPKG_MK_FILE)
else
$(error Cannot find $(PYTHONPKG_MK_FILE). Make sure you are building from within the project top-level directory.)
endif
