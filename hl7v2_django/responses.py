"""
    responses.py

    mechanism to create a response from a request message. There are
    three response types, ACK, NAK and a valid response.

    There are many weaknesses in this code. At the moment, the separator
    structure is fixed. Encoding and separators should be taken from the
    request.
"""

import time

# John Paulett's hl7 module - sudo pip install hl7
import hl7

# Message Separators
SEP = '|^~\&'
CR_SEP = '\r'

def timestamp():
    """Copied from socketServer->workerThread"""
    # get rid of nasty leap seconds by just "stretching" the time
    date = time.localtime(time.time())
    if date.tm_sec > 59:
        date.tm_sec = 59
    return time.strftime('%Y%m%d%H%M%S', date)

def next_serial(counter=[0]):
    """
        Need to issue control_id numbers to messages.
        For now just use the machine timestamp - max 100 per second
    """
    counter[0] += 1
    return (int(time.time()) * 100) + (counter[0] % 100)

def hl7ACK(request, ack_type, err_description='', message_type=None, extra_segments=None):
    """
        Generate a HL7 ACK message for a given request message
        This is used early on in the communications code and should
        not be used by the application.

        The default ack type is ACK^req type. This can be replaced by
        passing in a message type, e.g. "MFK^M01" for a master file
        notification ack message.
    """
    serial = next_serial()
    if extra_segments is None:
        extra_segments = []
    ack_type = ack_type.upper()

    iMSH = request['MSH'][0]
    local_fac, local_app = iMSH[5], iMSH[4]
    remote_fac, remote_app = iMSH[3], iMSH[2]
    req_message_type = iMSH[8]
    version_id = iMSH[11]
    control_id = iMSH[9]
    if not message_type:
        message_type = hl7.Field(SEP[1], ['ACK', req_message_type[1]])
    elif type(message_type) not in [hl7.Field, str, unicode]:
        message_type = hl7.Field(SEP[1], message_type) # assume list

    MSH = hl7.Segment(SEP[0], ['MSH', SEP[1:], local_app , local_fac, remote_app, remote_fac, timestamp(), '',
        message_type, str(serial), 'P', version_id, ''])
    MSA = hl7.Segment(SEP[0], ['MSA', ack_type, control_id, err_description])
    response = hl7.Message(CR_SEP, [MSH, MSA] + extra_segments)
    return response

def hl7NAK(ack_type, err_description, version_id='2.4'):
    """
        Generate a HL7 NAK message. The request cannot be used as it
        may have invalid structure.
        This is used early on in the communications code and should
        not be used by the application.
    """
    serial = next_serial()
    MSH = hl7.Segment(SEP[0], ['MSH', SEP[1:],'','','','',timestamp(), '', 'ACK', str(serial),
        'P', version_id, ''])
    MSA = hl7.Segment(SEP[0], ['MSA', ack_type, '', err_description, ''])
    response = hl7.Message(CR_SEP, [MSH, MSA])
    return response

# Alias
hl7Error = hl7NAK

def hl7Response(request, message_type, version_id='2.4', extra_segments=None):
    """
        Generate a HL7 RESPONSE message for a given request message.
        Just a MSG HDR

        message_type can be a string 'MFN^M02' or a list ['MFN', 'M02']
        or a hl7.Field('^', ['MFN', 'M02'])
    """
    serial = next_serial()
    if extra_segments is None:
        extra_segments = []

    iMSH = request['MSH'][0]
    local_fac, local_app = iMSH[5], iMSH[4]
    remote_fac, remote_app = iMSH[3], iMSH[2]
    # version_id = iMSH[11]
    if type(message_type) not in [hl7.Field, str, unicode]:
        message_type = hl7.Field(SEP[1], message_type) # assume list

    MSH = hl7.Segment(SEP[0], [
        'MSH',
        SEP[1:],        # 2.16.9.2 MSH-2: Encoding Characters
        local_app,      # 2.16.9.3 MSH-3: Sending Application
        local_fac,      # 2.16.9.4 MSH-4: Sending Facility
        remote_app,     # 2.16.9.5 MSH-5: Receiving Application
        remote_fac,     # 2.16.9.6 MSH-6: Receiving Facility
        timestamp(),    # 2.16.9.7 MSH-7: Date/Time Of Message
        '',             # 2.16.9.8 MSH-8: Security
        message_type,   # 2.16.9.9 MSH-9: Message Type
        str(serial),    # 2.16.9.10 MSH-10: Message Control ID
        'P',            # 2.16.9.11 MSH-11: Processing ID
        version_id,     # 2.16.9.12 MSH-12: Version ID
        '',             # Sequence Number
                        # Continuation Pointer
                        # Accept Acknowledgment Type
                        # Application Acknowledgment Type
                        # Country Code
                        # Character Set
                        # Principal Language Of Message
                        # Alternate Character Set Handling Scheme
                        # Conformance Statement ID 
        ])

    response = hl7.Message(CR_SEP, [MSH] + extra_segments)
    return response

if __name__ == '__main__':
    """
        This is a MFN^M05 (staff master file) message generated from Message workbench.
    """

    MSG = [r"MSH|^~\&|||||||MFN^M05|HEALTHLINKID|P|2.4",
    r"MFI|||UPD|||AL",
    r"MFE|MAD|||""|CE",
    r"STF|||Gill^Gill^^^Kevin^MD^B||||A|||||19660429",]

    MSG = '\r'.join(MSG) + '\r'
    m = hl7.parse(MSG)
    print 'ORIGINAL MESSAGE'
    print unicode(m).replace('\r', '\n')
    print 'ACK'
    print unicode(hl7ACK(m, 'AA', 'TEST ACK')).replace('\r', '\n')
    print 'NAK'
    print unicode(hl7NAK('AE', 'BAD REQUEST')).replace('\r', '\n')
    print 'RESPONSE'
    print unicode(hl7Response(m, ['MFK', 'M02'])).replace('\r', '\n')
    print 'ACK RESPONSE'
    print unicode(hl7ACK(m, 'AA', message_type=['MFK', 'M02'])).replace('\r', '\n')
