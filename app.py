import os
import platform
import secrets
import subprocess
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///reminders.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    remind_time = db.Column(db.DateTime, nullable=False)
    triggered = db.Column(db.Boolean, default=False)


def desktop_alert(title, msg):
    os_name = platform.system()
    if os_name == "Windows":
        escaped_title = title.replace("'", "''")
        escaped_msg = msg.replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "Add-Type -AssemblyName System.Drawing; "
            "$notification = New-Object System.Windows.Forms.NotifyIcon; "
            "$notification.Icon = [System.Drawing.SystemIcons]::Information; "
            "$notification.Visible = $true; "
            f"$notification.BalloonTipTitle = '{escaped_title}'; "
            f"$notification.BalloonTipText = '{escaped_msg}'; "
            "$notification.ShowBalloonTip(8000); "
            "for ($i = 0; $i -lt 90; $i++) { "
            "[System.Windows.Forms.Application]::DoEvents(); "
            "Start-Sleep -Milliseconds 100 }; "
            "$notification.Dispose()"
        )
        subprocess.run(
            ["powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    elif os_name == "Darwin":
        escaped_msg = msg.replace("\\", "\\\\").replace('"', '\\"')
        escaped_title = title.replace("\\", "\\\\").replace('"', '\\"')
        subprocess.run(
            [
                "osascript",
                "-e",
                f'display notification "{escaped_msg}" with title "{escaped_title}"',
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    elif os_name == "Linux":
        subprocess.run(
            ["notify-send", title, msg],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    else:
        raise RuntimeError(f"Desktop notifications are not supported on {os_name}.")


def check_reminders():
    with app.app_context():
        now = datetime.now()
        due_reminders = Reminder.query.filter(
            Reminder.remind_time <= now,
            Reminder.triggered.is_(False),
        ).all()
        for reminder in due_reminders:
            try:
                desktop_alert(
                    reminder.title,
                    reminder.description or "Your reminder is due.",
                )
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                app.logger.exception(
                    "Could not notify for reminder %s: %s", reminder.id, error
                )
                continue
            reminder.triggered = True
        db.session.commit()


scheduler = BackgroundScheduler()
scheduler.add_job(check_reminders, "interval", seconds=30)
scheduler.start()


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("desc", "").strip()
        time_str = request.form.get("remind_time", "")

        if not title:
            flash("Add a title for your reminder.", "error")
        elif len(title) > 100:
            flash("Keep the title to 100 characters or fewer.", "error")
        elif len(description) > 200:
            flash("Keep the description to 200 characters or fewer.", "error")
        else:
            try:
                remind_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
            except ValueError:
                flash("Choose a valid date and time for your reminder.", "error")
            else:
                reminder = Reminder(
                    title=title,
                    description=description,
                    remind_time=remind_time,
                )
                db.session.add(reminder)
                db.session.commit()
                flash("Your reminder is all set.", "success")
                return redirect(url_for("home"))

    pending = Reminder.query.filter(Reminder.triggered.is_(False)).order_by(
        Reminder.remind_time
    ).all()
    completed = Reminder.query.filter(Reminder.triggered.is_(True)).order_by(
        Reminder.remind_time.desc()
    ).all()
    return render_template("index.html", pending=pending, completed=completed)


@app.post("/delete/<int:rid>")
def delete(rid):
    reminder = db.get_or_404(Reminder, rid)
    db.session.delete(reminder)
    db.session.commit()
    flash("Reminder deleted.", "success")
    return redirect(url_for("home"))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=False, host=os.environ.get("HOST", "0.0.0.0"), port=5001)
