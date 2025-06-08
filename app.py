from flask import Flask, flash, redirect, render_template, request, url_for, session
from werkzeug.security import check_password_hash # BUAT CEK PASSWORD YANG DIMASUKIN PAS LOGIN SAMA GA AMA YANG ADA DIDATABASE TANPA NGELIAT PASSWORD ASLINYA
from functools import wraps # BUAT DECORATOR
from config import Config 
import os # SUPAYA BISA BUAT FOLDER 
from datetime import date, datetime, timedelta # BUAT TANGGAL DAN WAKTU
from werkzeug.utils import secure_filename # BUAT NAMA FILE YANG AMAN SAAT UPLOAD
from abc import ABC, abstractmethod 
from admin_routes import AdminRoutes 
from guru_routes import GuruRoutes
from murid_routes import MuridRoutes

def cek_file(nama_file, ekstensi_file): # FUNGSI BUAT CEK FILE YANG DIUPLOAD PUNYA EXTENSION YANG DIIZINKAN
    return '.' in nama_file and \
           nama_file.rsplit('.', 1)[1].lower() in ekstensi_file

class BaseFlaskApplication:
    def __init__(self, app_name):
        self._flask_app = Flask(app_name)
        self._app_name = app_name

    def get_flask_instance(self): # GETTER
        return self._flask_app

    def application_greeting(self): # SALAM (BUAT DIOVERRIDE) 
        return f"Selamat datang diaplikasi {self._app_name}!"

    @abstractmethod 
    def run(self):
        self.app.run(debug=True)

class Portal(BaseFlaskApplication): # TURUNAN DARI CLASS BaseFlaskApplication
    def __init__(self):
        super().__init__(__name__) 
        self.app = self.get_flask_instance() 
        self.app.secret_key = 'ganti_dengan_kunci_rahasia_yang_kuat_dan_unik_98765!'
        self.con = Config() 
        self._atur_file() # UNTUK MENGATUR LOKASI FOLDER UPLOAD DAN ALLOWED EXTENSIONS
        self._variabel_bawaan() # BUAT VARIABEL BAWAAAN YANG AKAN DIGUNAKAN DI TEMPLATE
        admin_router = AdminRoutes(self.app, self.con, self.admin_login_required, cek_file)
        admin_router.register_routes()
        guru_router = GuruRoutes(self.app, self.con, self.guru_login_required, self._cek_guru_pembina_ekskul, cek_file)
        guru_router.register_routes()
        murid_router = MuridRoutes(self.app, self.con, self.murid_login_required)
        murid_router.register_routes()
        self.routes()


    def application_greeting(self): 
        base_greeting = super().application_greeting() 
        return f"Selamat Datang di Portal Ekstrakurikuler Sekolah!"

    def _atur_file(self):
        self.app.config['UPLOAD_FOLDER'] = os.path.join(self.app.root_path, 'static/uploads/materi_ekskul')
        self.app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}
        self.app.config['LOGO_UPLOAD_FOLDER'] = os.path.join(self.app.root_path, 'static/uploads/logos')
        self.app.config['ALLOWED_LOGO_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
        if not os.path.exists(self.app.config['LOGO_UPLOAD_FOLDER']):
            os.makedirs(self.app.config['LOGO_UPLOAD_FOLDER'], exist_ok=True)

    def _variabel_bawaan(self):
        @self.app.context_processor
        def info_waktu():
            from datetime import datetime
            return {'now': datetime.now()}

    def _login_required_for_role(self, target_role, message): # BUAT DECORATOR LOGIN SESUAI ROLE
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if 'user_id' not in session:
                    flash('Anda harus login untuk mengakses halaman ini.', 'warning')
                    return redirect(url_for('login'))
                if session.get('peran') != target_role:
                    flash(message, 'danger')
                    current_user_role = session.get('peran')
                    if current_user_role == 'admin': return redirect(url_for('dashboard_admin'))
                    if current_user_role == 'guru': return redirect(url_for('dashboard_guru'))
                    if current_user_role == 'murid': return redirect(url_for('dashboard_murid'))
                    return redirect(url_for('login'))
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    def admin_login_required(self, f):
        return self._login_required_for_role('admin', 'Hanya admin yang dapat mengakses halaman ini.')(f)

    def guru_login_required(self, f):
        return self._login_required_for_role('guru', 'Hanya guru yang dapat mengakses halaman ini.')(f)

    def murid_login_required(self, f):
        return self._login_required_for_role('murid', 'Hanya murid yang dapat mengakses halaman ini.')(f)
    
    def _cek_guru_pembina_ekskul(self, cek_id_ekskul): # CEK APAKAH GURU YANG LOGIN PEMBINA EKSKUL APA
        guru_id_session = session.get('user_id')
        ekskul = self.con.get_ekskul_by_id(cek_id_ekskul) 
        if not ekskul:
            flash(f"Ekstrakurikuler dengan ID {cek_id_ekskul} tidak ditemukan.", "danger")
            return False, None 
        if ekskul.get('id_guru_pembina') != guru_id_session:
            flash("Anda tidak memiliki akses untuk mengelola ekskul tersebut.", "danger")
            return False, ekskul 
        return True, ekskul

    def routes(self):
        @self.app.route('/')
        def index(): # KE DASHBOARD MASING-MASING SETELAH LOGIN
            if 'user_id' in session:
                peran = session.get('peran')
                if peran == 'admin':
                    return redirect(url_for('dashboard_admin'))
                elif peran == 'guru':
                    return redirect(url_for('dashboard_guru'))
                elif peran == 'murid':
                    return redirect(url_for('dashboard_murid'))
                else:
                    session.clear()
            return redirect(url_for('login')) 

        @self.app.route('/testdb')
        def test_db(): # CEK NYAMBUNG AMA DATABASE ATAU TIDAK
            try:
                if self.con.check_db_connection(): 
                    return "Koneksi database berhasil!"
                else:
                    return "Koneksi database gagal."
            except Exception as e:
                return f"Error saat mencoba koneksi database: {e}"

        @self.app.route('/login', methods=['GET', 'POST'])
        def login(): # HALAMAN LOGIN
            if 'user_id' in session:
                peran = session.get('peran')
                if peran == 'admin': return redirect(url_for('dashboard_admin'))
                if peran == 'guru': return redirect(url_for('dashboard_guru'))
                if peran == 'murid': return redirect(url_for('dashboard_murid'))
            
            if request.method == 'POST': # BUAT LOGIN PAKE USERNAME DAN PASSWORD
                username = request.form['username']
                password = request.form['password']
                user = self.con.get_user_by_username(username)
                if user and user.get('password_hash') and check_password_hash(user['password_hash'], password):
                    if not user.get('status_aktif', False): 
                        flash('Akun Anda tidak aktif. Silakan hubungi admin.', 'warning')
                        return redirect(url_for('login'))
                    
                    session['user_id'] = user['id_pengguna']
                    session['username'] = user['username']
                    session['nama_lengkap'] = user['nama_lengkap']
                    session['peran'] = user['peran']
                    session.permanent = False
                    flash(f"Login berhasil! Selamat datang, {user['nama_lengkap']}.", 'success')
                    if user['peran'] == 'admin': return redirect(url_for('dashboard_admin'))
                    if user['peran'] == 'guru': return redirect(url_for('dashboard_guru'))
                    if user['peran'] == 'murid': return redirect(url_for('dashboard_murid'))
                    flash('Peran pengguna tidak dikenal setelah login.', 'danger')
                    session.clear()
                else:
                    flash('Username atau password salah.', 'danger')
            return render_template('login.html')

        @self.app.route('/logout') # BUAT LOGOUT
        def logout():
            session.clear()
            flash('Anda telah berhasil logout.', 'info')
            return redirect(url_for('login'))

    def run(self):
        self.app.run(debug=True) 

if __name__ == "__main__":
    portal = Portal()
    portal.run()