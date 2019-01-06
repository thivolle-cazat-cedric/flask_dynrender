import re
import json
from os import environ
from os.path import isfile, join
from configparser import ConfigParser
from flask import Flask, request
from flask_assets import Environment
from flask_mail import Mail
from flask_wtf.recaptcha.validators import RECAPTCHA_ERROR_CODES
from . import jinja_tools
from .mail_handler import check_mail_conf


assets = Environment()
mail = Mail()
FLOAT_REG = re.compile(r'^\d?(\.|\,)\d+$')
TRUE_VALUES = ('TRUE', 'YES',)
FALSE_VALUES = ('FALSE', 'NO',)


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


def init_app(app, conf_file=None, flask_section='flask'):
    conf_file = conf_file or environ.get('FLASK_DYNRENDER', None)
    bool_keys = ('DEBUG', 'ASSETS_DEBUG')
    if not conf_file:
        app.logger.warning('No configuration file')
        return False
    if not isfile(conf_file):
        mess = 'Configration file not found: %s' % conf_file
        app.logger.error(mess)
        raise IOError(mess)

    conf_p = ConfigParser()
    conf_p.read(conf_file)
    if flask_section in conf_p.sections():
        app.config.update({
            key.upper(): _cast_value(conf_p.get(flask_section, key))
            for key in conf_p.options(flask_section)
        })
        for key in bool_keys:
            if conf_p.has_option(flask_section, key.lower()):
                app.config[key] = conf_p.getboolean(flask_section, key.lower())
    tpl_folder = app.config.get('TEMPLATE_FOLDER', app.template_folder)
    app.template_folder = tpl_folder
    app.static_folder = app.config.get('STATIC_FOLDER', app.static_folder)
    app.config_parser = conf_p
    app.conf_dynrender = {}
    app.logger.debug(
        'static_folder: %s | template_folder: %s | data_folder: %s' % (
            app.static_folder, app.template_folder, app.config['DATA_FOLDER']))
    _actions = (
        (app.jinja_env.globals, jinja_tools.env_globals),
        (app.jinja_env.filters, jinja_tools.env_filters))
    for jina_var, items in _actions:
        jina_var.update({k: v for k, v in items})

    return True


def init_urls(app):
    from . import views
    view_tgt = app.conf_dynrender.get('VIEW_CLASS', 'JsonJinjaHtmlView')
    viewcls = [
        V
        for V in views.BaseView.__subclasses__()
        if V.__name__ == view_tgt
    ]
    if not viewcls:
        app.logger.info('Class "%s" not found' % view_tgt)
        return False
    viewcls = viewcls[0]
    endpnt = app.conf_dynrender.get('ENDPOINT', 'root')
    app.add_url_rule('/', view_func=viewcls.as_view('%s_emtpy' % endpnt))
    app.add_url_rule('/<path:target>', view_func=viewcls.as_view(endpnt))


def init_assets(app):
    assets.init_app(app)
    yaml_cfg = join(
        app.config['DATA_FOLDER'],
        app.config.get('ASSETS_FILENAME', 'assets.yaml'))
    if isfile(yaml_cfg):
        app.logger.debug('load yaml cfg: %s' % yaml_cfg)
        assets.from_yaml(yaml_cfg)
    else:
        app.logger.debug('No yaml assets configuration file')


def init_contact(app):
    app.contact_uri = None
    if not app.config_parser.has_section('contact'):
        return False
    recapt_key = ('USE_SSL', 'PUBLIC_KEY', 'PRIVATE_KEY', 'PARAMETERS')
    app.contact_uri = app.config_parser.get('contact', 'uri')
    contact = {
        ('RECAPTCHA_%s' % opt.upper()):
            _cast_value(app.config_parser.get('contact', opt))
        for opt in app.config_parser.options('contact')
        if opt.upper() in recapt_key}
    app.config.update(contact)
    RECAPTCHA_ERROR_CODES.update({
        'missing-input-secret': 'Le paramettre secret est manquant.',
        'invalid-input-secret': 'le parameter secret est mal formaté',
        'missing-input-response': 'Le paramètre de réponse est manquant',
        'invalid-input-response': 'La réponse est invalid ou malformaté.'
    })
    app.config['MAIL'] = check_mail_conf({
        (opt.upper()): _cast_value(app.config_parser.get('mail', opt))
        for opt in app.config_parser.options('mail')
    })
    mail.init_app(app)
    return True


def create_app(
    conf_file=None, name=None, flask_section='flask', dynrender='dynrender'
):
    app = Flask(name or __name__)
    if init_app(app, conf_file, flask_section):
        app.conf_dynrender.update({
            k.upper(): app.config_parser.get(dynrender, k)
            for k in app.config_parser.options(dynrender)
        })
        init_urls(app)
        init_assets(app)
        init_contact(app)
    else:
        app.logger.error('No dynrender application can be created')
    return app
