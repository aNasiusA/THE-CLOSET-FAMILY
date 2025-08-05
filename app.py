from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import pyodbc
from pyodbc import IntegrityError
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from hashlib import sha256

UPLOAD_FOLDER = 'c:/xampp/htdocs/THE CLOSET FAMILY/static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# File Upload Configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def handle_upload(file):
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            return f'/static/uploads/{filename}'
        except Exception as e:
            app.logger.error(f"File upload error: {str(e)}")
            return None
    return None

@app.errorhandler(413)
def too_large(e):
    return "File is too large", 413

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database connection
def get_db_connection():
    try:
        # Try to connect to THE_CLOSET_FAMILY directly
        conn = pyodbc.connect(
            'DRIVER={SQL Server};'
            'SERVER=DESKTOP-7E4VF5M\\SQLEXPRESS;'
            'DATABASE=THE_CLOSET_FAMILY;'
            'Trusted_Connection=yes;'
        )
        return conn
    except pyodbc.ProgrammingError as e:
        # If database does not exist, connect to master and create it
        if "Cannot open database" in str(e):
            master_conn = pyodbc.connect(
                'DRIVER={SQL Server};'
                'SERVER=DESKTOP-7E4VF5M\\SQLEXPRESS;'
                'DATABASE=master;'
                'Trusted_Connection=yes;'
            )
            cursor = master_conn.cursor()
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'THE_CLOSET_FAMILY')
                BEGIN
                    CREATE DATABASE THE_CLOSET_FAMILY
                END
            """)
            master_conn.commit()
            master_conn.close()
            # Try connecting again
            conn = pyodbc.connect(
                'DRIVER={SQL Server};'
                'SERVER=DESKTOP-7E4VF5M\\SQLEXPRESS;'
                'DATABASE=THE_CLOSET_FAMILY;'
                'Trusted_Connection=yes;'
            )
            return conn
        else:
            error_msg = f"Database connection error: {str(e)}"
            print(error_msg)
            flash(error_msg, 'error')
            raise
    except pyodbc.Error as e:
        error_msg = f"Database connection error: {str(e)}"
        print(error_msg)
        flash(error_msg, 'error')
        raise

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # Only allow non-admins to sign up as Member
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        role = request.form['role']

        # Prevent users from signing up as Admin
        if role.lower() == 'admin':
            flash('Only the system administrator can create admin accounts.', 'error')
            return redirect(url_for('signup'))

        # Store password as plain text (not recommended for production)
        password_to_store = password

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO Users (Username, PasswordHash, Email, Role) VALUES (?, ?, ?, ?)",
                (username, password_to_store, email, role)
            )
            conn.commit()
            conn.close()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except pyodbc.IntegrityError:
            conn.close()
            flash('Username already exists. Please choose a different username.', 'error')
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Compare plain text password
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT UserID, Role FROM Users WHERE Username=? AND PasswordHash=?", (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user.UserID
            session['role'] = user.Role
            flash('Login successful!', 'success')
            if user.Role and user.Role.lower() == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.Role and user.Role.lower() == 'member':
                return redirect(url_for('member_dashboard'))
            else:
                flash('Unknown user role.', 'error')
                return redirect(url_for('logout'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role', '').lower()
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'member':
        return redirect(url_for('member_dashboard'))
    else:
        flash('Unauthorized access.', 'error')
        return redirect(url_for('logout'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if session.get('role', '').lower() != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('logout'))
    return render_template('admin_dashboard.html')

@app.route('/member_dashboard')
@login_required
def member_dashboard():
    if session.get('role', '').lower() != 'member':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('logout'))
    return render_template('member_dashboard.html')

@app.route('/event_registrants')
@login_required
def event_registrants():
    if session.get('role', '').lower() != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT 
            m.FirstName,
            m.LastName, 
            m.Email,
            m.Phone,
            e.EventName,
            e.EventDate,
            CASE 
                WHEN m.Phone IS NOT NULL AND m.Address IS NOT NULL AND m.Country IS NOT NULL THEN 'Member'
                ELSE 'Invitee'
            END as Status
        FROM Members m
        INNER JOIN EventRegistrations er ON m.MemberID = er.MemberID
        INNER JOIN Events e ON er.EventID = e.EventID
        WHERE (m.Phone IS NULL OR m.Address IS NULL OR m.Country IS NULL)
        ORDER BY e.EventDate DESC, m.LastName, m.FirstName
    """)
    registrants = cursor.fetchall()
    conn.close()
    return render_template('event_registrants.html', registrants=registrants)

@app.route('/members')
@login_required
def members():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor()
    # Get total number of members for pagination
    cursor.execute("""
        SELECT COUNT(*) FROM Members
        WHERE 
            (Phone IS NOT NULL AND Phone <> '')
            OR (Address IS NOT NULL AND Address <> '')
            OR (Country IS NOT NULL AND Country <> '')
    """)
    total_members = cursor.fetchone()[0]

    # Get paginated members
    cursor.execute("""
        SELECT DISTINCT m.MemberID, m.FirstName, m.LastName, m.Email, m.Phone, m.Address, m.Country, m.Birthday 
        FROM Members m
        WHERE 
            (m.Phone IS NOT NULL AND m.Phone <> '')
            OR (m.Address IS NOT NULL AND m.Address <> '')
            OR (m.Country IS NOT NULL AND m.Country <> '')
        ORDER BY m.LastName, m.FirstName
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """, (offset, per_page))
    members = cursor.fetchall()

    # For admin, fetch events for each member
    if session.get('role', '').lower() == 'admin':
        member_ids = [m[0] for m in members]  # m[0] is MemberID
        events_map = {}
        if member_ids:
            cursor.execute("""
                SELECT er.MemberID, e.EventName, e.EventDate
                FROM EventRegistrations er
                JOIN Events e ON er.EventID = e.EventID
                WHERE er.MemberID IN ({})
            """.format(','.join('?' * len(member_ids))), member_ids)
            for row in cursor.fetchall():
                events_map.setdefault(row.MemberID, []).append(row)
        columns = [desc[0] for desc in cursor.description]
        members_list = []
        for m in members:
            m_dict = dict(zip(columns, m))
            m_dict['events'] = events_map.get(m_dict['MemberID'], [])
            members_list.append(m_dict)
        members = members_list
    conn.close()

    # Manual pagination object for template
    class Pagination:
        def __init__(self, page, per_page, total_count):
            self.page = page
            self.per_page = per_page
            self.total_count = total_count

        @property
        def pages(self):
            return max(1, (self.total_count + self.per_page - 1) // self.per_page)

        @property
        def has_prev(self):
            return self.page > 1

        @property
        def has_next(self):
            return self.page < self.pages

        @property
        def prev_num(self):
            return self.page - 1

        @property
        def next_num(self):
            return self.page + 1

        def iter_pages(self, left_edge=2, right_edge=2, left_current=2, right_current=2):
            last = 0
            for num in range(1, self.pages + 1):
                if (
                    num <= left_edge
                    or (num > self.page - left_current - 1 and num < self.page + right_current)
                    or num > self.pages - right_edge
                ):
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    pagination = Pagination(page, per_page, total_members)

    return render_template('members.html', members=members, pagination=pagination)

@app.route('/events')
@login_required
def events():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT e.EventID, e.EventName, e.EventDate, e.Description, e.Location, e.EventImage, 
               COUNT(er.EventRegistrationID) as RegisteredCount
        FROM Events e
        LEFT JOIN EventRegistrations er ON e.EventID = er.EventID
        GROUP BY e.EventID, e.EventName, e.EventDate, e.Description, e.Location, e.EventImage
    """)
    events = cursor.fetchall()
    conn.close()
    return render_template('events.html', events=events)

@app.route('/register_event/<int:event_id>', methods=['POST'])
@login_required
def register_event(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 1 FROM EventRegistrations 
            WHERE EventID = ? AND MemberID = ?
        """, (event_id, session['user_id']))
        
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Already registered'})
        
        cursor.execute("""
            INSERT INTO EventRegistrations (EventID, MemberID, RegistrationDate)
            VALUES (?, ?, GETDATE())
        """, (event_id, session['user_id']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/register_for_event/<int:event_id>', methods=['POST'])
@login_required
def register_for_event(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json(silent=True)
        if data and data.get('invitee_name') and data.get('invitee_email'):
            invitee_name = data['invitee_name']
            invitee_email = data['invitee_email']
            # Ensure invitee exists in Members table before registering
            cursor.execute("SELECT MemberID FROM Members WHERE Email = ?", (invitee_email,))
            row = cursor.fetchone()
            if row:
                member_id = row[0]
            else:
                first_name = invitee_name.split()[0]
                last_name = ' '.join(invitee_name.split()[1:]) if len(invitee_name.split()) > 1 else ''
                cursor.execute(
                    "INSERT INTO Members (FirstName, LastName, Email, JoinDate, IsInvitee) VALUES (?, ?, ?, GETDATE(), 1)",
                    (first_name, last_name, invitee_email)
                )
                conn.commit()
                cursor.execute("SELECT MemberID FROM Members WHERE Email = ?", (invitee_email,))
                member_id = cursor.fetchone()[0]
        else:
            member_id = session['user_id']
            # Ensure member exists in Members table
            cursor.execute("SELECT 1 FROM Members WHERE MemberID = ?", (member_id,))
            if not cursor.fetchone():
                cursor.execute("SELECT Username, Email FROM Users WHERE UserID = ?", (member_id,))
                user_row = cursor.fetchone()
                if user_row:
                    username, email = user_row
                else:
                    username, email = f"Member{member_id}", f"member{member_id}@example.com"
                cursor.execute(
                    "INSERT INTO Members (FirstName, LastName, Email, JoinDate) VALUES (?, ?, ?, GETDATE())",
                    (username, '', email)
                )
                conn.commit()
                cursor.execute("SELECT MemberID FROM Members WHERE Email = ?", (email,))
                member_id = cursor.fetchone()[0]

        # Check if already registered
        cursor.execute("""
            SELECT 1 FROM EventRegistrations 
            WHERE EventID = ? AND MemberID = ?
        """, (event_id, member_id))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'This person is already registered for this event.'})

        # Register for the event
        cursor.execute("""
            INSERT INTO EventRegistrations (EventID, MemberID, RegistrationDate)
            VALUES (?, ?, GETDATE())
        """, (event_id, member_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Successfully registered for the event.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    finally:
        conn.close()

@app.route('/departments')
@login_required
def departments():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DepartmentID, DepartmentName, Description, DepartmentHeads FROM Departments")
    departments = cursor.fetchall()
    joined_departments = []
    # Use MinistryID from MemberMinistries table
    if session.get('role', '').lower() != 'admin':
        cursor.execute("SELECT MinistryID FROM MemberMinistries WHERE MemberID = ?", (session['user_id'],))
        joined_departments = cursor.fetchall()
    conn.close()
    return render_template('departments.html', departments=departments, joined_departments=joined_departments)

@app.route('/Givings')
@login_required
def Givings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Givings")
    Givings = cursor.fetchall()
    conn.close()
    return render_template('Givings.html', Givings=Givings)

@app.route('/donations')
@login_required
def donations():
    conn = get_db_connection()
    cursor = conn.cursor()
    role = session.get('role', '').lower()
    user_id = session.get('user_id')
    if role == 'admin':
        cursor.execute("SELECT DonationID, MemberID, DonationDate, Amount, Currency FROM Givings")
        donations = cursor.fetchall()
    else:
        cursor.execute("SELECT DonationID, MemberID, DonationDate, Amount, Currency FROM Givings WHERE MemberID = ?", (user_id,))
        donations = cursor.fetchall()
    conn.close()
    return render_template('donations.html', Givings=donations)

@app.route('/leaders')
@login_required
def leaders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Leaders")
    leaders = cursor.fetchall()
    conn.close()
    return render_template('leaders.html', leaders=leaders)

@app.route('/add_member', methods=['GET', 'POST'])
@login_required
def add_member():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone'] or None
        address = request.form['address'] or None
        country = request.form['country'] or None
        birthday = request.form['birthday'] or None

        # Validate and format the birthday
        if birthday:
            try:
                birthday = datetime.strptime(birthday, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format for Birthday. Please use YYYY-MM-DD.', 'error')
                return redirect(url_for('add_member'))

        conn = get_db_connection()
        cursor = conn.cursor()
        # Prevent duplicate member by email or name+email
        cursor.execute("SELECT 1 FROM Members WHERE Email = ? OR (FirstName = ? AND LastName = ? AND Email = ?)", (email, first_name, last_name, email))
        if cursor.fetchone():
            conn.close()
            flash('A member with this name and email already exists.', 'error')
            return redirect(url_for('add_member'))

        insert_sql = (
            "INSERT INTO Members (FirstName, LastName, Email, Phone, Address, Country, Birthday) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)"
        )
        params = (
            str(first_name) if first_name else None,
            str(last_name) if last_name else None,
            str(email) if email else None,
            str(phone) if phone else None,
            str(address) if address else None,
            str(country) if country else None,
            str(birthday) if birthday else None
        )
        cursor.execute(insert_sql, params)
        conn.commit()
        conn.close()
        flash('Member added successfully!')
        return redirect(url_for('members'))
    return render_template('add_member.html')

@app.route('/delete_member/<int:member_id>', methods=['POST'])
@login_required
def delete_member(member_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if the member exists
        cursor.execute("SELECT 1 FROM Members WHERE MemberID = ?", (member_id,))
        if not cursor.fetchone():
            flash('Member not found.', 'error')
            return redirect(url_for('members'))

        # Delete event registrations for this member to avoid foreign key constraint errors
        cursor.execute("DELETE FROM EventRegistrations WHERE MemberID = ?", (member_id,))
        # Delete member-related records from dependent tables and then the member
        cursor.execute("DELETE FROM Attendances WHERE MemberID = ?", (member_id,))
        cursor.execute("DELETE FROM Givings WHERE MemberID = ?", (member_id,))
        cursor.execute("DELETE FROM MemberMinistries WHERE MemberID = ?", (member_id,))
        cursor.execute("DELETE FROM Members WHERE MemberID = ?", (member_id,))
        conn.commit()
        flash('Member deleted successfully!')
    except Exception as e:
        flash(f'Could not delete member: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('members'))

@app.route('/delete_members', methods=['POST'])
@login_required
def delete_members():
    if session.get('role', '').lower() != 'admin':
        flash('Unauthorized.', 'error')
        return redirect(url_for('members'))
    member_ids = request.form.getlist('member_ids')
    if not member_ids:
        flash('No members selected.', 'error')
        return redirect(url_for('members'))
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for member_id in member_ids:
            # Delete event registrations for this member to avoid foreign key constraint errors
            cursor.execute("DELETE FROM EventRegistrations WHERE MemberID = ?", (member_id,))
            cursor.execute("DELETE FROM Attendances WHERE MemberID = ?", (member_id,))
            cursor.execute("DELETE FROM Givings WHERE MemberID = ?", (member_id,))
            cursor.execute("DELETE FROM MemberMinistries WHERE MemberID = ?", (member_id,))
            cursor.execute("DELETE FROM Members WHERE MemberID = ?", (member_id,))
        conn.commit()
        flash('Selected members deleted successfully!', 'success')
    except Exception as e:
        flash(f'Could not delete selected members: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('members'))

@app.route('/add_event', methods=['POST'])
@login_required
def add_event():
    try:
        event_name = request.form['event_name']
        event_date = request.form['event_date']
        description = request.form['description']
        location = request.form['location']

        # Convert event_date to SQL Server DATETIME format if needed
        if 'T' in event_date:
            event_date = event_date.replace('T', ' ')
        if len(event_date) == 16:
            event_date += ':00'

        image_url = None
        if 'event_image' in request.files:
            image_url = handle_upload(request.files['event_image'])

        conn = get_db_connection()
        cursor = conn.cursor()
        # Check if an event with the same name, date, and location already exists
        cursor.execute(
            "SELECT 1 FROM Events WHERE EventName = ? AND EventDate = ? AND Location = ?",
            (event_name, event_date, location)
        )
        if cursor.fetchone():
            conn.close()
            flash('An event with the same name, date, and location already exists.', 'error')
            return redirect(url_for('events'))

        cursor.execute(
            "INSERT INTO Events (EventName, EventDate, Description, Location, EventImage) VALUES (?, ?, ?, ?, ?)",
            (event_name, event_date, description, location, image_url)
        )
        conn.commit()
        conn.close()
        flash('Event added successfully!')
    except Exception as e:
        flash(f'Error adding event: {str(e)}', 'error')
    return redirect(url_for('events'))

@app.route('/delete_event/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # First, delete all registrations for this event to avoid foreign key constraint errors
        cursor.execute("DELETE FROM EventRegistrations WHERE EventID = ?", (event_id,))
        # Then, delete the event itself
        cursor.execute("DELETE FROM Events WHERE EventID = ?", (event_id,))
        conn.commit()
        flash('Event deleted successfully!', 'success')
    except Exception as e:
        flash(f'Could not delete event: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('events'))

@app.route('/add_department', methods=['GET', 'POST'])
@login_required
def add_department():
    if request.method == 'POST':
        department_name = request.form['department_name']
        description = request.form['description']
        department_heads = request.form['department_heads']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Departments (DepartmentName, Description, DepartmentHeads) VALUES (?, ?, ?)",
            (department_name, description, department_heads)
        )
        conn.commit()
        conn.close()
        flash('Department added successfully!')
        return redirect(url_for('departments'))
    return render_template('add_department.html')

@app.route('/delete_department/<int:department_id>', methods=['POST'])
@login_required
def delete_department(department_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM Departments WHERE DepartmentID = ?", (department_id,))
        if cursor.fetchone() is None:
            flash('Department not found.')
        else:
            cursor.execute("DELETE FROM Departments WHERE DepartmentID = ?", (department_id,))
            conn.commit()
            flash('Department deleted successfully!')
    except IntegrityError:
        flash('Cannot delete department: it is referenced by one or more ministries.')
    except Exception as e:
        flash('Could not delete department: ' + str(e))
    finally:
        conn.close()
    return redirect(url_for('departments'))

@app.route('/members_dashboard')
def members_dashboard():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cursor = conn.cursor()
    # Get total number of members for pagination
    cursor.execute("SELECT COUNT(*) FROM Members")
    total_members = cursor.fetchone()[0]

    # Get paginated members
    cursor.execute("""
        SELECT MemberID, FirstName, LastName, Email, Phone, Address, Country
        FROM Members
        ORDER BY MemberID
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """, (offset, per_page))
    all_members = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(DISTINCT m.MemberID)
        FROM Members m
        JOIN Attendances a ON m.MemberID = a.MemberID
        WHERE MONTH(a.AttendanceDate) = MONTH(GETDATE()) AND YEAR(a.AttendanceDate) = YEAR(GETDATE())
    """)
    active_members = cursor.fetchone()[0]
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN DATEDIFF(YEAR, Birthday, GETDATE()) <= 18 THEN 1 ELSE 0 END) AS 'Age_0_18',
            SUM(CASE WHEN DATEDIFF(YEAR, Birthday, GETDATE()) BETWEEN 19 AND 35 THEN 1 ELSE 0 END) AS 'Age_19_35',
            SUM(CASE WHEN DATEDIFF(YEAR, Birthday, GETDATE()) BETWEEN 36 AND 50 THEN 1 ELSE 0 END) AS 'Age_36_50',
            SUM(CASE WHEN DATEDIFF(YEAR, Birthday, GETDATE()) > 50 THEN 1 ELSE 0 END) AS 'Age_51_plus'
        FROM Members 
        WHERE Birthday IS NOT NULL
    """)
    age_row = cursor.fetchone()
    age_groups = {
        'labels': ['0-18', '19-35', '36-50', '51+'],
        'data': [
            age_row.Age_0_18 or 0,
            age_row.Age_19_35 or 0,
            age_row.Age_36_50 or 0,
            age_row.Age_51_plus or 0
        ]
    }
    stats = {
        'total_members': total_members,
        'active_members': active_members
    }
    conn.close()

    # Manual pagination object for template
    class Pagination:
        def __init__(self, page, per_page, total_count):
            self.page = page
            self.per_page = per_page
            self.total_count = total_count

        @property
        def pages(self):
            return max(1, (self.total_count + self.per_page - 1) // self.per_page)

        @property
        def has_prev(self):
            return self.page > 1

        @property
        def has_next(self):
            return self.page < self.pages

        @property
        def prev_num(self):
            return self.page - 1

        @property
        def next_num(self):
            return self.page + 1

        def iter_pages(self, left_edge=2, right_edge=2, left_current=2, right_current=2):
            last = 0
            for num in range(1, self.pages + 1):
                if (
                    num <= left_edge
                    or (num > self.page - left_current - 1 and num < self.page + right_current)
                    or num > self.pages - right_edge
                ):
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    pagination = Pagination(page, per_page, total_members)

    return render_template(
        'members_dashboard.html',
        stats=stats,
        age_groups=age_groups,
        all_members=all_members,
        pagination=pagination
    )

@app.route('/edit_member/<int:member_id>', methods=['GET', 'POST'])
@login_required
def edit_member(member_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone'] or None  # Convert empty strings to None
        address = request.form['address'] or None
        country = request.form['country'] or None
        birthday = request.form['birthday'] or None

        # Validate and format the birthday
        if birthday:
            try:
                birthday = datetime.strptime(birthday, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format for Birthday. Please use YYYY-MM-DD.', 'error')
                return redirect(url_for('edit_member', member_id=member_id))

        # Update member details in the database
        cursor.execute("""
            UPDATE Members 
            SET FirstName=?, LastName=?, Email=?, Phone=?, Address=?, Country=?, Birthday=? 
            WHERE MemberID=?
        """, (first_name, last_name, email, phone, address, country, birthday, member_id))
        conn.commit()
        conn.close()
        flash('Member updated successfully!')
        return redirect(url_for('members'))
    else:
        cursor.execute("SELECT MemberID, FirstName, LastName, Email, Phone, Address, Country, Birthday FROM Members WHERE MemberID=?", (member_id,))
        member = cursor.fetchone()
        conn.close()
        if not member:
            flash('Member not found.', 'error')
            return redirect(url_for('members'))
        return render_template('edit_member.html', member=member)

@app.route('/attendance_dashboard')
@login_required
def attendance_dashboard():
    if session.get('role', '').lower() != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all members for attendance marking
    cursor.execute("SELECT MemberID, FirstName, LastName FROM Members ORDER BY FirstName, LastName")
    members = cursor.fetchall()
    
    # Get today's attendance
    cursor.execute("""
        SELECT m.FirstName, m.LastName, a.ServiceType, 
               FORMAT(a.AttendanceDate, 'hh:mm tt') as AttendanceTime
        FROM Attendances a
        JOIN Members m ON a.MemberID = m.MemberID
        WHERE CAST(a.AttendanceDate AS DATE) = CAST(GETDATE() AS DATE)
        ORDER BY a.AttendanceDate DESC
    """)
    today_attendance = cursor.fetchall()
    
    # Get attendance data for the past 4 weeks
    cursor.execute("""
        SELECT 
            FORMAT(DATEADD(DAY, -number, GETDATE()), 'MMM dd') as DateLabel,
            (SELECT COUNT(DISTINCT MemberID) 
             FROM Attendances 
             WHERE CAST(AttendanceDate AS DATE) = CAST(DATEADD(DAY, -number, GETDATE()) AS DATE)) as Count
        FROM master..spt_values 
        WHERE type = 'P' AND number <= 28
        ORDER BY number DESC
    """)
    attendance_rows = cursor.fetchall()
    
    # Ensure attendance_data['labels'] and ['values'] are lists, not methods or objects
    attendance_labels = []
    attendance_values = []
    for row in attendance_rows:
        attendance_labels.append(row[0])
        attendance_values.append(int(row[1]) if row[1] is not None else 0)
    attendance_data = {
        'labels': attendance_labels,
        'values': attendance_values
    }
    
    conn.close()
    return render_template('attendance_dashboard.html', 
                         members=members,
                         today_attendance=today_attendance,
                         attendance_data=attendance_data)

@app.route('/mark_attendance', methods=['POST'])
@login_required
def mark_attendance():
    if session.get('role', '').lower() != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    data = request.get_json()
    date = data.get('date')
    service_type = data.get('service_type')
    member_ids = data.get('members', [])
    
    if not date or not service_type or not member_ids:
        return jsonify({'success': False, 'message': 'Missing required data'})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for member_id in member_ids:
            cursor.execute("""
                INSERT INTO Attendances (MemberID, AttendanceDate, ServiceType)
                VALUES (?, ?, ?)
            """, (member_id, date, service_type))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
    finally:
        conn.close()

@app.route('/Givings_dashboard')
@login_required
def Givings_dashboard():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT ISNULL(SUM(Amount), 0) FROM Givings
            WHERE MONTH(DonationDate) = MONTH(GETDATE()) AND YEAR(DonationDate) = YEAR(GETDATE())
        """)
        this_month = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COUNT(DISTINCT MemberID) FROM Givings
            WHERE MONTH(DonationDate) = MONTH(GETDATE()) AND YEAR(DonationDate) = YEAR(GETDATE())
        """)
        donors = cursor.fetchone()[0]
        cursor.execute("""
            SELECT TOP 4 FORMAT(DonationDate, 'MMM yyyy') as Month, SUM(Amount)
            FROM Givings
            GROUP BY YEAR(DonationDate), MONTH(DonationDate), FORMAT(DonationDate, 'MMM yyyy')
            ORDER BY MIN(DonationDate) DESC
        """)
        rows = cursor.fetchall()
    except pyodbc.ProgrammingError:
        cursor.execute("""
            SELECT ISNULL(SUM(Amount), 0) FROM Finances
            WHERE TransactionType='Income' AND MONTH(TransactionDate) = MONTH(GETDATE()) AND YEAR(TransactionDate) = YEAR(GETDATE())
        """)
        this_month = cursor.fetchone()[0]
        cursor.execute("""
            SELECT COUNT(*) FROM Finances
            WHERE TransactionType='Income' AND MONTH(TransactionDate) = MONTH(GETDATE()) AND YEAR(TransactionDate) = YEAR(GETDATE())
        """)
        donors = cursor.fetchone()[0]
        cursor.execute("""
            SELECT TOP 4 FORMAT(TransactionDate, 'MMM yyyy') as Month, SUM(Amount)
            FROM Finances
            WHERE TransactionType='Income'
            GROUP BY YEAR(TransactionDate), MONTH(TransactionDate), FORMAT(TransactionDate, 'MMM yyyy')
            ORDER BY MIN(TransactionDate) DESC
        """)
        rows = cursor.fetchall()
    donation_summary = {
        'labels': [row[0] for row in reversed(rows)],
        'data': [float(row[1]) for row in reversed(rows)]
    }
    stats = {
        'this_month': this_month,
        'donors': donors
    }
    conn.close()
    return render_template('Givings_dashboard.html', stats=stats, donation_summary=donation_summary)

@app.route('/main_dashboard')
@login_required
def main_dashboard():
    return render_template('dashboard.html')

@app.route('/add_donation', methods=['GET', 'POST'])
@login_required
def add_donation():
    if request.method == 'POST':
        member_id = request.form['member_id']
        amount = request.form['amount']
        currency = request.form['currency']
        donation_date = request.form.get('donation_date') or datetime.now().strftime('%Y-%m-%d')
        conn = get_db_connection()
        cursor = conn.cursor()
        # Add currency to the Givings table if not already present
        try:
            cursor.execute(
                "ALTER TABLE Givings ADD Currency NVARCHAR(10) NULL"
            )
            conn.commit()
        except Exception:
            pass  # Ignore if column already exists
        cursor.execute(
            "INSERT INTO Givings (MemberID, DonationDate, Amount, Currency) VALUES (?, ?, ?, ?)",
            (member_id, donation_date, amount, currency)
        )
        conn.commit()
        conn.close()
        flash('Donation added successfully!', 'success')
        return redirect(url_for('donations'))
    # Fetch members for the dropdown
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MemberID, FirstName, LastName FROM Members")
    members = cursor.fetchall()
    conn.close()
    # Provide a list of common currencies (now includes CAD and AUD)
    currencies = ['USD', 'EUR', 'GBP', 'NGN', 'KES', 'ZAR', 'GHS', 'XAF', 'XOF', 'CAD', 'AUD']
    return render_template('add_donation.html', members=members, currencies=currencies)

@app.route('/delete_donation/<int:donation_id>', methods=['POST'])
@login_required
def delete_donation(donation_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Givings WHERE DonationID = ?", (donation_id,))
        conn.commit()
        flash('Donation deleted successfully!', 'success')
    except Exception as e:
        flash(f'Could not delete donation: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('donations'))

@app.route('/join_department/<int:department_id>', methods=['POST'])
@login_required
def join_department(department_id):
    member_id = session.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Ensure the member exists in Members table
        cursor.execute("SELECT 1 FROM Members WHERE MemberID = ?", (member_id,))
        if not cursor.fetchone():
            cursor.execute("SELECT Username, Email FROM Users WHERE UserID = ?", (member_id,))
            user_row = cursor.fetchone()
            if user_row:
                username, email = user_row
            else:
                username, email = f"Member{member_id}", f"member{member_id}@example.com"
            cursor.execute(
                "INSERT INTO Members (FirstName, LastName, Email, JoinDate) VALUES (?, ?, ?, GETDATE())",
                (username, '', email)
            )
            conn.commit()
            cursor.execute("SELECT MemberID FROM Members WHERE Email = ?", (email,))
            member_id = cursor.fetchone()[0]

        # Find the correct MinistryID for this department
        cursor.execute("SELECT MinistryID FROM Ministries WHERE DepartmentID = ?", (department_id,))
        ministry_row = cursor.fetchone()
        if not ministry_row:
            flash('This department is not available to join. Please contact admin.', 'error')
            return redirect(url_for('departments'))
        ministry_id = ministry_row[0]

        # Prevent duplicate department join
        cursor.execute("SELECT 1 FROM MemberMinistries WHERE MemberID = ? AND MinistryID = ?", (member_id, ministry_id))
        if cursor.fetchone():
            flash('You have already joined this department.', 'info')
        else:
            cursor.execute("INSERT INTO MemberMinistries (MemberID, MinistryID) VALUES (?, ?)", (member_id, ministry_id))
            conn.commit()
            flash('You have successfully joined the department!', 'success')
    except Exception as e:
        flash(f'Could not join department: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('departments'))

@app.route('/unjoin_department/<int:department_id>', methods=['POST'])
@login_required
def unjoin_department(department_id):
    member_id = session.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Find the correct MinistryID for this department
        cursor.execute("SELECT MinistryID FROM Ministries WHERE MinistryID = ? OR DepartmentID = ?", (department_id, department_id))
        ministry_row = cursor.fetchone()
        if not ministry_row:
            flash('This department is not available to unjoin. Please contact admin.', 'error')
            return redirect(url_for('departments'))
        ministry_id = ministry_row[0]

        # Remove the member from the department (MemberMinistries)
        cursor.execute("DELETE FROM MemberMinistries WHERE MemberID = ? AND MinistryID = ?", (member_id, ministry_id))
        conn.commit()
        flash('You have successfully unjoined the department.', 'success')
    except Exception as e:
        flash(f'Could not unjoin department: {str(e)}', 'error')
    finally:
        conn.close()
    return redirect(url_for('departments'))

@app.route('/department_members/<int:department_id>')
@login_required
def department_members(department_id):
    if session.get('role', '').lower() != 'admin':
        flash('Unauthorized access.', 'error')
        return redirect(url_for('departments'))
    conn = get_db_connection()
    cursor = conn.cursor()
    # Find the ministry for this department using DepartmentID
    cursor.execute("SELECT MinistryID FROM Ministries WHERE DepartmentID = ?", (department_id,))
    ministry_row = cursor.fetchone()
    if not ministry_row:
        conn.close()
        flash('No ministry found for this department.', 'error')
        return redirect(url_for('departments'))
    ministry_id = ministry_row[0]
    # Get all members in this ministry/department
    cursor.execute("""
        SELECT m.MemberID, m.FirstName, m.LastName, m.Email, m.Phone, m.Address, m.Country, m.Birthday
        FROM MemberMinistries mm
        JOIN Members m ON mm.MemberID = m.MemberID
        WHERE mm.MinistryID = ?
    """, (ministry_id,))
    members = cursor.fetchall()
    cursor.execute("SELECT DepartmentName FROM Departments WHERE DepartmentID = ?", (department_id,))
    dept = cursor.fetchone()
    conn.close()
    return render_template('department_members.html', members=members, department_name=dept.DepartmentName if dept else "Department")

if __name__ == '__main__':
    app.run(debug=True)
if __name__ == '__main__':
    app.run(debug=True)
