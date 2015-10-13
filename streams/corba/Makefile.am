AM_LDFLAGS = $(OMNIORB_LIBS)
AM_CPPFLAGS = $(OMNIORB_CFLAGS) -I $(top_srcdir)/common

noinst_PROGRAMS = reader writer

reader_SOURCES = reader.cpp rawdataSK.cpp
writer_SOURCES = writer.cpp rawdataSK.cpp

BUILT_SOURCES = rawdataSK.cpp rawdata.h rawdata/__init__.py
CLEANFILES = $(BUILT_SOURCES) rawdata_idl.py

%SK.cpp %.h: idl/%.idl
	omniidl -bcxx -Wbh=.h -Wbs=SK.cpp $<

%/__init__.py: idl/%.idl
	omniidl -bpython -C ../.. -Wbpackage=streams.corba $<

clean-local:
	-rm -rf rawdata rawdata__POA
