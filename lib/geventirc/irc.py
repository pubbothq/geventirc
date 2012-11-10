from __future__ import absolute_import

import logging

import gevent.queue
import gevent.pool
from gevent import socket

from geventirc import message
from geventirc import replycode
from geventirc import handlers

IRC_PORT = 6667
IRCS_PORT = 6697

module_logger = logging.getLogger(__name__)

class Client(object):

    def __init__(self, hostname, nick, port=IRC_PORT,
            local_hostname=None, server_name=None, real_name=None, ssl=False, logger=None):
        self.hostname = hostname
        self.port = port
        self.nick = nick
        self.ssl = ssl
        self._socket = None
        self.real_name = real_name or nick
        self.local_hostname = local_hostname or socket.gethostname() #@UndefinedVariable
        self.server_name = server_name or 'gevent-irc'
        self._recv_queue = gevent.queue.Queue()
        self._send_queue = gevent.queue.Queue()
        self._group = gevent.pool.Group()
        self._handlers = {}
        self._global_handlers = set()
        self.channels = set()
        self.logger = logger or module_logger

    def add_handler(self, to_call, *commands):
        if not commands:
            if hasattr(to_call, 'commands'):
                commands = to_call.commands
            else:
                self._global_handlers.add(to_call)
                return

        for command in commands:
            command = str(command).upper()
            if self._handlers.has_key(command):
                self._handlers[command].add(to_call)
                continue
            self._handlers[command] = set([to_call])

    def _handle(self, msg):
        handlers = self._global_handlers | self._handlers.get(msg.command, set())
        if handlers is not None:
            for handler in handlers:
                self._group.spawn(handler, self, msg)

    def send_message(self, msg):
        self._send_queue.put(msg.encode())

    def start(self):
        self.connect()
        self._group.spawn(self._send_loop)
        self._group.spawn(self._process_loop)
        self._group.spawn(self._recv_loop)
        self.send_message(message.Nick(self.nick))
        self.send_message(
                message.User(
                    self.nick,
                    self.local_hostname,
                    self.server_name,
                    self.real_name))

    def connect(self):
        address = None
        try:
            address = (socket.gethostbyname(self.hostname), self.port)
        except socket.gaierror: #@UndefinedVariable
            self.logger.error('Hostname not found')
            raise
        self.logger.debug('Connecting to %r...' % (address,))
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #@UndefinedVariable
        if self.ssl: self._socket = gevent.ssl.SSLSocket(self._socket)
        self._socket.connect(address)

    def _recv_loop(self):
        buf = ''
        while 1:
            try:
                data = self._socket.recv(512)
            except gevent.GreenletExit: 
                raise
            except Exception as e:
                self.logger.exception("Disconnected from IRC: %s %s", type(e).__name__, str(e))
                gevent.spawn(self.reconnect)
            buf += data
            pos = buf.find("\r\n")
            while pos >= 0:
                line = buf[0:pos]
                self._recv_queue.put(line)
                buf = buf[pos + 2:]
                pos = buf.find("\r\n")

    def _send_loop(self):
        while 1:
            command = self._send_queue.get()
            try:
                enc_cmd = command.decode('utf8')
            except UnicodeDecodeError:
                try:
                    enc_cmd = command.decode('latin1')
                except UnicodeDecodeError:
                    self.logger.warn('Send failed due to character conversion error')
                    continue
            
            enc_cmd = enc_cmd.encode('utf8', 'ignore')
            self.logger.debug('send: %r', enc_cmd[:-2])
            try:
                self._socket.sendall(enc_cmd)
            except Exception as e:
                self.logger.exception("Client._send_loop failed")
                gevent.spawn(self.reconnect)

    def _process_loop(self):
        while 1:
            data = self._recv_queue.get()
            msg = message.CTCPMessage.decode(data)
            self._handle(msg)

    def stop(self):
        self._group.kill()
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def reconnect(self, delay=0, flush=True):
        self.logger.info("Shutdown for reconnect")
        self.stop()
        if flush:
            self._send_queue.queue.clear()
        gevent.sleep(delay)
        self.start()
        self.logger.info("Reconnected")    
    
    def join(self):
        self._group.join()

    def msg(self, to, content):
        for line in content.strip().split('\n'):
            self.send_message(message.PrivMsg(to, line))

    def quit(self, msg=None):
        self.send_message(message.Quit(msg))
        self.stop()


if __name__ == '__main__':

    class MeHandler(object):
        commands = ['PRIVMSG']

        def __call__(self, client, msg):
            if client.nick == msg.params[0]:
                nick, _, _ = msg.prefix_parts
                client.send_message(
                        message.Me(nick, "do nothing it's just a bot"))

    nick = 'geventbot'
    client = Client('irc.freenode.net', nick, port=6667)
    client.add_handler(handlers.ping_handler, 'PING')
    client.add_handler(handlers.JoinHandler('#flood!'))
    # client.add_handler(hello.start, '001')
    client.add_handler(handlers.ReplyWhenQuoted("I'm just a bot"))
    client.add_handler(handlers.print_handler)
    client.add_handler(handlers.nick_in_use_handler, replycode.ERR_NICKNAMEINUSE)
    client.add_handler(handlers.ReplyToDirectMessage("I'm just a bot"))
    client.add_handler(MeHandler())
    client.start()
    client.join()

