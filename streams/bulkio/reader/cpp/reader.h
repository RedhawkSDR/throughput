#ifndef READER_IMPL_H
#define READER_IMPL_H

#include "reader_base.h"

class reader_i : public reader_base
{
    ENABLE_LOGGING
    public:
        reader_i(const char *uuid, const char *label);
        ~reader_i();
        int serviceFunction();
};

#endif // READER_IMPL_H
