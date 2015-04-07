#include <stdexcept>
#include <cstring>

#include <unistd.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>

#include "transport.hh"

Transport* Transport::Factory(const std::string& protocol)
{
    if (protocol == "unix") {
        return new UnixTransport();
    } else if (protocol == "tcp") {
        return new TcpTransport();
    } else {
        throw std::invalid_argument("invalid transport type '" + protocol + "'");
    }
}

UnixTransport::UnixTransport() :
    _readfd(-1),
    _writefd(-1)
{
    int sv[2];
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) == -1) {
        throw std::runtime_error("");
    }
    _readfd = sv[0];
    _writefd = sv[1];
}

UnixTransport::~UnixTransport()
{
    if (_readfd >= 0) {
        close(_readfd);
    }
    if (_writefd >= 0) {
        close(_writefd);
    }
}

int UnixTransport::readfd()
{
    return _readfd;
}

int UnixTransport::writefd()
{
    return _writefd;
}


TcpTransport::TcpTransport()
{
    memset(&_addr, 0, sizeof(sockaddr_in));

    _sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (_sockfd < 0) {
        throw std::runtime_error("socket");
    }

    _addr.sin_family = AF_INET;
    _addr.sin_port = 0;
    _addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (bind(_sockfd, (struct sockaddr*)&_addr, sizeof(_addr)) < 0) {
        throw std::runtime_error("bind");
    }

    socklen_t len = sizeof(_addr);
    if (getsockname(_sockfd, (struct sockaddr*)&_addr, &len)) {
        throw std::runtime_error("getsockname");
    }

    if (listen(_sockfd, 1) == -1) {
        throw std::runtime_error("listen");
    }
}

TcpTransport::~TcpTransport()
{
    if (_sockfd >= 0) {
        close(_sockfd);
    }
}

int TcpTransport::readfd()
{
    int readfd = socket(AF_INET, SOCK_STREAM, 0);
    if (readfd < 0) {
        throw std::runtime_error("socket");
    }

    if (connect(readfd, (struct sockaddr*)&_addr, sizeof(_addr)) == -1) {
        throw std::runtime_error("connect");
    }
        
    return readfd;
}

int TcpTransport::writefd()
{
    return accept(_sockfd, NULL, NULL);
}
