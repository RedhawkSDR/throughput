#include <iostream>
#include <deque>

#include <omniORB4/CORBA.h>

#include "rawdata.hh"

class Reader : public virtual POA_rawdata::reader {
public:
    Reader() :
        _received(0),
        _thread(0),
        _mutex(),
        _cond(&_mutex)
    {
        _thread = new omni_thread(&Reader::thread_start, this);
        _thread->start();
    }

    void push_octet(const rawdata::octet_sequence& data)
    {
        _received += data.length();
        queue_buffer(data);
    }

    void push_short(const rawdata::short_sequence& data)
    {
        _received += data.length() * sizeof(CORBA::Short);
        queue_buffer(data);
    }

    void push_float(const rawdata::float_sequence& data)
    {
        _received += data.length() * sizeof(CORBA::Float);
        queue_buffer(data);
    }

    CORBA::LongLong received()
    {
        return _received;
    }

private:
    void thread_run()
    {
        _mutex.lock();
        while (true) {
            while (_queue.empty()) {
                _cond.wait();
            }
            delete _queue.front();
            _queue.pop_front();
        }
        _mutex.unlock();
    }

    static void thread_start(void* arg)
    {
        Reader* reader = (Reader*)arg;
        reader->thread_run();
    }

    size_t _received;
    omni_thread* _thread;

    struct deletable {
        virtual ~deletable() { }
    };

    template <class T>
    struct sequence_deleter : public deletable {
        sequence_deleter(T& src)
        {
            const CORBA::ULong maximum = src.maximum();
            const CORBA::ULong length = src.length();
            _seq.replace(maximum, length, src.get_buffer(1), 1);

        }

        virtual ~sequence_deleter()
        {
        }

        T _seq;
    };

    template <class T>
    void queue_buffer(const T& src)
    {
        _mutex.lock();
        _queue.push_back(new sequence_deleter<T>(const_cast<T&>(src)));
        _cond.signal();
        _mutex.unlock();
    }

    omni_mutex _mutex;
    omni_condition _cond;
    std::deque<deletable*> _queue;
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
}
