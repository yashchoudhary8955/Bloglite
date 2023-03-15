from flask import Flask
from flask import render_template
from flask import request
from flask import Flask,render_template,request,redirect,url_for,session
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager,login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
import matplotlib.pyplot as plt
import pandas as pd
from datetime import date
from flask import flash
import os
import base64
from wtforms.validators import DataRequired
from wtforms import HiddenField





app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite3'
app.config['SECRET_KEY'] = 'thisisasecretkey'

db = SQLAlchemy()
bcrypt = Bcrypt(app)
db.init_app(app)
app.app_context().push()

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    name = db.Column(db.String, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(120))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    likes = db.relationship('Like', backref='post', lazy='dynamic')
    comments = db.relationship('Comment', backref='post', lazy='dynamic')

    def __repr__(self):
        return '<Post {}>'.format(self.title)
    

    
followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement = True)
    username = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    is_active = db.Column(db.Boolean, default=True)
    
    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')
    

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0
    
    def get_id(self):
        return self.id

    def is_authenticated(self):
        return True

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(140))
    #timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))



# Create the likes table
class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


def user(username):
   user = User.query.filter_by(username=username).first()


class RegisterForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=3, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Register')

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError(
                'That username already exists. Please choose a different one.')


class LoginForm(FlaskForm):
    username = StringField(validators=[
                           InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})

    password = PasswordField(validators=[
                             InputRequired(), Length(min=3, max=20)], render_kw={"placeholder": "Password"})

    submit = SubmitField('Login')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                is_active = True
                #return redirect(url_for('main.html'))
                return render_template('main.html',user=user)
                
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def name():
    user = current_user
    return user

uname = name()
print(uname)

@ app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('signup.html', form=form)


@app.route('/profile')
def profile():
    username = current_user.username
    user = User.query.filter_by(username=username).first()
    followers = user.followers.count()
    followed = user.followed.count()
    posts = user.posts.count()
    return render_template('profile.html',username=username, user=user, followers=followers, followed=followed, posts=posts)


@app.route("/index")
def index():
    return render_template("index.html")

@app.route("/indexu")
def indexu():
    return render_template("indexu.html")

@app.route("/main")
def main():
    return render_template("main.html",user=user)



@app.route('/AddPost', methods=['GET', 'POST'])
@login_required
def AddPost():
    
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')

    app.config['UPLOAD_FOLDER'] = 'static/uploads/'
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        image = request.files['image']
        if image.filename == '':
            flash('No selected file')
            return redirect(request.url)
        
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image.filename))
        
        with open(os.path.join(app.config['UPLOAD_FOLDER'], image.filename), 'rb') as file:
            data = file.read()
        post = Post(name=name, description=description, image=os.path.join(app.config['UPLOAD_FOLDER'], image.filename), user_id=current_user.id)
        
        db.session.add(post)
        db.session.commit()
        posts = Post.query.all()
        post_id=post.id
        return render_template('main.html',user=user,posts=posts)
    return render_template('AddPost.html',user=user)

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    if request.method == 'POST':
        search_query = request.form['search']
        users = User.query.filter(User.username.like(f"%{search_query}%")).all()
        return render_template('search_results.html', users=users)
    return render_template('search.html')




@app.route('/follow', methods=['GET', 'POST'])
@login_required
def follow():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('index'))
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(url_for('index'))
        if current_user.is_following(user):
            flash('You are already following {}'.format(username))
            return redirect(url_for('index'))
        current_user.follow(user)
        db.session.commit()
        flash('You are now following {}!'.format(username))
        return redirect(url_for('index'))
    return render_template('follow.html')

@app.route('/unfollow', methods=['GET', 'POST'])
@login_required
def unfollow():
    if request.method == 'POST':
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(url_for('indexu'))
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(url_for('indexu'))
        if not current_user.is_following(user):
            flash('You are not currently following {}'.format(username))
            return redirect(url_for('indexu'))
        current_user.unfollow(user)
        db.session.commit()
        flash('You are no longer following {}.'.format(username))
        return redirect(url_for('indexu'))
    return render_template('unfollow.html')



@app.route('/myposts')
def myposts():
    user_id = current_user.id
    posts = Post.query.filter_by(user_id=user_id).all()
    return render_template('myposts.html', posts=posts)


@app.route('/following')
@login_required
def following():
        following_users = current_user.followed.all()
        following_users_id = [user.id for user in following_users]
        posts = Post.query.filter(Post.user_id.in_(following_users_id)).all()

        def has_liked(post_id):
            liked_post = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()
            if liked_post:
                return True
            else:
                return False

        return render_template('following.html', posts=posts, has_liked=has_liked)

        





@app.route('/like/<int:post_id>', methods=['POST'])
@login_required
def like(post_id):
    post = Post.query.get(post_id)
    user = current_user
    like = Like(post_id=post_id, user_id=user.id)
    db.session.add(like)
    db.session.commit()
    return redirect(url_for('following'))

# Route for unliking a post
@app.route('/unlike/<int:post_id>', methods=['POST'])
@login_required
def unlike(post_id):
    post = Post.query.get(post_id)
    user = current_user
    like = Like.query.filter_by(post_id=post_id, user_id=user.id).first()
    db.session.delete(like)
    db.session.commit()
    return redirect(url_for('following'))


@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    post = Post.query.filter_by(id=post_id).first()
    if request.method == 'POST':
        post.name = request.form['name']
        post.description = request.form['description']
        db.session.commit()
        return redirect(url_for('myposts', post_id=post.id))
    return render_template('editpost.html', post=post)


@app.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    form = CommentForm()
    form.post_id.data = id
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, post_id=id, user_id=current_user.id)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been published.')
    return render_template('following.html', form=form)





class CommentForm(FlaskForm):
    content = StringField('Content', validators=[DataRequired()])
    post_id = HiddenField()
    submit = SubmitField('Submit')


@app.route('/add_comment', methods=['POST'])
def add_comment():
    form = CommentForm()
    post_id = form.post_id.data
    post = Post.query.get(post_id)
    comment = Comment(content=form.content.data, post_id=post.id, user_id=current_user.id)
    db.session.add(comment)
    db.session.commit()
    flash('Your comment has been published.')
    return redirect(url_for('following', post_id=post_id))
    





   







if __name__=='__main__':
    db.create_all()
    app.debug=True
    app.run()