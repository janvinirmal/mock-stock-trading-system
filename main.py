from datetime import timedelta
from flask import session
from . import create_app

app = create_app()

if __name__== '__main__':
    app.run(debug=True)

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=5)