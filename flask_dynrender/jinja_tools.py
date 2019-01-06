import re
from os.path import isfile, join
from babel.dates import format_date as bd_format_date
from babel.dates import format_time as bd_format_time
from babel.dates import format_datetime as bd_format_datetime
from babel.dates import format_timedelta as bd_format_timedelta
from flask import url_for, current_app, g


def url_static(file_name, *args, **kwargs):
    return url_for('static', filename=file_name, *args, **kwargs)


def format_date(d, fmt='medium', lcl='fr'):
    return bd_format_date(d, format=fmt, locale=lcl)


def format_datetime(dt, fmt='medium', lcl='fr'):
    return bd_format_datetime(dt, format=fmt, locale=lcl)


def format_time(tm, fmt='medium', lcl='fr'):
    return bd_format_time(tm, format=fmt, locale=lcl)


def format_timedelta(
    tm, granularity='second', threshold=.85, add_direction=False,
    format='long', lcl='fr'
):
    return bd_format_timedelta(
        tm, granularity=granularity, threshold=threshold,
        add_direction=add_direction, format=format, locale=lcl)


def read(fname, default=None):
    abs_fname = join(current_app.config.get(
        'DATA_FOLDER', current_app.template_folder), fname)
    if isfile(abs_fname):
        return open(abs_fname, 'r').read()
    return default or 'no such file %s' % abs_fname


def script_url(filename, **kwargs):
    return '<script src="{0}" {1}></script>'.format(
        url_static(filename), ' '.join(' %s="%s"' % i for i in kwargs.items()))


def kwargs_base_target(reg_value, default=None):
    m = re.match(reg_value, g.base_target)
    return m.groupdict() if m else default


def kwargs_target(reg_value, default=None):
    m = re.match(reg_value, g.target)
    return m.groupdict() if m else default


def split(values, spliter=',', strip=True):
    return [
        v.strip() if strip else v for v in values.split(spliter) if v.strip()]


def lower_like_id(val, replace=''):
    return val.lower().replace(' ', '_')


def get_fieldclass(field, default='form-control'):
    ret = 'form-control'
    if field.errors:
        ret += ' is-invalid'
    return ret


def field_feedback(field):
    if not field.errors:
        return ''
    feedback = '<div class="invalid-feedback"><ul>'
    for err in field.errors:
        feedback += '<li>{0}</li>'.format(err)
    feedback += '</ul></div>'
    return feedback


env_filters = (
    ('format_date', format_date),
    ('format_datetime', format_datetime),
    ('format_time', format_time),
    ('format_timedelta', format_timedelta),
    ('kw_target', kwargs_target),
    ('kw_base_target', kwargs_base_target),
    ('read', read),
    ('split', split),
    ('lower_like_id', lower_like_id),
    ('field_feedback', field_feedback),
)

env_globals = (
    ('url_static', url_static),
    ('script_url', script_url),
    ('get_fieldclass', get_fieldclass),
)
