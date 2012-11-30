import gevent
from geventirc import message
from geventirc import replycode


def ping_handler(client, msg):
    client.send_message(message.Pong(client.nick))

def print_handler(client, msg):
    print msg.encode()[:-2]

def log_handler(client, msg):
    client.logger.debug("recv: " + msg.encode()[:-2])

def nick_in_use_handler(client, msg):
    client.nick = msg.params[1] + '_'
    client.send_message(message.Nick(client.nick))


class AuthHandler(object):
    
    commands = ['001']

    def __init__(self, name, password, command='OPER'):
        self.name = name
        self.password = password
        self.command = command
        
    def __call__(self, client, msg):
        client.send_message(message.Command((self.name, self.password), command=self.command))

        
class IRCShutdownHandler(object):
    """ Reconnect when server dies 
    """
    commands = ['NOTICE']
    
    def __call__(self, client, msg):
        if "Exiting" in msg.params:
            client.logger.info("Stopping client")
            client.stop()
            gevent.sleep(10)
            client.logger.info("Starting client")
            client.start()
            
            
class JoinHandler(object):
    
    commands = ['001', 'KICK']

    def __init__(self, channel, rejoin=True, rejoinmsg=''):
        self.channel = channel
        self.rejoin = rejoin
        self.rejoinmsg = rejoinmsg

    def __call__(self, client, msg):
        if msg.command == '001':
            client.channels.add(self.channel)
            client.send_message(message.Join(self.channel))
        elif self.rejoin:
            chan, kicked = msg.params[:2]
            kicker = msg.prefix_parts[1]
            # reason = '' if len(msg.params) <= 2 else msg.params[2]
            if chan in client.channels and kicked == client.nick:
                client.send_message(message.Join(self.channel))
                if self.rejoinmsg:
                    if "%s" in self.rejoinmsg: 
                        rejoinmsg = self.rejoinmsg % kicker
                    else: 
                        rejoinmsg = self.rejoinmsg
                    client.send_message(message.PrivMsg(self.channel, rejoinmsg))


class NickServHandler(object):
    
    commands = ['001',
        replycode.ERR_NICKNAMEINUSE,
        replycode.ERR_NICKCOLLISION]

    def __init__(self, nick, password):
        self.nick = nick
        self.current_nick = None
        self.password = password

    def __call__(self, client, msg):
        if msg.command == str(replycode.ERR_NICKNAMEINUSE) or \
                msg.command == str(replycode.ERR_NICKCOLLISION):
            nick = msg.params[1]
            self.current_nick = nick + '_'
            client.send_message(message.Nick(self.current_nick))
            return
        if msg.command == '001':
            client.send_message(message.Nick(self.nick))
            self.current_nick = self.nick
            msg = message.PrivMsg('nickserv', 'identify ' + self.password)
            client.send_message(msg)


class ReplyWhenQuoted(object):
    
    commands = ['PRIVMSG']

    def __init__(self, reply):
        self.reply = reply

    def __call__(self, client, msg):
        channel, content = msg.params[0], " ".join(msg.params[1:])
        if client.nick in content:
            # check if this is a direct message
            if channel != client.nick:
                client.msg(channel, self.reply)


class MeHandler(object):
    commands = ['PRIVMSG']

    def __init__(self, reply):
        self.reply = reply

    def __call__(self, client, msg):
        if client.nick == msg.params[0]:
            nick, _, _ = msg.prefix_parts
            client.send_message(
                    message.Me(nick, self.reply))


class ReplyToDirectMessage(object):

    commands = ['PRIVMSG']

    def __init__(self, reply):
        self.reply = reply

    def __call__(self, client, msg):
        channel = msg.params[0]
        if client.nick == channel:
            nick, user_agent, host = msg.prefix_parts
            if nick is not None:
                client.msg(nick, self.reply)


class PrivMsgBuffer(object):
    commands = ['PRIVMSG']
    
    def __init__(self):
        self.buffer = []

    def __call__(self, client, msg):
        channel = msg.params[0]
        if client.nick == channel:
            nick, user_agent, host = msg.prefix_parts
            if nick is not None:
                self.buffer.append((nick, msg))
                
    def __len__(self):
        return len(self.buffer)
        

class PeriodicMessage(object):
    """ Send a message every interval or `wait`
    !!! gevent 1.0 only !!!
    """
    
    commands = ['001']

    def __init__(self, channel, msg='hello', wait=1.0):
        self.channel = channel
        self.msg = 'hello'
        self.wait = wait

    def start(self, client, msg):
        self.client = client
        self._schedule()

    def _schedule(self):
        timer = gevent.get_hub().loop.timer(self.wait) #@UndefinedVariable
        timer.start(self.__call__)

    def run(self):
        self.client.msg(self.channel, self.msg)
    
    def __call__(self):
        gevent.spawn(self.run)
        self._schedule()

