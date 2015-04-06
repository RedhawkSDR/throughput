#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>
#include <cstdio>
#include <cstring>

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/un.h>

int main(int argc, const char* argv[])
{
    if (argc < 4) {
        exit(1);
    }

    int fd;

    if (strcmp(argv[1], "unix") == 0) {
        fd = socket(AF_UNIX, SOCK_STREAM, 0);
        if (fd < 0) {
            perror("socket");
            exit(1);
        }

        struct sockaddr_un writer;
        writer.sun_family = AF_UNIX;
        strcpy(writer.sun_path, argv[2]);
        int len = strlen(writer.sun_path) + sizeof(writer.sun_family);
        if (writer.sun_path[0] == '@') {
            writer.sun_path[0] = '\0';
        }
        if (connect(fd, (struct sockaddr*)&writer, len) < 0) {
            perror("connect");
            exit(1);
        }
    } else if (strcmp(argv[1], "tcp") == 0) {
        fd = socket(AF_INET, SOCK_STREAM, 0);
        if (fd < 0) {
            perror("socket");
        }

        char* address = strdup(argv[2]);
        char* isep = strchr(address, ':');
        short port = atoi(isep+1);
        *isep = '\0';

        struct sockaddr_in server;
        memset(&server, 0, sizeof(sockaddr_in));
        server.sin_family = AF_INET;
        server.sin_port = port;
        inet_aton(address, &server.sin_addr);

        if (connect(fd, (struct sockaddr*)&server, sizeof(server)) < 0) {
            perror("connect");
            exit(1);
        }
    } else {
        std::cerr << "Unknown protocol '" << argv[1] << "'" << std::endl;
        exit(1);
    }

    int bufsize = atoi(argv[3]);

    std::vector<char> buffer;
    buffer.resize(bufsize);

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

    close(fd);

    std::cout << count << std::endl;

    return 0;
}
