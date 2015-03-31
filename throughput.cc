#include <iostream>
#include <sstream>
#include <string>
#include <vector>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <cmath>

#include <ctype.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <time.h>
#include <getopt.h>

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

void writer(int fd, size_t bufsize, size_t nbuffers)
{
    std::vector<char> buffer;
    buffer.resize(bufsize);

    ssize_t count = 0;
    for (int ii = 0; ii < nbuffers; ++ii) {
        count += write(fd, &buffer[0], buffer.size());
    }
    std::cout << "parent: wrote " << count << std::endl;

    read(fd, &count, sizeof(count));
    std::cout << "parent: acknowledged " << count << std::endl;
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
    std::cout << "child: read " << count << std::endl;
    write(fd, &count, sizeof(count));
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
            transfer_size = atoi(optarg);
            break;
        case 'n':
            total_transfers = atoi(optarg);
            break;
        case 'T':
            transport_type = optarg;
            break;
        default:
            exit(1);
        }
    }

    int sv[2]; /* the pair of socket descriptors */
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) == -1) {
        perror("socketpair");
        exit(1);
    }

    pid_t reader_pid = fork();
    if (reader_pid < 0) {
        perror("fork");
        exit(1);
    } else if (reader_pid == 0) {  /* child */
        reader(sv[1], transfer_size, total_transfers);
    } else { /* parent */
        // Mark start time
        struct timespec start;
        clock_gettime(CLOCK_MONOTONIC, &start);

        // Push data to socket
        writer(sv[0], transfer_size, total_transfers);

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
    }

    return 0;
}
