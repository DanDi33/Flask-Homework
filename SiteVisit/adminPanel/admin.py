import os
from PIL import Image

import flask
from flask import Blueprint, render_template, redirect, url_for, flash, session, g, json, make_response
import sqlite3

from werkzeug.utils import secure_filename

from SiteVisit.adminPanel.useful.forms import ProfileForm

admin = Blueprint('adminPanel', __name__, template_folder='templates', static_folder='static')
menu = [{"url": ".index", "title": "Панель"}, {"url": "authorize.logout", "title": "Выйти"}]

db = None


@admin.before_request
def before_request():
    # Подключение к базе. Присваиваем db link_db
    global db
    db = g.get("link_db")


@admin.teardown_request
def teardown_request(request):
    global db
    db = None
    return request


@admin.route("/", methods=["POST", "GET"])
@admin.route("/profile", methods=["POST", "GET"])
def index():
    social_in = []

    if not isLogged():
        return redirect(url_for('authorize.login'))

    profile = select_user(session['name'])

    if profile is None:
        print(f"Профиль {session['name']} - не найден")
        return redirect(url_for('authorize.login'))

    social_out = json.loads(profile['social'])
    form = ProfileForm()

    if form.validate_on_submit():
        for i in range(6):
            if form[f'logo{i + 1}'].data != 'None' and form[f'url{i + 1}'].data != 'None':
                social_in.append({'log_num': form[f'logo{i + 1}'].name, 'name': form[f'logo{i + 1}'].data,
                                  'name_url': form[f'url{i + 1}'].name, 'url': form[f'url{i + 1}'].data})
        print(form.avatar.type)
        print(form.avatar)
        print(form.avatar.name)
        print(form.avatar.data)
        print(profile['id'])
        file = form.avatar.data
        upload_avatar(file, profile['id'])
        image = form.avatar.data
        filename = secure_filename(image)
        os.makedirs(flask.current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        im = Image.open(image)
        im_new = crop_max_square(im)
        im_new.save(os.path.join(flask.current_app.config['UPLOAD_FOLDER'], filename), quality=95)

        # ima = Image.open(image)
        # im_new = crop_max_square(ima)
        # im_new.save(os.path.join(flask.current_app.config['UPLOAD_FOLDER'], '111.jpg'), quality=95)

        if db:
            try:
                cur = db.cursor()
                cur.execute(f"UPDATE profiles SET 'name' = ?, "
                            f"'surname' = ?, "
                            f"'phone' = ?, "
                            f"'profession' = ?, "
                            f"'about' = ?, "
                            f"'social' = ? "
                            f"WHERE id LIKE ?;", (form.name.data,
                                                  form.surname.data,
                                                  form.phone.data,
                                                  form.profession.data,
                                                  form.about.data,
                                                  json.dumps(social_in),
                                                  session['id']))
                db.commit()
                return redirect(url_for('adminPanel.index'))
            except sqlite3.Error as e:
                flash("Ошибка при добавлении в БД", category="error")
                print("Ошибка добавления в БД" + str(e))

    return render_template("adminPanel/profile.html", title="Главная", menu=menu,
                           profile=profile, form=form, social=social_out)


def select_user(user_name):
    # Функция из БД возвращает профиль по логину(user_name)
    # При обращении к функции, возьми name из session (session['name])
    if db:
        try:
            cur = db.cursor()
            cur.execute(f'SELECT * FROM profiles WHERE user_name = "{user_name}" LIMIT 1')
            profile = cur.fetchall()[0]
            if not profile:
                print(f"Профиль {user_name} - не найден (adminPanel/admin.py def select_user).")
                return None
        except sqlite3.Error as e:
            print(f'Ошибка при запросе к БД -  (adminPanel/admin.py def select_user). {e}')
            return None
        print(f"Данные профиля {user_name} успешно выгружены. (adminPanel/admin.py def select_user).")
        return profile
    print(f"Ошибка подключения к БД. db - False (adminPanel/admin.py def select_user).")
    return None


def upload_avatar(file, person_id):
    if file:
        try:
            with open(file, "rb") as f:
                img = f.read()
            res = update_user_avatar(img, person_id)
            if not res:
                flash("Ошибка обновления аватара", "error")
                return redirect(url_for("adminPanel.index"))
            flash("Аватар обновлен", "success")
        except FileNotFoundError as e:
            print(f"Ошибка чтения файла ({file}). {e} (adminPanel/admin.py def upload_avatar).")
            flash("Ошибка чтения файла", "error")
    else:
        print(f"{file} - файл не найден. (adminPanel/admin.py def upload_avatar).")
        flash("Ошибка чтения файла", "error")
    return redirect(url_for("adminPanel.index"))


def update_user_avatar(img, user_id):
    if not img:
        return False
    if not db:
        print(f"Ошибка подключения к БД.db - False (adminPanel/admin.py def update_user_avatar).")
        return False
    try:
        binary = sqlite3.Binary(img)
        cur = db.cursor()
        cur.execute(f"UPDATE profiles SET avatar = ? WHERE id = ?", (binary, user_id))
        db.commit()
    except sqlite3.Error as e:
        print(f"Ошибка обновления аватара. (adminPanel/admin.py def update_user_avatar). {e}")
        return False
    return True


@admin.route("/userava")
def userava():
    print("user_ava")
    profile = select_user(session['name'])
    img = profile['avatar']
    if not img:
        return ""
    answer = make_response(img)
    answer.headers["Content-Type"] = "image/png"
    return answer


def crop_center(pil_img, crop_width: int, crop_height: int) -> Image:
    """
    Функция для обрезки изображения по центру.
    """
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))


def crop_max_square(pil_img):
    return crop_center(pil_img, min(pil_img.size), min(pil_img.size))


def isLogged():
    return True if session.get('name') else False
