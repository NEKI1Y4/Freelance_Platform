from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admin',
    'database': 'freelance_platform'
}

def get_unread_count(user_id):
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM notifications WHERE user_id = %s AND is_read = 0", (user_id,))
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return count
@app.route('/', methods=['GET'])
def home():
    username = session.get('username')
    return render_template('home.html', username=username)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role_id = request.form.get('role_id')  # <-- добавлено получение role_id из формы
        password_hash = generate_password_hash(password)
        try:
            conn = mysql.connector.connect(**db_config)
            cursor = conn.cursor()
            # теперь сохраняем и role_id
            cursor.execute(
                "INSERT INTO users (username, email, password, role_id) VALUES (%s, %s, %s, %s)",
                (username, email, password_hash, role_id)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Регистрация прошла успешно! Теперь войдите.')
            return redirect(url_for('login'))
        except mysql.connector.Error as e:
            flash('Ошибка регистрации: ' + str(e))
            return render_template('form.html')
    # Передаём roles для формы регистрации (если хочешь динамическое отображение ролей)
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM roles")
    roles = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('form.html', roles=roles)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Вы успешно вошли!')
            return redirect(url_for('home'))
        else:
            flash('Неверное имя пользователя или пароль')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    # Проверить, есть ли уже портфолио для этого пользователя
    cursor.execute("SELECT * FROM portfolios WHERE user_id = %s", (user_id,))
    portfolio = cursor.fetchone()

    # Если нет портфолио — создать пустое
    if not portfolio:
        cursor.execute(
            "INSERT INTO portfolios (user_id, otchestvo, city, gender, birthdate, about) VALUES (%s, '', '', '', NULL, '')",
            (user_id,))
        conn.commit()
        cursor.execute("SELECT * FROM portfolios WHERE user_id = %s", (user_id,))
        portfolio = cursor.fetchone()

    # Обновление профиля
    if request.method == 'POST':
        if request.form.get('form_type') == 'profile':
            otchestvo = request.form.get('otchestvo', '')
            city = request.form.get('city', '')
            gender = request.form.get('gender', '')
            birthdate = request.form.get('birthdate', None)
            cursor.execute(
                "UPDATE portfolios SET otchestvo=%s, city=%s, gender=%s, birthdate=%s WHERE user_id=%s",
                (otchestvo, city, gender, birthdate, user_id)
            )
            conn.commit()
        elif request.form.get('form_type') == 'about':
            about = request.form.get('about', '')
            cursor.execute(
                "UPDATE portfolios SET about=%s WHERE user_id=%s",
                (about, user_id)
            )
            conn.commit()
        # Перечитать обновлённые данные
        cursor.execute("SELECT * FROM portfolios WHERE user_id = %s", (user_id,))
        portfolio = cursor.fetchone()
        flash('Изменения сохранены!')
        return redirect(url_for('dashboard'))

    # Получить email из users
    cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    email = user['email'] if user else ''

    cursor.close()
    conn.close()

    return render_template(
        'dashboard.html',
        username=session.get('username', ''),
        email=email,
        otchestvo=portfolio.get('otchestvo', ''),
        city=portfolio.get('city', ''),
        gender=portfolio.get('gender', ''),
        birthdate=portfolio.get('birthdate', ''),
        about=portfolio.get('about', ''),
    )

@app.route('/employer', methods=['GET', 'POST'])
def employer():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    employer_id = session['user_id']

    # Сохраняем вакансию в БД
    if request.method == 'POST' and request.form.get('form_type') == 'create_resume':
        full_name = request.form.get('full_name', '')
        position = request.form.get('position', '')
        description = request.form.get('description', '')
        experience = request.form.get('experience', '')
        skills = request.form.get('skills', '')
        phone = request.form.get('phone', '')
        email = request.form.get('email', '')
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO orders (full_name, position, description, experience, skills, phone, email, employer_id, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (full_name, position, description, experience, skills, phone, email, employer_id, created_at)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash('Вакансия успешно создана!')
        return redirect(url_for('employer'))

    # Получаем все вакансии от этого работодателя
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM orders WHERE employer_id = %s ORDER BY created_at DESC", (employer_id,))
    resumes = cursor.fetchall()

    # Получаем все уведомления для работодателя
    cursor.execute(
        "SELECT * FROM notifications WHERE user_id = %s AND is_read = 0 ORDER BY created_at DESC",
        (employer_id,)
    )
    notifications = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('employer.html', notifications=notifications, resumes=resumes)

@app.route('/notification/read/<int:notif_id>', methods=['POST'])
def read_notification(notif_id):
    employer_id = session.get('user_id')
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE notifications SET is_read = 1 WHERE id = %s AND user_id = %s",
        (notif_id, employer_id)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(request.referrer or url_for('employer'))
@app.route('/worker')
def worker():
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.*, u.username AS employer_name
        FROM orders o
        JOIN users u ON o.employer_id = u.id
        ORDER BY o.created_at DESC
    """)
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('worker.html', orders=orders)

@app.route('/respond_order', methods=['POST'])
def respond_order():
    order_id = request.form.get('order_id')
    user_id = session.get('user_id')  # Предполагается, что пользователь авторизован

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    try:
        # Сохрани отклик в БД
        cursor.execute(
            "INSERT INTO responses (order_id, worker_id) VALUES (%s, %s)",
            (order_id, user_id)
        )
        # Получаем работодателя для заказа
        cursor.execute("SELECT employer_id FROM orders WHERE id = %s", (order_id,))
        employer_id = cursor.fetchone()[0]
        # Добавляем уведомление
        notif_text = "На ваш заказ поступил новый отклик!"
        cursor.execute(
            "INSERT INTO notifications (user_id, message, is_read) VALUES (%s, %s, 0)",
            (employer_id, notif_text)
        )
        conn.commit()
        flash("Вы успешно откликнулись на заказ!", "success")
    except Exception as e:
        flash(f"Ошибка отклика: {e}", "danger")
    finally:
        cursor.close()
        conn.close()
    return redirect(request.referrer or url_for('worker'))

@app.route('/admin')
def admin_panel():
    if session.get('username') != 'admin':
        flash('Нет доступа')
        return redirect(url_for('home'))

    search = request.args.get('search', '')
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)

    if search:
        cursor.execute("SELECT * FROM users WHERE username LIKE %s", (f"%{search}%",))
    else:
        cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    cursor.execute("SELECT * FROM orders")
    orders = cursor.fetchall()

    cursor.execute("SELECT * FROM responses")
    responses = cursor.fetchall()

    cursor.close()
    conn.close()
    unread_count = get_unread_count(session['user_id'])

    return render_template('admin_panel.html', users=users, orders=orders, responses=responses, unread_count=unread_count)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if session.get('username') != 'admin':
        flash('Нет доступа')
        return redirect(url_for('home'))
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Пользователь удалён!')
    return redirect(url_for('admin_panel'))

@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
def admin_edit_user(user_id):
    if session.get('username') != 'admin':
        flash('Нет доступа')
        return redirect(url_for('home'))
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role_id = request.form.get('role_id')
        cursor.execute(
            "UPDATE users SET username=%s, email=%s, role_id=%s WHERE id=%s",
            (username, email, role_id, user_id)
        )
        conn.commit()
        flash('Данные пользователя обновлены!')
        cursor.close()
        conn.close()
        return redirect(url_for('admin_panel'))
    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    unread_count = get_unread_count(session['user_id'])
    return render_template('admin_edit_user.html', user=user, unread_count=unread_count)




@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из аккаунта.')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)