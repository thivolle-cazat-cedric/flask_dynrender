import re
import json
from os.path import realpath, join
from flask import redirect, request, url_for


FLOAT_REG = re.compile(r'^\d?(\.|\,)\d+$')
TRUE_VALUES = ('TRUE', 'YES',)
FALSE_VALUES = ('FALSE', 'NO',)


def redirect_to_static():
    return redirect(url_for('static', filename=request.path[1:]))


def _cast_value(value):
    if not isinstance(value, str):
        return value
    try:
        if value.isdigit():
            return int(value)
        if FLOAT_REG.match(value):
            return float(value)
        if value.upper() in TRUE_VALUES:
            return True
        if value.upper() in FALSE_VALUES:
            return False
        if value.startswith('{') and value.endswith('}'):
            return json.loads(value)
    except:
        pass
    return value


def _get_realpath(path):
    if path.startswith('/'):
        return path
    return realpath(path)
