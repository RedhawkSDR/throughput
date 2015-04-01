#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <cstring>
#include <algorithm>

#include <time.h>
#include <getopt.h>

#include "transport.h"

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

void writer(int fd, size_t bufsize, size_t nbuffers)
{
    std::vector<char> buffer;
    buffer.resize(bufsize);

    ssize_t count = 0;
    for (int ii = 0; ii < nbuffers; ++ii) {
        count += write(fd, &buffer[0], buffer.size());
    }
    read(fd, &count, sizeof(count));
}

void reader(int fd, size_t bufsize, size_t nbuffers)
{
    std::vector<char> buffer;
    buffer.resize(bufsize);

    ssize_t count = 0;
    size_t expected = bufsize*nbuffers;
    while (count < expected) {
        count += read(fd, &buffer[0], buffer.size());
    }
    write(fd, &count, sizeof(count));
}

pid_t start_reader(Transport* transport, size_t bufsize, size_t nbuffers)
{
    pid_t reader_pid = fork();
    if (reader_pid < 0) {
        perror("fork");
        exit(1);
    } else if (reader_pid > 0) {
        return reader_pid;
    }

    reader(transport->readfd(), bufsize, nbuffers);
    exit(0);
}

int main(int argc, char* const argv[])
{
    size_t transfer_size = 1024;
    size_t total_transfers = 1000;
    std::string transport_type = "unix";

    struct option long_options[] = {
        {"transport", required_argument, 0, 'T'},
        {0, 0, 0, 0}
    };

    char opt;
    int index;
    while ((opt = getopt_long(argc, argv, "n:s:", long_options, &index)) != -1) {
        switch (opt) {
        case 's':
            transfer_size = parse_number(optarg);
            break;
        case 'n':
            total_transfers = parse_number(optarg);
            break;
        case 'T':
            transport_type = optarg;
            break;
        default:
            exit(1);
        }
    }

    int sockfd = -1;
    std::string address;
    Transport* transport = 0;
    if (transport_type == "unix") {
        transport = new UnixTransport();
    } else if (transport_type == "tcp") {
        transport = new TcpTransport();
    } else {
        std::cerr << "Invalid tranport type '" << transport_type << "'" << std::endl;
        exit(1);
    }

    pid_t reader_pid = start_reader(transport, transfer_size, total_transfers);

    int writefd = transport->writefd();

    // Mark start time
    struct timespec start;
    clock_gettime(CLOCK_MONOTONIC, &start);

    // Push data to socket
    writer(writefd, transfer_size, total_transfers);

    // Mark end time
    struct timespec end;
    clock_gettime(CLOCK_MONOTONIC, &end);

    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec-start.tv_nsec)*1e-9;
    double throughput = (transfer_size*total_transfers) / elapsed;

    std::cout << "Elapsed: " << format_time(elapsed) << std::endl;
    std::cout << "Throughput: " << format_throughput(throughput) << std::endl;

    // Wait for child to exit
    int status;
    waitpid(reader_pid, &status, 0);

    return 0;
}
