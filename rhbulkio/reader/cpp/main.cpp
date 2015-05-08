#include <iostream>
#include "ossie/ossieSupport.h"

#include "reader.h"
int main(int argc, char* argv[])
{
    reader_i* reader_servant;
    Resource_impl::start_component(reader_servant, argc, argv);
    return 0;
}

