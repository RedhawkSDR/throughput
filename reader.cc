#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>
#include <cstdio>

#include <sys/socket.h>
#include <sys/un.h>

int main(int argc, const char* argv[])
{
    if (argc < 3) {
        exit(1);
    }

    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0) {
        perror("socket");
        exit(1);
    }

    struct sockaddr_un writer;
    writer.sun_family = AF_UNIX;
    strcpy(writer.sun_path, argv[1]);
    int len = strlen(writer.sun_path) + sizeof(writer.sun_family);
    if (connect(fd, (struct sockaddr*)&writer, len) < 0) {
        perror("connect");
        exit(1);
    }

    int bufsize = atoi(argv[2]);

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
