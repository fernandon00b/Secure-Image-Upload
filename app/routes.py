import os
import secrets
from flask import render_template, url_for, flash, redirect, request, abort
from app import app, db, bcrypt
from app.forms import RegistrationForm, LoginForm, UploadForm
from app.models import User, Image as ImageModel
from flask_login import login_user, current_user, logout_user, login_required
from PIL import Image
import base64
from werkzeug.utils import secure_filename

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = secure_filename(random_hex + f_ext)
    picture_path = os.path.join(app.config['UPLOAD_FOLDER'], picture_fn)
    
    # Save the picture
    form_picture.save(picture_path)

    return picture_fn

def get_image_base64(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash('Your account has been created! You are now logged in.', 'success')
        return redirect(url_for('account'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('account'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('account'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    logout_user()
    flash('You have been logged out!', 'success')
    return redirect(url_for('home'))

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UploadForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            image = ImageModel(image_file=picture_file, owner=current_user)
            db.session.add(image)
            db.session.commit()
            flash('Your image has been uploaded!', 'success')
    images = ImageModel.query.filter_by(owner=current_user).all()
    images_base64 = [
        {
            'id': image.id,
            'base64': get_image_base64(os.path.join(app.config['UPLOAD_FOLDER'], image.image_file))
        }
        for image in images
    ]
    return render_template('account.html', title='Account', form=form, images=images_base64)

@app.route("/image/<int:image_id>")
@login_required
def image(image_id):
    image = ImageModel.query.get_or_404(image_id)
    if image.owner != current_user:
        abort(403)
    
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.image_file)
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    return render_template('image.html', image_base64=encoded_string)

@app.route("/image/<int:image_id>/delete", methods=['POST'])
@login_required
def delete_image(image_id):
    image = ImageModel.query.get_or_404(image_id)
    if image.owner != current_user:
        abort(403)
    
    # Delete the image file from the local storage
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.image_file)
    if os.path.exists(image_path):
        os.remove(image_path)
    
    db.session.delete(image)
    db.session.commit()
    flash('Your image has been deleted!', 'success')
    return redirect(url_for('account'))
