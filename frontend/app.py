from flask import Flask, render_template
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html', current_date=datetime.now(timezone(timedelta(hours=-5), 'EST')).strftime("%H:%M:%S"))

if __name__ == '__main__':
    app.run(debug=True)