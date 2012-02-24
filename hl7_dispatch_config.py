
"""
     We need to be able to dispatch based on the message type,
     and the destination application.

     MSH.9/MSH.5/MSH.6

     2.16.9.2 MSH-2 Encoding characters (ST) 00002
     2.16.9.3 MSH-3 Sending application (HD) 00003
     2.16.9.4 MSH-4 Sending facility (HD) 00004
     2.16.9.5 MSH-5 Receiving application (HD) 00005
     2.16.9.6 MSH-6 Receiving facility (HD) 00006
     2.16.9.7 MSH-7 Date/time of message (TS) 00007
     2.16.9.8 MSH-8 Security (ST) 00008
     2.16.9.9 MSH-9 Message type (CM) 00009 

     Remember to escape the ^ and any other special characters being used.
"""
from hl7v2_django.dispatch import pattern

rules = [
    pattern('MFN\^M05/.*', 'sd.mfn_handlers.m05'),  # staff
    pattern('MFN\^M02/.*', 'sd.mfn_handlers.m02'),  # practitioner
]

