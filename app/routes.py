import os
from datetime import datetime
from flask import render_template, flash, redirect, url_for, send_from_directory, request
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
from flask_login import current_user, login_user, logout_user, login_required

from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, UploadForm, ApprovalForm, AvatarForm
from app.models import User, Post, Video
from app.email import send_password_reset_email, send_registration_email, send_approval_email, indev_registration_email, indev_approval_email


def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['VIDEO_EXTENSIONS']


def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['IMAGE_EXTENSIONS']

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()

        flash("Post successful.")
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) if posts.has_prev else None

    return render_template('index.html',  title='Ryse Tor', form=form, posts=posts.items, next_url=next_url, prev_url=prev_url)


@app.route('/eyewitness', methods=['GET', 'POST'])
@login_required
def eyewitness():
    form = UploadForm()

    if form.validate_on_submit():

        f = form.upload.data
        if not allowed_video_file(f.filename):
            flash("Invalid file type")
            return redirect(url_for('eyewitness'))

        filename = secure_filename(f.filename)
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], 'video', filename))

        video = Video(title=form.title.data, description=form.description.data, filename=filename, author=current_user)
        db.session.add(video)
        db.session.commit()
        flash("Video successfully uploaded.")
        return redirect(url_for('eyewitness'))

    page = request.args.get('page', 1, type=int)
    videos = current_user.followed_videos().paginate(
        page, app.config['VIDEOS_PER_PAGE'], False)

    next_url = url_for('eyewitness', page=videos.next_num) if videos.has_next else None
    prev_url = url_for('eyewitness', page=videos.prev_num) if videos.has_prev else None

    return render_template('eyewitness.html', title="The Frontlines", form=form, videos=videos.items, next_url=next_url, prev_url=prev_url)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash("Already logged in.")
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for('login'))
        if not user.verify_token(form.token.data):
            flash("Could not authenticated using provided token.")
            return redirect(url_for('login'))
            
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')

        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')

        return redirect(next_page)

    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    flash("You are no longer logged in.")
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        flash("Already logged in")
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)

        user.generate_token()

        db.session.add(user)
        db.session.commit()
        #send_registration_email(user, form.note_to_admin.data)
        indev_registration_email(user, form.note_to_admin.data)
        
        app.logger.info('New Registrant: {}'.format(user.email))
        app.logger.info("Registrant token: {}".format(user.auth_token))
        flash("Success. CHeck your email for further instructions.")
        return redirect(url_for("login"))

    return render_template('register.html', title='Register', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()

    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(page, app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('user', username=username, page=posts.next_num) if posts.has_next else None
    prev_url = url_for('user', username=username, page=posts.prev_num) if posts.has_prev else None

    return render_template('user.html', user=user, posts=posts.items, next_url=next_url, prev_url=prev_url)


@app.route('/user/<username>/videos')
@login_required
def videos(username):
    user = User.query.filter_by(username=username).first_or_404()

    page = request.args.get('page', 1, type=int)
    videos = user.videos.order_by(Video.timestamp.desc()).paginate(page, app.config['VIDEOS_PER_PAGE'], False)

    next_url = url_for('videos', username=username, page=videos.next_num) if videos.has_next else None

    prev_url = url_for('videos', username=username, page=videos.prev_num) if videos.has_prev else None

    return render_template('videos.html', user=user, videos=videos.items, next_url=next_url, prev_url=prev_url)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data

        db.session.commit()
        flash("Your changes have been saved.")
        return redirect(url_for('edit_profile'))

    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me

    return render_template('edit_profile.html', title="Edit Profile", form=form)


@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()

    if user is None:
        flash("User {} not found.".format(username))
        return redirect(url_for('index'))

    if user == current_user:
        flash("You cannot follow yourself.")
        return redirect(url_for('user', username=username))

    current_user.follow(user)
    db.session.commit()
    flash("You are now following {}".format(username))
    return redirect(url_for('user', username=username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()

    if user is None:
        flash("User {} not found".format(username))
        return redirect(url_for('index'))

    if user == current_user:
        flash("You cannot unfollow yourself.")
        return redirect(url_for('user', username=username))


    current_user.unfollow(user)
    db.session.commit()

    flash('You are no longer following {}'.format(username))
    return redirect(url_for('user', username=username))


@app.route('/watch/<title>')
@login_required
def watch(title):
    video = Video.query.filter_by(title=title).first_or_404()
    if current_user != video.author:
        video.views += 1
        db.session.commit()

    return send_from_direectory(os.path.join(app.config['UPLOAD_FOLDER'], 'video'), video.filename)


@app.route('/delete_video/<title>')
@login_required
def delete_video(title):
    video = Video.query.filter_by(title=title).first()

    if video is None:
        flash("Video {} does not exist".format(title))
        return redirect(url_for('index'))

    if current_user != video.author:
        flash("you cannot delete another user's video")
        return redirect(url_for('index'))

    db.session.delete(video)
    db.session.commit()
    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'video', video.filename))

    flash('Video successfully deleted')
    return redirect(url_for('videos', username=current_user.username))


@app.route('/send_token/<username>', methods=['GET', 'POST'])
@login_required
def send_token(username):
    user = User.query.filter_by(username=username).first_or_404()

    form = ApprovalForm()

    if form.validate_on_submit():

        if form.admin_key.data != app.config['ADMIN_KEY']:
            flash("Invalid Admin Key")
            return redirect(url_for('send_token', username=username))

        if user.approved:
            flash("User already approved.")
            return redirect(url_for('index'))

        #send_approval_email(user=user, message=form.message.data, admin=form.admin.data)
        indev_approval_email(user=user, message=form.message.data, admin=form.admin.data)
        user.approved = True
        db.session.commit()
        flash("User approved for registration.")
        return redirect(url_for('index'))

    return render_template('send_token.html', title="Admin Approval", form=form, user=user)


@app.route('/user/<username>/avatar')
@login_required
def avatar(username):
    user = User.query.filter_by(username=username).first_or_404()

    filename = user.avatar
    if filename is None:
        filename = 'placeholder.jpg'

    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'image'), filename)


@app.route('/upload/avatar', methods=['GET', 'POST'])
@login_required
def upload_avatar():

    form = AvatarForm()

    if form.validate_on_submit():
        f = form.upload.data

        if not allowed_image_file(f.filename):
            flash("Invalid file type")
            return redirect(url_for('upload_avatar'))

        filename = secure_filename(f.filename)
        f.save(os.path.join(app.config['UPLOAD_FOLDER'], 'image', filename))

        current_user.avatar = filename
        db.session.commit()

        flash('Avatar successfully uploaded.')
        return redirect(url_for('user', username=current_user.username))

    return render_template('upload_avatar.html', title='Avatar Upload', form=form)
