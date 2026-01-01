import uuid
import datetime
from datetime import timedelta
from icalendar import Calendar, Event
from flask import Flask, render_template, request, jsonify, make_response

app = Flask(__name__, static_folder='static')

# Events stored server-side. Date format: YYYY-MM-DD
events = []


@app.route("/")
def main():
    return render_template("index.html", events=events)


def add(data):
    """Add a new event. Expects JSON: {"date": "YYYY-MM-DD", "title": "..."}
    Returns the updated events array as JSON.
    """
    if not data or 'date' not in data or 'title' not in data:
        return jsonify({'error': 'invalid payload'}), 400

    ev = {'date': data['date'], 'title': data['title']}
    events.append(ev)
    return jsonify(events)


def edit(data):
    """Edit an existing event. Expects JSON:
    { "old_date": "YYYY-MM-DD", "old_title": "...", "date": "YYYY-MM-DD", "title": "..." }
    Returns the updated events array as JSON.
    """
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

@app.route('/event', methods=['PUT'])
def event():
    data = request.get_json(silent=True)
    if 'old_title' in data:
        return edit(data)
    else:
        return add(data)

@app.route('/event', methods=['DELETE'])
def delete():
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


@app.route('/events', methods=['GET'])
def download():
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


@app.route('/events', methods=['PUT'])
def upload():
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
        # dtstart is required; summary is optional (use default title when absent)
        if not c.get('dtstart'):
            return jsonify({'error': 'missing dtstart in VEVENT', 'vevent': str(c)}), 400
        try:
            dtval = c.get('dtstart').dt
            if isinstance(dtval, datetime.datetime):
                dtval = dtval.date()
            _ = dtval.isoformat()
        except Exception as exc:
            return jsonify({'error': 'malformed date in uploaded ics', 'vevent': str(c), 'details': str(exc)}), 400

    # All validated — now import
    added = 0
    for component in vevents:
        summary = component.get('summary')
        dtval = component.get('dtstart').dt
        if isinstance(dtval, datetime.datetime):
            dtval = dtval.date()
        date_str = dtval.isoformat()
        title = str(summary) if summary is not None else '(no title)'
        exists = any(e.get('date') == date_str and e.get('title') == title for e in events)
        if not exists:
            events.append({'date': date_str, 'title': title, 'uid': str(component.get('uid') or uuid.uuid4().hex)})
            added += 1

    return jsonify(events)
