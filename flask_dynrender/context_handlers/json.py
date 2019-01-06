import json
from flask import current_app
from .base import BaseContextHandler


class JsonContextHandler(BaseContextHandler):

    extension = 'json'

    def get_root_path(self):
        return current_app.config.get('JSON_DATA_DIR', super().get_root_path())

    def get_data(self, target):
        return json.load(open(target))
