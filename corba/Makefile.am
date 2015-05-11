AM_LDFLAGS = $(OMNIORB_LIBS)
AM_CPPFLAGS = $(OMNIORB_CFLAGS) -I $(top_srcdir)/common

noinst_PROGRAMS = reader writer

reader_SOURCES = reader.cc rawdataSK.cc
writer_SOURCES = writer.cc rawdataSK.cc

BUILT_SOURCES = rawdataSK.cc rawdata.hh rawdata/__init__.py
CLEAN_FILES = $(BUILT_SOURCES)

rawdataSK.cc rawdata.hh: idl/rawdata.idl
	omniidl -bcxx $<

rawdata/__init__.py: idl/rawdata.idl
	omniidl -bpython -C .. -Wbpackage=corba $<

clean-local:
	-rm -rf rawdata rawdata__POA
