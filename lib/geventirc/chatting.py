'''
Created on 10.11.2012

This module requires pyaiml installed and some .aiml files

@author: nimrod
'''
import gevent
import time
import os
import random
import aiml #@UnresolvedImport


class ChatKernel(aiml.Kernel):
    default_kwargs = dict(name='Annette', gender='female', master='Antonin', botmaster='boss', 
                          nationality='French', city='Paris', species='geventircbot', job='Secretary', 
                          birthdate='Feb 18th 2012', birthplace='Nantes', language='Python', 
                          religion='atheist', order='hero', location='home', state='busy',
                          email='email@somewhere.com')
    
    def __init__(self, **kwargs):
        aiml.Kernel.__init__(self)
        self.verbose(False)
        kw = self.default_kwargs.copy()
        kw.update(kwargs)
        for key, val in kw.items():
            self.setBotPredicate(key, val)

    def _processDate(self, elem, sessionID):
        """ Process a <date> AIML element.
            <date> elements resolve to the current date and time. The
            AIML specification doesn't require any particular format for
            this information, so I go with whatever's simplest.
        """
        try: 
            fmt = elem[1]['format']
        except KeyError: 
            fmt = '%Y-%m-%d'  
        return time.strftime(fmt)


class ChatHandler(object):
    
    commands = ['PRIVMSG']
    excludes = set(['psychology.aiml', 'update1.aiml', 'reduction4.safe.aiml']) # Disfunct packages

    def __init__(self, name, channel, aiml_dir=None, chat_brain=None, logger=None, kernel_params=None):
        self.channel = channel
        kernel_params = kernel_params or {}
        kernel_params['name'] = name
        self.ai = ChatKernel(**kernel_params)
        self.shut_up = True
        if chat_brain and os.path.isfile(chat_brain):
            self.ai.loadBrain(chat_brain)
        elif aiml_dir and os.path.isdir(aiml_dir):
            for aiml_file in os.listdir(aiml_dir):
                if aiml_file in self.excludes: 
                    continue
                if logger is not None: 
                    logger.info("Learning %s", aiml_file)
                self.ai.learn(os.path.join(aiml_dir, aiml_file))
            if chat_brain:
                self.ai.saveBrain(chat_brain)

    def __call__(self, client, msg):
        channel, content = msg.params[0], ' '.join(msg.params[1:])
        # Only talk in defined channel, if allowed
        if self.channel and channel != self.channel: 
            return
        nick, user_agent, host = msg.prefix_parts
        content_lower = content.lower()
        if hasattr(client, 'authenticated_users') and nick in client.authenticated_users:
            if self.shut_up:
                if client.nick.lower() in content_lower:
                    # Client starts replying (again)
                    self.shut_up = False
                    # No return, so bot directly replies to this msg
                else:
                    return
            elif client.nick.lower() in content_lower:
                for silence_cmd in 'shut up', 'be silent', 'be quiet', 'stop it':
                    if silence_cmd in content_lower:
                        # Client will not answer further talk
                        self.shut_up = True
                        resp = random.choice(("Ok, I'm quiet now", "Sorry for my gossip, I'm already silent"))
                        client.msg(channel, resp)
                        return

        self.ai.setPredicate('name', nick)
        resp = self.ai.respond(content)
        delay = len(resp) / 6.5
        gevent.sleep(delay * (1 + random.random() * 0.5))
        client.msg(channel, resp)

