from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import requests
import os
from flask_login import LoginManager, login_user, logout_user, current_user, UserMixin
from authlib.integrations.flask_client import OAuth

from flask_sqlalchemy import SQLAlchemy
API_TOKEN = os.environ.get('API_TOKEN')
app = Flask(__name__)
app.secret_key = 'random_secret_key'
app.config['SECRET_KEY'] = 'some_random_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
oauth = OAuth(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    models = db.relationship('ModelInfo', backref='owner', lazy=True)

class ModelInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    url = db.Column(db.String(200), nullable=False)
    api_token = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

google = oauth.register(
    name='google',
    client_id='191880688169-evnduajbagpfenab8nqusi75d3l5bkm7.apps.googleusercontent.com',
    client_secret='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',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    refresh_token_url=None,
    redirect_to='login_callback',
    client_kwargs={'scope': 'profile email'},
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
    
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login')
def login():
    redirect_uri = url_for('login_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/login/callback')
def login_callback():
    token = google.authorize_access_token()
    resp = google.get('https://www.googleapis.com/oauth2/v2/userinfo')
    user_info = resp.json()
    # Check if user exists
    user = User.query.filter_by(google_id=user_info['id']).first()
    
    # If user does not exist, create a new user
    if not user:
        user = User(google_id=user_info['id'], name=user_info['name'], email=user_info['email'])
        db.session.add(user)
        db.session.commit()
        print('added', user)
    
    # Log the user in
    login_user(user)
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/', methods=['GET', 'POST'])
def home():
    if current_user.is_authenticated:
        user_models = ModelInfo.query.filter_by(user_id=current_user.id).all()
    else:
        user_models = []
    user_input = ""
    responses = {}

    if request.method == 'POST':
        user_input = request.form.get('prompt')
        image = request.files.get('image')

        for model in user_models:
            if user_input:  # If user entered text
                responses[model.name] = query_model(user_input, model.url, model.api_token)
            elif image:  # If user uploaded an image
                # Save the uploaded image temporarily
                filename = os.path.join("temp", image.filename)
                image.save(filename)

                # Use the image to get response
                responses[model.name] = query_vision_model(filename, model.url, model.api_token)
                print(responses[model.name])
                # Optionally, remove the saved image if no longer needed
                os.remove(filename)

    return render_template('index.html', models=user_models, model_responses=responses , user_input=user_input)


def query_vision_model(filename, api_url, api_token):
    headers = {"Authorization": f"Bearer {api_token}"}
    with open(filename, "rb") as f:
        data = f.read()
    try:
        response_data = requests.post(api_url, headers=headers, data=data)
        response_data.raise_for_status()  # Raise an error for HTTP errors
        res = response_data.json()  # Modify this as per the actual response structure
    except requests.RequestException:
        res = "Error retrieving response from this model."
    return res

def query_model(prompt, api_url, api_token):
    headers = {"Authorization": f"Bearer {api_token}"}
    payload = {"inputs": prompt}
    try:
        response_data = requests.post(api_url, headers=headers, json=payload)
        response_data.raise_for_status()  # Raise an error for HTTP errors
        res = response_data.json()[0]['generated_text']
    except requests.RequestException:
        res = "Error retrieving response from this model."
    return res
            

@app.route('/edit_model/<int:model_id>', methods=['GET', 'POST'])
def edit_model(model_id):
    model = ModelInfo.query.get_or_404(model_id)
    
    if request.method == 'POST':
        model.name = request.form.get('name')
        model.url = request.form.get('url')
        model.api_token = request.form.get('api_token')
        db.session.commit()
        return redirect(url_for('home'))

    return render_template('model_form.html', model=model)


@app.route('/add_model', methods=['POST'])
def add_model():
    data = request.json
    new_model = ModelInfo(name=data['name'], url=data['url'], api_token=data['api_token'], user_id=current_user.id)
    db.session.add(new_model)
    db.session.commit()
    return jsonify({'message': 'Model added successfully!'}), 201

@app.route('/delete_model/<int:model_id>', methods=['DELETE'])
def delete_model(model_id):
    model = ModelInfo.query.get_or_404(model_id)
    db.session.delete(model)
    db.session.commit()
    return jsonify({'message': 'Model deleted successfully!'}), 200


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)

