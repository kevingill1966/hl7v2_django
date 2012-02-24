""" 
    The MLLP protocol is very simple. A process sends bytes to another
    process, Bytes are wrapped in a frame using frame characters. 
    The content of the frame is limited to printable ascii characters 
    and the carriage return.
""" 



import socket
import select
import logging
from optparse import make_option
import pdb

import hl7

from django.core.management.base import BaseCommand
from django.conf import settings

from hl7v2_django import responses
from hl7v2_django.dispatch import Dispatcher


# Error logging - configured vi settings file in DJANGO
logger = logging.getLogger(__name__)


# Constants
LLP_SB = chr(0x0B)   # Start of Frame
LLP_EB = chr(0x1C)   # end of frame
LLP_ACK = chr(0x06)    # ACK
LLP_NAK = chr(0x15)  # NAK
LLP_MIN = chr(0x20)   # content of LLP frame must be >= 0x20
CR = chr(0xD)

BLKSIZE=8192

class LLPServer(object):
    def __init__(self, config):

        # Initialise the sockets - we are listening on them both
        self.epoll = select.epoll()
        self.recv_sock = []       # Sockets we are listening on
        self.recv_fileno = []     # filenos for these sockets
        self.mllp_ack = []        # mllp ack for these sockets
        for c in config:
            recv_sock = self._mk_socket(c['recv_addr'])
            self.ack = c.get('mllp_ack')
            logger.info('Listening for RECV ON %s', c['recv_addr'])
            recv_fileno = recv_sock.fileno()
            self.epoll.register(recv_fileno, select.EPOLLIN)
            self.recv_sock.append(recv_sock)
            self.recv_fileno.append(recv_fileno)
            self.mllp_ack.append(c.get('mllp_ack', False))

    def _mk_socket(self, addr):
        """
            Set up the socket as per:
            http://scotdoyle.com/python-epoll-howto.html
        """
        if addr.find(':') != -1:
            host, port = addr.split(':', 1)
            port = int(port)
        else:
            host = '127.0.0.1'
            port = int(addr)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(5)
        s.setblocking(0)
        return(s)

    def _read_frame(self, s):
        """Receive a frame, unwrap it, return it"""
        try:
            buffer = s.recv(BLKSIZE)
        except:
           return None
        # TODO: Handle closed connection
        if len(buffer) == 0:
            return None

        # Search for the SOF
        sof = buffer.find(LLP_SB)
        if sof < 0:
            logger.error('ERROR: No start byte found in message buffer\n%s', buffer.replace(CR, '\n'))
            return buffer

        buffer = buffer[sof+1:]
        message = []
        while 1:
            eof = buffer.find(LLP_EB)
            if eof != -1:
                message.append(buffer[:eof])
                break
            message.append(buffer)
            buffer = s.recv(BLKSIZE)
        message = ''.join(message)
        for c in message:
            assert(c >= LLP_MIN or c == CR)
        return message

    def _write_ack(self, s):
        transmit = LLP_SB + LLP_ACK + LLP_EB + CR
        return s.send(transmit)

    def _write_nak(self, s):
        transmit = LLP_SB + LLP_NAK + LLP_EB + CR
        return s.send(transmit)

    def _write_frame(self, s, message):
        """Send a frame, wrap it"""
        # TODO: Handle closed connection

        # Validate the message
        for c in message:
            assert(c >= LLP_MIN or c == CR)

        if message[-1] == CR:
            transmit = LLP_SB + message + LLP_EB + CR
        else:
            transmit = LLP_SB + message + CR + LLP_EB + CR
        sent = 0 
        while sent < len(transmit):
            bytes = s.send(transmit[sent:])
            sent += bytes
        return sent

    def dispatch(self, recv_handler):
        """ 
            Receive messages, pass them to handler
        """
        recv_connections = {}
        ack_connections = {}

        while True:
            delay = 5
            events = self.epoll.poll(delay)
            for fileno, event in events:
                if fileno in self.recv_fileno:
                    recv_sock = self.recv_sock[self.recv_fileno.index(fileno)]
                    mllp_ack = self.mllp_ack[self.recv_fileno.index(fileno)]
                    connection, address = recv_sock.accept()
                    recv_connections[connection.fileno()] = connection
                    ack_connections[connection.fileno()] = mllp_ack
                    self.epoll.register(connection.fileno(), select.EPOLLIN)
                    connection.setblocking(0)
                elif event & select.EPOLLIN:
                    if fileno in recv_connections:
                        frame = self._read_frame(recv_connections[fileno])
                        if frame in [LLP_NAK, LLP_ACK]:
                            logger.debug('ACK recieved from recv socket: %s', frame.replace(CR, '\n'))
                        elif frame is None:
                            self.epoll.unregister(fileno)
                            recv_connections[fileno].close()
                            del recv_connections[fileno]
                            logger.debug('Closing recv socket')
                        else:
                            recv_handler(frame, self, recv_connections[fileno])
                            if ack_connections[fileno]:
                                self._write_ack(recv_connections[fileno])
                elif event & select.EPOLLHUP:
                    logger.debug('EVENT: EPOLLHUP')
                    self.epoll.unregister(fileno)
                    if fileno in recv_connections:
                        recv_connections[fileno].close()
                        del recv_connections[fileno]


class Command(BaseCommand):
    args = 'runmllpserver'
    help = """Run a server communicating with a HL7 server to dispatch messages.

        Usage:\n\n\tdjango [options] runmllpserver [--pdb] 

        --pdb for postmortem debugger
        """ 
    option_list = BaseCommand.option_list + (
        make_option('--pdb',
            action='store_true',
            dest='postmortem',
            default=False,
            help='Post mortem debugger on error'),
        )

    postmortem = False

    def handle(self, *args, **options):
        config = settings.MLLP_SOCKETS
        server = LLPServer(config)
        self.dispatcher = Dispatcher()
        if options['postmortem']:
            try:
                self.postmortem = True
                server.dispatch(self.recv_handler)
            except:
                pdb.post_mortem()
                raise
        else:
            server.dispatch(self.recv_handler)


    def recv_handler(self, msg, server, connection):
        msg = msg.decode('utf-8')
        logger.debug('RECV: %s', msg.replace(CR, '\n'))
        # Logic here - parse the message HL7
        # perform required validation
        # Send ack / error message that message received.
        # If enhanced mode, do the requisite steps to store then ack 
        try:
            msg = hl7.parse(msg)
        except:
            logger.exception('Error parsing message')
            if self.postmortem:
                pdb.post_mortem()
            resp = responses.hl7NAK('AE', 'UNABLE TO PARSE REQUEST')
            logger.debug('SEND: %s', unicode(resp).replace(CR, '\n'))
            server._write_frame(connection, unicode(resp).encode('utf-8'))
            return

        try:
            # DISPATCH MESSAGE HERE. Expect an acknowledgement response message - 
            resp = self.dispatcher.dispatch(msg)
            if resp is None:
                raise Exception('Application returned and invalid response (None) - response required')
            logger.debug('SEND: %s', unicode(resp).replace(CR, '\n'))
            server._write_frame(connection, unicode(resp).encode('utf-8'))
            return
        except:
            logger.exception('Error dispatching message')
            if self.postmortem:
                pdb.post_mortem()
            resp = responses.hl7NAK('AE', 'INTERNAL ERROR PROCESSING REQUEST')
            logger.debug('SEND: %s', unicode(resp).replace(CR, '\n'))
            server._write_frame(connection, unicode(resp).encode('utf-8'))
            return

