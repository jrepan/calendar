from flask import Flask, render_template, request, jsonify, make_response

app = Flask(__name__)

# Sample events stored server-side. Date format: YYYY-MM-DD
sample_events = []


@app.route("/")
def hello_world():
    return render_template("index.html", events=sample_events)


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
