import click
from flask import Blueprint
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import session
from flask import url_for
from flask import current_app
from flask.cli import with_appcontext
from werkzeug.exceptions import abort

import random
from pathlib import Path
from collections import defaultdict

from paircomp.auth import login_required
from paircomp.db import get_db

bp = Blueprint("comparison", __name__)


def register_task(csv_path):
    tasks = [tuple(l.strip().split(','))
             for l in open(csv_path)]
    static_dir = Path(__file__).with_name('static')

    for paths in tasks:
        for path in paths:
            path = static_dir.joinpath(path)
            if not path.exists():
                raise RuntimeError(f'"{path}" is not found.')

    db = get_db()
    db.executemany(
        "INSERT INTO task (img_0, img_1) VALUES (?, ?)",
        tasks,
    )
    db.commit()

    return tasks


@click.command("register-task")
@click.argument('csv_path')
@with_appcontext
def register_task_command(csv_path):
    """Register tasks from csv file."""
    tasks = register_task(csv_path)
    click.echo(f"Registered {len(tasks)} tasks.")


@click.command("get-summary")
@with_appcontext
def get_summary_command():
    """Get summary csv file from the database."""
    db = get_db()
    id2task, id2votes = dict(), dict()
    for task in db.execute("SELECT * FROM task").fetchall():
        _id = task["id"]
        id2task[_id], id2votes[_id] = task, [0, 0]

    for vote in db.execute("SELECT * FROM vote").fetchall():
        id2votes[vote['task_id']][vote['selection']] += 1

    with Path('summary.csv').open('w') as f:
        for _id, task in id2task.items():
            img_0, img_1 = task['img_0'], task['img_1']
            vote_0, vote_1 = id2votes[_id]
            result = [img_0, str(vote_0), img_1, str(vote_1)]
            f.write(','.join(result) + '\n')

    click.echo("Saved voting results to summary.csv.")


@bp.route("/", methods=("GET", "POST"))
@login_required
def index():
    db = get_db()
    if request.method == "POST":
        vote = request.form["vote"]
        task = db.execute(
            "SELECT * FROM task WHERE id = ?", (session["task_id"],)
        ).fetchone()
        if task["img_0"] == vote:
            selection = 0
        elif task["img_1"] == vote:
            selection = 1
        else:
            raise RuntimeError
        db.execute(
            "INSERT INTO vote (task_id, user_id, selection) VALUES (?, ?, ?)",
            (task["id"], session["user_id"], selection),
        )
        db.commit()
        return redirect(url_for('index'))
    else:
        all_tasks = db.execute("SELECT * FROM task").fetchall()
        rows = db.execute(
            "SELECT * FROM vote WHERE user_id = ?", (session["user_id"],)
        ).fetchall()
        done = set([row['task_id'] for row in rows])

        imgs = []
        for row in all_tasks:
            _id = row["id"]
            if _id not in done:
                session["task_id"] = _id
                img_0, img_1 = row['img_0'], row['img_1']
                if random.random() < 0.5:
                    imgs = [img_0, img_1]
                else:
                    imgs = [img_1, img_0]
                break

        return render_template("comparison.html", imgs=imgs)
