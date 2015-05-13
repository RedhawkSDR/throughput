#ifndef WRITER_IMPL_H
#define WRITER_IMPL_H

#include "writer_base.h"

class writer_i : public writer_base
{
    ENABLE_LOGGING
    public:
        writer_i(const char *uuid, const char *label);
        ~writer_i();
        int serviceFunction();

    private:
        std::vector<CORBA::Octet> buffer;
};

#endif // WRITER_IMPL_H
