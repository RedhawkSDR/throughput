#include <iostream>
#include "ossie/ossieSupport.h"

#include "writer.h"
int main(int argc, char* argv[])
{
    writer_i* writer_servant;
    Resource_impl::start_component(writer_servant, argc, argv);
    return 0;
}

