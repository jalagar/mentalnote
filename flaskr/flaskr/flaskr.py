# -*- coding: utf-8 -*-
"""
    Flaskr
    ~~~~~~

    A microblog example application written as Flask tutorial with
    Flask and sqlite3.

    :copyright: (c) 2015 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""


import os
import cPickle
from sqlite3 import dbapi2 as sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash, jsonify
from analyze import *

# create our little application :)
app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'flaskr.db'),
    DEBUG=True,
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('initdb')
def initdb_command():
    """Creates the database tables."""
    init_db()
    print('Initialized the database.')

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

@app.route('/')
def show_entries():
    return render_template('index.html')

@app.route('/add', methods=['POST'])
def add_entry():
    db = get_db()
    text = request.form['text']
    analysis = analyze(text)
    bytes = cPickle.dumps(analysis[1], 1)
    db.execute('insert into entries (text, time, tones) values (?, ?, ?)',
               [text, analysis[0], str(bytes)])
    db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('analyzeWeb'))

@app.route('/analyze', methods=['GET', 'POST'])
def analyzeWeb():
    db = get_db()
    db.text_factory = str
    cur = db.execute('select text, time, tones from entries order by id desc')
    entries = cur.fetchall()
    return render_template('analyze.html', entries=lineEmotionData(entries))

@app.route('/entry/<date>')
def show_entry(date):
    entry = query_db('select text, time, tones from entries where time = ?', [date], one=True)
    return render_template('entry.html', entry=all_time_tone_analysis([entry])[0])

def query_db(query, args=(), one=False):
    db = get_db()
    db.text_factory = str
    cur = db.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

@app.route('/aggregations', methods=['GET', 'POST'])
def aggregations():
    db = get_db()
    db.text_factory = str
    cur = db.execute('select text, time, tones from entries order by id desc')
    entries = cur.fetchall()
    return render_template('aggregations.html', entries=lineEmotionData(entries))

@app.route('/journal')
def print_entries():
    db = get_db()
    db.text_factory = str
    cur = db.execute('select text, time, tones from entries order by id desc')
    entries = cur.fetchall()
    data = retrieveEmotionData(entries)
    for time in data:
        emotions = data[time]["tones"]
        maxScore = 0
        mood = ""
        for emotionDict in emotions:
            if emotionDict["score"] >= maxScore:
                maxScore = emotionDict["score"]
                mood = emotionDict["tone_name"]
        data[time]["mood"] = mood
    return render_template('journal.html', entries=data)

# average over all emotions
@app.route('/getEmotionVals', methods=['GET'])
def getEmotionVals():
    db = get_db()
    db.text_factory = str
    cur = db.execute('select text, time, tones from entries order by id desc')
    entries = cur.fetchall()
    # query all emotion values
    data = retrieveEmotionData(entries)
    return json.dumps(averageEmotionValues(data))

@app.route('/getCurrentData', methods=['GET'])
def getCurrentData():
    db = get_db()
    db.text_factory = str
    cur = db.execute('select text, time, tones from entries order by id desc')
    entries = cur.fetchall()
    tones = cPickle.loads(str(entries[0][2]))
    currentTone = {}

    for tone in tones:
        if tone["tone_id"] == "anger":
            currentTone["Anger"] = tone["score"]
        if tone["tone_id"] == "disgust":
            currentTone["Disgust"] = tone["score"]
        if tone["tone_id"] == "fear":
            currentTone["Fear"] = tone["score"]
        if tone["tone_id"] == "joy":
            currentTone["Joy"] = tone["score"]
        if tone["tone_id"] == "sadness":
            currentTone["Sadness"] = tone["score"]
        # getDailyText(entries[0][0])
    return json.dumps({"text": entries[0][0], "tones": currentTone})

@app.route('/getLineVals', methods=['GET'])
def getLineVals():
    db = get_db()
    db.text_factory = str
    cur = db.execute('select text, time, tones from entries order by id desc')
    entries = cur.fetchall()
    # query all emotion values
    data = lineEmotionData(entries)
    return json.dumps(data)
