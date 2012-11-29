import pytest
from geventirc.message import irc_split, irc_unsplit

message_splits = (
    ('NICK :test_name', ('', 'NICK', ['test_name'])),
    ('NICK test_name', ('', 'NICK', ['test_name'])),
    (':srv NICK :test_name', ('srv', 'NICK', ['test_name'])),        
    (':srv NICK :test_name asdf', ('srv', 'NICK', ['test_name asdf'])),   
    (':srv NICK test_name asdf', ('srv', 'NICK', ['test_name', 'asdf'])),          
    (':srv NICK test_name asdf :sdf: ddd', ('srv', 'NICK', ['test_name', 'asdf', 'sdf: ddd'])),
    
    # Examples from RFC 2812
    (':Angel!wings@irc.org PRIVMSG Wiz :Are you receiving this message ?', 
            ('Angel!wings@irc.org', 'PRIVMSG', ['Wiz', 'Are you receiving this message ?'])),
    ('PRIVMSG kalt%millennium.stealth.net :Do you like cheese?', 
            ('', 'PRIVMSG', ['kalt%millennium.stealth.net', 'Do you like cheese?']))          
)

@pytest.mark.parametrize(("msg", "msgsplit"),  message_splits)
def test_irc_split(msg, msgsplit):
    assert msgsplit == irc_split(msg)

@pytest.mark.parametrize(("msg", "msgsplit"),  message_splits)
def test_split_unsplit(msg, msgsplit):
    msg = irc_unsplit(*msgsplit)
    assert irc_split(msg) == msgsplit, \
            "%s -> %s -> %s" % (msg, msgsplit, irc_split(msg))

