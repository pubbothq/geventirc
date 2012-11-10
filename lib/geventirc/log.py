'''
Created on 10.11.2012

@author: nimrod
'''
import logging


class IRCLogHandler(logging.Handler):
    """ Dumps usual log output to some IRC channel
    """
    
    def __init__(self, client, channel, level=logging.NOTSET):
        logging.Handler.__init__(self, level=level)
        self.client = client
        self.channel = channel
        self.client.join_channel(self.channel)

    def emit(self, record):
        self.client.msg(self.channel, self.format(record))


