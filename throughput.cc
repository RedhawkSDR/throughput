#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <algorithm>
#include <stdexcept>

#include <time.h>
#include <unistd.h>
#include <getopt.h>
#include <pthread.h>

#include "transport.hh"

std::string format_time(double seconds)
{
    static const char* units[] = {
        "sec",
        "msec",
        "usec",
        "nsec",
    };
    int exponent = std::max(0.0, std::ceil(std::log10(seconds)/-3.0));

    std::ostringstream oss;
    oss << (seconds*std::pow(1000, exponent)) << ' ' << units[exponent];
    return oss.str();
}

std::string format_throughput(double bps)
{
    static const char* units[] = {
        "Bps"
        "KBps",
        "MBps",
        "GBps",
    };
    if (bps <= 0.0) {
        return "0";
    }
    std::ostringstream oss;
    int exponent = std::log(bps)/log(1024);
    bps /= (int)pow(1024, exponent);
    oss << bps << ' ' << units[exponent-1];
    return oss.str();
}

int parse_number(const std::string& text)
{
    std::istringstream iss(text);
    int result;
    iss >> result;
    if (!iss) {
        throw std::invalid_argument("not a number: " + text);
    }
    if (!iss.eof()) {
        // Assume next character is a suffix
        char suffix;
        iss >> suffix;
        std::string::size_type exponent = std::string("kmg").find(std::tolower(suffix));
        if (exponent == std::string::npos) {
            throw std::invalid_argument("invalid suffix '" + std::string(1, suffix) + "'");
        }
        result *= std::pow(1024, exponent+1);

        // There should be no more characters left in the string
        if (iss.peek() != EOF) {
            throw std::invalid_argument("extra characters in value '" + text + "'");
        }
    }
    return result;
}

double parse_time(const std::string& text)
{
    return atof(text.c_str());
}

class ThroughputTest
{
public:
    ThroughputTest(const std::string& protocol, size_t bufsize) :
        _transport(Transport::Factory(protocol)),
        _bufsize(bufsize),
        _running(true),
        _count(0)
    {
        pthread_create(&_reader, NULL, &ThroughputTest::reader_thread, this);
    }

    void start()
    {
        pthread_create(&_writer, NULL, &ThroughputTest::writer_thread, this);
    }

    void stop()
    {
        // Wait for writer to exit
        _running = false;
        pthread_join(_writer, NULL);

        // Wait for reader to exit
        pthread_join(_reader, NULL);
    }

    size_t count()
    {
        return _count;
    }

    ~ThroughputTest()
    {
    }
    
private:
    void writer()
    {
        pthread_setname_np(_writer, "write-thread");

        int fd = _transport->writefd();

        // Push data to socket
        std::vector<char> buffer;
        buffer.resize(_bufsize);

        while (_running) {
            write(fd, &buffer[0], buffer.size());
        }

        // Close the write side of the socket so the reader knows no more data
        // is coming
        shutdown(fd, SHUT_WR);

        // Get the final acknowledged read count
        read(fd, &_count, sizeof(_count));
    }

    void reader()
    {
        pthread_setname_np(_reader, "read-thread");

        int fd = _transport->readfd();

        std::vector<char> buffer;
        buffer.resize(_bufsize);

        ssize_t count = 0;
        while (true) {
            ssize_t pass = read(fd, &buffer[0], buffer.size());
            if (pass <= 0) {
                if (pass < 0) {
                    perror("read");
                }
                break;
            }
            count += pass;
        }
        write(fd, &count, sizeof(count));
    }

    static void* reader_thread(void* data)
    {
        ThroughputTest* test = (ThroughputTest*)data;
        test->reader();
        return 0;
    }

    static void* writer_thread(void* data)
    {
        ThroughputTest* test = (ThroughputTest*)data;
        test->writer();
        return 0;
    }

    Transport* _transport;
    size_t _bufsize;

    pthread_t _reader;
    pthread_t _writer;
    volatile bool _running;

    ssize_t _count;
};

int main(int argc, char* const argv[])
{
    size_t transfer_size = 1024;
    std::string transport_type = "unix";
    double time_period = 1.0;
    int count = 1;

    struct option long_options[] = {
        {"transport", required_argument, 0, 'T'},
        {0, 0, 0, 0}
    };

    char opt;
    int index;
    while ((opt = getopt_long(argc, argv, "n:s:t:", long_options, &index)) != -1) {
        switch (opt) {
        case 's':
            transfer_size = parse_number(optarg);
            break;
        case 'n':
            count = atoi(optarg);
            break;
        case 't':
            time_period = parse_time(optarg);
            break;
        case 'T':
            transport_type = optarg;
            break;
        default:
            exit(1);
        }
    }

    std::vector<ThroughputTest*> tests;
    for (int ii = 0; ii < count; ++ii) {
        tests.push_back(new ThroughputTest(transport_type, transfer_size));
    }

    // Mark start time
    struct timespec start;
    clock_gettime(CLOCK_MONOTONIC, &start);

    for (int ii = 0; ii < tests.size(); ++ii) {
        tests[ii]->start();
    }

    sleep(time_period);

    for (int ii = 0; ii < tests.size(); ++ii) {
        tests[ii]->stop();
    }

    // Mark end time
    struct timespec end;
    clock_gettime(CLOCK_MONOTONIC, &end);

    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec-start.tv_nsec)*1e-9;
    std::cout << "Elapsed: " << format_time(elapsed) << std::endl;

    double aggregate_throughput = 0.0;
    for (int ii = 0; ii < tests.size(); ++ii) {
        double throughput = tests[ii]->count() / elapsed;
        aggregate_throughput += throughput;
    }

    std::cout << "Throughput: " << format_throughput(aggregate_throughput) << std::endl;

    return 0;
}
