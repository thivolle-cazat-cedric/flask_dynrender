from flask_wtf import FlaskForm, RecaptchaField
from wtforms import StringField, TextAreaField, ValidationError
from wtforms.fields.html5 import EmailField
from wtforms.validators import DataRequired, Length
from validate_email import validate_email


class ContactBaseForm(FlaskForm):
    firstname = StringField('firstname', validators=[
        DataRequired(message="Obligatoir"),
        Length(min=1, message="Doit contenir au moins %(min)s caractère")])
    lastname = StringField('lastname', validators=[
        DataRequired(message="Obligatoir"),
        Length(min=1, message="Doit contenir au moins %(min)s caractère")])
    email = EmailField('email', validators=[
        DataRequired(message="Obligatoir")])
    message = TextAreaField('message', validators=[
        DataRequired(message="Obligatoir"),
        Length(min=3, message="Doit contenir au moins %(min)s caractères")])
    # recaptcha = RecaptchaField('recaptcha')

    def validate_email(self, field):
        if not validate_email(field.data):
            raise ValidationError('Adresse email invalide')


def get_form_class(app):
    return ContactBaseForm
