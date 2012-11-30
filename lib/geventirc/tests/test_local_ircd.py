'''
Created on 29.11.2012

@author: nimrod
'''
import gevent, gevent.monkey
gevent.monkey.patch_all()

import pytest
import logging
import socket
import sys
import os

import hircd

from geventirc import Client
from geventirc import handlers, replycode, message

TEST_NICK = 'test_cl'
TEST_PASSWORD = 'testpass'
TEST_HOST = 'irc.freenode.net'
TEST_PORT = 6667
TEST_CHANNEL = '#testing'


def create_client(host, nickname, password=None, **kwargs):
    """ Create quite simple default client"""
    cl = Client(host, nickname, **kwargs)
    cl.add_handler(handlers.ping_handler, 'PING') # for keepalives
    cl.add_handler(handlers.JoinHandler(TEST_CHANNEL, rejoinmsg='%s sucks'))
    
    cl.add_handler(handlers.ReplyWhenQuoted("I'm busy!"))
    cl.add_handler(handlers.nick_in_use_handler, replycode.ERR_NICKNAMEINUSE)
    if password:
        cl.add_handler(handlers.AuthHandler(nickname, password))
    cl.add_handler(handlers.IRCShutdownHandler())
    return cl
    
def create_server(host, port):
    try:
        ircd = hircd.IRCServer((host, port), hircd.IRCClient)
        hircd.logger.info('Starting hircd on %s:%s', host, port)
        gevent.spawn(ircd.serve_forever)
        hircd.logger.info('hircd started')
    except socket.error, e:
        logging.error(repr(e))
        sys.exit(-2)
    else:
        return ircd
    
class TestSetupClass(object):
    setup_cnt = 0
    
    @classmethod
    def setup_class(cls):
        cls.setup_cnt += 1
        
    def test_1(self):
        assert self.setup_cnt == 1
    
    def test_2(self):
        assert self.setup_cnt == 1
    
    def test_3(self):
        assert self.setup_cnt == 1


class TestLocal(object):
    @classmethod
    def setup_class(cls):
        cls.server = create_server('localhost', TEST_PORT)
        cls.client = create_client('localhost', TEST_NICK, port=TEST_PORT)

    @classmethod
    def teardown_class(cls):
        cls.client.stop()
        cls.server.shutdown()

    def test_connect(self):
        self.client.start()
        with gevent.Timeout(0.5):
            while not self.client.nick in self.server.clients:
                gevent.sleep(0.01)
        assert self.client.nick in self.server.clients
        
    def test_join_on_connect(self):
        with gevent.Timeout(0.5):
            while TEST_CHANNEL not in self.server.channels:
                gevent.sleep(0.01)
        client_list = self.server.channels[TEST_CHANNEL].clients
        assert self.client.nick in [c.nick for c in client_list]
    
    def test_join(self):
        another_channel = TEST_CHANNEL + '_other'
        self.client.send_message(message.Join(another_channel))
        gevent.sleep(0.1)
        client_list = self.server.channels[another_channel].clients
        assert self.client.nick in [c.nick for c in client_list]
    
    def test_authenticated(self):
        # Hircd does not yet provide authentication
        pass
    
    def test_privmsg(self):
        pass
    
    def test_rejoin(self):
        self.client.send_message(message.Kick(TEST_CHANNEL, self.client.nick, 'testkicking'))
        with gevent.Timeout(0.5):
            while self.client.nick in [c.nick for c in self.server.channels[TEST_CHANNEL].clients]:
                gevent.sleep(0.01)
            assert self.client.nick not in [c.nick for c in self.server.channels[TEST_CHANNEL].clients]
        with gevent.Timeout(0.5):
            while self.client.nick not in [c.nick for c in self.server.channels[TEST_CHANNEL].clients]:
                gevent.sleep(0.01)
            assert self.client.nick in [c.nick for c in self.server.channels[TEST_CHANNEL].clients]
    
    def test_reconnect(self):
        self.client.reconnect()
        assert len(self.client._send_queue.queue) == 2
        assert self.client.nick not in self.server.clients
        with gevent.Timeout(3):
            while self.client._send_queue.queue:
                gevent.sleep(0.1)
        assert not self.client._send_queue.queue # Reconnection commands got send
        
    def test_shutdown(self):
        self.client.stop()
        self.client.join()
        assert not self.client._group
        assert self.client._socket is None


@pytest.mark.skipif('True')
class Remote(object):
    @classmethod
    def setUpClass(cls):
        cls.client = cls.create_client(TEST_HOST, TEST_NICK, password=TEST_PASSWORD)

    def test_01_connect(self):
        self.client.start()
        self.client.connect()
        
    def test_02_authenticated(self):
        pass
    
    def test_03_join(self):
        pass
    
    def test_04_msg(self):
        pass
    

class Chatting(object):
    @classmethod
    def setUpClass(cls):
        from geventirc import chatting
        cls.client = cl = Client('localhost', TEST_NICK, password=None)
        cl.add_handler(handlers.ping_handler, 'PING') # for keepalives
        cl.add_handler(handlers.JoinHandler("#testing", rejoinmsg='%s sucks'))
        cl.add_handler(chatting.ChatHandler(TEST_NICK, '#testchat', 
                aiml_dir=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'alice')))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tl = TestLocal()
    tl.setup_class()
    tl.test_connect()
    tl.test_join_on_connect()
    tl.test_join()
    tl.test_rejoin()
    tl.test_reconnect()
    tl.test_shutdown()
    