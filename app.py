import os
import hashlib
from flask import Flask, render_template, request, jsonify, make_response, session, redirect, url_for, send_from_directory

app = Flask(__name__, static_folder=None)

# Secret key for session. Override with SECRET_KEY env var in production.
# If not provided, generate a random ephemeral key on startup.
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24).hex()

# Password handling: always use SHA1. Provide the SHA1 hex via
# `AUTH_PASSWORD_SHA1`. If not set, default to SHA1('password').
AUTH_PASSWORD_HASH = os.environ.get('AUTH_PASSWORD_SHA1')
if not AUTH_PASSWORD_HASH:
    AUTH_PASSWORD_HASH = hashlib.sha1('password'.encode('utf-8')).hexdigest()

# Sample events stored server-side. Date format: YYYY-MM-DD
sample_events = []


@app.route("/")
def hello_world():
    return render_template("index.html", events=sample_events)


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
    next_url = request.args.get('next') or url_for('hello_world')
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
    sample_events.append(ev)
    return jsonify(sample_events)


@app.route('/delete-event', methods=['POST'])
def delete_event():
    """Delete an event. Expects JSON: {"date": "YYYY-MM-DD", "title": "..."}
    Returns the updated events array as JSON.
    """
    data = request.get_json(silent=True)
    if not data or 'date' not in data or 'title' not in data:
        return jsonify({'error': 'invalid payload'}), 400

    for i, ev in enumerate(sample_events):
        if ev.get('date') == data['date'] and ev.get('title') == data['title']:
            sample_events.pop(i)
            return jsonify(sample_events)

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
    for ev in sample_events:
        if ev.get('date') == old_date and ev.get('title') == old_title:
            ev['date'] = data['date']
            ev['title'] = data['title']
            return jsonify(sample_events)

    return jsonify({'error': 'not found'}), 404


@app.route('/download-events', methods=['GET'])
def download_events():
    """Download all events in JSON."""
    resp = make_response(jsonify(sample_events))
    resp.headers['Content-Disposition'] = 'attachment; filename=events.json'
    return resp
