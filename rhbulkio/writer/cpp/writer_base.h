#ifndef WRITER_IMPL_BASE_H
#define WRITER_IMPL_BASE_H

#include <boost/thread.hpp>
#include <ossie/Resource_impl.h>
#include <ossie/ThreadedComponent.h>

#include <bulkio/bulkio.h>

class writer_base : public Resource_impl, protected ThreadedComponent
{
    public:
        writer_base(const char *uuid, const char *label);
        ~writer_base();

        void start() throw (CF::Resource::StartError, CORBA::SystemException);

        void stop() throw (CF::Resource::StopError, CORBA::SystemException);

        void releaseObject() throw (CF::LifeCycle::ReleaseError, CORBA::SystemException);

        void loadProperties();

    protected:
        // Member variables exposed as properties
        CORBA::ULong transfer_length;

        // Ports
        bulkio::OutOctetPort *dataOctet_out;

    private:
};
#endif // WRITER_IMPL_BASE_H
