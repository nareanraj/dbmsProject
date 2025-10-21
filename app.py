from flask import Flask, render_template, request, redirect, session, flash, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os

app = Flask(__name__)

# ---------------- CONFIG ----------------
app.secret_key = 'your_secret_key_here'  # required for sessions

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

class Post(db.Model):
    __tablename__ = 'posts'
    post_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('Comment', backref='post', cascade="all, delete-orphan", lazy=True)

class Comment(db.Model):
    __tablename__ = 'comments'
    comment_id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.post_id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---------------- CREATE TABLES ----------------
with app.app_context():
    db.create_all()

# ---------------- HELPER FUNCTIONS ----------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# login-required decorator
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

# ---------- Home (Posts) ----------
@app.route('/')
@login_required
def index():
    posts = Post.query.order_by(Post.post_id.desc()).all()
    print(posts)
    return render_template('index.html', userpost=posts)

# ---------- Add Post ----------
@app.route('/add_post', methods=['GET', 'POST'])
@login_required
def add_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        author = session['user']
        image_file = request.files.get('image')
        image_filename = None

        if image_file and allowed_file(image_file.filename):
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)

        new_post = Post(title=title, content=content, author=author, image=image_filename)
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
    if request.method == 'POST':
        name = request.form['name']
        comment_text = request.form['comment']
        new_comment = Comment(post_id=post.post_id, name=name, comment=comment_text)
        db.session.add(new_comment)
        db.session.commit()
        flash("Comment added!", "success")
        return redirect(f'/post/{post_id}')
    comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.comment_id.asc()).all()
    return render_template('post.html', post=post, comments=comments)

# ---------- Delete Post ----------
@app.route('/delete_post/<int:post_id>')
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    # ✅ Check ownership
    if post.author != session['user']:
        flash("You can only delete your own posts.", "danger")
        return redirect('/')

    db.session.delete(post)
    db.session.commit()
    flash("Post deleted successfully.", "info")
    return redirect('/')

# ---------------- RUN APP ----------------
if __name__ == '__main__':
    app.run(debug=True)
