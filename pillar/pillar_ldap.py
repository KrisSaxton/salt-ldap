'''
This pillar module parses a config file specified in the salt master config, and
executes a series of LDAP searches based on that config.  Data returned by these
searches is aggregrated with data items found later in the LDAP search order 
overriding data found earlier on. The final result set is merged with the pillar
data.
'''

# Import python libs
import os
import logging
import traceback

# Import salt libs
import salt.config
import salt.utils
from salt._compat import string_types

# Import third party libs
import yaml
from jinja2 import Environment, FileSystemLoader
try:
    import ldap
    import ldap.modlist
    has_ldap = True
except ImportError:
    has_ldap = False

# Set up logging
log = logging.getLogger(__name__)

def __virtual__():
    '''
    Only return if ldap module is installed
    '''
    if has_ldap:
        return 'pillar_ldap'
    else:
        return False

def _render_template(config_file):
    '''
    Render config template, substituting grains where found.
    '''
    dirname, filename = os.path.split(config_file)
    env = Environment(loader=FileSystemLoader(dirname))
    template = env.get_template(filename)
    config = template.render(__grains__)
    return config

def _config(name, conf):
    '''
    Return a value for 'name' from  the config file options.
    '''
    try:
        value = conf[name]
    except KeyError:
        value = None
    return value

def _result_to_dict(data, attrs=None):
    '''
    Formats LDAP search results as a pillar dictionary.
    Attributes tagged in the pillar config file ('attrs') are scannned for the
    'key=value' format.  Matches are written to the dictionary directly as:
    dict[key] = value
    For example, search result:

        saltKeyValue': ['ntpserver=ntp.acme.local', 'foo=myfoo']
    
    is written to the pillar data dictionary as:

        {'ntpserver': 'ntp.acme.local', 'foo': 'myfoo'}
    '''
    
    if not attrs:
        attrs = []
    result = {}
    for key in data:
        if key in attrs:
            for item in data.get(key):
                if '=' in item:
                    k, v = item.split('=')
                    result[k] = v
                else:
                    result[key] = data.get(key)
        else:
            result[key] = data.get(key)
    return result

def _do_search(conf):
    '''
    Builds connection and search arguments, performs the LDAP search and
    formats the results as a dictionary appropriate for pillar use.
    '''
    # Build LDAP connection args
    connargs = {}
    for name in ['server', 'port', 'tls', 'binddn', 'bindpw']:
        connargs[name] = _config(name, conf)
    # Build search args
    try:
        filter = conf['filter']
    except KeyError:
        raise SaltInvocationError('missing filter')
    dn = _config('dn', conf)
    scope = _config('scope', conf) 
    attrs = _config('attrs', conf) 
    # Perform the search
    try:
       raw_result = __salt__['ldap.search'](filter, dn, scope, attrs, **connargs)['results'][0][1]
    except Exception:
        msg = traceback.format_exc()
        log.critical('Failed to retrieve pillar data from LDAP: {0}'.format(msg))
        return {}
    if raw_result:
        result = _result_to_dict(raw_result, attrs)
    return result

def ext_pillar(config_file):
    '''
    Execute LDAP searches and return the aggregated data
    '''
    if os.path.isfile(config_file):
        try:
            with open(config_file, 'r') as raw_config:
                config = _render_template(config_file) or {}
                opts = yaml.safe_load(config) or {}
            opts['conf_file'] = config_file
        except Exception as e:
            import salt.log
            msg = 'Error parsing configuration file: {0} - {1}'
            if salt.log.is_console_configured():
                log.warn(msg.format(config_file, e))
            else:
                print(msg.format(config_file, e))
    else:
        log.debug('Missing configuration file: {0}'.format(config_file))

    data = {}
    for source in opts['search_order']:
        config = opts[source]
        result = _do_search(config)
        if result:
            data.update(result)
    return data
