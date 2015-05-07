#include <iostream>
#include <deque>

#include <omniORB4/CORBA.h>

#include <threaded_deleter.h>

#include "rawdata.hh"

class Reader : public virtual POA_rawdata::reader {
public:
    Reader() :
        _received(0)
    {
    }

    void push_octet(const rawdata::octet_sequence& data)
    {
        _received += data.length();
        _deleter.deallocate_array(const_cast<rawdata::octet_sequence&>(data).get_buffer(1));
    }

    void push_short(const rawdata::short_sequence& data)
    {
        _received += data.length() * sizeof(CORBA::Short);
        _deleter.deallocate_array(const_cast<rawdata::short_sequence&>(data).get_buffer(1));
    }

    void push_float(const rawdata::float_sequence& data)
    {
        _received += data.length() * sizeof(CORBA::Float);
        _deleter.deallocate_array(const_cast<rawdata::float_sequence&>(data).get_buffer(1));
    }

    CORBA::LongLong received()
    {
        return _received;
    }

private:
    threaded_deleter _deleter;
    size_t _received;
};

int main (int argc, char* argv[])
{
    CORBA::ORB_var orb = CORBA::ORB_init(argc, argv);

    CORBA::Object_var obj = orb->resolve_initial_references("RootPOA");
    PortableServer::POA_var root_poa = PortableServer::POA::_narrow(obj);
    PortableServer::POAManager_var manager = root_poa->the_POAManager();
    manager->activate();

    Reader* reader = new Reader();
    PortableServer::ObjectId_var oid = root_poa->activate_object(reader);
    rawdata::reader_var ref = reader->_this();
    CORBA::String_var ior = orb->object_to_string(ref);
    std::cout << ior << std::endl;

    orb->run();

    orb->shutdown(true);

    orb->destroy();
}
