import re
import datetime
from os import walk
from os.path import splitext, join, dirname, isfile, basename
from flask import current_app
from ..exceptions import DataHandlerNotReady
from ..jinja_tools import kwargs_base_target


date_now_re = re.compile(r'^Date\(now\)$')
date_re = re.compile(
    r'^Date\((?P<year>\d{4})\,(?P<month>[01]?\d)\,(?P<day>[0-3]?\d)\)$')
datetime_now_re = re.compile(r'^Datetime\(now\)$')
datetime_re = re.compile(
    r'^Datetime\((?P<year>\d{4})\,(?P<month>[01]?\d)\,(?P<day>[0-3]\d)\,'
    r'(?P<hour>[0-2]?\d)\,(?P<minute>[0-5]?\d)(\,(?P<second>[0-5]?\d))?\)$')

match_set = [
    (None, re.compile(r'^none$', re.IGNORECASE)),
    (False, re.compile(r'^false$', re.IGNORECASE)),
    (True, re.compile(r'^true$', re.IGNORECASE)),
]
match_cast = [
    (float, re.compile(r'^\d+[\.]\d+$')),
    (int, re.compile(r'^\d+$'))
]
datetime_cast = [
    (datetime.date, date_re),
    (datetime.date.today, date_now_re),
    (datetime.datetime, datetime_re),
    (datetime.datetime.now, datetime_now_re),
]


class BaseContextHandler(object):
    target = None
    _processed = False
    extension = None
    global_name = '_global_'
    actions = (
        ('append', r'^\+[\w\s_\-]+[^-_+]$'),
        ('prepend', r'^[^-_+][\w\s_\-]+\+$'),
        ('include', r'^!include$'),
        ('get', r'^!get$'),
        ('read', r'^!read_(?P<key>.+)$')
    )
    _sub_include = False

    def __init__(self, target, **kwargs):
        self.target = target
        self.kwargs = kwargs
        self._data = {
            'global': {
            },
            'scope': {},
            'meta': {}
        }
        if not self._data['global']:
            self._data['global'] = {}
        self._data['global']['target'] = splitext(target)[0]
        self._data['global']['base_target'] = basename(
            self._data['global']['target'])
        self._data['global']['kwargs'] = kwargs
        self._processed = False

    def _find_files(self, fname):
        return tuple(
            join(folder, fname)
            for folder, _, files in walk(self.get_root_path())
            if fname in files)

    def is_meta_key(self, key):
        return re.sub(r'[\+\|\_\-\.\#]', '', key).startswith('meta')

    def parse_value(self, value):
        if not isinstance(value, str):
            return value
        strip_v = value.strip()
        for v, reg in match_set:
            if reg.match(strip_v) is not None:
                return v
        for _cls, reg in match_cast:
            if reg.match(strip_v) is not None:
                return _cls(strip_v)
        for _cls, reg in datetime_cast:
            match = reg.match(strip_v)
            if match:
                gpdict = match.groupdict()
                if gpdict:
                    return _cls(
                        **{k: int(v) for k, v in gpdict.items()})
                else:
                    return _cls()
        return value

    def meta_parse(self, data):
        meta = {}
        for key in data:
            if self.is_meta_key(key):
                if isinstance(data[key], dict):
                    meta.update(data[key])
                else:
                    meta[key.replace('meta_', '')] = data[key]
        return meta

    def find_action(self, key):
        for action_name, reg in self.actions:
            match = re.search(reg, key)
            if match:
                return action_name, match
        return None, None

    def get_root_path(self):
        return current_app.config.get(
            'DATA_FOLDER', current_app.template_folder)

    def get_scope_fname(self):
        return '%s.%s' % (splitext(self.target)[0], self.extension)

    def get_scope_path(self):
        return join(self.get_root_path(), self.get_scope_fname())

    def get_data(self, target):
        raise NotImplementedError()

    def get_action(self, data_tgt, action_name, key, value, match):
        fct_name = 'get_action_%s' % action_name.lower()
        action_handler = getattr(self, fct_name, None)
        if action_handler:
            return action_handler(data_tgt, key, value, match)
        return key, value

    def get_action_append(self, data_tgt, key, value, match):
        n_key = key[1:]
        if n_key not in self._data[data_tgt]:
            return n_key, value
        if isinstance(value, dict):
            data = self._data[data_tgt][n_key].copy()
            data.update(value)
            return n_key, data
        data = self._data[data_tgt][n_key]
        data += value
        return n_key, data

    def get_action_prepend(self, data_tgt, key, value, match):
        self._data[data_tgt][key] = value
        n_key = key[:-1]
        if n_key not in self._data[data_tgt]:
            return n_key, value
        if isinstance(value, dict):
            value.update(self._data[data_tgt][n_key].copy())
            return n_key, value
        return n_key, value + self._data[data_tgt][n_key]

    def get_action_include(self, data_tgt, key, inc_tgt, match):
        if self._sub_include:
            return False
        ctx_hdl = type(self)(inc_tgt)
        ctx_hdl._sub_include = True
        ctx_hdl.process_scope()
        return 'include', ctx_hdl._data['scope']

    def get_action_get(self, data_tgt, key, get_args, match):
        if self._sub_include:
            return False
        d_val = get_args
        get_args = get_args.split(',')
        inc_tgt = get_args[0].strip()
        get_name = get_args[1].strip()
        n_key = get_args[2] if len(get_args) > 2 else get_args[1]
        ctx_hdl = type(self)(inc_tgt)
        ctx_hdl._sub_include = True
        ctx_hdl.process_scope()
        ctx_hdl._processed = True
        scope = ctx_hdl.get_scope()

        if ':' in get_name:
            i = int(get_name.split(':')[1])
            get_name = get_name.split(':')[0]
            try:
                value = scope.get(get_name, [])[i]
            except IndexError:
                current_app.logger.warning(
                    'fail to action get in target : %s key : %s:%s' % (
                        inc_tgt, get_name, i))
                return key, d_val
        elif '.' in get_name:
            k = int(get_name.split('.')[1])
            get_name = get_name.split('.')[0]
            try:
                value = scope.get(get_name, {})[k]
            except KeyError:
                current_app.logger.warning(
                    'fail to action get in target : %s key : %s.%s' % (
                        inc_tgt, get_name, k))
                return key, d_val
        value = scope.get(get_name)
        return n_key, value

    def get_action_read(self, data_tgt, rkey, fname, match):
        key = match.groupdict()['key']
        self._data[data_tgt][key] = fname
        file_path = join(self.get_root_path(), fname)
        if isfile(file_path):
            value = open(file_path, 'r').read()
        else:
            value = 'no such file: %s' % file_path
        return key, value

    def update(self, tgt, data):
        if tgt not in self._data:
            raise ValueError('key "%s" not initialized in data' % tgt)
        for key, val in data.items():
            if isinstance(val, str):
                action, match = self.find_action(key)
                if action:
                    key, val = self.get_action(tgt, action, key, val, match)
            elif key not in ('meta', 'global'):
                key, val = self.clean_val(tgt, key, val)
            self._data[tgt][key] = val

    def clean_val(self, tgt, key, val):
        if isinstance(val, dict):
            val = self.clean_val_dict(tgt, val)
        if isinstance(val, (list, tuple)):
            val = self.clean_val_list(tgt, key, val)
        return key, val

    def clean_val_dict(self, tgt, data):
        cleaned = {}
        for key, val in data.items():
            if isinstance(val, dict):
                val = self.clean_val_dict(tgt, val)
            else:
                action, match = self.find_action(key)
                if action:
                    key, val = self.get_action(tgt, action, key, val, match)
            cleaned[key] = val
        return cleaned

    def clean_val_list(self, tgt, key, val):
        cleaned = []
        for v in val:
            if isinstance(v, dict):
                v = self.clean_val_dict(tgt, v)
            else:
                action, match = self.find_action(val)
                if action:
                    key, val = self.get_action(tgt, action, key, val, match)
            cleaned.append(v)
        return cleaned

    def process_global(self):
        global_fname = '{0}.{1}'.format(self.global_name, self.extension)
        target_dirs = ['']
        target_dirs += (n for n in dirname(self.target).split('/') if n)
        dir_name = self.get_root_path()
        g_files = self._find_files(global_fname)
        for folder in target_dirs:
            dir_name = join(dir_name, folder)
            target_fname = join(dir_name, global_fname)
            if target_fname in g_files:
                self.update('global', self.get_data(target_fname))
        return True

    def process_scope(self):
        try:
            self.update('scope', self.get_data(self.get_scope_path()))
        except Exception as e:
            current_app.logger.error('Processing scope error', exc_info=e)
            return False
        return True

    def process_meta(self):
        for data in self._data.values():
            self.update('meta', self.meta_parse(data))

    def process(self):
        self.process_global()
        self.process_scope()
        self.process_meta()
        self._processed = True

    def get_global(self):
        if not self._processed:
            raise DataHandlerNotReady('data not processed')
        return self._data.get('global', {})

    def get_scope(self):
        if not self._processed:
            raise DataHandlerNotReady('data not processed')
        return self._data.get('scope', {})

    def get_uri_kwargs(self):
        kwargs_reg = self._data.get('global', {}).get('uri_kwargs')
        if kwargs_reg:
            match = re.match(kwargs_reg, self.target)
            return match.groupdict() if match else {}

    def get_meta(self):
        if not self._processed:
            raise DataHandlerNotReady('data not processed')
        return self._data.get('meta', {})
