#ifndef CONTROL_H
#define CONTROL_H

#include <string>

#include <inttypes.h>

struct control {
    volatile uint64_t total_bytes;
    volatile uint32_t transfer_size;
};

control* open_control(const std::string& filename);
void close_control(control* address);

#endif // CONTROL_H
