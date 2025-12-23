import os
import hashlib
import io
import uuid
import datetime
from datetime import timedelta
from icalendar import Calendar, Event
from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for, send_from_directory

app = Flask(__name__, static_folder=None)

# Secret key for session.
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24).hex()

# Password handling: always use SHA1. Provide the SHA1 hex via
# `AUTH_PASSWORD_SHA1`. If not set, default to SHA1('password').
AUTH_PASSWORD_HASH = os.environ.get('AUTH_PASSWORD_SHA1')
if not AUTH_PASSWORD_HASH:
    AUTH_PASSWORD_HASH = hashlib.sha1('saladus'.encode('utf-8')).hexdigest()

# Events stored server-side. Date format: YYYY-MM-DD
events = []


@app.route("/")
def main():
    return render_template("index.html", events=events)


@app.before_request
def require_login():
    # Allow access to the login page and static asset serving route
    allowed_endpoints = ('login', 'static')
    if request.endpoint in allowed_endpoints:
        return
    if not session.get('logged_in'):
        return redirect(url_for('login', next=request.path))


@app.route('/login', methods=['GET', 'POST'])
def login():
    next_url = request.args.get('next') or url_for('main')
    error = None
    if request.method == 'POST':
        password = request.form.get('password', '')
        hashed = hashlib.sha1(password.encode('utf-8')).hexdigest()
        if hashed == AUTH_PASSWORD_HASH:
            session['logged_in'] = True
            return redirect(next_url)
        error = 'Invalid password'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# Serve static files through a guarded route so everything is protected
@app.route('/static/<path:filename>')
def static(filename):
    return send_from_directory('static', filename)


@app.route('/add-event', methods=['POST'])
def add_event():
    """Add a new event. Expects JSON: {"date": "YYYY-MM-DD", "title": "..."}
    Returns the updated events array as JSON.
    """
    data = request.get_json(silent=True)
    if not data or 'date' not in data or 'title' not in data:
        return jsonify({'error': 'invalid payload'}), 400

    ev = {'date': data['date'], 'title': data['title']}
    events.append(ev)
    return jsonify(events)


@app.route('/delete-event', methods=['POST'])
def delete_event():
    """Delete an event. Expects JSON: {"date": "YYYY-MM-DD", "title": "..."}
    Returns the updated events array as JSON.
    """
    data = request.get_json(silent=True)
    if not data or 'date' not in data or 'title' not in data:
        return jsonify({'error': 'invalid payload'}), 400

    for i, ev in enumerate(events):
        if ev.get('date') == data['date'] and ev.get('title') == data['title']:
            events.pop(i)
            return jsonify(events)

    return jsonify({'error': 'not found'}), 404


@app.route('/edit-event', methods=['POST'])
def edit_event():
    """Edit an existing event. Expects JSON:
    { "old_date": "YYYY-MM-DD", "old_title": "...", "date": "YYYY-MM-DD", "title": "..." }
    Returns the updated events array as JSON.
    """
    data = request.get_json(silent=True)
    if not data or 'old_date' not in data or 'old_title' not in data or 'date' not in data or 'title' not in data:
        return jsonify({'error': 'invalid payload'}), 400

    old_date = data['old_date']
    old_title = data['old_title']
    for ev in events:
        if ev.get('date') == old_date and ev.get('title') == old_title:
            ev['date'] = data['date']
            ev['title'] = data['title']
            return jsonify(events)

    return jsonify({'error': 'not found'}), 404


@app.route('/download-events', methods=['GET'])
def download_events():
    """Download all events as an iCalendar (.ics) file.

    Events are exported as all-day VEVENTs using the stored YYYY-MM-DD date.
    """
    cal = Calendar()
    cal.add('prodid', '-//codespaces-flask//EN')
    cal.add('version', '2.0')

    for ev in events:
        # Validate date format for each event; return error on first malformed date
        date_str = ev.get('date')
        try:
            dt = datetime.date.fromisoformat(date_str)
        except Exception:
            return jsonify({'error': 'malformed date in stored events', 'event': ev}), 400
        ical_ev = Event()
        ical_ev.add('summary', ev.get('title', ''))
        # All-day event: use DATE value
        ical_ev.add('dtstart', dt)
        # DTEND for all-day events is non-inclusive: set to next day
        ical_ev.add('dtend', dt + timedelta(days=1))
        ical_ev.add('uid', ev.get('uid') or uuid.uuid4().hex)
        cal.add_component(ical_ev)

    ics_bytes = cal.to_ical()
    resp = make_response(ics_bytes)
    resp.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    resp.headers['Content-Disposition'] = 'attachment; filename=events.ics'
    return resp


@app.route('/upload-events', methods=['POST'])
def upload_events():
    """Accept an uploaded .ics file and import VEVENTs into the server-side events list.

    Expects a file field named 'file'. Returns the updated events array as JSON.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'no file provided'}), 400
    f = request.files['file']
    data = f.read()
    try:
        cal = Calendar.from_ical(data)
    except Exception:
        return jsonify({'error': 'invalid ics file'}), 400

    # Validate all VEVENTs first: ensure dtstart and summary present and dates parseable
    vevents = [c for c in cal.walk() if c.name == 'VEVENT']
    for c in vevents:
        if not c.get('summary') or not c.get('dtstart'):
            return jsonify({'error': 'missing summary or dtstart in VEVENT', 'vevent': str(c)}), 400
        try:
            dtval = c.get('dtstart').dt
            if isinstance(dtval, datetime.datetime):
                dtval = dtval.date()
            _ = dtval.isoformat()
        except Exception:
            return jsonify({'error': 'malformed date in uploaded ics', 'vevent': str(c)}), 400

    # All validated — now import
    added = 0
    for component in vevents:
        summary = component.get('summary')
        dtval = component.get('dtstart').dt
        if isinstance(dtval, datetime.datetime):
            dtval = dtval.date()
        date_str = dtval.isoformat()
        title = str(summary)
        exists = any(e.get('date') == date_str and e.get('title') == title for e in events)
        if not exists:
            events.append({'date': date_str, 'title': title, 'uid': str(component.get('uid') or uuid.uuid4().hex)})
            added += 1

    return jsonify(events)
