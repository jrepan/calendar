import uuid
import datetime
from datetime import timedelta
from icalendar import Calendar, Event
from flask import Flask, render_template, request, jsonify, make_response
import db

app = Flask(__name__, static_folder='static')
db.init_db()

@app.route("/")
def main():
    return render_template("index.html", events=db.fetch_events())

@app.route('/event', methods=['PUT'])
def event():
    data = request.get_json(silent=True)
    if not data or 'date' not in data or 'title' not in data:
        return jsonify({'error': 'invalid payload'}), 400
    date = data['date']
    title = data['title']
    uid = data['uid'] or uuid.uuid4().hex
    db.update_event(uid, date, title)
    return jsonify(db.fetch_events())

@app.route('/event', methods=['DELETE'])
def delete():
    data = request.get_json(silent=True)
    if not data or 'uid' not in data:
        return jsonify({'error': 'invalid payload'}), 400
    success = db.delete_event(data['uid'])
    if not success:
        return jsonify({'error': 'not found'}), 404
    return jsonify(db.fetch_events())

@app.route('/events', methods=['GET'])
def download():
    cal = Calendar()
    cal.add('prodid', '-//codespaces-flask//EN')
    cal.add('version', '2.0')

    for ev in db.fetch_events():
        date_str = ev.get('date')
        try:
            dt = datetime.date.fromisoformat(date_str)
        except Exception:
            return jsonify({'error': 'malformed date in stored events', 'event': ev}), 400
        ical_ev = Event()
        ical_ev.add('summary', ev.get('title', ''))
        ical_ev.add('dtstart', dt)
        # DTEND for all-day events is non-inclusive: set to next day
        ical_ev.add('dtend', dt + timedelta(days=1))
        ical_ev.add('uid', ev.get('uid'))
        cal.add_component(ical_ev)

    ics_bytes = cal.to_ical()
    resp = make_response(ics_bytes)
    resp.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    resp.headers['Content-Disposition'] = 'attachment; filename=events.ics'
    return resp


@app.route('/events', methods=['PUT'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'no file provided'}), 400
    f = request.files['file']
    data = f.read()
    try:
        cal = Calendar.from_ical(data)
    except Exception:
        return jsonify({'error': 'invalid ics file'}), 400

    # Validate everything first
    vevents = [c for c in cal.walk() if c.name == 'VEVENT']
    for c in vevents:
        if not c.get('dtstart'):
            return jsonify({'error': 'missing dtstart in VEVENT', 'vevent': str(c)}), 400
        try:
            dtval = c.get('dtstart').dt
            if isinstance(dtval, datetime.datetime):
                dtval = dtval.date()
        except Exception as exc:
            return jsonify({'error': 'malformed date in uploaded ics', 'vevent': str(c), 'details': str(exc)}), 400

    # All validated, now import
    events = []
    for component in vevents:
        uid = component.get('uid') or uuid.uuid4().hex
        summary = component.get('summary')
        title = str(summary) if summary is not None else '(no title)'
        dtval = component.get('dtstart').dt
        if isinstance(dtval, datetime.datetime):
            dtval = dtval.date()
        date_str = dtval.isoformat()
        if not db.event_exists(uid):
            events.append({'uid': uid, 'date': date_str, 'title': title})
    db.insert_events(events)
    return jsonify(db.fetch_events())
