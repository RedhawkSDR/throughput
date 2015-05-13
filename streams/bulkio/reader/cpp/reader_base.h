#ifndef READER_IMPL_BASE_H
#define READER_IMPL_BASE_H

#include <boost/thread.hpp>
#include <ossie/Resource_impl.h>
#include <ossie/ThreadedComponent.h>

#include <bulkio/bulkio.h>

class reader_base : public Resource_impl, protected ThreadedComponent
{
    public:
        reader_base(const char *uuid, const char *label);
        ~reader_base();

        void start() throw (CF::Resource::StartError, CORBA::SystemException);

        void stop() throw (CF::Resource::StopError, CORBA::SystemException);

        void releaseObject() throw (CF::LifeCycle::ReleaseError, CORBA::SystemException);

        void loadProperties();

    protected:
        // Member variables exposed as properties
        CORBA::ULongLong received;

        // Ports
        bulkio::InOctetPort *dataOctet_in;

    private:
};
#endif // READER_IMPL_BASE_H
