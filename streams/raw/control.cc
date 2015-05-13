#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

#include "control.h"

control* open_control(const std::string& filename)
{
    int fd = open(filename.c_str(), O_RDWR);
    if (fd < 0) {
        return 0;
    }

    void* address = mmap(NULL, sizeof(control), PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    return reinterpret_cast<control*>(address);
}

void close_control(control* address)
{
    munmap(address, sizeof(control));
}
