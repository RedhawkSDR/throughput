all:
	cd raw && make
	cd corba && make

clean:
	cd raw && make clean
	cd corba && make clean
