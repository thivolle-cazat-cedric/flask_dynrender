import re
from configparser import ConfigParser, ExtendedInterpolation
from flask import current_app
from .base import BaseContextHandler


class IniContextHandler(BaseContextHandler):

    extension = 'ini'
    _list_reg = re.compile(
        r'^(?P<root>[a-zA-Z_0-9]+)\:(?P<index>[0-9]+)$')
    _dict_reg = re.compile(
        r'^(?P<root>[a-zA-Z_0-9]+)\.(?P<key>[a-zA-Z_0-9]+)$')

    def get_root_path(self):
        return current_app.config.get('INI_DATA_DIR', super().get_root_path())

    def _section_todict(self, conf_p, section):
        data = {
            opt: self.parse_value(conf_p.get(section, opt))
            for opt in conf_p.options(section)}
        return data

    def _find_dict_keys(self, keys):
        '''
        '''
        items = {}
        for key in keys:
            match = self._dict_reg.match(key)
            if match:
                values = match.groupdict()
                if values['root'] not in items:
                    items[values['root']] = []
                items[values['root']].append(values['key'])
        return items

    def _find_list_keys(self, keys):
        '''
        '''
        items = {}
        for key in keys:
            match = self._list_reg.match(key)
            if match:
                values = match.groupdict()
                if values['root'] not in items:
                    items[values['root']] = []
                items[values['root']].append(int(values['index']))
        return items

    def _get_ignored_keys(self, keys):
        return tuple(
            k for k in keys
            if self._dict_reg.match(k) or self._list_reg.match(k))

    def _merge_dict(self, data, items, conf_p):
        for root, keys in items.items():
            data[root] = {}
            for key in keys:
                if key not in data[root]:
                    data[root][key] = {}
                section = '%s.%s' % (root, key)
                data[root][key].update(self._section_todict(conf_p, section))
                data.pop(section)

    def _merge_list(self, data, items, conf_p):
        for key, indexes in items.items():
            data[key] = []
            for index in sorted(indexes):
                section = ('%s:%s' % (key, index))
                s_dict = self._section_todict(conf_p, section)
                s_dict['__index__'] = index
                data[key].append(s_dict)
                data.pop(section)

    def get_data(self, target):
        conf = ConfigParser(
            interpolation=ExtendedInterpolation(),
            inline_comment_prefixes=(';#',)
        )
        conf.read(target)
        data = {}
        _keys = conf.sections()
        dict_items = self._find_dict_keys(_keys)
        list_items = self._find_list_keys(_keys)
        ignors_keys = self._get_ignored_keys(_keys)
        for section in conf.sections():
            data[section] = {
                opt: self.parse_value(conf.get(section, opt))
                for opt in conf.options(section) if opt not in ignors_keys
            }
        data.update(data.pop('scope', {}))
        self._merge_dict(data, dict_items, conf)
        self._merge_list(data, list_items, conf)
        return data

    def update_action_get(self, data_tgt, key, get_args):
        if self._sub_include:
            return False

        _get_args = get_args
        get_args = get_args.split(',')
        inc_tgt = get_args[0].strip()
        get_name = get_args[1].strip()
        dst = get_args[2] if len(get_args) > 2 else get_args[1]
        if ':' not in get_name:
            return super().update_action_get(data_tgt, key, _get_args)
        get_name, index = get_name.split(':')[:2]
        index = int(index)
        ctx_hdl = type(self)(inc_tgt)
        ctx_hdl._sub_include = True
        ctx_hdl.process()
        src_data = ctx_hdl.get_scope().get(get_name, [])
        try:
            value = next(
                x for x in src_data if x.get('__index__', -10) == index)
        except StopIteration:
            current_app.logger.warning(
                'action get fail on target %s, key %s:%s' % (
                    inc_tgt, get_name, index))
            return False
        self._data[data_tgt][dst] = value
        return True
