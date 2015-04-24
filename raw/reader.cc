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

#include "control.h"

int connect_unix(const std::string& address)
{
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) {
        perror("socket");
        return -1;
    }

    struct sockaddr_un writer;
    writer.sun_family = AF_UNIX;
    strcpy(writer.sun_path, address.c_str());
    int len = strlen(writer.sun_path) + sizeof(writer.sun_family);
    if (writer.sun_path[0] == '@') {
        writer.sun_path[0] = '\0';
    }
    if (connect(fd, (struct sockaddr*)&writer, len) < 0) {
        perror("connect");
        return -1;
    }
    return fd;
}

int connect_tcp(const std::string& address)
{
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        perror("socket");
        return -1;
    }

    struct sockaddr_in server;
    memset(&server, 0, sizeof(sockaddr_in));
    server.sin_family = AF_INET;
    std::string::size_type isep = address.find(':');
    server.sin_port = atoi(address.substr(isep+1).c_str());
    inet_aton(address.substr(0, isep).c_str(), &server.sin_addr);

    if (connect(fd, (struct sockaddr*)&server, sizeof(server)) < 0) {
        perror("connect");
        return -1;
    }
    return fd;
}

int connect(const std::string& protocol, const std::string& address)
{
    if (protocol == "unix") {
        return connect_unix(address);
    } else if (protocol == "tcp") {
        return connect_tcp(address);
    } else {
        std::cerr << "Unknown protocol '" << protocol << "'" << std::endl;
        return -1;
    }
}

int main(int argc, const char* argv[])
{
    if (argc < 4) {
        exit(1);
    }

    int fd = connect(argv[1], argv[2]);
    if (fd < 0) {
        exit(1);
    }

    control* state = open_control(argv[3]);
    std::vector<char> buffer;

    ssize_t count = 0;
    while (true) {
        size_t buffer_size = state->transfer_size;
        if (buffer_size != buffer.size()) {
            buffer.resize(buffer_size);
        }
        ssize_t pass = read(fd, &buffer[0], buffer.size());
        if (pass <= 0) {
            if (pass < 0) {
                perror("read");
            }
            break;
        }
        state->total_bytes += pass;
    }

    close(fd);

    return 0;
}
