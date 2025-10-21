from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

app = Flask(__name__)

# ---------------- CONFIG ----------------
app.secret_key = 'your_secret_key_here'

# MySQL connection
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Narean%4025@localhost/blog_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# ---------------- MODELS ----------------
class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    posts = db.relationship('Post', backref='user', cascade="all, delete-orphan", lazy=True)

class Post(db.Model):
    __tablename__ = 'posts'
    post_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    image = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('Comment', backref='post', cascade="all, delete-orphan", lazy=True)
    likes = db.relationship('Like', backref='post', cascade="all, delete-orphan", lazy=True)

class Comment(db.Model):
    __tablename__ = 'comments'
    comment_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Like(db.Model):
    __tablename__ = 'likes'
    like_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    __tablename__ = 'messages'
    message_id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

class Notification(db.Model):
    __tablename__ = 'notifications'
    notification_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    content = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'like', 'comment', etc
    reference_id = db.Column(db.Integer)  # post_id or comment_id
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

# ---------------- CREATE TABLES ----------------
with app.app_context():
    db.create_all()

# ---------------- HELPERS ----------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------- ROUTES ----------------

# ---------- Register ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user' in session:
        return redirect('/')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists!", "warning")
            return redirect('/register')

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect('/login')
    return render_template('register.html')

# ---------- Login ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        return redirect('/')
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user'] = user.username
            flash(f"Welcome, {user.username}!", "success")
            return redirect('/')
        else:
            flash("Invalid username or password", "danger")
    return render_template('login.html')

# ---------- Logout ----------
@app.route('/logout')
@login_required
def logout():
    session.pop('user', None)
    flash("You have logged out.", "info")
    return redirect('/login')

# ---------- Home ----------
@app.route('/')
@login_required
def index():
    current_user = User.query.filter_by(username=session['user']).first()
    posts = Post.query.order_by(Post.created_at.desc()).all()
    
    # Add is_liked property to each post
    for post in posts:
        post.is_liked = Like.query.filter_by(
            user_id=current_user.user_id,
            post_id=post.post_id
        ).first() is not None
    
    # Get unread counts
    unread_messages = Message.query.filter_by(
        receiver_id=current_user.user_id,
        is_read=False
    ).count()
    
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.user_id,
        is_read=False
    ).count()
    
    return render_template('index.html', 
                         posts=posts,
                         unread_messages=unread_messages,
                         unread_notifications=unread_notifications)

# ---------- Add Post ----------
@app.route('/add_post', methods=['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        current_user = User.query.filter_by(username=session['user']).first()
        image_file = request.files.get('image')
        image_filename = None

        if image_file and allowed_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)

        new_post = Post(title=title, content=content, user_id=current_user.user_id, image=image_filename)
        db.session.add(new_post)
        db.session.commit()
        flash("Post added successfully!", "success")
        return redirect('/')
    return render_template('add_post.html')

# ---------- View Single Post ----------
@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
@login_required
def post(post_id):
    post = Post.query.get_or_404(post_id)
    current_user = User.query.filter_by(username=session['user']).first()
    
    if request.method == 'POST':
        comment_text = request.form['comment']
        new_comment = Comment(
            post_id=post.post_id, 
            name=current_user.username,
            comment=comment_text
        )
        db.session.add(new_comment)
        
        # Create notification for post owner if it's not their own post
        if current_user.user_id != post.user_id:
            notification = Notification(
                user_id=post.user_id,
                content=f"{current_user.username} commented on your post: {post.title[:30]}...",
                type='comment',
                reference_id=post_id
            )
            db.session.add(notification)
            
        db.session.commit()
        flash("Comment added!", "success")
        return redirect(f'/post/{post_id}')
        
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at.desc()).all()
    return render_template('post.html', post=post, comments=comments)

# ---------- Delete Post ----------
@app.route('/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    current_user = User.query.filter_by(username=session['user']).first()

    if post.user_id != current_user.user_id:
        flash("You can only delete your own posts.", "danger")
        return redirect('/')

    db.session.delete(post)
    db.session.commit()
    flash("Post deleted successfully.", "info")
    return redirect('/')

# ---------- Toggle Like ----------
@app.route('/toggle_like/<int:post_id>', methods=['POST'])
@login_required
def toggle_like(post_id):
    current_user = User.query.filter_by(username=session['user']).first()
    post = Post.query.get_or_404(post_id)
    
    existing_like = Like.query.filter_by(
        user_id=current_user.user_id,
        post_id=post_id
    ).first()
    
    if existing_like:
        db.session.delete(existing_like)
    else:
        new_like = Like(user_id=current_user.user_id, post_id=post_id)
        db.session.add(new_like)
        
        # Create notification for post owner if it's not their own post
        if current_user.user_id != post.user_id:
            notification = Notification(
                user_id=post.user_id,
                content=f"{current_user.username} liked your post: {post.title[:30]}...",
                type='like',
                reference_id=post_id
            )
            db.session.add(notification)
    
    db.session.commit()
    return redirect(request.referrer or url_for('index'))

@app.route('/my_posts')
@login_required
def my_posts():
    current_user = User.query.filter_by(username=session['user']).first()
    posts = Post.query.filter_by(user_id=current_user.user_id).order_by(Post.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/messages')
@login_required
def messages():
    current_user = User.query.filter_by(username=session['user']).first()
    messages = Message.query.filter(
        (Message.sender_id == current_user.user_id) |
        (Message.receiver_id == current_user.user_id)
    ).order_by(Message.created_at.desc()).all()
    return render_template('messages.html', messages=messages)

@app.route('/notifications')
@login_required
def notifications():
    current_user = User.query.filter_by(username=session['user']).first()
    notifications = Notification.query.filter_by(
        user_id=current_user.user_id
    ).order_by(Notification.created_at.desc()).all()
    
    # Mark notifications as read
    for notification in notifications:
        notification.is_read = True
    db.session.commit()
    
    return render_template('notifications.html', notifications=notifications)

@app.route('/settings')
@login_required
def settings():
    current_user = User.query.filter_by(username=session['user']).first()
    return render_template('settings.html', user=current_user)

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)
