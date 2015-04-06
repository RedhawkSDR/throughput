LDFLAGS = -lrt -pthread
CXXFLAGS = -pthread -g -O2

all: reader writer throughput

throughput: throughput.cc transport.cc

reader: reader.cc

writer: writer.cc

clean:
	rm -f throughput
