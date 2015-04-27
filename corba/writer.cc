#include <iostream>

#include <omniORB4/CORBA.h>

#include "rawdata.hh"

class Writer : public virtual POA_rawdata::writer {
public:
    Writer() :
        _thread(0),
        _running(true),
        _length(1024)
    {
        _thread = new omni_thread(&Writer::thread_start, this);
    }

    void connect(rawdata::reader_ptr reader, const char* format)
    {
        _format = format;
        _reader = rawdata::reader::_duplicate(reader);
    }

    void transfer_length(CORBA::Long length)
    {
        _length = length;
    }

    void start()
    {
        _thread->start();
    }

    void stop()
    {
        _running = false;
    }

private:
    void thread_run()
    {
        if (_format == "float") {
            rawdata::float_sequence data;
            data.length(_length);
            while (_running) {
                if (data.length() != _length) {
                    data.length(_length);
                }
                _reader->push_float(data);
            }
        } else if (_format == "short") {
            rawdata::short_sequence data;
            data.length(_length);
            while (_running) {
                if (data.length() != _length) {
                    data.length(_length);
                }
                _reader->push_short(data);
            }
        } else {
            rawdata::octet_sequence data;
            data.length(_length);
            while (_running) {
                if (data.length() != _length) {
                    data.length(_length);
                }
                _reader->push_octet(data);
            }
        }
    }

    static void* thread_start(void* arg)
    {
        Writer* writer = (Writer*)arg;
        writer->thread_run();
        return 0;
    }

    omni_thread* _thread;
    rawdata::reader_var _reader;
    volatile bool _running;
    std::string _format;
    int _length;
};

int main (int argc, char* argv[])
{
    CORBA::ORB_var orb = CORBA::ORB_init(argc, argv);

    CORBA::Object_var obj = orb->resolve_initial_references("RootPOA");
    PortableServer::POA_var root_poa = PortableServer::POA::_narrow(obj);
    PortableServer::POAManager_var manager = root_poa->the_POAManager();
    manager->activate();

    Writer* writer = new Writer();
    PortableServer::ObjectId_var oid = root_poa->activate_object(writer);
    rawdata::writer_var ref = writer->_this();
    CORBA::String_var ior = orb->object_to_string(ref);
    std::cout << ior << std::endl;

    orb->run();

    orb->shutdown(true);
}
