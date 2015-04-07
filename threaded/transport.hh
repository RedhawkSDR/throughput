#ifndef _transport_hh_
#define _transport_hh_

#include <netinet/in.h>

class Transport {
public:
    virtual ~Transport() { }
    virtual int readfd() = 0;
    virtual int writefd() = 0;

    static Transport* Factory(const std::string& protocol);
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

#endif // _transport_hh_
