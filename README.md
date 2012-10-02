# salt-ldap

This repo contains some salt LDAP plugins.  Current plugins are:

 * Module: an LDAP salt module which can perform searches against an LDAP server.

 * Pillar: an LDAP pillar backend which can retrieve salt states and values from an LDAP directory.

## Module:

Currently only a search function has been implemented as the module currently exists purely to
support the pillar plugin.

ldap.search:

Run an arbitrary LDAP query and return the results.

CLI Examples::

    salt 'ldaphost' ldap.search "filter=cn=myhost"

returns: 

    'myhost': { 'count': 1,
                'results': [['cn=myhost,ou=hosts,o=acme,dc=local',
                    {'saltKeyValue': ['ntpserver=ntp.acme.local', 'foo=myfoo'],
                     'saltState': ['foo', 'bar']}]],
                'time': {'human': '1.2ms', 'raw': '0.00123'}}}

Search and connection options can be overridden by specifying the relevant
option as key=value pairs, for example:

    salt 'ldaphost' ldap.search filter=cn=myhost dn=ou=hosts,o=acme,dc=local scope=1 attrs='' server='localhost' port='7393' tls=True bindpw='ssh'

### Module Config:

Default values for all options with the expection of filter (which must be specified as an argument)
can be placed in the minion config.  An example minion config snippet:

    # In /etc/salt/minion
    # LDAP module configuration
    ldap.basedn: o=isp,o=acme,dc=local
    ldap.binddn: uid=admin,o=acme,dc=local
    ldap.bindpw: sssssh
    ldap.attrs: [saltKeyValue, saltState]

## Pillar:

This pillar module parses a config file specified in the salt master config, and
executes a series of LDAP searches based on that config.  Data returned by these
searches is aggregrated with data items found later in the LDAP search order 
overriding data found earlier on. The final result set is merged with the pillar
data.


### Pillar Config:

Load the pillar plugin by adding the following to your salt master config:

    ext_pillar:
        - pillar_ldap: /etc/salt/pillar/plugins/pillar_ldap.yaml

Adjust to suit the location of your pillar_ldap.yaml config file

The behaviour of the pillar module is controlled by the config file

An example config file is included below:

    ldap: &defaults
        server: localhost
        port: 389
        tls: False
        dn: o=test,o=acme,dc=local
        binddn: uid=admin,o=acme,dc=local
        bindpw: ssssh
        attrs: [saltKeyValue, saltState]
        scope: 1

    search_order:
        - hosts
        - {{ fqdn }} 

    hosts:
        <<: *defaults
        filter: ou=hosts
        dn: o=testorg,o=test,o=acme,dc=local

    {{ fqdn }}:
        <<: *defaults
        filter: cn={{ fqdn }}
        dn: ou=hosts,o=testorg,o=test,o=acme,dc=local

The config file my be paramertised with grains (e.g. fqdn)

Attributes tagged in the pillar config file ('attrs') are scannned for the
'key=value' format.  Matches are written to the dictionary directly as:
dict[key] = value

For example, search result:

    saltKeyValue': ['ntpserver=ntp.acme.local', 'foo=myfoo']
    
is written to the pillar data dictionary as:

    {'ntpserver': 'ntp.acme.local', 'foo': 'myfoo'}


Schema:

The attributes specified in both the module and pillar plugin use a custom schema, but any existing 
LDAP attributes can be used if this is preferred.  For reference the following schema additions (use your own OID space) were used to implement the SaltKeyValue and SaltState attributes in my particular environment:

    attributetype (  1.3.6.1.4.1.25593.2.1.1.10.10
    NAME 'saltState'
    DESC 'Salt State'
    EQUALITY caseIgnoreMatch
    SUBSTR caseIgnoreSubstringsMatch
    SYNTAX 1.3.6.1.4.1.1466.115.121.1.15 )

    attributetype ( 1.3.6.1.4.1.25593.2.1.1.10.11
    NAME 'saltKeyValue'
    DESC 'Salt data expressed as a key=value pair'
    EQUALITY caseIgnoreMatch
    SUBSTR caseIgnoreSubstringsMatch
    SYNTAX 1.3.6.1.4.1.1466.115.121.1.15 )

    objectclass ( 1.3.6.1.4.1.25593.2.1.2.12 
    NAME 'saltData' 
    DESC 'Salt Data objectclass'
    SUP top AUXILIARY
    MAY ( saltstate $ saltkeyvalue ) )
