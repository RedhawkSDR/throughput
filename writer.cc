#include <iostream>
#include <cstdlib>
#include <cstdio>

#include <signal.h>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <linux/limits.h>

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
        sprintf(server.sun_path, "/tmp/writer-%d", getpid());
        unlink(server.sun_path);
        socklen_t len = strlen(server.sun_path) + sizeof(server.sun_family);
        bind(sockfd, (struct sockaddr*)&server, len);

        std::cout << server.sun_path << std::endl;
    } else {
        std::cerr << "Unknown protocol '" << argv[1] << "'" << std::endl;
    }

    listen(sockfd, 1);

    int bufsize = atoi(argv[2]);
    char* buffer = (char*)malloc(bufsize);
    memset(buffer, 0, bufsize);

    int fd = accept(sockfd, NULL, NULL);

    ssize_t count = 0;
    while (running) {
        count += write(fd, buffer, bufsize);
    }

    /* Close the socket so the reader knows no more data is coming */
    close(fd);

    free(buffer);

    exit(0);
}
