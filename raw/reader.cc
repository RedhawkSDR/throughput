#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <deque>

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/un.h>

#include <omnithread.h>

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

class Reader {
public:
    Reader() :
        _thread(0),
        _mutex(),
        _cond(&_mutex)
    {
        _thread = new omni_thread(&Reader::thread_start, this);
        _thread->start();
    }

    void queue(char* data)
    {
        _mutex.lock();
        _queue.push_back(data);
        _cond.signal();
        _mutex.unlock();
    }

private:
    void thread_run()
    {
        _mutex.lock();
        while (true) {
            while (_queue.empty()) {
                _cond.wait();
            }
            delete[] _queue.front();
            _queue.pop_front();
        }
        _mutex.unlock();
    }

    static void thread_start(void* arg)
    {
        Reader* reader = (Reader*)arg;
        reader->thread_run();
    }

    omni_thread* _thread;
    omni_mutex _mutex;
    omni_condition _cond;
    std::deque<char*> _queue;
};

int main(int argc, const char* argv[])
{
    if (argc < 4) {
        exit(1);
    }

    int fd = connect(argv[1], argv[2]);
    if (fd < 0) {
        exit(1);
    }

    Reader reader;

    control* state = open_control(argv[3]);

    ssize_t count = 0;
    while (true) {
        size_t buffer_size = state->transfer_size;
        char* buffer = new char[buffer_size];
        ssize_t pass = read(fd, &buffer[0], buffer_size);
        if (pass <= 0) {
            delete[] buffer;
            if (pass < 0) {
                perror("read");
            }
            break;
        }
        reader.queue(buffer);
        state->total_bytes += pass;
    }

    close(fd);

    return 0;
}
