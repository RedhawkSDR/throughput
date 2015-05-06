OMNITHREAD_LIBS = $(shell pkg-config --libs omnithread3)
OMNITHREAD_CFLAGS = $(shell pkg-config --cflags omnithread3)
LDFLAGS = -lrt $(OMNITHREAD_LIBS)
CXXFLAGS = -g -O2
CPPFLAGS = $(OMNITHREAD_CFLAGS)

all: reader writer

reader: reader.cc control.o

writer: writer.cc control.o

clean:
	rm -f reader writer
