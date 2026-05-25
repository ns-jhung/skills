WHAT         = "Uses nstenantcleanup for dyn deprovisioning"
SERVICE_NAME = "nsdyncleanup"
DEB_PKG_NAME = "nsdyncleanup"
REQUIRE_NETSKOPE_COMMON = "no"

PYTHON_LOCAL_BINARY_PATH =

VIRTUALENV_PYPI_TYPE=unbounded

STORK_COMPONENT_NAME = dyncleanup
FIRST_LOCAL_COMPONENT_TARGETS = publish
include $(NS_BUILD_DIR)/compile/stork-build.mk

# Generally used when creating a python package based on netskope common.ns
# code. Format is:
#  src_in_common:dest_in_pkg
#  OVERLAY_FILES = $(NS_BUILD_DIR)/common/netskope/log/*.py:src/netskope/log
#

include $(NS_BUILD_DIR)/compile/pythonpkg-py3.mk
