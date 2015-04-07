#include <iostream>
#include <vector>
#include <cstdlib>
#include <cstdio>

#include <signal.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/un.h>

static volatile bool running = true;

static void sigint_received(int /*unused*/)
{
    running = false;
}

int main(int argc, const char* argv[])
{
    if (argc < 3) {
        exit(1);
    }

    // Set up a signal handler so that SIGINT will trigger a close and exit
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = sigint_received;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGINT, &sa, NULL);

    int sockfd;
    if (strcmp(argv[1], "unix") == 0) {
        sockfd = socket(AF_UNIX, SOCK_STREAM, 0);
        if (sockfd < 0) {
            perror("socket");
            exit(1);
        }

        struct sockaddr_un server;
        server.sun_family = AF_UNIX;
        snprintf(server.sun_path, sizeof(server.sun_path), "@writer-%d", getpid());
        socklen_t len = strlen(server.sun_path) + sizeof(server.sun_family);
        std::cout << server.sun_path << std::endl;
        server.sun_path[0] = '\0';
        bind(sockfd, (struct sockaddr*)&server, len);
    } else if (strcmp(argv[1], "tcp") == 0) {
        sockfd = socket(AF_INET, SOCK_STREAM, 0);
        if (sockfd < 0) {
            perror("socket");
            exit(1);
        }

        struct sockaddr_in server;
        memset(&server, 0, sizeof(sockaddr_in));
        server.sin_family = AF_INET;
        server.sin_port = 0;
        server.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        if (bind(sockfd, (struct sockaddr*)&server, sizeof(server)) < 0) {
            perror("bind");
            exit(1);
        }

        socklen_t len = sizeof(server);
        if (getsockname(sockfd, (struct sockaddr*)&server, &len) < 0) {
            perror("getsockname");
            exit(1);
        }

        std::cout << inet_ntoa(server.sin_addr) << ":" << server.sin_port << std::endl;
    } else {
        std::cerr << "Unknown protocol '" << argv[1] << "'" << std::endl;
        exit(1);
    }

    listen(sockfd, 1);

    int bufsize = atoi(argv[2]);
    std::vector<char> buffer;
    buffer.resize(bufsize);

    int fd = accept(sockfd, NULL, NULL);

    char temp;
    std::cin.get(temp);

    ssize_t count = 0;
    while (running) {
        count += write(fd, &buffer[0], buffer.size());
    }

    // Close the socket so the reader knows no more data is coming
    close(fd);

    exit(0);
}
