"""
    Master File Notification messages (Chapter 8)
"""
from hl7v2_django import responses

def m02(request, *args, **kwargs):  # practitioner
    import pdb; pdb.set_trace()

    resp = responses.hl7ACK(request, 'AA')
    return resp

def m05(request, *args, **kwargs):  # location
    import pdb; pdb.set_trace()

    resp = responses.hl7ACK(request, 'AA')
    return resp
