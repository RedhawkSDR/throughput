#include <netinet/in.h>

class Transport {
public:
    virtual ~Transport() { }
    virtual int readfd() = 0;
    virtual int writefd() = 0;
};

class UnixTransport : public Transport
{
public:
    UnixTransport();
    ~UnixTransport();

    int readfd();
    int writefd();

private:
    int _readfd;
    int _writefd;
};

class TcpTransport : public Transport
{
public:
    TcpTransport();
    ~TcpTransport();
    int readfd();
    int writefd();

private:
    int _sockfd;
    struct sockaddr_in _addr;
};
