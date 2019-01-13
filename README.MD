# Flask DynRender

project is in developpement mode.

This project is a simple but flexible to render website via [Flask](http://flask.pocoo.org).

website build from templates directory architecture, and the context temapte depend to folder data architecture.

# Install

## From source
``` sh
git clone https://github.com/thivolle-cazat-cedric/flask_dynrender.git
cd flask_dynrender
python3 -m venv .env
source .env/bin/activate
python setup.py develop
# i'm waiting a pull reqeust. or if it refused, i create custom widget
pip install -U --force-reinstall git+https://github.com/thivolle-cazat-cedric/flask-wtf.git@tc-htmlattrs
cd samples
export FLASK_APP=flask_dynrender:create_app
export FLASK_DYNRENDER=sample-cfg.ini
export FLASK_DEBUG=1
flask run
```

# TODO
 - [ ] Documentations
 - [ ] Packaging
 - [ ] Exemples
 - [ ] Test
