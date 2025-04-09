from flask import Flask, render_template, request, redirect, url_for, flash, session
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from openai import OpenAI
import uuid


load_dotenv(".env.dev")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key")


#supabase_url = os.getenv("SUPABASE_URL", "https://wwpdbvewqeoindredumk.supabase.co")
supabase_url = os.getenv("SUPABASE_URL", "https://cmkwvyhqmsonrzveejze.supabase.co")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

#openai_api_key = os.getenv("OPENAI_API_KEY")
#aiClient = OpenAI(api_key=openai_api_key)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        try:
            
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            
            # After successful signup, create a record in the users table
            # This is necessary for row-level security policies to work correctly
            user_id = response.user.id
            supabase.table('users').insert({
                "id": user_id,
                "email": email
            }).execute()
            
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error creating account: {str(e)}', 'error')
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        try:
            
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            
            session['user_id'] = response.user.id
            session['email'] = email
            session['access_token'] = response.session.access_token
            session['refresh_token'] = response.session.refresh_token
            
            
            user_data = supabase.table('users').select('*').eq('id', response.user.id).execute()
            
            
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Login failed: {str(e)}', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access the dashboard', 'error')
        return redirect(url_for('login'))
    
    
    try:
        # Check if both tokens exist in session before using them
        if 'access_token' in session and 'refresh_token' in session:
            supabase.auth.set_session(session['access_token'], session['refresh_token'])
        else:
            flash('Session expired. Please log in again.', 'error')
            return redirect(url_for('login'))
        
        response = supabase.table('syllabi').select('*').eq('user_id', session['user_id']).execute()
        syllabi = response.data
    except Exception as e:
        flash(f'Error retrieving syllabi: {str(e)}', 'error')
        syllabi = []
    
    return render_template('dashboard.html', syllabi=syllabi)

@app.route('/upload', methods=['GET', 'POST'])
def upload_syllabus():
    if 'user_id' not in session:
        flash('Please log in to upload syllabi', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        upload_type = request.form.get('upload_type')
        course_name = request.form.get('course_name')
        
        if upload_type == 'file':
            
            if 'file' not in request.files:
                flash('No file part', 'error')
                return redirect(request.url)
            
            file = request.files['file']
            if file.filename == '':
                flash('No selected file', 'error')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)
                
                
                try:
                    # Check if both tokens exist in session before using them
                    if 'access_token' in session and 'refresh_token' in session:
                        supabase.auth.set_session(session['access_token'], session['refresh_token'])
                    else:
                        flash('Session expired. Please log in again.', 'error')
                        return redirect(url_for('login'))
                    
                    supabase.table('syllabi').insert({
                        "user_id": session['user_id'],
                        "course_name": course_name,
                        "file_path": file_path,
                        "content_type": "file"
                    }).execute()
                except Exception as e:
                    flash(f'Error uploading syllabus: {str(e)}', 'error')
                    return redirect(url_for('upload_syllabus'))
                
                flash('Syllabus uploaded successfully!', 'success')
                return redirect(url_for('dashboard'))
        else:
            
            content = request.form.get('content')
            
            
            try:
                # Check if both tokens exist in session before using them
                if 'access_token' in session and 'refresh_token' in session:
                    supabase.auth.set_session(session['access_token'], session['refresh_token'])
                else:
                    flash('Session expired. Please log in again.', 'error')
                    return redirect(url_for('login'))
                
                supabase.table('syllabi').insert({
                    "user_id": session['user_id'],
                    "course_name": course_name,
                    "content": content,
                    "content_type": "text"
                }).execute()
            except Exception as e:
                flash(f'Error saving syllabus content: {str(e)}', 'error')
                return redirect(url_for('upload_syllabus'))
            
            flash('Syllabus content saved successfully!', 'success')
            return redirect(url_for('dashboard'))
    
    return render_template('upload.html')

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        flash('Please log in to access settings', 'error')
        return redirect(url_for('login'))
    
    
    try:
        # Check if both tokens exist in session before using them
        if 'access_token' in session and 'refresh_token' in session:
            supabase.auth.set_session(session['access_token'], session['refresh_token'])
        else:
            flash('Session expired. Please log in again.', 'error')
            return redirect(url_for('login'))
        
        user_data = supabase.table('users').select('*').eq('id', session['user_id']).execute()
        user = user_data.data[0] if user_data.data else None
    except Exception as e:
        flash(f'Error retrieving user data: {str(e)}', 'error')
        user = None
    
    if request.method == 'POST':
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('settings'))
    
    return render_template('settings.html', user=user)

#Finish this implementation
def chat():
    if 'user_id' not in session:
        flash('Please log in to access chat', 'error')
        return redirect(url_for('login'))
    
    try:
        # Check if both tokens exist in session before using them
        if 'access_token' in session and 'refresh_token' in session:
            supabase.auth.set_session(session['access_token'], session['refresh_token'])
        else:
            flash('Session expired. Please log in again.', 'error')
            return redirect(url_for('login'))
        
        # Implement chat functionality here
    except Exception as e:
        flash(f'Error retrieving chat data: {str(e)}', 'error')
    
    return render_template('chat.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)