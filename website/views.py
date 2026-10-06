from flask import Blueprint, render_template, redirect, url_for,flash
from flask_login import login_required, current_user
from .models import User
from flask import request, jsonify
from datetime import datetime, time, timedelta
from .models import Workspace, Booking, Notification, db, Note, ClassRoutine
from werkzeug.security import generate_password_hash, check_password_hash
from zoneinfo import ZoneInfo
import pytz



views = Blueprint('views',__name__)



@views.route('/')
@login_required
def home():
    # Fetch the 2 most recent workspaces
    recent_workspaces = Workspace.query.order_by(Workspace.id.desc()).limit(2).all()

    # Fetch the 2 most recent bookings for the current user
    recent_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.date.desc()).limit(2).all()

    return render_template(
        "dashboard.html",
        user=current_user,
        recent_workspaces=recent_workspaces,
        recent_bookings=recent_bookings
    )



@views.route('/workspace')
@login_required
def list_workspace():
    # Fetch all workspaces
    workspaces = Workspace.query.all()

    # Fetch all reserved workspaces
    reserved_workspace_ids = {booking.workspace_id for booking in Booking.query.all()}

    # Annotate workspaces with reservation status
    workspace_data = [
        {
            "id": workspace.id,
            "name": workspace.name,
            "capacity": workspace.capacity,
            "amenities": workspace.amenities,
            "reserved": False
        }
        for workspace in workspaces
    ]

    return render_template("workspace-list.html", user=current_user, workspaces=workspace_data)

from datetime import datetime

@views.route("/api/bookings/<int:workspace_id>")
@login_required
def get_workspace_bookings(workspace_id):
    date_str = request.args.get('date')
    schedule = []

    if date_str:
        # Filter for the modal use case
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        day_name = selected_date.strftime('%A')  # e.g., 'Monday'

        # Bookings on selected date
        bookings = Booking.query.filter_by(workspace_id=workspace_id, date=selected_date).all()
        for b in bookings:
            schedule.append({
                "date": b.date.strftime('%Y-%m-%d'),
                "start_time": b.start_time.strftime('%H:%M'),
                "end_time": b.end_time.strftime('%H:%M'),
                "type": "Booking"
            })

        # Class routines that occur on this weekday
        routines = ClassRoutine.query.filter_by(room_id=workspace_id, day=day_name).all()
        seen_classes = set()
        for r in routines:
            key = (r.day, r.start_time, r.end_time, r.subject, r.division)
            if key in seen_classes:
                continue
            seen_classes.add(key)
            schedule.append({
                "date": date_str,
                "start_time": r.start_time.strftime('%H:%M'),
                "end_time": r.end_time.strftime('%H:%M'),
                "type": f"Class ({r.subject}) - {r.division}"
            })

    else:
        # No date passed — return everything for the view schedule page
        bookings = Booking.query.filter_by(workspace_id=workspace_id).all()
        for b in bookings:
            schedule.append({
                "date": b.date.strftime('%Y-%m-%d'),
                "start_time": b.start_time.strftime('%H:%M'),
                "end_time": b.end_time.strftime('%H:%M'),
                "type": "Booking"
            })

        routines = ClassRoutine.query.filter_by(room_id=workspace_id).all()
        seen_classes = set()
        for r in routines:
            key = (r.day, r.start_time, r.end_time, r.subject, r.division)
            if key in seen_classes:
                continue
            seen_classes.add(key)
            schedule.append({
                "day": r.day,
                "start_time": r.start_time.strftime('%H:%M'),
                "end_time": r.end_time.strftime('%H:%M'),
                "type": f"Class ({r.subject}) - {r.division}"
            })

    return jsonify(schedule)


@views.route('/details/<int:id>')
@login_required
def workspace_details(id):
    # Fetch workspace details
    workspace = Workspace.query.get_or_404(id)

    # Check if reserved
    is_reserved = Booking.query.filter_by(workspace_id=id).first() is not None

    return render_template("workspace-details.html", user=current_user, workspace=workspace, reserved=is_reserved)



@views.route('/setting')
@login_required
def setting():
  return render_template("settings.html", user = current_user)


from datetime import datetime ,date



def get_weekday_dates(day_name, months=6):
    today = date.today()
    weekday_target = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'].index(day_name)
    end_date = today + timedelta(days=30 * months)

    current = today
    results = []
    while current <= end_date:
        if current.weekday() == weekday_target:
            results.append(current)
        current += timedelta(days=1)
    return results


@views.route('/reserve', methods=['POST'])
@login_required
def reserve_workspace():
    workspace_id = request.form.get('workspace_id')
    booking_date_str = request.form.get('date')
    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    details = request.form.get('details')

    # Parse date and time
    try:
        booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
    except ValueError:
        flash('Invalid date or time format.', category='error')
        return redirect(url_for('views.workspace_details', id=workspace_id))

    # Convert to datetime objects for validation
    start_dt = datetime.combine(booking_date, start_time)
    end_dt = datetime.combine(booking_date, end_time)

    # Validate time range
    allowed_start = time(8, 0)
    allowed_end = time(17, 0)

    if start_time < allowed_start or end_time > allowed_end:
        flash('Bookings must be between 08:00 AM and 05:00 PM.', category='error')
        return redirect(url_for('views.workspace_details', id=workspace_id))

    # Validate duration
    duration = end_dt - start_dt
    if duration < timedelta(minutes=45) or duration > timedelta(hours=4):
        flash('Booking must be at least 45 minutes and at most 4 hours.', category='error')
        return redirect(url_for('views.workspace_details', id=workspace_id))

    # Check for booking conflicts
    booking_conflict = Booking.query.filter_by(workspace_id=workspace_id, date=booking_date).filter(
        Booking.start_time < end_time,
        Booking.end_time > start_time
    ).first()

    # Convert booking_date to weekday string (e.g., 'Monday')
    day_of_week = booking_date.strftime('%A')

    # Check for class routine conflicts
    class_conflict = ClassRoutine.query.filter_by(room_id=workspace_id, day=day_of_week).filter(
        ClassRoutine.start_time < end_time,
        ClassRoutine.end_time > start_time
    ).first()

    if booking_conflict or class_conflict:
        flash('The workspace is unavailable for the selected time slot.', category='error')
        return redirect(url_for('views.workspace_details', id=workspace_id))


    if class_conflict:
        flash('The workspace is already booked for the selected time slot.', category='error')
        return redirect(url_for('views.workspace_details', id=workspace_id))

    # Save booking
    new_booking = Booking(
        user_id=current_user.id,
        workspace_id=workspace_id,
        date=booking_date,
        start_time=start_time,
        end_time=end_time
    )
    db.session.add(new_booking)
    db.session.commit()
    print("Form values:", workspace_id, booking_date_str, start_time_str, end_time_str, details)

    workspace = Workspace.query.get(workspace_id)

    # Notify user
    notification_message = f"Your booking for {workspace.name} on {booking_date} from {start_time} to {end_time} has been confirmed."
    notification = Notification(user_id=current_user.id, message=notification_message)
    db.session.add(notification)

    # Notify admin
    admin = User.query.filter_by(email="Admin1@gmail.com").first()
    if admin:
        action_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime('%d %b %Y at %I:%M %p')
        admin_msg = f"[ADMIN ALERT] {current_user.first_name} has reserved workspace '{workspace.name}' for {booking_date.strftime('%d %b %Y')} at {action_time}."
        db.session.add(Notification(user_id=admin.id, message=admin_msg))

    db.session.commit()
    return redirect(url_for('views.bookings'))


@views.route('/cancel', methods=['POST'])
@login_required
def cancel_booking():
    booking_id = request.form.get('booking_id')

    # Find the booking
    booking = Booking.query.get(booking_id)
    if not booking or booking.user_id != current_user.id:
        flash('Booking not found or unauthorized.', category='error')
        return redirect(url_for('views.bookings'))

    # Validate workspace existence
    workspace = Workspace.query.get(booking.workspace_id)
    if not workspace:
        flash('Workspace associated with the booking not found.', category='error')
        return redirect(url_for('views.bookings'))

    # Delete booking
    db.session.delete(booking)
    db.session.commit()

    # Add notification
    notification_message = f"Your booking for {workspace.name} on {booking.date} has been canceled."
    notification = Notification(user_id=current_user.id, message=notification_message)
    db.session.add(notification)
    db.session.commit()
    
    admin = User.query.filter_by(email="Admin1@gmail.com").first()
    if admin:
        action_time = datetime.now(ZoneInfo("Asia/Kolkata")).strftime('%d %b %Y at %I:%M %p')
        admin_msg = f"[ADMIN ALERT] {current_user.first_name} has canceled their booking for workspace '{workspace.name}' scheduled on {booking.date.strftime('%d %b %Y')} at {action_time}."
        print("Admin message:", admin_msg)

        db.session.add(Notification(user_id=admin.id, message=admin_msg))
        db.session.commit()

    return redirect(url_for('views.bookings'))


@views.route('/notification')
@login_required
def notification():
    keyword = request.args.get('keyword', '').lower()
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    
    # Use ZoneInfo to convert to IST (Indian Standard Time)
    ist = ZoneInfo("Asia/Kolkata")
    
    for notification in notifications:
        if notification.timestamp:
            # Check if the timestamp is naive (without timezone)
            if notification.timestamp.tzinfo is None:
                # If naive, set it to UTC (assuming the timestamp is in UTC)
                notification.timestamp = notification.timestamp.replace(tzinfo=ZoneInfo("UTC"))
            
            # Convert to IST
            notification.timestamp = notification.timestamp.astimezone(ist)

    # Apply the keyword filter if provided
    if keyword:
        notifications = [n for n in notifications if keyword in n.message.lower()]

    return render_template("notifications.html", user=current_user, notifications=notifications, keyword=keyword)

@views.route('/bookings')
@login_required
def bookings():
    # Get all bookings for the current user, ordered by date
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.date.desc()).all()
    return render_template("my-bookings.html", user=current_user, bookings=bookings)

@views.route('/add-workspace', methods=['GET', 'POST'])
@login_required
def add_workspace():
    if request.method == 'POST':
        name = request.form['name']
        capacity = request.form['capacity']
        floor = request.form['floor']
        amenities = request.form['amenities']
        
        # Create and add workspace
        new_workspace = Workspace(name=name, capacity=capacity, floor=floor, amenities=amenities)
        db.session.add(new_workspace)
        db.session.commit()

        # Create notification (optional)
        message = f"Workspace '{name}' added."
        notify = Notification(message=message, user_id=current_user.id)
        db.session.add(notify)
        db.session.commit()

        flash("Workspace added successfully!", "success")
        return redirect('/add-workspace')

    # For GET request
    workspaces = Workspace.query.all()
    return render_template("add-workspace.html", workspaces=workspaces)

@views.route('/delete-workspace/<int:workspace_id>', methods=['POST'])
@login_required
def delete_workspace(workspace_id):
    workspace = Workspace.query.get_or_404(workspace_id)
    db.session.delete(workspace)
    db.session.commit()
    flash('Workspace deleted successfully.', 'success')
    return redirect('/add-workspace')


@views.route('/work')
@login_required
def work():
    workspaces = Workspace.query.all()
    return render_template("add-workspace.html",  workspaces=workspaces, user = current_user)

@views.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # Validate and update user information
        if username:
            current_user.first_name = username
        if email:
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != current_user.id:
                flash('Email is already taken.', category='error')
                return redirect(url_for('views.profile'))
            current_user.email = email
        if password:
            if len(password) < 7:
                flash('Password must be at least 7 characters long.', category='error')
                return redirect(url_for('views.profile'))
            current_user.password = generate_password_hash(password, method='pbkdf2:sha256')

        # Save changes to the database
        db.session.commit()
        flash('Profile updated successfully!', category='success')
        return redirect(url_for('views.profile'))

    return render_template('profile.html', user=current_user)
  
@views.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    try:
        # Delete all bookings made by the user
        Booking.query.filter_by(user_id=current_user.id).delete()

        # Delete all notifications related to the user
        Notification.query.filter_by(user_id=current_user.id).delete()

        # Delete the user account
        db.session.delete(current_user)
        db.session.commit()

        flash('Your account and all associated data have been deleted.', category='success')
        return redirect(url_for('auth.login'))
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting your account. Please try again.', category='error')
        return redirect(url_for('views.settings'))



@views.route('/class-routine', methods=['GET', 'POST'])
@login_required
def class_routine():
    time_slots = {
        "Slot 1": (time(8, 45), time(10, 25)),
        "Slot 2": (time(10, 50), time(12, 40)),
        "Slot 3": (time(13, 40), time(15, 30))
    }

    if request.method == 'POST':
        day = request.form['day']
        division = request.form['division']
        success_rooms = []

        for slot_name in ["Slot 1", "Slot 2", "Slot 3"]:
            split = request.form.get(f'split_{slot_name}', '') == 'on'
            capacity = int(request.form.get(f'capacity_{slot_name}', 0))
            subjects = [request.form.get(f'subject_{slot_name}_1')]
            if split:
                subjects.append(request.form.get(f'subject_{slot_name}_2'))

            start, end = time_slots[slot_name]
            times = [(start, end)]
            if split:
                mid = (datetime.combine(datetime.today(), start) +
                    (datetime.combine(datetime.today(), end) - datetime.combine(datetime.today(), start)) / 2).time()
                times = [(start, mid), (mid, end)]

            for i, (start_time, end_time) in enumerate(times):
                assigned_room = None
                for ws in Workspace.query.all():
                    if ws.capacity < capacity:
                        continue
                    conflict = ClassRoutine.query.filter_by(day=day, room_id=ws.id).filter(
                        ClassRoutine.start_time < end_time,
                        ClassRoutine.end_time > start_time
                    ).first()

                    if not conflict:
                        assigned_room = ws
                        break
                if not assigned_room:
                    flash(f"No available room for {slot_name} Period {i+1}", category='error')
                    return redirect(url_for('views.class_routine'))

                for routine_date in get_weekday_dates(day):
                    routine = ClassRoutine(
                        user_id=current_user.id,
                        division=division,
                        day=day,
                        time_slot=slot_name,
                        period_number=i + 1,  # Period 1 or 2
                        subject=subjects[i],
                        start_time=start_time,
                        end_time=end_time,
                        room_id=assigned_room.id,
                        timestamp=routine_date
                    )
                    db.session.add(routine)
                
                success_rooms.append(f"{slot_name} P{i+1}: {assigned_room.name}")

        db.session.commit()

        admin = User.query.filter_by(email="Admin1@gmail.com").first()
        if admin:
            admin_msg = f"[ADMIN ALERT] {current_user.first_name} assigned class rooms for {division} on {day}."
            notification = Notification(user_id=admin.id, message=admin_msg)
            db.session.add(notification)
            db.session.commit()

        flash("Rooms assigned: " + "; ".join(success_rooms), category='success')
        return redirect(url_for('views.class_routine'))

    # Query to get all routines (no deduplication)
    all_routines = (
        db.session.query(ClassRoutine)
        .filter(ClassRoutine.period_number.in_([1, 2]))  # Ensure both periods are included
        .order_by(ClassRoutine.day, ClassRoutine.time_slot, ClassRoutine.division, ClassRoutine.period_number)
        .all()
    )
    # Deduplicate: group by (day, division, slot) and keep only one
    unique_routines = {}
    for r in all_routines:
        key = (r.day, r.division, r.period_number,r.time_slot)
        if key not in unique_routines:
            unique_routines[key] = r

    routines = list(unique_routines.values())

    

    return render_template('class-routine.html', user=current_user, routines=routines)


   
   
@views.route('/api/floor-rooms')
@login_required
def get_floor_rooms():
    floor = request.args.get('floor', type=int)
    if floor is None:
        return jsonify([])

    rooms = Workspace.query.filter_by(floor=floor).all()
    room_list = []
    for r in rooms:
        room_list.append({
            'id': r.id,
            'name': r.name,
            'x': r.x or 100,  # default positions if null
            'y': r.y or 100,
            'reserved': r.reserved
        })

    return jsonify(room_list)


@views.route('/api/add-room', methods=['POST'])
@login_required
def add_room():
    if current_user.role != 'admin':
        return jsonify({"error": "Unauthorized"}), 403

    name = request.form.get('name')
    capacity = request.form.get('capacity')
    location = request.form.get('location')
    x = request.form.get('x')
    y = request.form.get('y')
    floor = request.form.get('floor')

    if not all([name, capacity, location, x, y, floor]):
        return jsonify({"error": "Incomplete data"}), 400

    new_workspace = Workspace(
        name=name,
        capacity=int(capacity),
        amenities='N/A',
        location=location,
        floor=int(floor),
        x=int(x),
        y=int(y)
    )
    db.session.add(new_workspace)
    db.session.commit()
    return jsonify({"success": True})

@views.route('/floormap')
@login_required
def floormap():
    return render_template('floormap.html', user=current_user)


@views.route('/api/update-room-positions', methods=['POST'])
@login_required
def update_room_positions():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json()
    positions = data.get('positions', [])

    for pos in positions:
        room = Workspace.query.get(pos['id'])
        if room:
            room.x = int(pos['x'])
            room.y = int(pos['y'])

    db.session.commit()
    return jsonify({'message': 'Positions updated successfully'})
