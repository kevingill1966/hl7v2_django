HL7 V2 Django App
-----------------

This app provides a interface between a django application and a HL7 message
broker (i.e. myrth).

Requirements:

    Django: 1.3.1
    hl7: John Paulett's hl7 module

Usage:

    python manage.py runmllpserver

Message Dispatchers:

The hl7 messages should be dispatched using a mechanism similar to django.
A set of hl7_handers are identified. The dispatcher works down through
them until it finds a function/class that can handle its message.

The function/class handles the message and returns a hl7ACK object.

