import os

from flask import Flask


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        SECRET_KEY="dev",
        # store the database in the instance folder
        DATABASE=os.path.join(app.instance_path, "paircomp.sqlite"),
    )

    # load the instance config, if it exists
    app.config.from_pyfile("config.py", silent=True)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # register the database commands
    from paircomp import db
    from paircomp import comparison

    db.init_app(app)
    app.cli.add_command(comparison.register_task_command)
    app.cli.add_command(comparison.get_summary_command)

    # apply the blueprints to the app
    from paircomp import auth, comparison

    app.register_blueprint(auth.bp)
    app.register_blueprint(comparison.bp)

    # make url_for('index') == url_for('blog.index')
    # in another app, you might define a separate main index here with
    # app.route, while giving the blog blueprint a url_prefix, but for
    # the tutorial the blog will be the main index
    app.add_url_rule("/", endpoint="index")

    return app
