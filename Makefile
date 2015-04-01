LDFLAGS = -lrt -pthread
CXXFLAGS = -pthread -g -O2

throughput: throughput.cc transport.cc

clean:
	rm -f throughput
