import os, sched, time
import datetime as dt
from flask import render_template, redirect, url_for, flash, jsonify, request
from flask_security import current_user, login_user, login_required, logout_user


from src.extentions.database import db
from src.extentions.userstore import user_datastore
from src.models.forms import LoginForm, SignupForm, ProductForm, InventoryForm
from src.models.entities import User, Appointment

# Authentication functions


def register():
    registro = SignupForm()

    if registro.validate_on_submit():
        new_user = User(
            username=registro.username.data,
            email=registro.email.data, password=registro.password.data,
            firstName=registro.firstName.data,
            lastName=registro.lastName.data,
            number=registro.number.data,
        )
        db.session.add(new_user)
        db.session.commit()
        db.session.close()

        flash('Registro logrado exitosamente', "success")
        return render_template('regis_ success.html')
    return render_template('register.html', formi=registro)


def login():
    login = LoginForm()

    if login.validate_on_submit():
        username = login.username.data
        password = login.password.data
        user = User.get_by_user(username)
        if user and user.check_password(password):
            login_user(user, remember=True)
            return redirect(url_for('home.dash'))
        else:
            flash("Usuario o contraseña incorrecto", "danger")
            render_template('login.html', formi=login)

    return render_template('login.html', formi=login)

@login_required
def logout():
    logout_user()
    return redirect(url_for("home.index"))

# Private sites
@login_required
def dash():
    template_vars = {
        "title": "Barber - Dash",
        "state": "dash",
        "user": current_user,
        "av_data": availability(),
        "bu_data": get_appointments(),
    }
    return render_template('dash.html', **template_vars)

def availability():
    def clean_time(date):
        date_str=date.strftime('%Y-%m-%d %H:%M:%S')
        return dt.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

    def make_dates(now, weekday):
        WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"]
        
        diff = dt.timedelta(days=WEEKDAYS.index(weekday)-now.weekday())
        day = now + diff
        day = day.replace(hour=0, minute=0, second=0)
        start = 7
        stop = 20
        dates = [clean_time(day+dt.timedelta(hours=i)) for i in range(24)]
        filtered = []
        for i in range(len(dates)):
            if dates[i].hour < start or dates[i].hour > stop:
                pass
            elif dates[i] < now:
                pass
            else:
                filtered.append(dates[i])
        if filtered != []:
            filtered.pop(0)
        return filtered
    
    def make_week():
        WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"]
        days = {}
        pivot = now.weekday()
        for i in range(len(WEEKDAYS)):
            if i >= pivot:
                days[WEEKDAYS[i]] = True
            else:
                days[WEEKDAYS[i]] = []
        return days
    
    def make_day(days, now):
        for day in days.keys():
            if days[day]:
                days[day] = make_dates(now, day)
        return days

    def pop_dates(dates):
        WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday"]
        busy = Appointment.get_all()
        for appointment in busy:
            date = appointment.date
            day = WEEKDAYS[date.weekday()]
            if date in dates[day]:
                dates[day].remove(date)
        return dates
            
    now = dt.datetime.now().replace(minute=0, second=0)
    dates = make_day(make_week(), now)
    true_dates = pop_dates(dates)
    return true_dates

def get_appointments():
    def make_data(appointment: Appointment):
        user = User.get_by_id(appointment.id_user)
        data = {}
        data["id"] = appointment.id
        data["id_user"] = appointment.id_user
        data["service"] = appointment.name.split(":")[0]
        data["description"] = appointment.description
        data["value"] = appointment.value 
        data["date"] = appointment.date
        data["init_hour"] = appointment.init_hour
        data["end_hour"] = appointment.end_hour
        data["status"] = appointment.status
        data["fistName"] = user.firstName
        data["lastName"] = user.lastName
        return data

    id_user = current_user.id
    role = current_user.flag
    appointments = []
    query = None
    if role == "customer":
        query = Appointment.get_by_id_user(id_user)
    elif role == "admin":
        query = Appointment.get_all()
    
    if query:
        appointments = list(map(lambda obj: make_data(obj), query))
    return appointments

def set_appointment():
    date_str = request.form["hora"].split('.')[0]
    service = request.form["servicio"]
    name = f"{service}:{current_user.username}"
    date = dt.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
    appointment = Appointment(name, date)
    db.session.add(appointment)
    db.session.commit()
    db.session.close()
    return redirect(url_for("home.dash"))

def delete_appointment(appointment_id):
    deleted = Appointment.get_by_id(appointment_id)
    db.session.delete(deleted)
    db.session.commit()
    db.session.close()
    return redirect(url_for("home.dash"))

# Multi-threading funtions
def update_appointments_status(**args):
    app = args["app"]
    db = args["db"]
    import datetime as dt
    import sched, time
    def kill_appointments(db, app):
        appointments = Appointment.get_all()
        now = dt.datetime.now()
        with app.app_context():
            for appointment in appointments:
                date = appointment.date
                print(date < now)
                if date < now:
                    db.session.delete(appointment)
            db.session.commit()
            db.session.close()
        return

    kill_appointments(db, app)
    while True:
        try:
            now = dt.datetime.now().replace(minute=0, second=0)
            target_time = now + dt.timedelta(minutes=60)
            appoint_killer = sched.scheduler(time.localtime, time.sleep)
            appoint_killer.enterabs(target_time, 0, kill_db)
            time.sleep(5)
        except:
            break
    return -1

def test_daemon(*args):
    print(f"daemon entered-> {args}")
    return

# Public sites

def get_user_storage():
    return f"{user_datastore}"

def get_user():
    return current_user


def index():
    template_vars = {
        "title": "Barber",
        "statmmutableMultiDicte": "inicio",
        "is_log": current_user.is_authenticated
    }
    return render_template("index.html", **template_vars)


def salon():
    template_vars = {
        "title": "Barber - Salon",
        "state": "salon",
        "is_log": current_user.is_authenticated
    }
    return render_template("salon.html", **template_vars)