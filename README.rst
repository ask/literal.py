##############################################
 literal.py - Python code generation tool
##############################################

:Version: 1.0.0

Synopsis
========

Literal is a fun weekend project to create a way to generate python
code with Python code.  Instead of having string literals of Python
code, you use ``literal.ly`` objects that remembers the operations
done to them, and the history of operations is the resulting
Python program.

This is just an experiment that I wanted to play with;
It's usefulness is not proven, and more than likely
this will be thrown away as a failed experiment. So use
with care and caution.

Quick overview
--------------

::

    import literal

    @literal.py
    def unpack_octet(x, payload, offset, unpack_from):
        x <<= unpack_from('B', payload, offset)
        offset += 1

    print(unpack_octet())

Gives::

    x = unpack_from('B', payload, offset)
    offset += 1


Or another example used to create argument unpackers
for the AMQP protocol::

    def unpack(method):

        @literal.py
        def body(p, payload, offset, unpack_from, argtuple, ssize):
            fields = method.fields
            names = p.tuple(*self.field_names)

            for i, fset in enumerate(fields):
                if len(fset) == 1:
                    for field in fset:
                        name = p.var(field.name)
                        if field.format == '*':
                            # This is a string payload,
                            # don't have to unpack
                            name <<= payload[offset:offset + ssize]
                            offset += ssize
                        else:
                            # A single field to unpack
                            name <<= unpack_from(struct_format(field.format),
                                                payload, offset)[0]
                            offset += field.size
                else:
                    # A list of field to unpack
                    these = p.tuple(*fset.names)
                    these <<= unpack_from(struct_format(fset.format),
                                        payload, offset)
                    offset += sum(f.size for f in fset)
                return names

            return body().as_fun(lambda payload, offset: 1,
                                method.name)


Would generate the following code for the AMQP method ``basic_deliver``::

    def deliver(payload, offset):
        ssize = unpack_from('B', payload, offset)[0]
        offset += 1
        consumer_tag = payload[offset:offset + ssize]
        offset += ssize
        delivery_tag, redelivered, ssize = unpack_from('QBB', payload, offset)
        offset += 10
        exchange = payload[offset:offset + ssize]
        offset += ssize
        ssize = unpack_from('B', payload, offset)[0]
        offset += 1
        routing_key = payload[offset:offset + ssize]
        offset += ssize
        return (consumer_tag, delivery_tag, redelivered,
                exchange, routing_key)


More documentation to come.

Installation
============

You can install `litera.py` either via the Python Package Index (PyPI)
or from source.

To install using `pip`,::

    $ pip install literal

To install using `easy_install`,::

    $ easy_install literal

If you have downloaded a source tarball you can install it
by doing the following,::

    $ python setup.py build
    # python setup.py install # as root


Bug tracker
===========

If you have any suggestions, bug reports or annoyances please report them
to our issue tracker at http://github.com/ask/literal.py/issues/

Contributing
============

Development of `literal.py` happens at Github:
http://github.com/ask/literal.py

You are highly encouraged to participate in the development. If you don't
like Github (for some reason) you're welcome to send regular patches.

License
=======

This software is licensed under the `New BSD License`. See the `LICENSE`
file in the top distribution directory for the full license text.
