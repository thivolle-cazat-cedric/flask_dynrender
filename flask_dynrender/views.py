from os.path import splitext, join, dirname
from jinja2.exceptions import TemplateNotFound
from flask import abort, request, g, current_app, render_template, flash
from flask.views import MethodView as FlaskMethodView
from .context_handlers import JsonContextHandler, IniContextHandler
from .forms import get_form_class
from .mail_handler import get_message
from . import mail


class BaseView(FlaskMethodView):
    path = None
    kwargs = None
    target_kw = 'target'
    TPL_EXT = 'jinja2'
    ext_uri = 'html'
    ext_sensitive_case = True
    hidden_prefix = ('.', '_')
    auto_index = True
    ctx_handler_class = None

    def dispatch_request(self, *args, **kwargs):
        meth = getattr(self, request.method.lower(), None)
        self.kwargs = kwargs
        self.target = self.clean_target(kwargs.get(self.target_kw, ''))
        if not self.target:
            self.target = 'index.{0}'.format(self.ext_uri)
        if not self.validate_target(self.target):
            abort(404)

        # If the request method is HEAD and we don't have a handler for it
        # retry with GET.
        if meth is None and request.method == 'HEAD':
            meth = getattr(self, 'get', None)

        return meth() if meth else abort(405)

    def validate_target(self, target):
        if any(target.startswith(x) for x in self.hidden_prefix):
            return False
        if self.ext_sensitive_case:
            return target.endswith(self.ext_uri)
        return target.lower().endswith(self.ext_uri.lower())

    def clean_target(self, target):
        if self.auto_index and not target.endswith('.%s' % self.ext_uri):
            return join(target, 'index.{0}'.format(self.ext_uri))
        return target

    def get_template(self):
        path = '{0}.{1}'.format(splitext(self.target)[0], self.TPL_EXT)
        pattern = join(dirname(self.target), '_pattern_.{0}'.format(self.TPL_EXT))
        try:
            return current_app.jinja_env.select_template([path, pattern])
        except TemplateNotFound as e:
            if current_app.debug:
                raise e
            abort(404)

    def get_ctx_handler_class(self):
        if self.ctx_handler_class is None:
            raise NotImplementedError(
                'Overide get_ctx_handler_class or define ctx_handler_class')
        return self.ctx_handler_class

    def get_ctx_handler(self, **kwargs):
        kwargs.pop('target', None)
        return self.get_ctx_handler_class()(target=self.target, **kwargs)

    def get_context(self, **kwargs):
        ctx_kw = self.kwargs.copy()
        ctx_kw.update(kwargs)
        ctx_handler = self.get_ctx_handler(identifier=self.target, **ctx_kw)
        ctx_handler.process()
        for key, value in ctx_handler.get_global().items():
            setattr(g, key, value)
        ctx = ctx_handler.get_scope()
        ctx['META'] = ctx_handler.get_meta()
        ctx['__kwargs__'] = ctx_handler.get_uri_kwargs()
        if current_app.contact_uri == request.path:
            ctx['form'] = self.kwargs.get(
                'form', get_form_class(current_app)())
        return ctx

    def render(self):
        ctx = self.get_context()
        return render_template(self.get_template(), __scope__=ctx, **ctx)

    def get(self):
        return self.render()

    def post(self):
        if not current_app.config_parser.has_section('contact'):
            abort(405)
        if request.path != current_app.config_parser.get('contact', 'uri'):
            abort(405)
        form = get_form_class(current_app)(request.form)
        self.kwargs['form'] = form
        if form.validate():
            mess = get_message(form)
            mail.send(mess)
            flash_mess = current_app.config.get('mail', {}).get('FLASH')
            if flash_mess:
                flash(flash_mess)
        return self.render()


class JsonJinjaHtmlView(BaseView):
    ctx_handler_class = JsonContextHandler


class IniJinjaHtmlView(BaseView):
    ctx_handler_class = IniContextHandler
