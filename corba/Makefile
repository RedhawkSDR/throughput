LDFLAGS = -lomniORB4
CXXFLAGS = -g -O2

all: reader writer rawdata/__init__.py

reader: reader.cc rawdataSK.o

writer: writer.cc rawdataSK.o

rawdataSK.cc rawdata.h: idl/rawdata.idl
	omniidl -bcxx $<

rawdata/__init__.py: idl/rawdata.idl
	omniidl -bpython -C .. -Wbpackage=corba $<

clean:
	rm -f reader writer
	rm -r *.o
	rm -f rawdata.hh rawdataSK.cc
	rm -rf rawdata rawdata__POA rawdata_idl.py
	rm -f *.pyc
