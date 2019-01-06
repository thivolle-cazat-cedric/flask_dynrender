from collections import defaultdict
from flask import current_app, render_template
from flask_mail import Message
from .exceptions import ConfigrationMailError

TPL_TXT = '''Prénom: {{form.firstname}}\n\r
Nom: {{form.lastname}}\n\r
email: {{form.email}}\n\r
-- message --
{{form[message]}}\n\r'''

TPL_HTML = '''<table>
    <tr>
        <th>Prénom</th><td>{{form.firstname}}</td>
    </tr>
    <tr>
        <th>Nom</th><td>{{form.lastname}}</td>
    </tr>
    <tr>
        <th>email</th><td>{{form.email}}</td>
    </tr>
    <tr><th colspan="2">message</th></tr>
    <tr><td collspan="2">{{form.message}}</td></tr>
</table>'''


def check_mail_conf(mail_conf):
    src = mail_conf.get('FROM', '').strip()
    dst = mail_conf.get('TO','').strip()
    subject = mail_conf.get(
        'SUBJECT', 'Nouveau message de {form[email]}').strip()
    if not src or '@' not in src:
        raise ConfigrationMailError('mail.from: invalide value "%s"' % src)
    dst = [d.strip() for d in dst.split(',') if d.strip()]
    if not dst:
        raise ConfigrationMailError('mail.to: invalide value "%s"' % dst)
    mail_conf.update({
        'FROM': src,
        'TO': dst,
        'SUBJECT': subject,
        'HTML_TPL': mail_conf.get('HTML_TPL', '').strip(),
        'TXT_TPL': mail_conf.get('TXT_TPL', '').strip()
    })
    return mail_conf


def get_message(form):
    values = defaultdict(str)
    values.update({f.name: f.data for f in form})
    mail = current_app.config.get('MAIL', {})
    if not mail:
        raise ValueError('Configuration MAIL is empty')
    msg = Message(
        mail['SUBJECT'].format(form=values),
        sender=mail['FROM'], recipients=mail['TO'])

    txt = current_app.jinja_env.from_string(TPL_TXT)
    html = current_app.jinja_env.from_string(TPL_HTML)
    if mail.get('HTML_TPL'):
        try:
            html = current_app.jinja_env.get_template(mail['HTML_TPL'])
        except Exception as e:
            current_app.logger.error(
                'html mail template not found "%s"' % mail['HTML_TPL'],
                exc_info=e)
    if mail.get('TXT_TPL'):
        try:
            txt = current_app.jinja_env.get_template(mail['TXT_TPL'])
        except Exception as e:
            current_app.logger.error(
                'text mail template not found "%s"' % mail['TXT_TPL'],
                exc_info=e)
    ctx = {'form': values}
    msg.body = render_template(txt, **ctx)
    msg.html = render_template(html, **ctx)
    return msg
