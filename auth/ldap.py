'''
Module to provide authentication using simple LDAP binds.

REQUIREMENT 1:

Required python modules: ldap
'''
# Import Python libs
from __future__ import absolute_import
import logging
import traceback

# Import Salt libs
from salt.exceptions import CommandExecutionError

# Import third party libs
from jinja2 import Environment
try:
    import ldap
    import ldap.modlist
except ImportError:
    log.error('Failed to import LDAP module, LDAP authentication disabled')
    log.error(traceback.format_exc())

log = logging.getLogger(__name__)

# Defaults, should really go into the master config
__opts__ = {'server': 'localhost',
            'port': '389',
            'tls': False,
            'scope': 2,
            'basedn': 'o=acme,c=gb',
            'binddn': 'uid=admin,o=acme,c=gb',
            'bindpw': 'sssssh',
            'filter': 'emailAddress={{ username }}'}


def _render_template(filter, username):
    '''
    Render filter template, substituting username where found.
    '''
    env = Environment()
    template = env.from_string(filter)
    dict = {'username': username}
    return template.render(dict)


class _LDAPConnection:

    """Setup an LDAP connection."""

    def __init__(self, server, port, tls, binddn, bindpw):
        '''
        Bind to an LDAP directory using passed credentials."""
        '''
        self.server = server
        self.port = port
        self.tls = tls
        self.binddn = binddn
        self.bindpw = bindpw
        try:
            self.LDAP = ldap.initialize('ldap://%s:%s' %
                                        (self.server, self.port))
            self.LDAP.protocol_version = 3  # ldap.VERSION3
            self.LDAP.set_option(ldap.OPT_REFERRALS, 0)  # Needed for AD
            if self.tls:
                self.LDAP.start_tls_s()
            self.LDAP.simple_bind_s(self.binddn, self.bindpw)
        except Exception:
            msg = 'Failed to bind to LDAP server %s:%s as %s' % \
                (self.server, self.port, self.binddn)
            raise CommandExecutionError(msg)


def auth(username, password, **kwargs):
    '''
    Authenticate via an LDAP bind
    '''
    # Get default config, create connection dictionary
    filter = _render_template(__opts__['filter'], username)
    dn = __opts__['basedn']
    scope = __opts__['scope']
    connargs = {}
    for name in ['server', 'port', 'tls', 'binddn', 'bindpw']:
        connargs[name] = __opts__[name]

    # Initial connection with config dn and password
    _ldap = _LDAPConnection(**connargs).LDAP
    # Search for user dn
    msg = 'Running LDAP user dn search with filter:%s, dn:%s, scope:%s' %\
        (filter, dn, scope)
    log.debug(msg)
    result = _ldap.search_s(dn, int(scope), filter)
    if len(result) < 1:
        log.warn('Unable to find user {0}'.format(username))
        return False
    elif len(result) > 1:
        log.warn('Found multiple results for user {0}'.format(username))
        return False
    authdn = result[0][0]
    # Update connection dictionary with user dn and password
    connargs['binddn'] = authdn
    connargs['bindpw'] = password
    # Attempt bind with user dn and password
    log.debug('Attempting LDAP bind with user dn: {0}'.format(authdn))
    try:
        _ldap = _LDAPConnection(**connargs).LDAP
    except:
        log.warn('Failed to authenticate user dn via LDAP: {0}'.format(authdn))
        return False
    msg = 'Successfully authenticated user dn via LDAP: {0}'.format(authdn)
    log.debug(msg)
    return True
