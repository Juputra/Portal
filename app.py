from flask import Flask, flash, redirect, render_template, request, url_for, session
from werkzeug.security import check_password_hash # generate_password_hash sekarang ada di Config
from functools import wraps
from config import Config # Mengimpor kelas Config dari file config.py Anda
import os
from datetime import date
from werkzeug.utils import secure_filename
from datetime import datetime
# import pdfkit # Belum digunakan

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

class Portal:
    def __init__(self):
        self.app = Flask(__name__)
        # GANTI KUNCI RAHASIA INI DENGAN YANG LEBIH AMAN DAN ACAK!
        self.app.secret_key = 'ganti_dengan_kunci_rahasia_yang_kuat_dan_unik_98765!' 
        self.con = Config() # Membuat instance dari Config Anda
        self.routes()
        self.app.config['UPLOAD_FOLDER'] = 'static/uploads/materi_ekskul' 
        self.app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}



    def _login_required_for_role(self, target_role, message):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if 'user_id' not in session:
                    flash('Anda harus login untuk mengakses halaman ini.', 'warning')
                    return redirect(url_for('login'))
                if session.get('peran') != target_role:
                    flash(message, 'danger')
                    # Redirect ke dashboard pengguna yang login jika salah peran, atau ke login
                    current_user_role = session.get('peran')
                    if current_user_role == 'admin': return redirect(url_for('dashboard_admin'))
                    if current_user_role == 'guru': return redirect(url_for('dashboard_guru'))
                    if current_user_role == 'murid': return redirect(url_for('dashboard_murid'))
                    return redirect(url_for('login')) # Fallback
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    def admin_login_required(self, f):
        return self._login_required_for_role('admin', 'Hanya admin yang dapat mengakses halaman ini.')(f)

    def guru_login_required(self, f):
        return self._login_required_for_role('guru', 'Hanya guru yang dapat mengakses halaman ini.')(f)

    def murid_login_required(self, f):
        return self._login_required_for_role('murid', 'Hanya murid yang dapat mengakses halaman ini.')(f)


    def routes(self):
        @self.app.route('/')
        def index():
            if 'user_id' in session:
                peran = session.get('peran')
                if peran == 'admin':
                    return redirect(url_for('dashboard_admin'))
                elif peran == 'guru':
                    return redirect(url_for('dashboard_guru'))
                elif peran == 'murid':
                    return redirect(url_for('dashboard_murid'))
                else:
                    session.clear() # Peran tidak valid, bersihkan sesi
            return redirect(url_for('login')) # Ke halaman login umum

        @self.app.route('/testdb')
        def test_db():
            try:
                if self.con.check_db_connection(): # Menggunakan metode dari Config
                    return "Koneksi database berhasil!"
                else:
                    return "Koneksi database gagal. Periksa log server atau konfigurasi."
            except Exception as e:
                return f"Error saat mencoba koneksi database: {e}"

        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if 'user_id' in session:
                # Jika sudah login, arahkan ke dashboard yang sesuai
                peran = session.get('peran')
                if peran == 'admin': return redirect(url_for('dashboard_admin'))
                if peran == 'guru': return redirect(url_for('dashboard_guru'))
                if peran == 'murid': return redirect(url_for('dashboard_murid'))
            
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                
                user = self.con.get_user_by_username(username) 
                
                if user and user.get('password_hash') and check_password_hash(user['password_hash'], password):
                    if not user.get('status_aktif', False): # Jika status_aktif False atau tidak ada
                        flash('Akun Anda tidak aktif. Silakan hubungi administrator.', 'warning')
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

        @self.app.route('/logout') # Jadikan rute logout umum
        def logout():
            session.clear()
            flash('Anda telah berhasil logout.', 'info')
            return redirect(url_for('login'))

        # === Rute Admin ===
        # --- Admin Dashboard ---
        @self.app.route('/admin/dashboard')
        @self.admin_login_required
        def dashboard_admin():
            counts = self.con.get_counts() # Menggunakan metode dari Config Anda
            return render_template('admin/dashboard_admin.html', 
                                   jumlah_pengguna=counts.get('users',0), 
                                   jumlah_kelas=counts.get('kelas',0), 
                                   jumlah_ekskul=counts.get('ekskul',0), 
                                   jumlah_pengumuman=counts.get('pengumuman',0),
                                   jumlah_materi_ekskul=counts.get('materi_ekskul',0))

        # --- Manajemen Pengguna (Admin) ---
        @self.app.route('/admin/users')
        @self.admin_login_required
        def users_admin():
            gurus = self.con.get_users_by_role('guru')
            murids = self.con.get_users_by_role('murid')
            admins = self.con.get_users_by_role('admin') # Jika Anda ingin menampilkan admin juga
            return render_template('admin/users_admin.html', gurus=gurus, murids=murids, admins=admins)

        # --- Tambah Pengguna (Admin) ---
        @self.app.route('/admin/users/add', methods=['GET', 'POST'])
        @self.admin_login_required
        def add_user_admin():
            if request.method == 'POST':
                user_data = {
                    'username': request.form['username'].strip(),
                    'password': request.form['password'], # Password akan di-hash di Config.add_user
                    'nama_lengkap': request.form['nama_lengkap'].strip(),
                    'email': request.form['email'].strip(),
                    'peran': request.form['peran'],
                    'nomor_induk': request.form['nomor_induk'].strip() if request.form['nomor_induk'] else None,
                    'status_aktif': True 
                }
                
                if not all([user_data['username'], user_data['password'], user_data['nama_lengkap'], user_data['email'], user_data['peran']]):
                    flash('Semua field yang ditandai bintang (*) wajib diisi.', 'danger')
                elif self.con.get_user_by_username(user_data['username']): # Cek duplikasi username
                    flash(f"Username '{user_data['username']}' sudah digunakan.", 'danger')
                # Anda mungkin ingin menambahkan pengecekan duplikasi email juga
                # elif self.con.get_user_by_email(user_data['email']):
                #     flash(f"Email '{user_data['email']}' sudah digunakan.", 'danger')
                else:
                    user_id = self.con.add_user(user_data) # Menggunakan metode dari Config Anda
                    if user_id:
                        flash(f"Pengguna '{user_data['nama_lengkap']}' berhasil ditambahkan dengan ID: {user_id}!", 'success')
                        return redirect(url_for('users_admin'))
                    else:
                        flash('Gagal menambahkan pengguna. Periksa log server untuk detail.', 'danger')
            
            return render_template('admin/user_form_admin.html', action='Tambah', user_data=None)

        # --- Update Pengguna (Admin) ---
        @self.app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
        @self.admin_login_required
        def edit_user_admin(user_id):
            user_to_edit = self.con.get_user_by_id(user_id)
            if not user_to_edit:
                flash(f"Pengguna dengan ID {user_id} tidak ditemukan.", 'danger')
                return redirect(url_for('users_admin'))

            if request.method == 'POST':
                # Hati-hati dengan checkbox status_aktif
                status_aktif_form = 'status_aktif' in request.form

                user_data = {
                    'username': request.form['username'].strip(),
                    'nama_lengkap': request.form['nama_lengkap'].strip(),
                    'email': request.form['email'].strip(),
                    'peran': request.form['peran'],
                    'nomor_induk': request.form.get('nomor_induk','').strip() or None,
                    'status_aktif': status_aktif_form
                    # Password hanya diupdate jika diisi
                }
                password_baru = request.form.get('password','').strip()
                if password_baru: # Jika ada input password baru
                    user_data['password'] = password_baru # akan di-hash di Config.update_user

                # Validasi dasar
                if not all([user_data['username'], user_data['nama_lengkap'], user_data['email'], user_data['peran']]):
                    flash('Username, Nama Lengkap, Email, dan Peran wajib diisi.', 'danger')
                else:
                    # Cek duplikasi username/email (kecuali untuk user yang sedang diedit)
                    # Implementasi cek duplikasi ini bisa lebih baik di Config.update_user
                    
                    if self.con.update_user(user_id, user_data):
                        flash(f"Data pengguna '{user_data['nama_lengkap']}' berhasil diupdate!", 'success')
                        return redirect(url_for('users_admin'))
                    else:
                        flash('Gagal mengupdate data pengguna. Periksa log server.', 'danger')
                # Jika validasi gagal atau update gagal, render form lagi dengan data yang ada
                # Kita perlu mengisi kembali user_to_edit dengan data form agar perubahan tidak hilang
                user_to_edit.update(user_data) 
                if 'password' in user_to_edit: del user_to_edit['password'] # jangan kirim password plain ke template

            return render_template('admin/user_form_admin.html', action='Edit', user_data=user_to_edit)
        
        # --- Hapus Pengguna (Admin) ---
        @self.app.route('/admin/users/delete/<int:user_id>', methods=['POST']) # Gunakan POST untuk aksi hapus
        @self.admin_login_required
        def delete_user_admin(user_id):
            # Untuk keamanan, Anda bisa cek dulu apakah user yang akan dihapus bukan admin itu sendiri
            # atau satu-satunya admin.
            if session.get('user_id') == user_id:
                flash("Anda tidak dapat menghapus akun Anda sendiri.", "danger")
                return redirect(url_for('users_admin'))

            user_to_delete = self.con.get_user_by_id(user_id)
            if not user_to_delete:
                 flash(f"Pengguna dengan ID {user_id} tidak ditemukan.", 'danger')
                 return redirect(url_for('users_admin'))

            # Khusus: Jangan biarkan admin terakhir dihapus (opsional tapi disarankan)
            if user_to_delete['peran'] == 'admin':
                admins = self.con.get_users_by_role('admin')
                if len(admins) <= 1:
                    flash("Tidak dapat menghapus satu-satunya admin.", "danger")
                    return redirect(url_for('users_admin'))

            if self.con.delete_user(user_id):
                flash(f"Pengguna '{user_to_delete['nama_lengkap']}' berhasil dihapus.", 'success')
            else:
                flash(f"Gagal menghapus pengguna '{user_to_delete['nama_lengkap']}'. Periksa log server.", 'danger')
            return redirect(url_for('users_admin'))
        
        # --- Manajemen Kelas (Admin) ---
        @self.app.route('/admin/kelas')
        @self.admin_login_required
        def kelas_admin():
            kelas_list = self.con.get_all_kelas() # Menggunakan metode dari Config Anda
            return render_template('admin/kelas_admin.html', kelas_list=kelas_list)

        # --- Menambahkan Kelas (Admin) ---
        @self.app.route('/admin/kelas/add', methods=['GET', 'POST'])
        @self.admin_login_required
        def add_kelas_admin():
            if request.method == 'POST':
                id_wali_kelas_str = request.form.get('id_wali_kelas')
                kelas_data = {
                    'nama_kelas': request.form['nama_kelas'].strip(),
                    'tahun_ajaran': request.form['tahun_ajaran'].strip(),
                    'id_wali_kelas': int(id_wali_kelas_str) if id_wali_kelas_str and id_wali_kelas_str.isdigit() else None,
                    'deskripsi': request.form.get('deskripsi','').strip()
                }
                if not kelas_data['nama_kelas'] or not kelas_data['tahun_ajaran']:
                     flash('Nama Kelas dan Tahun Ajaran wajib diisi.', 'danger')
                else:
                    kelas_id = self.con.add_kelas(kelas_data) # Menggunakan metode dari Config Anda
                    if kelas_id:
                        flash(f"Kelas '{kelas_data['nama_kelas']}' berhasil ditambahkan!", 'success')
                        return redirect(url_for('kelas_admin'))
                    else:
                        flash('Gagal menambahkan kelas. Periksa log server.', 'danger')
            
            list_guru = self.con.get_users_by_role('guru') # Menggunakan metode dari Config Anda
            return render_template('admin/kelas_form_admin.html', action='Tambah', kelas_data=None, list_guru=list_guru)
        
        # --- Update Kelas (Admin)---
        @self.app.route('/admin/kelas/edit/<int:kelas_id>', methods=['GET', 'POST'])
        @self.admin_login_required
        def edit_kelas_admin(kelas_id):
            kelas_to_edit = self.con.get_kelas_by_id(kelas_id) # Ini mengambil dict, termasuk nama_wali_kelas
            if not kelas_to_edit:
                flash(f"Kelas dengan ID {kelas_id} tidak ditemukan.", 'danger')
                return redirect(url_for('kelas_admin'))

            if request.method == 'POST':
                id_wali_kelas_str = request.form.get('id_wali_kelas')
                kelas_data = {
                    'nama_kelas': request.form['nama_kelas'].strip(),
                    'tahun_ajaran': request.form['tahun_ajaran'].strip(),
                    'id_wali_kelas': int(id_wali_kelas_str) if id_wali_kelas_str and id_wali_kelas_str.isdigit() else None,
                    'deskripsi': request.form.get('deskripsi','').strip()
                }
                if not kelas_data['nama_kelas'] or not kelas_data['tahun_ajaran']:
                     flash('Nama Kelas dan Tahun Ajaran wajib diisi.', 'danger')
                else:
                    if self.con.update_kelas(kelas_id, kelas_data): # Anda perlu buat metode ini di Config
                        flash(f"Data kelas '{kelas_data['nama_kelas']}' berhasil diupdate!", 'success')
                        return redirect(url_for('kelas_admin'))
                    else:
                        flash('Gagal mengupdate data kelas. Periksa log server.', 'danger')
                # Isi kembali data form jika ada error
                kelas_to_edit.update(kelas_data)

            list_guru = self.con.get_users_by_role('guru')
            return render_template('admin/kelas_form_admin.html', action='Edit', kelas_data=kelas_to_edit, list_guru=list_guru)

        # --- Hapus Kelas (Admin) ---
        @self.app.route('/admin/kelas/delete/<int:kelas_id>', methods=['POST'])
        @self.admin_login_required
        def delete_kelas_admin(kelas_id):
            kelas_to_delete = self.con.get_kelas_by_id(kelas_id) # Untuk nama di pesan flash
            if not kelas_to_delete:
                flash(f"Kelas dengan ID {kelas_id} tidak ditemukan.", 'danger')
                return redirect(url_for('kelas_admin'))

            if self.con.delete_kelas(kelas_id):
                flash(f"Kelas '{kelas_to_delete['nama_kelas']}' berhasil dihapus.", 'success')
            else:
                flash(f"Gagal menghapus kelas '{kelas_to_delete['nama_kelas']}'. Periksa log server.", 'danger')
            return redirect(url_for('kelas_admin'))
        
        # --- Detail Kelas (Admin) ---
        @self.app.route('/admin/kelas/detail/<int:kelas_id>')
        @self.admin_login_required
        def kelas_detail_admin(kelas_id):
            kelas_info = self.con.get_kelas_by_id(kelas_id)
            if not kelas_info:
                flash(f"Kelas dengan ID {kelas_id} tidak ditemukan.", 'danger')
                return redirect(url_for('kelas_admin'))
            
            students_in_class = self.con.get_students_in_class(kelas_id)
            return render_template('admin/kelas_detail_admin.html', kelas_info=kelas_info, students=students_in_class)
        
        # --- Enroll Murid ke Kelas (Admin) ---
        @self.app.route('/admin/kelas/<int:kelas_id>/enroll', methods=['GET', 'POST'])
        @self.admin_login_required
        def enroll_student_kelas_admin(kelas_id):
            kelas_info = self.con.get_kelas_by_id(kelas_id)
            if not kelas_info:
                flash(f"Kelas dengan ID {kelas_id} tidak ditemukan.", 'danger')
                return redirect(url_for('kelas_admin'))

            if request.method == 'POST':
                murid_id_to_enroll = request.form.get('id_murid')
                if not murid_id_to_enroll:
                    flash("Pilih murid yang akan didaftarkan.", "warning")
                else:
                    murid_id_to_enroll = int(murid_id_to_enroll)
                    # Tahun ajaran diambil dari info kelas yang sedang dilihat
                    tahun_ajaran = kelas_info['tahun_ajaran'] 
                    
                    if self.con.enroll_student_to_class(murid_id_to_enroll, kelas_id, tahun_ajaran):
                        murid_info = self.con.get_user_by_id(murid_id_to_enroll)
                        flash(f"Murid '{murid_info['nama_lengkap'] if murid_info else 'ID: '+str(murid_id_to_enroll)}' berhasil didaftarkan ke kelas '{kelas_info['nama_kelas']}'.", 'success')
                        return redirect(url_for('kelas_detail_admin', kelas_id=kelas_id))
                    else:
                        flash(f"Gagal mendaftarkan murid ke kelas. Mungkin murid sudah terdaftar atau terjadi kesalahan.", 'danger')
            
            # Ambil daftar murid yang bisa di-enroll (belum ada di kelas ini atau belum punya kelas di tahun ajaran ini)
            # Tahun ajaran diambil dari kelas_info
            available_students = self.con.get_all_active_murid_exclude_kelas(kelas_id, kelas_info['tahun_ajaran'])
            return render_template('admin/enroll_student_kelas_form.html', kelas_info=kelas_info, available_students=available_students)
        
        # --- Keluarkan Murid dari Kelas (Admin) ---
        @self.app.route('/admin/kelas/<int:kelas_id>/remove_student/<int:murid_id>', methods=['POST'])
        @self.admin_login_required
        def remove_student_from_kelas_admin(kelas_id, murid_id):
            kelas_info = self.con.get_kelas_by_id(kelas_id)
            if not kelas_info:
                flash(f"Kelas dengan ID {kelas_id} tidak ditemukan.", 'danger')
                return redirect(url_for('kelas_admin'))

            murid_info = self.con.get_user_by_id(murid_id)
            if not murid_info:
                flash(f"Murid dengan ID {murid_id} tidak ditemukan.", 'danger')
                return redirect(url_for('kelas_detail_admin', kelas_id=kelas_id))

            tahun_ajaran = kelas_info['tahun_ajaran'] 
            # Status baru bisa 'dropout' atau 'pindah', atau status kustom jika ada
            if self.con.update_enrollment_status(murid_id, kelas_id, tahun_ajaran, new_status='dropout'):
                flash(f"Murid '{murid_info['nama_lengkap']}' telah dikeluarkan (status diubah menjadi 'dropout') dari kelas '{kelas_info['nama_kelas']}'.", 'success')
            else:
                flash(f"Gagal mengeluarkan murid '{murid_info['nama_lengkap']}' dari kelas. Periksa log server.", 'danger')
            return redirect(url_for('kelas_detail_admin', kelas_id=kelas_id))
        
        # --- Manajemen Ekstrakurikuler (Admin) ---
        @self.app.route('/admin/ekskul')
        @self.admin_login_required
        def ekskul_admin():
            ekskul_list = self.con.get_all_ekskul() # Menggunakan metode dari Config Anda
            return render_template('admin/ekskul_admin.html', ekskul_list=ekskul_list)

        @self.app.route('/admin/ekskul/add', methods=['GET', 'POST'])
        @self.admin_login_required
        def add_ekskul_admin():
            if request.method == 'POST':
                id_guru_pembina_str = request.form.get('id_guru_pembina')
                ekskul_data = {
                    'nama_ekskul': request.form['nama_ekskul'].strip(),
                    'id_guru_pembina': int(id_guru_pembina_str) if id_guru_pembina_str and id_guru_pembina_str.isdigit() else None,
                    'jadwal_deskripsi': request.form['jadwal_deskripsi'].strip(),
                    'lokasi': request.form.get('lokasi','').strip(),
                    'kuota_maksimal': int(request.form['kuota_maksimal']) if request.form.get('kuota_maksimal','').isdigit() else None,
                    'deskripsi': request.form.get('deskripsi','').strip(),
                    'kategori': request.form.get('kategori','').strip(),
                    'status_aktif': 'status_aktif' in request.form, 
                    'url_logo_ekskul': request.form.get('url_logo_ekskul','').strip() # Asumsi ada field ini di form
                }
                if not ekskul_data['nama_ekskul']:
                    flash('Nama Ekstrakurikuler wajib diisi.', 'danger')
                else:
                    ekskul_id = self.con.add_ekskul(ekskul_data) # Menggunakan metode dari Config Anda
                    if ekskul_id:
                        flash(f"Ekstrakurikuler '{ekskul_data['nama_ekskul']}' berhasil ditambahkan!", 'success')
                        return redirect(url_for('ekskul_admin'))
                    else:
                        flash('Gagal menambahkan ekstrakurikuler. Periksa log server.', 'danger')
                
            list_guru = self.con.get_users_by_role('guru') # Menggunakan metode dari Config Anda
            return render_template('admin/ekskul_form_admin.html', action='Tambah', ekskul_data=None, list_guru=list_guru)

        # --- Edit Ekstrakurikuler (Admin) ---
        @self.app.route('/admin/ekskul/edit/<int:ekskul_id>', methods=['GET', 'POST'])
        @self.admin_login_required
        def edit_ekskul_admin(ekskul_id):
            ekskul_to_edit = self.con.get_ekskul_by_id(ekskul_id) # Anda perlu buat metode ini di Config
            if not ekskul_to_edit:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan.", 'danger')
                return redirect(url_for('ekskul_admin'))

            if request.method == 'POST':
                id_guru_pembina_str = request.form.get('id_guru_pembina')
                ekskul_data = {
                    'nama_ekskul': request.form['nama_ekskul'].strip(),
                    'id_guru_pembina': int(id_guru_pembina_str) if id_guru_pembina_str and id_guru_pembina_str.isdigit() else None,
                    'jadwal_deskripsi': request.form['jadwal_deskripsi'].strip(),
                    'lokasi': request.form.get('lokasi','').strip(),
                    'kuota_maksimal': int(request.form['kuota_maksimal']) if request.form.get('kuota_maksimal','').isdigit() else None,
                    'deskripsi': request.form.get('deskripsi','').strip(),
                    'kategori': request.form.get('kategori','').strip(),
                    'status_aktif': 'status_aktif' in request.form,
                    'url_logo_ekskul': request.form.get('url_logo_ekskul','').strip()
                }
                if not ekskul_data['nama_ekskul']:
                    flash('Nama Ekstrakurikuler wajib diisi.', 'danger')
                else:
                    if self.con.update_ekskul(ekskul_id, ekskul_data): # Anda perlu buat metode ini di Config
                        flash(f"Data Ekstrakurikuler '{ekskul_data['nama_ekskul']}' berhasil diupdate!", 'success')
                        return redirect(url_for('ekskul_admin'))
                    else:
                        flash('Gagal mengupdate data ekstrakurikuler. Periksa log server.', 'danger')
                ekskul_to_edit.update(ekskul_data)
                
            list_guru = self.con.get_users_by_role('guru')
            return render_template('admin/ekskul_form_admin.html', action='Edit', ekskul_data=ekskul_to_edit, list_guru=list_guru)

        # --- Hapus Ekstrakurikuler (Admin) ---
        @self.app.route('/admin/ekskul/delete/<int:ekskul_id>', methods=['POST'])
        @self.admin_login_required
        def delete_ekskul_admin(ekskul_id):
            ekskul_to_delete = self.con.get_ekskul_by_id(ekskul_id) # Anda perlu buat metode ini di Config
            if not ekskul_to_delete:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan.",'danger')
                return redirect(url_for('ekskul_admin'))

            if self.con.delete_ekskul(ekskul_id): # Anda perlu buat metode ini di Config
                flash(f"Ekstrakurikuler '{ekskul_to_delete['nama_ekskul']}' berhasil dihapus.", 'success')
            else:
                flash(f"Gagal menghapus ekstrakurikuler '{ekskul_to_delete['nama_ekskul']}'. Mungkin masih ada data terkait (murid terdaftar). Periksa log server.", 'danger')
            return redirect(url_for('ekskul_admin'))

        # --- Detail Ekstrakurikuler (Admin) ---
        @self.app.route('/admin/ekskul/detail/<int:ekskul_id>')
        @self.admin_login_required
        def ekskul_detail_admin(ekskul_id):
            ekskul_info = self.con.get_ekskul_by_id(ekskul_id) # Asumsi metode ini sudah ada
            if not ekskul_info:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan.", 'danger')
                return redirect(url_for('ekskul_admin'))
            
            # Asumsi tahun ajaran aktif bisa didapatkan, atau diambil dari ekskul_info jika relevan
            # Untuk contoh, kita gunakan tahun ajaran default atau yang paling baru.
            # Anda mungkin perlu logika lebih canggih untuk menentukan tahun ajaran aktif.
            current_tahun_ajaran = "2024/2025" # GANTI DENGAN LOGIKA TAHUN AJARAN AKTIF ANDA
            
            members = self.con.get_members_of_ekskul(ekskul_id, current_tahun_ajaran)
            
            return render_template('admin/ekskul_detail_admin.html', 
                                   ekskul_info=ekskul_info, 
                                   members=members,
                                   tahun_ajaran_display=current_tahun_ajaran)

        # --- Daftarkan Murid ke Ekstrakurikuler (Admin) ---
        @self.app.route('/admin/ekskul/<int:ekskul_id>/register', methods=['GET', 'POST'])
        @self.admin_login_required
        def register_student_ekskul_admin(ekskul_id):
            ekskul_info = self.con.get_ekskul_by_id(ekskul_id) # Asumsi Anda sudah punya metode ini
            if not ekskul_info:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan.", 'danger')
                return redirect(url_for('ekskul_admin'))

            if request.method == 'POST':
                murid_id_to_register = request.form.get('id_murid')
                tahun_ajaran = request.form.get('tahun_ajaran') # Ambil tahun ajaran dari form atau default

                if not murid_id_to_register or not tahun_ajaran:
                    flash("Pilih murid dan masukkan tahun ajaran.", "warning")
                else:
                    murid_id_to_register = int(murid_id_to_register)
                    # Admin langsung mendaftarkan dengan status 'Disetujui'
                    if self.con.register_student_for_ekskul(murid_id_to_register, ekskul_id, tahun_ajaran, status_pendaftaran='Disetujui'):
                        murid_info = self.con.get_user_by_id(murid_id_to_register)
                        flash(f"Murid '{murid_info['nama_lengkap'] if murid_info else 'ID: '+str(murid_id_to_register)}' berhasil didaftarkan ke ekskul '{ekskul_info['nama_ekskul']}'.", 'success')
                        # Arahkan ke halaman detail ekskul jika ada, atau kembali ke daftar ekskul
                        return redirect(url_for('ekskul_admin')) 
                    else:
                        flash(f"Gagal mendaftarkan murid ke ekskul. Mungkin murid sudah terdaftar atau terjadi kesalahan.", 'danger')
            
            # Ambil tahun ajaran saat ini atau yang relevan
            # Untuk contoh, kita bisa hardcode atau ambil dari konfigurasi
            current_tahun_ajaran = "2024/2025" # Ganti dengan logika yang sesuai
            available_students = self.con.get_all_active_murid_exclude_ekskul(ekskul_id, current_tahun_ajaran)
            return render_template('admin/register_student_ekskul_form.html', ekskul_info=ekskul_info, available_students=available_students, current_tahun_ajaran=current_tahun_ajaran)

        # --- Keluarkan Murid dari Ekskul (Admin) ---
        @self.app.route('/admin/ekskul/remove_member/<int:pendaftaran_id>', methods=['POST'])
        @self.admin_login_required
        def remove_student_from_ekskul_admin(pendaftaran_id):
            # Ambil ID ekskul dari form (untuk redirect kembali) atau dari database jika perlu
            ekskul_id_redirect = request.form.get('ekskul_id_redirect')

            # Anda mungkin ingin mengambil info pendaftaran untuk nama murid, dll. untuk pesan flash
            # pendaftaran_info = self.con.get_pendaftaran_ekskul_by_id(pendaftaran_id) 
            # (perlu buat metode get_pendaftaran_ekskul_by_id jika ingin info detail)

            if self.con.update_ekskul_registration_status(pendaftaran_id, new_status='Berhenti'):
                flash(f"Anggota ekskul (Pendaftaran ID: {pendaftaran_id}) telah dikeluarkan (status diubah menjadi 'Berhenti').", 'success')
            else:
                flash(f"Gagal mengeluarkan anggota ekskul. Periksa log server.", 'danger')
            
            if ekskul_id_redirect:
                return redirect(url_for('ekskul_detail_admin', ekskul_id=ekskul_id_redirect))
            return redirect(url_for('ekskul_admin')) # Fallback jika tidak ada redirect ID

        # --- Manajemen Materi Ekskul (Admin) ---
        @self.app.route('/admin/materi_ekskul')
        @self.admin_login_required
        def materi_ekskul_admin():
            list_materi = self.con.get_all_materi_ekskul()
            return render_template('admin/materi_ekskul_admin.html', list_materi=list_materi)

        @self.app.route('/admin/materi_ekskul/tambah', methods=['GET', 'POST'])
        @self.admin_login_required
        def tambah_materi_ekskul_admin():
            if request.method == 'POST':
                id_ekskul = request.form.get('id_ekskul')
                judul_materi = request.form.get('judul_materi','').strip()
                deskripsi_materi = request.form.get('deskripsi_materi','').strip()
                tipe_konten = request.form.get('tipe_konten')
                
                path_konten_atau_link = None
                isi_konten_teks = None

                if not id_ekskul or not judul_materi or not tipe_konten:
                    flash("Ekskul, Judul Materi, dan Tipe Konten wajib diisi.", "danger")
                else:
                    id_ekskul = int(id_ekskul)
                    if tipe_konten == 'file':
                        if 'file_konten' not in request.files:
                            flash('Tidak ada bagian file yang dipilih.', 'danger')
                        else:
                            file = request.files['file_konten']
                            if file.filename == '':
                                flash('Tidak ada file yang dipilih untuk diunggah.', 'danger')
                            # elif file and allowed_file(file.filename, self.app.config['ALLOWED_EXTENSIONS']): # Anda perlu implementasi allowed_file
                            elif file: # Simplifikasi untuk contoh, tambahkan validasi ekstensi di produksi
                                filename = secure_filename(file.filename)
                                # Pastikan direktori upload ada
                                upload_path_dir = os.path.join(self.app.root_path, self.app.config['UPLOAD_FOLDER'])
                                if not os.path.exists(upload_path_dir):
                                    os.makedirs(upload_path_dir)
                                file.save(os.path.join(upload_path_dir, filename))
                                path_konten_atau_link = filename # Simpan nama file, atau path relatif dari UPLOAD_FOLDER
                                flash(f'File {filename} berhasil diunggah.', 'info')
                            else:
                                flash('Tipe file tidak diizinkan.', 'danger')
                    elif tipe_konten in ['link', 'video_embed']:
                        path_konten_atau_link = request.form.get('path_konten_atau_link_url','').strip()
                        if not path_konten_atau_link:
                             flash('URL/Link atau Kode Embed Video wajib diisi untuk tipe ini.', 'danger')
                    elif tipe_konten == 'teks':
                        isi_konten_teks = request.form.get('isi_konten_teks_area','').strip()
                        if not isi_konten_teks:
                            flash('Isi konten teks wajib diisi untuk tipe ini.', 'danger')
                    
                    # Lanjutkan penyimpanan jika path_konten_atau_link atau isi_konten_teks sudah valid (atau boleh kosong tergantung logika)
                    # Misalnya, jika tipe file dan file gagal diupload, path_konten_atau_link akan None
                    # Anda perlu logika validasi yang lebih baik di sini
                    
                    data_materi = {
                        'id_ekskul': id_ekskul,
                        'judul_materi': judul_materi,
                        'deskripsi_materi': deskripsi_materi,
                        'tipe_konten': tipe_konten,
                        'path_konten_atau_link': path_konten_atau_link,
                        'isi_konten_teks': isi_konten_teks,
                        'id_pengunggah': session['user_id']
                    }
                    
                    # Hanya simpan jika ada konten yang relevan (misal, file berhasil diupload atau link/teks diisi)
                    # Logika ini perlu disempurnakan: jika file wajib, maka harus ada path_konten_atau_link
                    save_to_db = False
                    if tipe_konten == 'file' and path_konten_atau_link: save_to_db = True
                    elif tipe_konten in ['link', 'video_embed'] and path_konten_atau_link: save_to_db = True
                    elif tipe_konten == 'teks' and isi_konten_teks: save_to_db = True
                    elif tipe_konten not in ['file', 'link', 'video_embed', 'teks']: # Tipe konten tidak valid
                        flash('Tipe konten tidak valid.', 'danger')
                        save_to_db = False


                    if save_to_db:
                        materi_id = self.con.add_materi_ekskul(data_materi)
                        if materi_id:
                            flash("Materi ekstrakurikuler berhasil ditambahkan!", "success")
                            return redirect(url_for('materi_ekskul_admin'))
                        else:
                            flash("Gagal menambahkan materi. Periksa log server.", "danger")
                    elif not path_konten_atau_link and not isi_konten_teks and tipe_konten in ['file', 'link', 'video_embed', 'teks']:
                         flash("Konten untuk materi (file/link/teks) tidak boleh kosong.", "danger")


            list_ekskul = self.con.get_all_ekskul()
            return render_template('admin/materi_ekskul_form_admin.html', 
                                   action="Tambah", 
                                   materi_data=None,
                                   list_ekskul=list_ekskul)
        @self.app.route('/admin/materi_ekskul/edit/<int:id_materi_ekskul>', methods=['GET', 'POST'])
        @self.admin_login_required
        def edit_materi_ekskul_admin(id_materi_ekskul):
            materi_data_lama = self.con.get_materi_ekskul_by_id(id_materi_ekskul)
            if not materi_data_lama:
                flash("Materi ekstrakurikuler tidak ditemukan.", "danger")
                return redirect(url_for('materi_ekskul_admin'))

            if request.method == 'POST':
                id_ekskul = request.form.get('id_ekskul')
                judul_materi = request.form.get('judul_materi','').strip()
                deskripsi_materi = request.form.get('deskripsi_materi','').strip()
                tipe_konten = request.form.get('tipe_konten')
                
                # Data yang akan diupdate
                data_to_update = {
                    'id_ekskul': int(id_ekskul) if id_ekskul else materi_data_lama['id_ekskul'],
                    'judul_materi': judul_materi if judul_materi else materi_data_lama['judul_materi'],
                    'deskripsi_materi': deskripsi_materi, # Bisa string kosong
                    'tipe_konten': tipe_konten if tipe_konten else materi_data_lama['tipe_konten']
                }
                
                new_path_konten_atau_link = None
                new_isi_konten_teks = None
                delete_old_file = False
                old_file_path = None

                if data_to_update['tipe_konten'] == 'file':
                    if 'file_konten' in request.files:
                        file = request.files['file_konten']
                        if file and file.filename != '': # Ada file baru diupload
                            # Hapus file lama jika ada
                            if materi_data_lama['tipe_konten'] == 'file' and materi_data_lama['path_konten_atau_link']:
                                delete_old_file = True
                                old_file_path = os.path.join(self.app.root_path, self.app.config['UPLOAD_FOLDER'], materi_data_lama['path_konten_atau_link'])
                            
                            filename = secure_filename(file.filename)
                            upload_path_dir = os.path.join(self.app.root_path, self.app.config['UPLOAD_FOLDER'])
                            if not os.path.exists(upload_path_dir): os.makedirs(upload_path_dir)
                            file.save(os.path.join(upload_path_dir, filename))
                            new_path_konten_atau_link = filename
                            data_to_update['path_konten_atau_link'] = new_path_konten_atau_link
                            data_to_update['isi_konten_teks'] = None # Pastikan isi_konten_teks di-null-kan
                            flash(f'File baru {filename} berhasil diunggah.', 'info')
                        # Jika tidak ada file baru diupload, gunakan path lama jika tipe konten tidak berubah dari file
                        elif materi_data_lama['tipe_konten'] == 'file':
                            data_to_update['path_konten_atau_link'] = materi_data_lama['path_konten_atau_link']
                            data_to_update['isi_konten_teks'] = None
                    # Jika tipe berubah ke file dari tipe lain, file wajib diupload
                    elif materi_data_lama['tipe_konten'] != 'file' and ('file_konten' not in request.files or request.files['file_konten'].filename == ''):
                         flash('File wajib diunggah jika tipe konten adalah file.', 'danger')
                         # Kembalikan ke form dengan data yang sudah diisi
                         list_ekskul = self.con.get_all_ekskul()
                         return render_template('admin/materi_ekskul_form_admin.html', 
                                               action="Edit", materi_data=request.form, # Kirim data form kembali
                                               list_ekskul=list_ekskul, id_materi_ekskul=id_materi_ekskul)


                elif data_to_update['tipe_konten'] in ['link', 'video_embed']:
                    new_path_konten_atau_link = request.form.get('path_konten_atau_link_url','').strip()
                    if not new_path_konten_atau_link:
                        flash('URL/Link atau Kode Embed Video wajib diisi untuk tipe ini.', 'danger')
                    else:
                        data_to_update['path_konten_atau_link'] = new_path_konten_atau_link
                        data_to_update['isi_konten_teks'] = None # Pastikan isi_konten_teks di-null-kan
                        if materi_data_lama['tipe_konten'] == 'file' and materi_data_lama['path_konten_atau_link']:
                            delete_old_file = True # Hapus file lama jika tipe berubah dari file
                            old_file_path = os.path.join(self.app.root_path, self.app.config['UPLOAD_FOLDER'], materi_data_lama['path_konten_atau_link'])

                elif data_to_update['tipe_konten'] == 'teks':
                    new_isi_konten_teks = request.form.get('isi_konten_teks_area','').strip()
                    if not new_isi_konten_teks:
                         flash('Isi konten teks wajib diisi untuk tipe ini.', 'danger')
                    else:
                        data_to_update['isi_konten_teks'] = new_isi_konten_teks
                        data_to_update['path_konten_atau_link'] = None # Pastikan path_konten_atau_link di-null-kan
                        if materi_data_lama['tipe_konten'] == 'file' and materi_data_lama['path_konten_atau_link']:
                            delete_old_file = True # Hapus file lama jika tipe berubah dari file
                            old_file_path = os.path.join(self.app.root_path, self.app.config['UPLOAD_FOLDER'], materi_data_lama['path_konten_atau_link'])
                
                # Lakukan update hanya jika validasi konten spesifik tipe berhasil
                # Anda perlu menambahkan logika validasi yang lebih kuat di sini
                # Contoh sederhana:
                is_content_valid = True
                if data_to_update['tipe_konten'] == 'file' and not data_to_update.get('path_konten_atau_link'): is_content_valid = False
                elif data_to_update['tipe_konten'] in ['link','video_embed'] and not data_to_update.get('path_konten_atau_link'): is_content_valid = False
                elif data_to_update['tipe_konten'] == 'teks' and not data_to_update.get('isi_konten_teks'): is_content_valid = False


                if is_content_valid and self.con.update_materi_ekskul(id_materi_ekskul, data_to_update):
                    if delete_old_file and old_file_path:
                        try:
                            if os.path.exists(old_file_path):
                                os.remove(old_file_path)
                                flash('File lama berhasil dihapus.', 'info')
                        except OSError as e:
                            flash(f'Gagal menghapus file lama: {e}', 'warning')
                    flash("Materi ekstrakurikuler berhasil diperbarui!", "success")
                    return redirect(url_for('materi_ekskul_admin'))
                elif not is_content_valid and not get_flashed_messages(): # Jika belum ada flash dari validasi di atas
                     flash("Gagal memperbarui materi. Konten tidak valid atau tidak diisi.", "danger")
                elif not get_flashed_messages():
                     flash("Gagal memperbarui materi. Periksa log server.", "danger")
                
                # Jika gagal, kembalikan ke form dengan data yang sudah diisi
                list_ekskul = self.con.get_all_ekskul()
                # Kirim data form yang terakhir diinput, bukan data_to_update yang mungkin sudah dimodifikasi
                form_data_kembali = dict(request.form) 
                form_data_kembali['path_konten_atau_link'] = materi_data_lama.get('path_konten_atau_link') # Jaga path file lama jika tidak diubah
                if materi_data_lama['tipe_konten'] == 'teks':
                     form_data_kembali['isi_konten_teks'] = materi_data_lama.get('isi_konten_teks')

                return render_template('admin/materi_ekskul_form_admin.html', 
                                       action="Edit", materi_data=form_data_kembali, 
                                       list_ekskul=list_ekskul, id_materi_ekskul=id_materi_ekskul)


            list_ekskul = self.con.get_all_ekskul()
            # Untuk form edit, materi_data_lama sudah berisi semua field dari database
            # Termasuk path_konten_atau_link dan isi_konten_teks yang benar
            return render_template('admin/materi_ekskul_form_admin.html', 
                                   action="Edit", 
                                   materi_data=materi_data_lama, 
                                   list_ekskul=list_ekskul,
                                   id_materi_ekskul=id_materi_ekskul)


        @self.app.route('/admin/materi_ekskul/hapus/<int:id_materi_ekskul>', methods=['POST'])
        @self.admin_login_required
        def hapus_materi_ekskul_admin(id_materi_ekskul):
            materi_info = self.con.delete_materi_ekskul(id_materi_ekskul)
            if materi_info:
                # Jika materi adalah file, hapus file fisiknya
                if materi_info['tipe_konten'] == 'file' and materi_info['path_konten_atau_link']:
                    try:
                        file_path = os.path.join(self.app.root_path, self.app.config['UPLOAD_FOLDER'], materi_info['path_konten_atau_link'])
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            flash(f"File materi '{materi_info['path_konten_atau_link']}' berhasil dihapus dari server.", 'info')
                    except OSError as e:
                        flash(f"Gagal menghapus file fisik: {e}", "warning")
                flash("Materi ekstrakurikuler berhasil dihapus!", "success")
            else:
                flash("Gagal menghapus materi ekstrakurikuler.", "danger")
            return redirect(url_for('materi_ekskul_admin'))

        # --- Manajemen Pengumuman (Admin) ---
        @self.app.route('/admin/pengumuman')
        @self.admin_login_required
        def pengumuman_admin():
            # Ambil semua pengumuman untuk ditampilkan
            list_pengumuman = self.con.get_all_pengumuman()
            return render_template('admin/pengumuman_admin.html', list_pengumuman=list_pengumuman)

        @self.app.route('/admin/pengumuman/tambah', methods=['GET', 'POST'])
        @self.admin_login_required
        def tambah_pengumuman_admin():
            if request.method == 'POST':
                judul = request.form.get('judul_pengumuman','').strip()
                isi = request.form.get('isi_pengumuman','').strip()
                target_peran = request.form.get('target_peran') 
                # Ambil target_kelas_id dan target_ekskul_id, pastikan integer atau None
                target_kelas_id_str = request.form.get('target_kelas_id')
                target_kelas_id = int(target_kelas_id_str) if target_kelas_id_str and target_kelas_id_str.isdigit() else None
                
                target_ekskul_id_str = request.form.get('target_ekskul_id')
                target_ekskul_id = int(target_ekskul_id_str) if target_ekskul_id_str and target_ekskul_id_str.isdigit() else None

                if not judul or not isi:
                    flash("Judul dan Isi pengumuman wajib diisi.", "danger")
                else:
                    data_pengumuman = {
                        'judul_pengumuman': judul,
                        'isi_pengumuman': isi,
                        'id_pembuat': session['user_id'], # ID admin yang login
                        'target_peran': target_peran if target_peran else None, # Jika "" jadikan None
                        'target_kelas_id': target_kelas_id,
                        'target_ekskul_id': target_ekskul_id
                    }
                    pengumuman_id = self.con.add_pengumuman(data_pengumuman)
                    if pengumuman_id:
                        flash("Pengumuman berhasil ditambahkan!", "success")
                        return redirect(url_for('pengumuman_admin'))
                    else:
                        flash("Gagal menambahkan pengumuman. Periksa log server.", "danger")
            
            # Ambil data untuk dropdown target (opsional, tapi bagus untuk UX)
            # Jika target_peran adalah 'semua', maka tidak perlu pilih kelas/ekskul
            # Jika target_peran adalah 'murid' atau 'guru', bisa jadi ada filter per kelas/ekskul
            list_kelas = self.con.get_all_kelas() # Asumsi metode ini sudah ada
            list_ekskul = self.con.get_all_ekskul() # Asumsi metode ini sudah ada
            
            return render_template('admin/pengumuman_form_admin.html', 
                                   action="Tambah", 
                                   pengumuman_data=None,
                                   list_kelas=list_kelas,
                                   list_ekskul=list_ekskul)

    # === Guru Route

    # --- Rute Dashboard Guru ---
        @self.app.route('/guru/dashboard')
        @self.guru_login_required
        def dashboard_guru():
            guru_id = session.get('user_id')
            nama_guru = session.get('nama_lengkap')
            
            # Ambil data dari Config
            jadwal_ekskul_guru = self.con.get_ekskul_by_pembina(guru_id)
            info_terbaru_guru = self.con.get_pengumuman_for_guru(guru_id) # Mungkin perlu id_guru
            
            # Untuk dropdown absen: ekskul yang dibina guru & murid yang relevan
            # Daftar ekskul sudah ada di jadwal_ekskul_guru
            # Daftar murid bisa diambil berdasarkan ekskul yang dipilih guru di form, atau semua murid terkait guru
            # Untuk V1, kita kirim semua murid yang relevan dengan guru ini.
            # HTML Anda (test.html) punya JS untuk manajemen siswa lokal, ini berbeda.
            # Untuk form absen, kita perlu daftar murid yang akan diabsen.
            tahun_ajaran_aktif = self.con.get_tahun_ajaran_aktif() if hasattr(self.con, 'get_tahun_ajaran_aktif') else "2024/2025"

            
            # Tahun ajaran aktif (ini perlu mekanisme yang lebih baik)
            murid_untuk_absen = self.con.get_murid_options_for_guru_absen(guru_id, tahun_ajaran_aktif)

            return render_template('guru/dashboard_guru.html', 
                                   nama_guru=nama_guru,
                                   jadwal_ekskul=jadwal_ekskul_guru,
                                   info_terbaru=info_terbaru_guru,
                                   murid_untuk_absen=murid_untuk_absen, # Untuk dropdown nama siswa di form absen
                                   ekskul_guru=jadwal_ekskul_guru, # Untuk dropdown ekskul di form absen
                                   tahun_ajaran_aktif=tahun_ajaran_aktif,
                                   default_tanggal_absen=date.today().isoformat())

        # --- Rute untuk Submit Absen Guru (BARU) ---
        @self.app.route('/guru/absen/submit', methods=['POST'])
        @self.guru_login_required
        def submit_absen_guru():
            guru_id = session.get('user_id')
            try:
                murid_id = int(request.form.get('id_murid'))
                ekskul_id = int(request.form.get('id_ekskul'))
                status_kehadiran = request.form.get('status_kehadiran')
                tanggal_kegiatan = request.form.get('tanggal_kegiatan')
                tahun_ajaran = request.form.get('tahun_ajaran') # Pastikan ini ada di form
                catatan = request.form.get('catatan_absen', '')
                jam_kegiatan = request.form.get('jam_kegiatan', None) # Opsional dari form

                if not all([murid_id, ekskul_id, status_kehadiran, tanggal_kegiatan, tahun_ajaran]):
                    flash("Data absen tidak lengkap. Semua field wajib diisi.", 'danger')
                    return redirect(url_for('dashboard_guru'))

                # Dapatkan id_pendaftaran_ekskul
                id_pendaftaran_ekskul = self.con.get_pendaftaran_ekskul_id(murid_id, ekskul_id, tahun_ajaran)

                if id_pendaftaran_ekskul:
                    if self.con.save_absensi_ekskul(id_pendaftaran_ekskul, tanggal_kegiatan, status_kehadiran, guru_id, catatan, jam_kegiatan):
                        flash("Data absensi berhasil disimpan/diperbarui.", "success")
                    else:
                        flash("Gagal menyimpan data absensi. Terjadi kesalahan.", "danger")
                else:
                    flash(f"Murid tidak terdaftar di ekstrakurikuler tersebut pada tahun ajaran {tahun_ajaran} atau pendaftaran tidak aktif.", "warning")
                
            except ValueError:
                flash("ID Murid atau ID Ekskul tidak valid.", "danger")
            except Exception as e:
                flash(f"Terjadi kesalahan internal: {e}", "danger")
                print(f"Error saat submit absen: {e}") # Untuk debugging di server

            return redirect(url_for('dashboard_guru'))
        
        # --- Halaman untuk Guru Mengelola Peserta Ekskulnya (BARU) ---
        @self.app.route('/guru/ekskul/<int:ekskul_id>/peserta')
        @self.guru_login_required
        def kelola_peserta_ekskul_guru(ekskul_id):
            guru_id = session.get('user_id')
            ekskul_info = self.con.get_ekskul_by_id(ekskul_id)

            # Validasi apakah guru ini adalah pembina ekskul tersebut
            if not ekskul_info or ekskul_info.get('id_guru_pembina') != guru_id:
                flash("Anda tidak memiliki akses untuk mengelola peserta ekskul ini.", "danger")
                return redirect(url_for('dashboard_guru'))

            # Tentukan tahun ajaran aktif
            tahun_ajaran_aktif = self.con.get_tahun_ajaran_aktif() if hasattr(self.con, 'get_tahun_ajaran_aktif') else "2024/2025" # GANTI INI

            current_members = self.con.get_members_of_ekskul(ekskul_id, tahun_ajaran_aktif)
            available_students_to_add = self.con.get_all_active_murid_exclude_ekskul(ekskul_id, tahun_ajaran_aktif)
            
            return render_template('guru/kelola_peserta_ekskul.html',
                                   ekskul_info=ekskul_info,
                                   members=current_members,
                                   available_students=available_students_to_add,
                                   tahun_ajaran_aktif=tahun_ajaran_aktif)

        # --- Tambah Peserta ke Ekskul oleh Guru (BARU) ---
        @self.app.route('/guru/ekskul/<int:ekskul_id>/add_peserta', methods=['POST'])
        @self.guru_login_required
        def add_peserta_ekskul_guru(ekskul_id):
            guru_id = session.get('user_id')
            ekskul_info = self.con.get_ekskul_by_id(ekskul_id)
            if not ekskul_info or ekskul_info.get('id_guru_pembina') != guru_id:
                flash("Anda tidak memiliki akses untuk menambah peserta ke ekskul ini.", "danger")
                return redirect(url_for('dashboard_guru'))

            murid_id = request.form.get('id_murid')
            tahun_ajaran = request.form.get('tahun_ajaran') # Seharusnya sama dengan tahun ajaran ekskul

            if not murid_id or not tahun_ajaran:
                flash("Murid dan tahun ajaran harus dipilih/diisi.", "danger")
            else:
                murid_id = int(murid_id)
                if self.con.register_student_for_ekskul(murid_id, ekskul_id, tahun_ajaran, 
                                                         status_pendaftaran='Disetujui', 
                                                         catatan_admin=f"Didaftarkan oleh Guru: {session.get('nama_lengkap')}"):
                    murid_info = self.con.get_user_by_id(murid_id)
                    flash(f"Murid '{murid_info['nama_lengkap'] if murid_info else 'ID '+str(murid_id)}' berhasil ditambahkan ke ekskul '{ekskul_info['nama_ekskul']}'.", "success")
                else:
                    flash("Gagal menambahkan murid. Mungkin sudah terdaftar atau terjadi kesalahan.", "danger")
            return redirect(url_for('kelola_peserta_ekskul_guru', ekskul_id=ekskul_id))

        # --- Keluarkan Peserta dari Ekskul oleh Guru (Mirip dengan admin, tapi dengan cek kepemilikan) ---
        @self.app.route('/guru/ekskul/remove_peserta/<int:pendaftaran_id>', methods=['POST'])
        @self.guru_login_required
        def remove_peserta_ekskul_guru(pendaftaran_id):
            guru_id = session.get('user_id')
            ekskul_id_redirect = request.form.get('ekskul_id_redirect') # Untuk redirect kembali

            # TODO: Validasi penting: Cek apakah pendaftaran_id ini milik ekskul yang dibina oleh guru_id yang login.
            # Ini memerlukan query tambahan di Config untuk mendapatkan detail pendaftaran
            # atau memvalidasi id_guru_pembina dari ekskul yang terkait pendaftaran_id.
            # Untuk sementara, kita asumsikan valid jika guru mengaksesnya dari halaman yang benar.

            if self.con.update_ekskul_registration_status(pendaftaran_id, new_status='Berhenti', 
                                                            catatan_admin=f"Dikeluarkan oleh Guru: {session.get('nama_lengkap')}"):
                flash(f"Status pendaftaran (ID: {pendaftaran_id}) diubah menjadi 'Berhenti'.", "success")
            else:
                flash("Gagal mengubah status pendaftaran.", "danger")
            
            if ekskul_id_redirect:
                return redirect(url_for('kelola_peserta_ekskul_guru', ekskul_id=int(ekskul_id_redirect)))
            return redirect(url_for('dashboard_guru')) # Fallback

        # --- Rute Dashboard Murid (Placeholder) ---
        @self.app.route('/murid/dashboard') # COPAS DARI SEBELUMNYA
        @self.murid_login_required 
        def dashboard_murid():
            return render_template('murid/dashboard_murid.html', nama_murid=session.get('nama_lengkap'))



    def run(self):
        self.app.run(debug=True, host='0.0.0.0', port=5001) 

if __name__ == "__main__":
    portal = Portal()
    portal.run()