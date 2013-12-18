import pytest
from geventirc.message import irc_split, irc_unsplit, prefix_split, \
        low_level_quote, low_level_dequote, ctcp_quote

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

prefix_splits = (
    # Examples from RFC 2812
    ('WiZ!jto@tolsun.oulu.fi', ('WiZ', 'jto', 'tolsun.oulu.fi')),
    ('syrk!kalt@millennium.stealth.net', ('syrk', 'kalt', 'millennium.stealth.net')),
    ('Trillian', ('Trillian', None, None)),
    ('Angel!wings@irc.org', ('Angel', 'wings', 'irc.org')),
)

@pytest.mark.parametrize(("prefix", "prefixsplit"),  prefix_splits)
def test_prefix_split(prefix, prefixsplit):
    assert prefixsplit == prefix_split(prefix)
    
def test_low_level_quoting():
    data = "some mess\r\0age with\nspecial\0charaters"
    encoded = low_level_quote(data)
    assert encoded == 'some mess\x10r\x100age with\x10nspecial\x100charaters'
    assert data == low_level_dequote(data)

def test_ctcp_quoting():
    data = "some mess\r\0age with\nspeci:al\0charaters"
    encoded = low_level_quote(data)
    encoded = ctcp_quote(encoded)
    print repr(encoded)
    assert encoded == 'some mess\x10r\x100age with\x10nspeci:al\x100charaters'

