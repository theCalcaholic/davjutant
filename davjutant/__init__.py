import os
from flask import Flask
from .routes import update_calendars, bp as routes_bp


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        CALDAV_URL=os.environ.get('CALDAV_URL', None),
        CALDAV_USER=os.environ.get('CALDAV_USER', None),
        CALDAV_PASSWORD=os.environ.get('CALDAV_PASSWORD', None),
        PORT=int(os.environ.get('PORT', '80')),
        ADDRESS=os.environ.get('ADDRESS', '0.0.0.0'),
        WEBHOOKS_SECRET=os.environ.get('WEBHOOKS_SECRET', None),
        VERBOSE=os.environ.get('DEBUG', 'false') == 'true')

    app.debug = app.config.get('VERBOSE')

    if test_config is None:
        app.config.from_pyfile('/etc/davjutant/config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    app.register_blueprint(routes_bp)

    return app


if __name__ == "__main__":
    app = create_app()

    app.run(host=app.config.get('ADDRESS'),
            port=app.config.get('PORT'),
            debug=app.config.get('VERBOSE'))
