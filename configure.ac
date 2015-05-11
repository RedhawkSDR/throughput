AC_INIT([throughput], 1.0.0)
AM_INIT_AUTOMAKE([foreign])

AC_PROG_CC
AC_PROG_CXX
AC_PROG_INSTALL

AC_CORBA_ORB
OSSIE_CHECK_OSSIE
OSSIE_SDRROOT_AS_PREFIX

m4_ifdef([AM_SILENT_RULES], [AM_SILENT_RULES([yes])])

# Dependencies
PKG_CHECK_MODULES([OMNITHREAD], [omnithread3])
PKG_CHECK_MODULES([OMNIORB], [omniORB4 >= 4.1.0])
PKG_CHECK_MODULES([PROJECTDEPS], [ossie >= 1.10 omniORB4 >= 4.1.0])
PKG_CHECK_MODULES([INTERFACEDEPS], [bulkio >= 1.10])
OSSIE_ENABLE_LOG4CXX
AX_BOOST_BASE([1.41])
AX_BOOST_SYSTEM
AX_BOOST_THREAD
AX_BOOST_REGEX

AC_CONFIG_FILES([Makefile \
                 corba/Makefile \
                 raw/Makefile \
                 rhbulkio/reader/cpp/Makefile rhbulkio/writer/cpp/Makefile])
AC_OUTPUT

