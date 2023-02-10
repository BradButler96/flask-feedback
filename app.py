from flask import Flask, render_template, redirect, session, flash
from flask_debugtoolbar import DebugToolbarExtension
from models import connect_db, db, User, Feedback
from forms import RegisterForm, LoginForm, FeedbackForm, UpdateFeedbackForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc


app = Flask(__name__)
app.app_context().push()
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql:///flask_feedback"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config["SECRET_KEY"] = "BigSecret"
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

connect_db(app)
db.create_all()

toolbar = DebugToolbarExtension(app)


@app.route('/')
def homepage():
    """Load homepage if nobody is logged in"""
    if "user_id" not in session:
        return render_template('index.html')

    else:
        user = User.query.get(session['user_id'])
        return redirect(f'/users/{ user.username }')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Load register form if nobody is logged in"""
    session_id = session['user_id']

    if "user_id" not in session:
        form = RegisterForm()

        if form.validate_on_submit():
            first_name = form.first_name.data
            last_name = form.last_name.data
            email = form.email.data
            username = form.username.data 
            password = form.password.data 

            new_user = User.register(first_name, last_name, email, username, password)
            db.session.add(new_user)
            try:
                db.session.commit()

            except IntegrityError:
                form.username.errors.append('Username taken.  Please pick another.')

                return render_template('register.html', form=form)

            session_id = new_user.id
            flash('Welcome! Successfully Created Your Account!', "success")

            return redirect(f'/users/{ new_user.username }')

        return render_template('register.html', form=form)

    else:
        user = User.query.get(session_id)
        return redirect(f'/users/{ user.username }')

    
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Load login form if nobody is logged in"""
    session_id = session['user_id']

    if "user_id" not in session:
        form = LoginForm()

        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data

            user = User.authenticate(username, password)

            if user:
                flash(f"Welcome Back, { user.username }!", "primary")
                session_id = user.id
                return redirect(f'/users/{ username }')
            else:
                form.username.errors = ['Invalid username/password.']

        return render_template('login.html', form=form)

    else:
        user = User.query.get(session_id)
        return redirect(f'/users/{ user.username }')


@app.route('/logout')
def logout():
    """Log user out"""
    session.pop('user_id')
    flash("Goodbye!", "info")

    return redirect('/')


@app.route('/users/<username>')
def profile(username):
    """Load user profile and feedback feed"""
    user = User.query.filter(User.username.ilike(username)).one_or_none()
    user_id = user.id

    if "user_id" not in session:
        flash("Please login first!", "danger")
        return redirect('/login')

    else:
        id = user_id
        first_name = user.first_name
        last_name = user.last_name
        username = user.username
        email = user.email
        feedback = Feedback.query.order_by(desc(Feedback.id)).all()

        return render_template('profile.html', 
                                id=id,
                                first_name=first_name, 
                                last_name=last_name, 
                                username=username, 
                                email=email, 
                                feedback=feedback)


@app.route('/users/<username>/delete', methods=['POST'])
def delete_user(username):
    """Delete user"""
    session_id = session['user_id']

    if 'user_id' not in session:
        flash("Please login first!", "danger")
        return redirect('/login')

    user = User.query.filter(User.username.ilike(username)).one_or_none()

    if user.id == session_id:
        db.session.delete(user)
        db.session.commit()
        session.pop('user_id')

        flash("You've successfully deleted your account!", 'info')
        return redirect('/')


@app.route('/users/<username>/feedback/add', methods=['GET', 'POST'])
def add_feedback(username):
    """Post feedback"""
    user = User.query.filter(User.username.ilike(username)).one_or_none()
    form = FeedbackForm()

    if "user_id" not in session:
        flash("Please login first!", "danger")
        return redirect('/')

    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        new_feedback = Feedback(title=title, content=content, user_id=session['user_id'])
        db.session.add(new_feedback)
        db.session.commit()

        flash('Feedback Created!', 'success')
        return redirect(f'/users/{ username }')

    return render_template('feedback.html', form=form, user=user, username=user.username)


@app.route('/feedback/<int:feedback_id>/update', methods=['GET', 'POST'])
def update_feedback(feedback_id):
    """Let users update their own posts"""
    feedback = Feedback.query.get_or_404(feedback_id)
    user_id = feedback.user_id
    user = User.query.get(user_id)
    form = UpdateFeedbackForm(obj=feedback)
    session_id = session['user_id']
    session_user = User.query.get(session_id)

    if "user_id" not in session:
        flash("Please login first!", "danger")
        return redirect('/')

    if user_id != session['user_id']:
        flash('Nice Try!', 'warning')
        return redirect(f'/users/{ session_user.username }')

    if user_id == session_id:
        if form.validate_on_submit():
            if form.title.data:
                feedback.title = form.title.data
            else:
                feedback.title = feedback.title

            if form.content.data:
                feedback.content = form.content.data
            else:
                feedback.content = feedback.content

            db.session.commit()
            flash('Feedback Modified!', 'success')
            return redirect(f'/users/{ user.username }')

    return render_template('feedback-edit.html', form=form, user=user, username=user.username)


@app.route('/feedback/<int:feedback_id>/delete', methods=['POST'])
def delete_feedback(feedback_id):
    """Let user delete their own posts"""
    feedback = Feedback.query.get_or_404(feedback_id)
    user_id = feedback.user_id
    user = User.query.get(user_id)
    session_id = session['user_id']

    if session_id == feedback.user_id:
        db.session.delete(feedback)
        db.session.commit()

        flash('Feedback Deleted!', 'success')
        return redirect(f'/users/{ user.username }')

    