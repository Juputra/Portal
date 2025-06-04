from flask import Flask, flash, redirect, render_template, request, url_for, session
from werkzeug.security import check_password_hash # generate_password_hash sekarang ada di Config
from functools import wraps
from config import Config # Mengimpor kelas Config dari file config.py Anda
import os
from datetime import date, datetime, timedelta
import datetime
from werkzeug.utils import secure_filename
from collections import defaultdict
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
        self.app.config['UPLOAD_FOLDER'] = os.path.join(self.app.root_path, 'static/uploads/materi_ekskul') 
        self.app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}
        @self.app.context_processor
        def inject_now():
            from datetime import datetime # Pastikan datetime diimpor di sini jika belum global
            return {'now': datetime.utcnow()} # atau datetime.now()



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
            counts = self.con.get_counts()
            # Ambil data untuk setiap tab
            gurus = self.con.get_users_by_role('guru')
            murids = self.con.get_users_by_role('murid')
            admins = self.con.get_users_by_role('admin')
            ekskul_list = self.con.get_all_ekskul()
            list_materi = self.con.get_all_materi_ekskul()
            pending_registrations = self.con.get_pending_registrations_detailed() # Untuk Admin
            list_pengumuman = self.con.get_all_pengumuman()
            absensi_list = self.con.get_all_absensi_ekskul_detailed() # Untuk Admin

            raw_absensi_list = self.con.get_all_absensi_ekskul_detailed() 
            absensi_list_processed = [] # List baru untuk data yang sudah diproses

            for absen_item_raw in raw_absensi_list:
                # Konversi ke dictionary jika hasil dari database adalah tuple atau tipe lain
                # Jika sudah dictionary, Anda bisa langsung .copy()
                if hasattr(absen_item_raw, '_asdict'): # Untuk namedtuple
                    absen_item = absen_item_raw._asdict().copy()
                elif isinstance(absen_item_raw, dict): # Untuk dictionary
                    absen_item = absen_item_raw.copy()
                else:
                    # Tambahkan penanganan jika tipe datanya berbeda atau perlu konversi manual
                    # Untuk sekarang, kita asumsikan bisa di-copy atau adalah dictionary
                    # Jika tidak, Anda perlu menyesuaikan cara Anda mengakses field di bawah
                    absen_item = dict(absen_item_raw) # Contoh fallback, sesuaikan jika perlu

                jam_mulai = absen_item.get('jam_mulai_kegiatan')
                
                if jam_mulai is None:
                    absen_item['jam_mulai_kegiatan_formatted'] = '-'
                elif isinstance(jam_mulai, str):
                    # Jika sudah string (misalnya sudah diformat dari DB atau input manual)
                    absen_item['jam_mulai_kegiatan_formatted'] = jam_mulai
                elif hasattr(jam_mulai, 'strftime'): 
                    # Untuk objek datetime.time atau datetime.datetime
                    absen_item['jam_mulai_kegiatan_formatted'] = jam_mulai.strftime('%H:%M')
                elif isinstance(jam_mulai, timedelta): 
                    # Penanganan khusus untuk objek datetime.timedelta
                    total_seconds = int(jam_mulai.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    absen_item['jam_mulai_kegiatan_formatted'] = f"{hours:02d}:{minutes:02d}"
                else:
                    # Fallback jika tipe datanya tidak dikenali
                    absen_item['jam_mulai_kegiatan_formatted'] = str(jam_mulai) 

                absensi_list_processed.append(absen_item)

            return render_template('admin/dashboard_admin.html', 
                                jumlah_pengguna=counts.get('users',0), 
                                jumlah_ekskul=counts.get('ekskul',0), 
                                jumlah_pengumuman=counts.get('pengumuman',0),
                                jumlah_materi_ekskul=counts.get('materi_ekskul',0),
                                # Data untuk tab-tab
                                gurus=gurus,
                                murids=murids,
                                admins=admins,
                                ekskul_list=ekskul_list,
                                list_materi=list_materi,
                                pending_registrations=pending_registrations,
                                list_pengumuman=list_pengumuman,
                                absensi_list=absensi_list
                                )

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
                return redirect(url_for('dashboard_admin') + '#pengguna-content')

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
                        return redirect(url_for('dashboard_admin') + '#pengguna-content')
                    else:
                        flash('Gagal mengupdate data pengguna. Periksa log server.', 'danger')
                # Jika validasi gagal atau update gagal, render form lagi dengan data yang ada
                # Kita perlu mengisi kembali user_to_edit dengan data form agar perubahan tidak hilang
                user_to_edit.update(user_data) 
                if 'password' in user_to_edit: del user_to_edit['password'] # jangan kirim password plain ke template

            return render_template('admin/user_form_admin.html', action='Edit', user_data=user_to_edit, cancel_url=url_for('dashboard_admin') + '#pengguna-content')
        
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
                        return redirect(url_for('dashboard_admin') + '#ekskul-content')
                    else:
                        flash('Gagal menambahkan ekstrakurikuler. Periksa log server.', 'danger')
                
            list_guru = self.con.get_users_by_role('guru') # Menggunakan metode dari Config Anda
            return render_template('admin/ekskul_form_admin.html', action='Tambah', ekskul_data=None, list_guru=list_guru, cancel_url=url_for('dashboard_admin') + '#ekskul-content')

        # --- Edit Ekstrakurikuler (Admin) ---
        @self.app.route('/admin/ekskul/edit/<int:ekskul_id>', methods=['GET', 'POST'])
        @self.admin_login_required
        def edit_ekskul_admin(ekskul_id):
            ekskul_to_edit = self.con.get_ekskul_by_id(ekskul_id) # Anda perlu buat metode ini di Config
            if not ekskul_to_edit:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan.", 'danger')
                return redirect(url_for('dashboard_admin') + '#ekskul-content')
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
                        return redirect(url_for('dashboard_admin') + '#ekskul-content')
                    else:
                        flash('Gagal mengupdate data ekstrakurikuler. Periksa log server.', 'danger')
                ekskul_to_edit.update(ekskul_data)
                
            list_guru = self.con.get_users_by_role('guru')
            return render_template('admin/ekskul_form_admin.html', action='Edit', ekskul_data=ekskul_to_edit, list_guru=list_guru, cancel_url=url_for('dashboard_admin') + '#ekskul-content')

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
            list_materi_ekskul = self.con.get_materi_by_ekskul_id(ekskul_id) 
            return render_template('admin/ekskul_detail_admin.html', 
                                   ekskul_info=ekskul_info, 
                                   members=members,
                                   list_materi=list_materi_ekskul,
                                   tahun_ajaran_display=current_tahun_ajaran)

        # --- Daftarkan Murid ke Ekstrakurikuler (Admin) ---
        @self.app.route('/admin/ekskul/<int:ekskul_id>/register', methods=['GET', 'POST'])
        @self.admin_login_required
        def register_student_ekskul_admin(ekskul_id):
            ekskul_info = self.con.get_ekskul_by_id(ekskul_id)
            if not ekskul_info:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan.", 'danger')
                return redirect(url_for('dashboard_admin') + '#ekskul-content')

            if request.method == 'POST':
                murid_id_to_register_str = request.form.get('id_murid')
                tahun_ajaran = request.form.get('tahun_ajaran')

                if not murid_id_to_register_str or not tahun_ajaran:
                    flash("Pilih murid dan masukkan tahun ajaran.", "warning")
                else:
                    try:
                        murid_id_to_register = int(murid_id_to_register_str)
                        catatan_pendaftar = f"Didaftarkan oleh Admin: {session.get('nama_lengkap')}"
                        
                        # Panggil metode yang sudah diupdate di Config
                        hasil_pendaftaran = self.con.register_student_for_ekskul(
                            murid_id_to_register, 
                            ekskul_id, 
                            tahun_ajaran, 
                            status_pendaftaran='Disetujui', # Admin langsung menyetujui
                            catatan_pendaftar=catatan_pendaftar
                        )

                        if isinstance(hasil_pendaftaran, int): # Berhasil, mengembalikan ID pendaftaran
                            murid_info = self.con.get_user_by_id(murid_id_to_register)
                            flash(f"Murid '{murid_info['nama_lengkap'] if murid_info else 'ID: '+str(murid_id_to_register)}' berhasil didaftarkan ke ekskul '{ekskul_info['nama_ekskul']}'.", 'success')
                            return redirect(url_for('ekskul_detail_admin', ekskul_id=ekskul_id))
                        elif hasil_pendaftaran == "KUOTA_PENUH":
                            flash(f"Gagal mendaftarkan murid. Kuota untuk ekskul '{ekskul_info['nama_ekskul']}' sudah penuh.", "warning")
                        elif hasil_pendaftaran == "SUDAH_TERDAFTAR":
                            murid_info = self.con.get_user_by_id(murid_id_to_register) # Ambil info murid untuk pesan
                            flash(f"Gagal mendaftarkan murid '{murid_info['nama_lengkap'] if murid_info else 'ID: '+str(murid_id_to_register)}'. Murid tersebut sudah memiliki record pendaftaran di ekskul '{ekskul_info['nama_ekskul']}' untuk tahun ajaran ini.", "warning")
                        elif hasil_pendaftaran == "EKSKUL_NOT_FOUND": # Meskipun sudah dicek di awal, ini untuk konsistensi
                            flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan saat proses pendaftaran.", 'danger')
                        else: # hasil_pendaftaran adalah False atau None (error umum)
                            flash(f"Gagal mendaftarkan murid ke ekskul '{ekskul_info['nama_ekskul']}'. Terjadi kesalahan pada sistem.", 'danger')
                    
                    except ValueError:
                        flash("ID Murid tidak valid.", "danger")
                    except Exception as e:
                        flash(f"Terjadi kesalahan internal: {e}", "danger")
                        print(f"Error di register_student_ekskul_admin: {e}")
                
                # Jika ada flash error atau warning, kita ingin kembali ke form dengan data yang mungkin sudah diisi
                # Namun, karena ini redirect, data form tidak akan terbawa kecuali kita pass lagi
                # Untuk kesederhanaan, kita redirect ke halaman GET form lagi
                return redirect(url_for('register_student_ekskul_admin', ekskul_id=ekskul_id))

            # Bagian GET request
            # Tentukan tahun ajaran aktif untuk dropdown dan filter
            current_tahun_ajaran = self.con.get_tahun_ajaran_aktif() if hasattr(self.con, 'get_tahun_ajaran_aktif') else "2024/2025" # GANTI INI
            available_students = self.con.get_all_active_murid_exclude_ekskul(ekskul_id, current_tahun_ajaran)
            
            return render_template('admin/register_student_ekskul_form.html', 
                                   ekskul_info=ekskul_info, 
                                   available_students=available_students, 
                                   current_tahun_ajaran=current_tahun_ajaran,
                                   cancel_url=url_for('ekskul_detail_admin', ekskul_id=ekskul_id))

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
            # Ambil id_ekskul_default dari query parameter jika ada
            id_ekskul_default = request.args.get('id_ekskul_default', type=int)
            
            # Siapkan data untuk form, terutama untuk pre-fill id_ekskul jika dari tombol "Tambah Materi untuk Ekskul Ini"
            materi_data_for_form = None
            if id_ekskul_default and request.method == 'GET': # Hanya pre-fill untuk GET request
                materi_data_for_form = {'id_ekskul': id_ekskul_default}
            if request.method == 'POST':
                id_ekskul = request.form.get('id_ekskul')
                judul_materi = request.form.get('judul_materi','').strip()
                deskripsi_materi = request.form.get('deskripsi_materi','').strip()
                tipe_konten = request.form.get('tipe_konten')
                
                path_konten_final = None # Untuk menyimpan nama file, URL, atau None
                isi_konten_teks_final = None

                if not id_ekskul or not judul_materi or not tipe_konten:
                    flash("Ekskul, Judul Materi, dan Tipe Konten wajib diisi.", "danger")
                else:
                    id_ekskul = int(id_ekskul)
                    save_to_db = False # Flag apakah data valid untuk disimpan

                    if tipe_konten == 'file':
                        if 'file_konten' not in request.files:
                            flash('Tidak ada bagian file yang dipilih untuk diunggah.', 'danger')
                        else:
                            file = request.files['file_konten']
                            if file.filename == '':
                                flash('Tidak ada file yang dipilih untuk diunggah.', 'danger')
                            elif file and allowed_file(file.filename, self.app.config['ALLOWED_EXTENSIONS']):
                                filename = secure_filename(file.filename) # Amankan nama file
                                
                                # Buat direktori upload jika belum ada
                                upload_path_dir = self.app.config['UPLOAD_FOLDER']
                                if not os.path.exists(upload_path_dir):
                                    os.makedirs(upload_path_dir, exist_ok=True) # exist_ok=True agar tidak error jika folder sudah ada
                                
                                file_path_tujuan = os.path.join(upload_path_dir, filename)
                                
                                # Cek jika file dengan nama sama sudah ada untuk menghindari penimpaan tidak sengaja
                                # Anda bisa menambahkan angka atau timestamp ke nama file jika ingin unik
                                # if os.path.exists(file_path_tujuan):
                                #     flash(f'File dengan nama {filename} sudah ada. Silakan ganti nama file atau hapus yang lama.', 'warning')
                                # else:
                                file.save(file_path_tujuan)
                                path_konten_final = filename # Simpan nama file (atau path relatif jika perlu)
                                save_to_db = True
                                flash(f'File {filename} berhasil diunggah.', 'info')
                            elif file: # Jika file ada tapi tidak diizinkan
                                flash('Tipe file tidak diizinkan. Ekstensi yang diizinkan: ' + ', '.join(self.app.config['ALLOWED_EXTENSIONS']), 'danger')
                    
                    elif tipe_konten in ['link', 'video_embed']:
                        path_konten_final = request.form.get('path_konten_atau_link_url','').strip()
                        if not path_konten_final:
                             flash('URL/Link atau Kode Embed Video wajib diisi untuk tipe ini.', 'danger')
                        else:
                            save_to_db = True
                    
                    elif tipe_konten == 'teks':
                        isi_konten_teks_final = request.form.get('isi_konten_teks_area','').strip()
                        if not isi_konten_teks_final:
                            flash('Isi konten teks wajib diisi untuk tipe ini.', 'danger')
                        else:
                            save_to_db = True
                    
                    else: # Tipe konten tidak valid
                        flash('Tipe konten tidak valid dipilih.', 'danger')

                    if save_to_db:
                        data_materi = {
                            'id_ekskul': id_ekskul,
                            'judul_materi': judul_materi,
                            'deskripsi_materi': deskripsi_materi,
                            'tipe_konten': tipe_konten,
                            'path_konten_atau_link': path_konten_final,
                            'isi_konten_teks': isi_konten_teks_final,
                            'id_pengunggah': session['user_id']
                        }
                        materi_id = self.con.add_materi_ekskul(data_materi)
                        if materi_id:
                            flash("Materi ekstrakurikuler berhasil ditambahkan!", "success")
                            return redirect(url_for('dashboard_admin') + '#materi-content')
                        else:
                            flash("Gagal menambahkan materi ke database. Periksa log server.", "danger")
            
            list_ekskul = self.con.get_all_ekskul()
            return render_template('admin/materi_ekskul_form_admin.html', 
                                   action="Tambah", 
                                   materi_data=request.form if request.method == 'POST' else None, # Kirim data form kembali jika ada error
                                   list_ekskul=list_ekskul,
                                   cancel_url=url_for('dashboard_admin') + '#materi-content')
        @self.app.route('/admin/materi_ekskul/edit/<int:id_materi_ekskul>', methods=['GET', 'POST'])
        @self.admin_login_required
        def edit_materi_ekskul_admin(id_materi_ekskul):
            materi_data_lama = self.con.get_materi_ekskul_by_id(id_materi_ekskul)
            if not materi_data_lama:
                flash("Materi ekstrakurikuler tidak ditemukan.", "danger")
                return redirect(url_for('dashboard_admin') + '#materi-content')

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
                                               list_ekskul=list_ekskul, id_materi_ekskul=id_materi_ekskul, cancel_url=url_for('dashboard_admin') + '#materi-content')


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
                    return redirect(url_for('dashboard_admin') + '#materi-content')
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
                                       list_ekskul=list_ekskul, id_materi_ekskul=id_materi_ekskul,cancel_url=url_for('dashboard_admin') + '#materi-content')


            list_ekskul = self.con.get_all_ekskul()
            # Untuk form edit, materi_data_lama sudah berisi semua field dari database
            # Termasuk path_konten_atau_link dan isi_konten_teks yang benar
            return render_template('admin/materi_ekskul_form_admin.html', 
                                   action="Edit", 
                                   materi_data=materi_data_lama, 
                                   list_ekskul=list_ekskul,
                                   id_materi_ekskul=id_materi_ekskul, cancel_url=url_for('dashboard_admin') + '#materi-content')


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
        
        @self.app.route('/admin/ekskul/pendaftaran')
        @self.admin_login_required
        def kelola_pendaftaran_ekskul_admin():
                # Admin melihat semua pendaftaran yang menunggu persetujuan
                pending_registrations = self.con.get_pending_registrations_detailed()
                return render_template('admin/kelola_pendaftaran_ekskul.html', 
                                       pending_registrations=pending_registrations,
                                       judul_halaman="Kelola Semua Pendaftaran Ekskul")

        @self.app.route('/admin/ekskul/pendaftaran/<int:pendaftaran_id>/setujui', methods=['POST'])
        @self.admin_login_required
        def setujui_pendaftaran_admin(pendaftaran_id):
                catatan = f"Disetujui oleh Admin: {session.get('nama_lengkap')}"
                # Panggil metode yang sudah ada di Config.py
                # Metode ini akan mengecek kuota juga sebelum menyetujui
                # Jika register_student_for_ekskul sudah handle semua, Anda bisa panggil itu
                # atau pastikan update_ekskul_registration_status juga cek kuota.
                
                # Untuk menyederhanakan, kita langsung update status. Pengecekan kuota IDEALNYA
                # ada di sini atau di metode update_ekskul_registration_status jika diubah
                # untuk kasus 'Disetujui'.

                # Cek kuota sebelum menyetujui
                pendaftaran_info = self.con.get_pendaftaran_ekskul_by_id(pendaftaran_id) # Buat metode ini jika belum ada
                if not pendaftaran_info:
                    flash("Data pendaftaran tidak ditemukan.", "danger")
                    return redirect(url_for('kelola_pendaftaran_ekskul_admin'))

                ekskul_info = self.con.get_ekskul_by_id(pendaftaran_info['id_ekskul'])
                if ekskul_info and ekskul_info.get('kuota_maksimal') is not None:
                    jumlah_peserta_aktif = self.con.count_active_members_ekskul(pendaftaran_info['id_ekskul'], pendaftaran_info['tahun_ajaran']) # Buat metode ini
                    if jumlah_peserta_aktif >= ekskul_info['kuota_maksimal']:
                        flash(f"Kuota untuk ekskul '{ekskul_info['nama_ekskul']}' sudah penuh. Pendaftaran tidak dapat disetujui.", "warning")
                        # Otomatis tolak jika kuota penuh saat approval
                        self.con.update_ekskul_registration_status(pendaftaran_id, 'Ditolak', f"Ditolak otomatis karena kuota penuh saat approval oleh Admin: {session.get('nama_lengkap')}")
                        return redirect(request.referrer or url_for('kelola_pendaftaran_ekskul_admin'))


                if self.con.update_ekskul_registration_status(pendaftaran_id, 'Disetujui', catatan):
                    flash('Pendaftaran berhasil disetujui.', 'success')
                else:
                    flash('Gagal menyetujui pendaftaran.', 'danger')
                return redirect(request.referrer or url_for('kelola_pendaftaran_ekskul_admin')) # Kembali ke halaman sebelumnya

        @self.app.route('/admin/ekskul/pendaftaran/<int:pendaftaran_id>/tolak', methods=['POST'])
        @self.admin_login_required
        def tolak_pendaftaran_admin(pendaftaran_id):
                # Anda bisa menambahkan field alasan penolakan di form jika mau
                alasan = request.form.get('alasan_penolakan', 'Ditolak oleh Admin.')
                catatan = f"{alasan} (Admin: {session.get('nama_lengkap')})"
                if self.con.update_ekskul_registration_status(pendaftaran_id, 'Ditolak', catatan):
                    flash('Pendaftaran berhasil ditolak.', 'success')
                else:
                    flash('Gagal menolak pendaftaran.', 'danger')
                return redirect(request.referrer or url_for('kelola_pendaftaran_ekskul_admin'))

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
                if target_peran == "":
                    target_peran_db = 'semua'
                elif target_peran in ['admin', 'guru', 'murid']:
                    target_peran_db = target_peran
                else: # Jika tidak ada yang dipilih atau nilai tidak valid, bisa default ke NULL atau 'semua'
                      # Tergantung bagaimana Anda ingin menangani jika tidak ada target peran spesifik
                      # namun ada target kelas atau ekskul. Untuk "Semua Peran" dari dropdown, ini akan jadi 'semua'.
                    target_peran_db = None # Atau 'semua' jika itu default jika target lain juga kosong 
                # Ambil target_kelas_id dan target_ekskul_id, pastikan integer atau None
                target_ekskul_id_str = request.form.get('target_ekskul_id')
                target_ekskul_id = int(target_ekskul_id_str) if target_ekskul_id_str and target_ekskul_id_str.isdigit() else None

                if not judul or not isi:
                    flash("Judul dan Isi pengumuman wajib diisi.", "danger")
                else:
                    data_pengumuman = {
                        'judul_pengumuman': judul,
                        'isi_pengumuman': isi,
                        'id_pembuat': session['user_id'], # ID admin yang login
                        'target_peran': target_peran_db, # Jika "" jadikan None
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
         # Asumsi metode ini sudah ada
            list_ekskul = self.con.get_all_ekskul() # Asumsi metode ini sudah ada
            
            return render_template('admin/pengumuman_form_admin.html', 
                                   action="Tambah", 
                                   pengumuman_data=None,
                                   list_ekskul=list_ekskul,
                                   cancel_url=url_for('dashboard_admin') + '#pengumuman-content')

        @self.app.route('/admin/pengumuman/edit/<int:id_pengumuman>', methods=['GET', 'POST'])
        @self.admin_login_required
        def edit_pengumuman_admin(id_pengumuman):
            pengumuman_to_edit = self.con.get_pengumuman_by_id(id_pengumuman)
            if not pengumuman_to_edit:
                flash(f"Pengumuman dengan ID {id_pengumuman} tidak ditemukan.", "danger")
                return redirect(url_for('dashboard_admin') + '#pengumuman-content')

            if request.method == 'POST':
                judul = request.form.get('judul_pengumuman','').strip()
                isi = request.form.get('isi_pengumuman','').strip()
                target_peran = request.form.get('target_peran')
                if target_peran == "":
                    target_peran_db = 'semua'
                elif target_peran in ['admin', 'guru', 'murid']:
                    target_peran_db = target_peran
                else: # Jika tidak ada yang dipilih atau nilai tidak valid, bisa default ke NULL atau 'semua'
                      # Tergantung bagaimana Anda ingin menangani jika tidak ada target peran spesifik
                      # namun ada target kelas atau ekskul. Untuk "Semua Peran" dari dropdown, ini akan jadi 'semua'.
                    target_peran_db = None # Atau 'semua' jika itu default jika target lain juga kosong 
                
                target_ekskul_id_str = request.form.get('target_ekskul_id')
                target_ekskul_id = int(target_ekskul_id_str) if target_ekskul_id_str and target_ekskul_id_str.isdigit() else None

                if not judul or not isi:
                    flash("Judul dan Isi pengumuman wajib diisi.", "danger")
                    # Untuk mengisi ulang form dengan data yang baru diinput jika ada error validasi
                    # Kita perlu membuat dict baru dari request.form dan menggabungkannya dengan data asli
                    # agar field yang tidak ada di form (seperti id_pembuat) tidak hilang
                    current_form_data = pengumuman_to_edit.copy() # Salin data asli
                    current_form_data.update(dict(request.form)) # Timpa dengan data form
                    # Konversi ID kembali ke int atau None karena request.form selalu string
                    current_form_data['target_ekskul_id'] = target_ekskul_id
                else:
                    data_pengumuman_update = {
                        'judul_pengumuman': judul,
                        'isi_pengumuman': isi,
                        'target_peran': target_peran_db,
                        'target_ekskul_id': target_ekskul_id
                        # id_pembuat dan tanggal_publikasi tidak diubah saat edit
                    }
                    if self.con.update_pengumuman(id_pengumuman, data_pengumuman_update):
                        flash("Pengumuman berhasil diperbarui!", "success")
                        return redirect(url_for('dashboard_admin') + '#pengumuman-content')
                    else:
                        flash("Gagal memperbarui pengumuman. Periksa log server.", "danger")
                        current_form_data = pengumuman_to_edit.copy()
                        current_form_data.update(dict(request.form))
                        current_form_data['target_ekskul_id'] = target_ekskul_id
                
                # Jika POST gagal atau validasi gagal, render form lagi)
                list_ekskul = self.con.get_all_ekskul()
                return render_template('admin/pengumuman_form_admin.html', 
                                   action="Edit", 
                                   pengumuman_data=current_form_data if 'current_form_data' in locals() else pengumuman_to_edit, 
                                   list_ekskul=list_ekskul,
                                   id_pengumuman=id_pengumuman,
                                   cancel_url=url_for('dashboard_admin') + '#pengumuman-content') # Penting untuk action form

            # Untuk GET request)
            list_ekskul = self.con.get_all_ekskul()
            return render_template('admin/pengumuman_form_admin.html', 
                                   action="Edit", 
                                   pengumuman_data=pengumuman_to_edit, 
                                   list_ekskul=list_ekskul,
                                   id_pengumuman=id_pengumuman)

        @self.app.route('/admin/pengumuman/hapus/<int:id_pengumuman>', methods=['POST']) # Hanya POST untuk keamanan
        @self.admin_login_required
        def hapus_pengumuman_admin(id_pengumuman):
            # Ambil judul untuk pesan flash sebelum dihapus
            pengumuman_to_delete = self.con.get_pengumuman_by_id(id_pengumuman)
            judul_pengumuman = pengumuman_to_delete['judul_pengumuman'] if pengumuman_to_delete else f"ID {id_pengumuman}"

            if self.con.delete_pengumuman(id_pengumuman):
                flash(f"Pengumuman '{judul_pengumuman}' berhasil dihapus.", "success")
            else:
                flash(f"Gagal menghapus pengumuman '{judul_pengumuman}'.", "danger")
            return redirect(url_for('pengumuman_admin'))
    
    # --- Manajemen Absensi Ekskul oleh Admin ---
        @self.app.route('/admin/absensi_ekskul')
        @self.admin_login_required
        def list_absensi_ekskul_admin():
            # Tambahkan filter jika perlu dari request.args
            # Untuk contoh, kita ambil semua
            absensi_list = self.con.get_all_absensi_ekskul_detailed()
            return render_template('admin/absensi_ekskul_list.html', absensi_list=absensi_list)
        
        @self.app.route('/admin/absensi_ekskul/manage', methods=['GET', 'POST']) 
        @self.app.route('/admin/absensi_ekskul/manage/<int:id_pendaftaran_ekskul>/<tanggal_kegiatan_str>', methods=['GET', 'POST'])
        @self.admin_login_required
        def manage_absensi_ekskul_admin(id_pendaftaran_ekskul=None, tanggal_kegiatan_str=None):
            action = "Edit" if id_pendaftaran_ekskul and tanggal_kegiatan_str else "Tambah"
            
            # Inisialisasi variabel form_data dan default di awal
            form_data = {
                'id_murid': None,
                'id_ekskul': None,
                'status_kehadiran': 'Hadir', # Default untuk Tambah
                'tanggal_kegiatan': date.today().isoformat(),
                'tahun_ajaran': self.con.get_tahun_ajaran_aktif() if hasattr(self.con, 'get_tahun_ajaran_aktif') else "2024/2025",
                'jam_mulai_kegiatan': '',
                'catatan': ''
            }
            
            # Inisialisasi default_tahun_ajaran_val di sini
            default_tahun_ajaran_val = self.con.get_tahun_ajaran_aktif() if hasattr(self.con, 'get_tahun_ajaran_aktif') else "2024/2025"
            default_tanggal_untuk_form = date.today().isoformat() # Dipakai untuk GET Tambah
            
            # Data asli dari DB (hanya relevan untuk mode Edit)
            original_db_data_for_edit = None 

            if action == "Edit":
                try:
                    db_entry = self.con.get_absensi_entry_for_edit(id_pendaftaran_ekskul, tanggal_kegiatan_str)
                    if db_entry:
                        original_db_data_for_edit = dict(db_entry) # Simpan data asli untuk POST error
                        form_data['id_murid'] = db_entry.get('id_murid')
                        form_data['id_ekskul'] = db_entry.get('id_ekskul')
                        form_data['status_kehadiran'] = db_entry.get('status_kehadiran')
                        form_data['tanggal_kegiatan'] = tanggal_kegiatan_str 
                        form_data['tahun_ajaran'] = db_entry.get('tahun_ajaran')
                        form_data['jam_mulai_kegiatan'] = db_entry.get('jam_mulai_kegiatan')
                        form_data['catatan'] = db_entry.get('catatan')
                        
                        # Update default_tahun_ajaran_val jika ada tahun ajaran spesifik dari data edit
                        default_tahun_ajaran_val = db_entry.get('tahun_ajaran', default_tahun_ajaran_val)
                        default_tanggal_untuk_form = tanggal_kegiatan_str # Untuk konsistensi
                    else:
                        flash("Data absensi yang akan diedit tidak ditemukan.", "warning")
                        return redirect(url_for('dashboard_admin') + '#absensi-ekskul-content')
                except ValueError:
                    flash("Format tanggal untuk edit tidak valid.", "danger")
                    return redirect(url_for('dashboard_admin') + '#absensi-ekskul-content')
                except Exception as e:
                    flash(f"Error mengambil data untuk diedit: {e}", "danger")
                    return redirect(url_for('dashboard_admin') + '#absensi-ekskul-content')

            if request.method == 'POST':
                admin_id = session['user_id']
                
                submitted_status_kehadiran = request.form.get('status_kehadiran')
                submitted_catatan_absen = request.form.get('catatan_absen', '')
                submitted_jam_kegiatan = request.form.get('jam_kegiatan') or None
                submitted_tanggal_kegiatan = request.form.get('tanggal_kegiatan')
                submitted_tahun_ajaran_pendaftaran = request.form.get('tahun_ajaran_pendaftaran')
                submitted_id_murid_str = request.form.get('id_murid') # Akan None jika 'Edit' karena disabled
                submitted_id_ekskul_str = request.form.get('id_ekskul') # Akan None jika 'Edit' karena disabled

                # Siapkan data untuk mengisi ulang form jika ada error
                # Mulai dengan data yang ada di form_data (hasil GET Edit atau default Tambah)
                form_data_on_post_error = form_data.copy() 

                if action == "Edit":
                    # Untuk Edit, field yg disabled/readonly tidak berubah dari original_db_data_for_edit
                    # Hanya update field yang bisa diubah dari form
                    if original_db_data_for_edit: # Pastikan ini ada
                        form_data_on_post_error['id_murid'] = original_db_data_for_edit.get('id_murid')
                        form_data_on_post_error['id_ekskul'] = original_db_data_for_edit.get('id_ekskul')
                        form_data_on_post_error['tanggal_kegiatan'] = tanggal_kegiatan_str # Dari URL, tidak berubah
                        form_data_on_post_error['tahun_ajaran'] = original_db_data_for_edit.get('tahun_ajaran') # Dari DB, tidak berubah
                    # Update dengan inputan pengguna untuk field yang bisa diedit
                    form_data_on_post_error['status_kehadiran'] = submitted_status_kehadiran
                    form_data_on_post_error['catatan'] = submitted_catatan_absen
                    form_data_on_post_error['jam_mulai_kegiatan'] = submitted_jam_kegiatan
                else: # action == "Tambah"
                    form_data_on_post_error = {
                        'id_murid': int(submitted_id_murid_str) if submitted_id_murid_str and submitted_id_murid_str.isdigit() else None,
                        'id_ekskul': int(submitted_id_ekskul_str) if submitted_id_ekskul_str and submitted_id_ekskul_str.isdigit() else None,
                        'status_kehadiran': submitted_status_kehadiran,
                        'tanggal_kegiatan': submitted_tanggal_kegiatan,
                        'tahun_ajaran': submitted_tahun_ajaran_pendaftaran,
                        'catatan': submitted_catatan_absen,
                        'jam_mulai_kegiatan': submitted_jam_kegiatan
                    }
                
                validation_passed = True
                # Validasi untuk mode Tambah
                if action == "Tambah" and (not form_data_on_post_error.get('id_murid') or \
                                        not form_data_on_post_error.get('id_ekskul') or \
                                        not submitted_status_kehadiran or \
                                        not submitted_tanggal_kegiatan or \
                                        not submitted_tahun_ajaran_pendaftaran):
                    flash("Untuk Tambah: Murid, Ekskul, Status, Tanggal, dan Tahun Ajaran Pendaftaran wajib diisi.", 'danger')
                    validation_passed = False
                elif action == "Edit" and not submitted_status_kehadiran: # Validasi untuk mode Edit
                    flash("Status Kehadiran wajib diisi saat mengedit.", 'danger')
                    validation_passed = False
                
                if validation_passed:
                    id_murid_for_logic = form_data_on_post_error.get('id_murid')
                    id_ekskul_for_logic = form_data_on_post_error.get('id_ekskul')
                    tahun_ajaran_for_logic = form_data_on_post_error.get('tahun_ajaran')
                    tanggal_kegiatan_for_save = form_data_on_post_error.get('tanggal_kegiatan') # Tanggal untuk disimpan

                    current_id_pendaftaran_to_save = id_pendaftaran_ekskul 
                    if action == "Tambah":
                        current_id_pendaftaran_to_save = self.con.get_pendaftaran_ekskul_id(
                            id_murid_for_logic, id_ekskul_for_logic, tahun_ajaran_for_logic
                        )
                    
                    if current_id_pendaftaran_to_save:
                        if self.con.save_absensi_ekskul(
                            current_id_pendaftaran_to_save, 
                            tanggal_kegiatan_for_save, 
                            submitted_status_kehadiran, 
                            admin_id, 
                            submitted_catatan_absen, 
                            submitted_jam_kegiatan
                        ):
                            flash(f"Data absensi berhasil di{action.lower()}kan.", "success")
                            return redirect(url_for('dashboard_admin') + '#absensi-ekskul-content')
                        else:
                            flash("Gagal menyimpan data absensi ke database.", "danger")
                    elif action == "Tambah": 
                        flash(f"Murid tidak terdaftar di ekstrakurikuler pada tahun ajaran {tahun_ajaran_for_logic} atau pendaftaran tidak aktif/ditemukan.", "warning")
                
                # Jika validasi gagal atau simpan gagal, `form_data` diisi dengan `form_data_on_post_error`
                form_data = form_data_on_post_error

            # Untuk GET request mode "Tambah", pastikan nilai default sudah ada di form_data
            if request.method == 'GET' and action == "Tambah":
                form_data['tanggal_kegiatan'] = default_tanggal_untuk_form # Sudah diinisialisasi di atas
                form_data['tahun_ajaran'] = default_tahun_ajaran_val     # Sudah diinisialisasi di atas
                form_data['status_kehadiran'] = 'Hadir'
                form_data.setdefault('id_murid', None)
                form_data.setdefault('id_ekskul', None)
                form_data.setdefault('catatan', '')
                form_data.setdefault('jam_mulai_kegiatan', '')

            list_ekskul = self.con.get_all_ekskul() 
            all_murid = self.con.get_all_active_murid() if hasattr(self.con, 'get_all_active_murid') else self.con.get_users_by_role('murid')
                
            return render_template('admin/absensi_ekskul_form_admin.html', 
                                action=action, 
                                absensi_data=form_data, 
                                list_ekskul=list_ekskul, 
                                list_murid=all_murid,
                                # default_tahun_ajaran dan default_tanggal_absen untuk fallback di template
                                default_tahun_ajaran=form_data.get('tahun_ajaran', default_tahun_ajaran_val),
                                default_tanggal_absen=form_data.get('tanggal_kegiatan', default_tanggal_untuk_form),
                                id_pendaftaran_ekskul_edit=id_pendaftaran_ekskul, 
                                tanggal_kegiatan_edit=tanggal_kegiatan_str,
                                cancel_url=url_for('dashboard_admin') + '#absensi-ekskul-content')


        @self.app.route('/admin/absensi_ekskul/hapus/<int:id_absensi_ekskul>', methods=['POST'])
        @self.admin_login_required
        def hapus_absensi_ekskul_admin(id_absensi_ekskul):
            if self.con.delete_absensi_ekskul(id_absensi_ekskul):
                flash("Entri absensi berhasil dihapus.", "success")
            else:
                flash("Gagal menghapus entri absensi.", "danger")
            return redirect(url_for('dashboard_admin') + '#absensi-ekskul-content')

    # === Guru Route ===

    # --- Rute Dashboard Guru ---
        def _cek_guru_pembina_ekskul(ekskul_id_to_check): # Jika nested function di routes()
            """Helper untuk cek apakah guru yang login adalah pembina ekskul_id_to_check."""
            guru_id_session = session.get('user_id')
            # 'self.con' merujuk pada instance Config dari objek Portal
            ekskul = self.con.get_ekskul_by_id(ekskul_id_to_check) 
            if not ekskul:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id_to_check} tidak ditemukan.", "danger")
                return False, None 
            if ekskul.get('id_guru_pembina') != guru_id_session:
                flash("Anda tidak memiliki hak akses untuk mengelola fitur ini pada ekskul tersebut.", "danger")
                return False, ekskul 
            return True, ekskul

        @self.app.route('/guru/dashboard')
        @self.guru_login_required
        def dashboard_guru():
            guru_id = session.get('user_id')
            nama_guru = session.get('nama_lengkap')
            # Mengambil pengumuman untuk guru (misalnya, yang targetnya 'semua' atau 'guru')
            info_terbaru_guru = self.con.get_pengumuman_for_guru(guru_id) # Pastikan metode ini ada di Config
            
            jadwal_ekskul_guru = self.con.get_ekskul_by_pembina(guru_id)
            tahun_ajaran_aktif = self.con.get_tahun_ajaran_aktif() # Pastikan metode ini ada
            
            murid_untuk_absen = self.con.get_murid_options_for_guru_absen(guru_id, tahun_ajaran_aktif) # Pastikan metode ini ada
            
            # Ambil pendaftaran yang menunggu persetujuan untuk ekskul yang dibina guru ini
            pending_registrations_guru = self.con.get_pending_registrations_detailed(id_guru_pembina=guru_id) # Pastikan metode ini ada
            ekskul_list_semua = self.con.get_all_ekskul() # Ambil semua ekskul
            return render_template('guru/dashboard_guru.html', 
                                   nama_guru=nama_guru,
                                   jadwal_ekskul=jadwal_ekskul_guru,
                                   info_terbaru=info_terbaru_guru,
                                   murid_untuk_absen=murid_untuk_absen,
                                   ekskul_guru=jadwal_ekskul_guru,
                                    ekskul_list_semua=ekskul_list_semua, # Untuk dropdown form absen
                                   tahun_ajaran_aktif=tahun_ajaran_aktif,
                                   default_tanggal_absen=date.today().isoformat(),
                                   pending_registrations=pending_registrations_guru)

        @self.app.route('/guru/ekskul/semua')
        @self.guru_login_required
        def list_all_ekskul_guru():
            ekskul_list = self.con.get_all_ekskul() 
            return render_template('guru/list_semua_ekskul.html', 
                                   ekskul_list=ekskul_list, 
                                   nama_guru=session.get('nama_lengkap'))

        @self.app.route('/guru/ekskul/detail/<int:ekskul_id>')
        @self.guru_login_required
        def detail_ekskul_guru(ekskul_id):
            guru_id = session.get('user_id')
            ekskul_info = self.con.get_ekskul_by_id(ekskul_id)

            if not ekskul_info:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan.", 'danger')
                return redirect(url_for('list_all_ekskul_guru'))

            materi_list = self.con.get_materi_by_ekskul_id(ekskul_id)
            tahun_ajaran_aktif = self.con.get_tahun_ajaran_aktif()
            members = self.con.get_members_of_ekskul(ekskul_id, tahun_ajaran_aktif)
            is_pembina = (guru_id == ekskul_info.get('id_guru_pembina'))

            return render_template('guru/detail_ekskul_guru.html',
                                   ekskul_info=ekskul_info,
                                   materi_list=materi_list,
                                   members=members,
                                   is_pembina=is_pembina,
                                   nama_guru=session.get('nama_lengkap'),
                                   tahun_ajaran_aktif=tahun_ajaran_aktif)

        @self.app.route('/guru/absen/submit', methods=['POST'])
        @self.guru_login_required
        def submit_absen_guru():
            guru_id = session.get('user_id')
            try:
                murid_id_str = request.form.get('id_murid')
                ekskul_id_str = request.form.get('id_ekskul')
                status_kehadiran = request.form.get('status_kehadiran')
                tanggal_kegiatan = request.form.get('tanggal_kegiatan')
                # Ambil tahun ajaran dari form, atau default ke tahun ajaran aktif
                tahun_ajaran = request.form.get('tahun_ajaran') or self.con.get_tahun_ajaran_aktif()
                
                if not all([murid_id_str, ekskul_id_str, status_kehadiran, tanggal_kegiatan, tahun_ajaran]) or \
                   not murid_id_str.isdigit() or not ekskul_id_str.isdigit():
                    flash("Data absen tidak lengkap atau ID tidak valid. Murid, Ekskul, Status, Tanggal, dan Tahun Ajaran wajib diisi.", 'danger')
                    return redirect(url_for('dashboard_guru'))

                murid_id = int(murid_id_str)
                ekskul_id = int(ekskul_id_str)
                
                # Verifikasi guru adalah pembina ekskul yang dipilih untuk absen
                # _cek_guru_pembina_ekskul mengembalikan (True/False, ekskul_info_or_None)
                is_pembina_for_absen, _ = _cek_guru_pembina_ekskul(ekskul_id) 
                if not is_pembina_for_absen:
                    # Flash message sudah dihandle oleh _cek_guru_pembina_ekskul
                    return redirect(url_for('dashboard_guru'))

                catatan = request.form.get('catatan_absen', '')
                jam_kegiatan = request.form.get('jam_kegiatan') or None # Akan jadi None jika string kosong

                id_pendaftaran_ekskul = self.con.get_pendaftaran_ekskul_id(murid_id, ekskul_id, tahun_ajaran)

                if id_pendaftaran_ekskul:
                    if self.con.save_absensi_ekskul(id_pendaftaran_ekskul, tanggal_kegiatan, status_kehadiran, guru_id, catatan, jam_kegiatan):
                        flash("Data absensi berhasil disimpan/diperbarui.", "success")
                    else:
                        flash("Gagal menyimpan data absensi. Terjadi kesalahan pada database.", "danger")
                else:
                    flash(f"Murid tidak terdaftar secara aktif di ekstrakurikuler tersebut pada tahun ajaran {tahun_ajaran}.", "warning")
            
            except ValueError: # Untuk int() conversion errors
                flash("ID Murid atau ID Ekskul tidak valid.", "danger")
            except Exception as e:
                flash(f"Terjadi kesalahan internal saat submit absen: {e}", "danger")
                print(f"Error saat submit absen oleh guru: {e}") 

            return redirect(url_for('dashboard_guru'))
            
        @self.app.route('/guru/ekskul/pendaftaran/<int:pendaftaran_id>/setujui', methods=['POST'])
        @self.guru_login_required
        def setujui_pendaftaran_guru(pendaftaran_id):
            guru_id_session = session.get('user_id')
            pendaftaran_info = self.con.get_pendaftaran_ekskul_by_id(pendaftaran_id)

            if not pendaftaran_info:
                flash("Data pendaftaran tidak ditemukan.", "danger")
                return redirect(request.referrer or url_for('dashboard_guru'))

            # Cek apakah guru yang login adalah pembina dari ekskul terkait
            is_pembina_of_ekskul, ekskul_info = _cek_guru_pembina_ekskul(pendaftaran_info['id_ekskul'])
            if not is_pembina_of_ekskul:
                # Flash message sudah dihandle oleh _cek_guru_pembina_ekskul
                return redirect(request.referrer or url_for('dashboard_guru'))

            # Cek kuota jika ada (ekskul_info didapat dari _cek_guru_pembina_ekskul)
            if ekskul_info and ekskul_info.get('kuota_maksimal') is not None:
                jumlah_peserta_aktif = self.con.count_active_members_ekskul(pendaftaran_info['id_ekskul'], pendaftaran_info['tahun_ajaran'])
                if jumlah_peserta_aktif >= ekskul_info['kuota_maksimal']:
                    flash(f"Kuota untuk ekskul '{ekskul_info['nama_ekskul']}' sudah penuh. Pendaftaran tidak dapat disetujui.", "warning")
                    self.con.update_ekskul_registration_status(pendaftaran_id, 'Ditolak', f"Ditolak otomatis karena kuota penuh saat approval oleh Guru: {session.get('nama_lengkap')}")
                    return redirect(request.referrer or url_for('dashboard_guru'))
            
            catatan = f"Disetujui oleh Guru Pembina: {session.get('nama_lengkap')}"
            if self.con.update_ekskul_registration_status(pendaftaran_id, 'Disetujui', catatan):
                flash('Pendaftaran berhasil disetujui.', 'success')
            else:
                flash('Gagal menyetujui pendaftaran.', 'danger')
            return redirect(request.referrer or url_for('dashboard_guru'))

        @self.app.route('/guru/ekskul/pendaftaran/<int:pendaftaran_id>/tolak', methods=['POST'])
        @self.guru_login_required
        def tolak_pendaftaran_guru(pendaftaran_id):
            pendaftaran_info = self.con.get_pendaftaran_ekskul_by_id(pendaftaran_id)
            if not pendaftaran_info:
                flash("Data pendaftaran tidak ditemukan.", "danger")
                return redirect(request.referrer or url_for('dashboard_guru'))

            is_pembina_of_ekskul, _ = _cek_guru_pembina_ekskul(pendaftaran_info['id_ekskul'])
            if not is_pembina_of_ekskul:
                return redirect(request.referrer or url_for('dashboard_guru'))

            alasan = request.form.get('alasan_penolakan_guru', 'Ditolak oleh Guru Pembina.')
            catatan = f"{alasan} (Guru: {session.get('nama_lengkap')})"
            if self.con.update_ekskul_registration_status(pendaftaran_id, 'Ditolak', catatan):
                flash('Pendaftaran berhasil ditolak.', 'success')
            else:
                flash('Gagal menolak pendaftaran.', 'danger')
            return redirect(request.referrer or url_for('dashboard_guru'))

        @self.app.route('/guru/ekskul/<int:ekskul_id>/peserta')
        @self.guru_login_required
        def kelola_peserta_ekskul_guru(ekskul_id):
            # Cek apakah guru adalah pembina
            is_pembina, ekskul_info = _cek_guru_pembina_ekskul(ekskul_id)
            if not is_pembina:
                return redirect(url_for('dashboard_guru')) # atau ke detail ekskul jika ekskul_info ada

            tahun_ajaran_aktif = self.con.get_tahun_ajaran_aktif() 
            current_members = self.con.get_members_of_ekskul(ekskul_id, tahun_ajaran_aktif)
            # Murid yang bisa ditambahkan: yang aktif dan belum terdaftar di ekskul ini T.A. ini
            available_students_to_add = self.con.get_all_active_murid_exclude_ekskul(ekskul_id, tahun_ajaran_aktif)
            
            return render_template('guru/kelola_peserta_ekskul.html',
                                   ekskul_info=ekskul_info,
                                   members=current_members,
                                   available_students=available_students_to_add,
                                   tahun_ajaran_aktif=tahun_ajaran_aktif,
                                   nama_guru=session.get('nama_lengkap'))

        @self.app.route('/guru/ekskul/<int:ekskul_id>/add_peserta', methods=['POST'])
        @self.guru_login_required
        def add_peserta_ekskul_guru(ekskul_id):
            is_pembina, ekskul_info = _cek_guru_pembina_ekskul(ekskul_id)
            if not is_pembina:
                 return redirect(url_for('dashboard_guru'))


            murid_id_str = request.form.get('id_murid')
            tahun_ajaran = request.form.get('tahun_ajaran') # Seharusnya sama dengan tahun ajaran ekskul

            if not murid_id_str or not tahun_ajaran or not murid_id_str.isdigit():
                flash("Murid dan tahun ajaran harus dipilih/diisi dengan benar.", "danger")
            else:
                murid_id = int(murid_id_str)
                catatan_pendaftar = f"Didaftarkan oleh Guru Pembina: {session.get('nama_lengkap')}"
                
                # Panggil metode register_student_for_ekskul dari Config
                # yang sudah menangani pengecekan kuota dan duplikasi
                hasil_pendaftaran = self.con.register_student_for_ekskul(
                    murid_id, ekskul_id, tahun_ajaran, 
                    status_pendaftaran='Disetujui', # Guru langsung menyetujui
                    catatan_pendaftar=catatan_pendaftar
                )

                if isinstance(hasil_pendaftaran, int): # Berhasil, ID pendaftaran dikembalikan
                    murid_info = self.con.get_user_by_id(murid_id)
                    flash(f"Murid '{murid_info['nama_lengkap'] if murid_info else 'ID '+str(murid_id)}' berhasil ditambahkan ke ekskul '{ekskul_info['nama_ekskul']}'.", "success")
                elif hasil_pendaftaran == "KUOTA_PENUH":
                    flash(f"Gagal menambahkan. Kuota untuk ekskul '{ekskul_info['nama_ekskul']}' sudah penuh.", "warning")
                elif hasil_pendaftaran == "SUDAH_TERDAFTAR":
                     murid_info = self.con.get_user_by_id(murid_id)
                     flash(f"Gagal menambahkan. Murid '{murid_info['nama_lengkap'] if murid_info else 'ID '+str(murid_id)}' sudah memiliki record pendaftaran di ekskul '{ekskul_info['nama_ekskul']}' untuk tahun ajaran ini.", "warning")
                elif hasil_pendaftaran == "EKSKUL_NOT_FOUND": # Seharusnya tidak terjadi jika _cek_guru_pembina_ekskul lolos
                    flash(f"Ekskul '{ekskul_info['nama_ekskul']}' tidak ditemukan.", "danger")
                else: # Error umum dari register_student_for_ekskul (return False)
                    flash("Gagal menambahkan murid. Terjadi kesalahan pada sistem.", "danger")
            
            return redirect(url_for('kelola_peserta_ekskul_guru', ekskul_id=ekskul_id))

        @self.app.route('/guru/ekskul/remove_peserta/<int:pendaftaran_id>', methods=['POST'])
        @self.guru_login_required
        def remove_peserta_ekskul_guru(pendaftaran_id):
            ekskul_id_redirect = request.form.get('ekskul_id_redirect') # Untuk redirect kembali

            pendaftaran_info = self.con.get_pendaftaran_ekskul_by_id(pendaftaran_id)
            if not pendaftaran_info:
                flash("Data pendaftaran tidak ditemukan.", "danger")
                return redirect(url_for('dashboard_guru'))

            # Cek apakah guru yang login adalah pembina dari ekskul terkait pendaftaran ini
            is_pembina, _ = _cek_guru_pembina_ekskul(pendaftaran_info['id_ekskul'])
            if not is_pembina:
                if ekskul_id_redirect and ekskul_id_redirect.isdigit():
                    return redirect(url_for('kelola_peserta_ekskul_guru', ekskul_id=int(ekskul_id_redirect)))
                return redirect(url_for('dashboard_guru'))

            catatan_admin = f"Dikeluarkan oleh Guru Pembina: {session.get('nama_lengkap')}"
            if self.con.update_ekskul_registration_status(pendaftaran_id, new_status='Berhenti', catatan_admin=catatan_admin):
                flash(f"Status pendaftaran (ID: {pendaftaran_id}) diubah menjadi 'Berhenti'.", "success")
            else:
                flash("Gagal mengubah status pendaftaran.", "danger")
            
            if ekskul_id_redirect and ekskul_id_redirect.isdigit():
                return redirect(url_for('kelola_peserta_ekskul_guru', ekskul_id=int(ekskul_id_redirect)))
            return redirect(url_for('dashboard_guru')) # Fallback

        # --- Rute CRUD Materi oleh Guru Pembina ---
        @self.app.route('/guru/ekskul/<int:ekskul_id>/materi/tambah', methods=['GET', 'POST'])
        @self.guru_login_required
        def tambah_materi_ekskul_guru(ekskul_id):
            is_pembina, ekskul_info = _cek_guru_pembina_ekskul(ekskul_id)
            if not is_pembina:
                return redirect(url_for('detail_ekskul_guru', ekskul_id=ekskul_id) if ekskul_info else url_for('dashboard_guru'))

            form_data_repopulate = {'id_ekskul': ekskul_id} 

            if request.method == 'POST':
                form_data_repopulate.update(request.form) 
                
                judul_materi = request.form.get('judul_materi','').strip()
                deskripsi_materi = request.form.get('deskripsi_materi','').strip()
                tipe_konten = request.form.get('tipe_konten')
                path_konten_final = None
                isi_konten_teks_final = None

                if not judul_materi or not tipe_konten:
                    flash("Judul Materi dan Tipe Konten wajib diisi.", "danger")
                else:
                    save_to_db = False 
                    if tipe_konten == 'file':
                        if 'file_konten' not in request.files or request.files['file_konten'].filename == '':
                            flash('Tidak ada file yang dipilih untuk diunggah (jika tipe file dipilih).', 'warning')
                        else:
                            file = request.files['file_konten']
                            if file and allowed_file(file.filename, self.app.config['ALLOWED_EXTENSIONS']):
                                filename = secure_filename(file.filename)
                                upload_path_dir = self.app.config['UPLOAD_FOLDER']
                                if not os.path.exists(upload_path_dir):
                                    os.makedirs(upload_path_dir, exist_ok=True)
                                try:
                                    file.save(os.path.join(upload_path_dir, filename))
                                    path_konten_final = filename
                                    save_to_db = True
                                    flash(f'File {filename} berhasil diunggah.', 'info')
                                except Exception as e:
                                    flash(f'Gagal menyimpan file: {e}', 'danger')
                            elif file: 
                                flash('Tipe file tidak diizinkan.', 'danger')
                    elif tipe_konten in ['link', 'video_embed']:
                        path_konten_final = request.form.get('path_konten_atau_link_url','').strip()
                        if not path_konten_final:
                            flash('URL/Link atau Kode Embed Video wajib diisi untuk tipe ini.', 'danger')
                        else:
                            save_to_db = True
                    elif tipe_konten == 'teks':
                        isi_konten_teks_final = request.form.get('isi_konten_teks_area','').strip()
                        if not isi_konten_teks_final:
                            flash('Isi konten teks wajib diisi untuk tipe ini.', 'danger')
                        else:
                            save_to_db = True
                    else: 
                        flash('Tipe konten tidak valid.', 'danger')

                    if save_to_db:
                        data_materi = {
                            'id_ekskul': ekskul_id,
                            'judul_materi': judul_materi,
                            'deskripsi_materi': deskripsi_materi,
                            'tipe_konten': tipe_konten,
                            'path_konten_atau_link': path_konten_final,
                            'isi_konten_teks': isi_konten_teks_final,
                            'id_pengunggah': session['user_id'] 
                        }
                        materi_id = self.con.add_materi_ekskul(data_materi)
                        if materi_id:
                            flash("Materi ekstrakurikuler berhasil ditambahkan!", "success")
                            return redirect(url_for('detail_ekskul_guru', ekskul_id=ekskul_id))
                        else:
                            flash("Gagal menambahkan materi ke database. Periksa log.", "danger")
            
            return render_template('guru/materi_ekskul_form_guru.html', 
                                   action="Tambah", 
                                   materi_data=form_data_repopulate, 
                                   ekskul_info=ekskul_info,
                                   id_ekskul=ekskul_id)

        @self.app.route('/guru/ekskul/<int:ekskul_id>/materi/edit/<int:id_materi_ekskul>', methods=['GET', 'POST'])
        @self.guru_login_required
        def edit_materi_ekskul_guru(ekskul_id, id_materi_ekskul):
            is_pembina, ekskul_info = _cek_guru_pembina_ekskul(ekskul_id)
            if not is_pembina:
                 return redirect(url_for('detail_ekskul_guru', ekskul_id=ekskul_id) if ekskul_info else url_for('dashboard_guru'))

            materi_data_lama = self.con.get_materi_ekskul_by_id(id_materi_ekskul)
            if not materi_data_lama or materi_data_lama['id_ekskul'] != ekskul_id:
                flash("Materi tidak ditemukan atau tidak sesuai dengan ekskul ini.", "danger")
                return redirect(url_for('detail_ekskul_guru', ekskul_id=ekskul_id))

            display_data = materi_data_lama.copy()

            if request.method == 'POST':
                display_data.update(request.form) 
                
                judul_materi = request.form.get('judul_materi','').strip()
                deskripsi_materi = request.form.get('deskripsi_materi','').strip()
                tipe_konten_form = request.form.get('tipe_konten')

                data_to_update = {
                    'id_ekskul': ekskul_id, 
                    'judul_materi': judul_materi if judul_materi else materi_data_lama['judul_materi'],
                    'deskripsi_materi': deskripsi_materi,
                    'tipe_konten': tipe_konten_form if tipe_konten_form else materi_data_lama['tipe_konten']
                }
                
                delete_old_file = False
                old_file_name_from_db = materi_data_lama.get('path_konten_atau_link') if materi_data_lama.get('tipe_konten') == 'file' else None
                is_content_valid_overall = True 

                if data_to_update['tipe_konten'] == 'file':
                    if 'file_konten' in request.files and request.files['file_konten'].filename != '':
                        file = request.files['file_konten']
                        if allowed_file(file.filename, self.app.config['ALLOWED_EXTENSIONS']):
                            if old_file_name_from_db: delete_old_file = True
                            filename = secure_filename(file.filename)
                            try:
                                file.save(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))
                                data_to_update['path_konten_atau_link'] = filename
                                data_to_update['isi_konten_teks'] = None
                                flash(f'File baru {filename} berhasil diunggah.', 'info')
                            except Exception as e:
                                flash(f'Gagal menyimpan file: {e}', 'danger'); is_content_valid_overall = False
                        else:
                            flash('Tipe file baru tidak diizinkan.', 'danger'); is_content_valid_overall = False
                    elif materi_data_lama['tipe_konten'] == 'file':
                         data_to_update['path_konten_atau_link'] = materi_data_lama['path_konten_atau_link']
                         data_to_update['isi_konten_teks'] = None
                    elif materi_data_lama['tipe_konten'] != 'file': 
                        flash('File wajib diunggah jika tipe konten diubah menjadi "file".', 'danger'); is_content_valid_overall = False
                elif data_to_update['tipe_konten'] in ['link', 'video_embed']:
                    new_val = request.form.get('path_konten_atau_link_url','').strip()
                    if not new_val: flash('URL/Link atau Kode Embed wajib diisi.', 'danger'); is_content_valid_overall = False
                    else:
                        data_to_update['path_konten_atau_link'] = new_val
                        data_to_update['isi_konten_teks'] = None
                        if old_file_name_from_db: delete_old_file = True
                elif data_to_update['tipe_konten'] == 'teks':
                    new_val = request.form.get('isi_konten_teks_area','').strip()
                    if not new_val: flash('Isi konten teks wajib diisi.', 'danger'); is_content_valid_overall = False
                    else:
                        data_to_update['isi_konten_teks'] = new_val
                        data_to_update['path_konten_atau_link'] = None
                        if old_file_name_from_db: delete_old_file = True
                
                if not data_to_update.get('judul_materi') : 
                    flash("Judul Materi wajib diisi.", "danger"); is_content_valid_overall = False

                if is_content_valid_overall:
                    if self.con.update_materi_ekskul(id_materi_ekskul, data_to_update):
                        if delete_old_file and old_file_name_from_db:
                            try:
                                file_to_remove = os.path.join(self.app.config['UPLOAD_FOLDER'], old_file_name_from_db)
                                if os.path.exists(file_to_remove):
                                    os.remove(file_to_remove)
                                    flash('File lama berhasil dihapus.', 'info')
                            except OSError as e: flash(f'Gagal menghapus file lama: {e}', 'warning')
                        flash("Materi berhasil diperbarui!", "success")
                        return redirect(url_for('detail_ekskul_guru', ekskul_id=ekskul_id))
                    else: 
                        if not get_flashed_messages(category_filter=["danger"]): 
                             flash("Gagal memperbarui materi ke database.", "danger")
                elif not get_flashed_messages(category_filter=["danger"]): 
                     flash("Gagal memperbarui materi. Pastikan semua field yang relevan terisi.", "danger")
            
            if display_data.get('tipe_konten') in ['link', 'video_embed']:
                display_data['path_konten_atau_link_url'] = display_data.get('path_konten_atau_link')
            elif display_data.get('tipe_konten') == 'teks':
                display_data['isi_konten_teks_area'] = display_data.get('isi_konten_teks')

            return render_template('guru/materi_ekskul_form_guru.html', 
                                   action="Edit", 
                                   materi_data=display_data, 
                                   ekskul_info=ekskul_info,
                                   id_ekskul=ekskul_id, 
                                   id_materi_ekskul=id_materi_ekskul)

        @self.app.route('/guru/ekskul/<int:ekskul_id>/materi/hapus/<int:id_materi_ekskul>', methods=['POST'])
        @self.guru_login_required
        def hapus_materi_ekskul_guru(ekskul_id, id_materi_ekskul):
            is_pembina, ekskul_info_check = _cek_guru_pembina_ekskul(ekskul_id) # Ambil juga ekskul_info
            if not is_pembina:
                return redirect(url_for('detail_ekskul_guru', ekskul_id=ekskul_id) if ekskul_info_check else url_for('dashboard_guru'))

            materi_info = self.con.get_materi_ekskul_by_id(id_materi_ekskul)
            if not materi_info or materi_info['id_ekskul'] != ekskul_id:
                flash("Materi tidak ditemukan atau tidak sesuai dengan ekskul ini.", "danger")
                return redirect(url_for('detail_ekskul_guru', ekskul_id=ekskul_id))

            materi_info_deleted = self.con.delete_materi_ekskul(id_materi_ekskul)
            if materi_info_deleted:
                if materi_info_deleted['tipe_konten'] == 'file' and materi_info_deleted['path_konten_atau_link']:
                    try:
                        file_path = os.path.join(self.app.config['UPLOAD_FOLDER'], materi_info_deleted['path_konten_atau_link'])
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            flash(f"File materi '{materi_info_deleted['path_konten_atau_link']}' berhasil dihapus dari server.", 'info')
                    except OSError as e:
                        flash(f"Gagal menghapus file fisik: {e}", "warning")
                flash("Materi berhasil dihapus dari database.", "success")
            else:
                flash("Gagal menghapus materi dari database.", "danger")
            return redirect(url_for('detail_ekskul_guru', ekskul_id=ekskul_id))

        # --- Rute Dashboard Murid (Placeholder) ---
        @self.app.route('/registrasi-murid', methods=['GET'])
        def form_registrasi_murid():
            # Jika pengguna sudah login, arahkan ke dashboardnya
            if 'user_id' in session:
                peran = session.get('peran')
                if peran == 'admin': return redirect(url_for('dashboard_admin'))
                if peran == 'guru': return redirect(url_for('dashboard_guru'))
                if peran == 'murid': return redirect(url_for('dashboard_murid'))
                # Jika peran tidak dikenal, fallback ke logout agar bisa registrasi/login ulang
                session.clear()
                return redirect(url_for('login'))
            return render_template('murid/register_murid.html')

        @self.app.route('/registrasi-murid/submit', methods=['POST'])
        def submit_registrasi_murid():
            if 'user_id' in session: # Seharusnya tidak bisa diakses jika sudah login
                return redirect(url_for('index'))

            nama_lengkap = request.form.get('nama_lengkap', '').strip()
            nomor_induk = request.form.get('nomor_induk', '').strip()
            email = request.form.get('email', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '') # Jangan strip password, bisa ada spasi sengaja
            confirm_password = request.form.get('confirm_password', '')

            # Validasi dasar
            if not all([nama_lengkap, nomor_induk, email, username, password, confirm_password]):
                flash('Semua field yang ditandai bintang (*) wajib diisi.', 'danger')
                return render_template('murid/register_murid.html', **request.form) # Kembalikan data form

            if password != confirm_password:
                flash('Password dan Konfirmasi Password tidak cocok.', 'danger')
                return render_template('murid/register_murid.html', **request.form)
            
            # Cek apakah username sudah ada
            if self.con.get_user_by_username(username):
                flash(f"Username '{username}' sudah digunakan. Silakan pilih username lain.", 'danger')
                return render_template('murid/register_murid.html', **request.form)

            # Opsional: Cek apakah email sudah ada
            # if self.con.get_user_by_email(email): # Anda mungkin perlu buat metode ini di Config.py
            #     flash(f"Email '{email}' sudah terdaftar.", 'danger')
            #     return render_template('register_murid.html', **request.form)

            # Opsional: Cek apakah Nomor Induk sudah ada (untuk peran murid)
            # if self.con.get_user_by_nomor_induk_and_role(nomor_induk, 'murid'): # Buat metode ini di Config.py
            #     flash(f"Nomor Induk '{nomor_induk}' sudah terdaftar.", 'danger')
            #     return render_template('register_murid.html', **request.form)

            # Jika semua validasi lolos, siapkan data untuk disimpan
            user_data = {
                'username': username,
                'password': password, # Password akan di-hash di Config.add_user
                'nama_lengkap': nama_lengkap,
                'email': email,
                'peran': 'murid', # Peran sudah pasti 'murid'
                'nomor_induk': nomor_induk,
                'status_aktif': True # Bisa diatur False jika butuh approval admin/verifikasi email
            }

            user_id = self.con.add_user(user_data) # Panggil metode add_user dari Config Anda

            if user_id:
                flash(f"Registrasi berhasil! Selamat datang, {nama_lengkap}. Silakan login.", 'success')
                return redirect(url_for('login'))
            else:
                flash('Registrasi gagal. Terjadi kesalahan pada server. Silakan coba lagi nanti.', 'danger')
                return render_template('murid/register_murid.html', **request.form)

        @self.app.route('/murid/dashboard')
        @self.murid_login_required # Menggunakan decorator yang sudah ada
        def dashboard_murid(): # Tidak perlu 'self' jika didefinisikan di dalam routes()
            murid_id = session.get('user_id')
            nama_murid = session.get('nama_lengkap')

            # Dapatkan tahun ajaran aktif
            # Pastikan metode get_tahun_ajaran_aktif() ada di Config.py Anda
            tahun_ajaran_aktif = self.con.get_tahun_ajaran_aktif() 
            if not tahun_ajaran_aktif:
                flash("Tidak dapat menentukan tahun ajaran aktif. Hubungi admin.", "warning")
                # Anda bisa memberikan nilai default atau menghentikan proses di sini
                # tergantung bagaimana Anda ingin menanganinya.
                # Untuk contoh ini, kita biarkan None jika tidak ada.
                # Atau: tahun_ajaran_aktif = "TAHUN_DEFAULT"

            # 1. Ambil Pengumuman untuk murid
            # Pastikan metode get_pengumuman_for_role ada di Config.py Anda
            pengumuman_list = self.con.get_pengumuman_for_role('murid', limit=5)

            # 2. Ambil Ekskul yang diikuti murid (beserta detailnya)
            ekskul_diikuti_list = [] # Default ke list kosong
            if murid_id and tahun_ajaran_aktif:
                # Pastikan metode get_ekskul_diikuti_murid_detail ada di Config.py Anda
                ekskul_diikuti_list = self.con.get_ekskul_diikuti_murid_detail(murid_id, tahun_ajaran_aktif)

            # 3. Ambil Materi untuk setiap ekskul yang diikuti
            materi_per_ekskul = {} 
            if ekskul_diikuti_list:
                for ekskul in ekskul_diikuti_list:
                    # Pastikan metode get_materi_by_ekskul_id ada di Config.py Anda
                    materi_list_untuk_ekskul_ini = self.con.get_materi_by_ekskul_id(ekskul['id_ekskul'])
                    if materi_list_untuk_ekskul_ini:
                        materi_per_ekskul[ekskul['nama_ekskul']] = materi_list_untuk_ekskul_ini
                    else:
                        materi_per_ekskul[ekskul['nama_ekskul']] = []

            return render_template('murid/dashboard_murid.html',
                                   nama_murid=nama_murid,
                                   pengumuman_list=pengumuman_list,
                                   ekskul_diikuti_list=ekskul_diikuti_list,
                                   materi_per_ekskul=materi_per_ekskul,
                                   tahun_ajaran_aktif=tahun_ajaran_aktif)
        @self.app.route('/murid/ekskul', methods=['GET'])
        @self.murid_login_required
        def lihat_ekskul_murid():
            murid_id = session.get('user_id')
            tahun_ajaran_aktif = self.con.get_tahun_ajaran_aktif()

            list_ekskul_tersedia = self.con.get_all_ekskul() # Ambil semua ekskul

            ekskul_sudah_diikuti = []
            if hasattr(self.con, 'get_ekskul_diikuti_murid_detail'):
                ekskul_sudah_diikuti = self.con.get_ekskul_diikuti_murid_detail(murid_id, tahun_ajaran_aktif)

            ids_ekskul_sudah_diikuti = [e['id_ekskul'] for e in ekskul_sudah_diikuti] if ekskul_sudah_diikuti else []

            return render_template('murid/lihat_ekskul.html', 
                                   list_ekskul=list_ekskul_tersedia,
                                   ids_ekskul_sudah_diikuti=ids_ekskul_sudah_diikuti,
                                   tahun_ajaran_aktif=tahun_ajaran_aktif,
                                   nama_murid=session.get('nama_lengkap'))

        # Rute untuk murid mendaftar ke ekskul
        @self.app.route('/murid/ekskul/<int:ekskul_id>/daftar', methods=['POST'])
        @self.murid_login_required
        def daftar_ekskul_murid(ekskul_id):
            murid_id = session.get('user_id')
            nama_murid = session.get('nama_lengkap')
            tahun_ajaran = request.form.get('tahun_ajaran')

            if not tahun_ajaran:
                flash('Tahun ajaran tidak valid.', 'danger')
                return redirect(url_for('lihat_ekskul_murid'))

            catatan_pendaftar = f"Didaftarkan oleh murid: {nama_murid}"
            status_awal_pendaftaran = 'Menunggu Persetujuan' # Atau 'Terdaftar'

            hasil_pendaftaran = self.con.register_student_for_ekskul(
                murid_id, ekskul_id, tahun_ajaran,
                status_pendaftaran=status_awal_pendaftaran,
                catatan_pendaftar=catatan_pendaftar
            )

            ekskul_info = self.con.get_ekskul_by_id(ekskul_id)
            nama_ekskul = ekskul_info['nama_ekskul'] if ekskul_info else f"ID {ekskul_id}"

            if isinstance(hasil_pendaftaran, int):
                flash(f"Anda berhasil mendaftar untuk ekstrakurikuler '{nama_ekskul}'. Status: {status_awal_pendaftaran}.", 'success')
            elif hasil_pendaftaran == "KUOTA_PENUH":
                flash(f"Maaf, kuota untuk ekstrakurikuler '{nama_ekskul}' sudah penuh.", 'warning')
            elif hasil_pendaftaran == "SUDAH_TERDAFTAR":
                flash(f"Anda sudah terdaftar atau sedang menunggu persetujuan untuk ekstrakurikuler '{nama_ekskul}' pada tahun ajaran ini.", 'warning')
            elif hasil_pendaftaran == "EKSKUL_NOT_FOUND":
                flash(f"Ekstrakurikuler '{nama_ekskul}' tidak ditemukan atau tidak aktif.", 'danger')
            else: 
                flash(f"Gagal mendaftar untuk ekstrakurikuler '{nama_ekskul}'. Terjadi kesalahan.", 'danger')

            return redirect(url_for('lihat_ekskul_murid'))

        @self.app.route('/murid/ekskul/saya')
        @self.murid_login_required
        def ekskul_saya_murid():
            murid_id = session.get('user_id')
            tahun_ajaran_aktif = self.con.get_tahun_ajaran_aktif()
            
            data_ekskul_diikuti = []
            if hasattr(self.con, 'get_pendaftaran_by_murid'):
                all_my_registrations = self.con.get_pendaftaran_by_murid(murid_id, tahun_ajaran_aktif)
                if all_my_registrations:
                    for reg in all_my_registrations:
                        detail_ekskul = self.con.get_ekskul_by_id(reg['id_ekskul']) 
                        if detail_ekskul:
                            data_ekskul_diikuti.append({
                                'id_ekskul': detail_ekskul['id_ekskul'], # <--- TAMBAHKAN INI
                                'nama_ekskul': detail_ekskul['nama_ekskul'],
                                'pembina': detail_ekskul.get('nama_guru_pembina', 'N/A'),
                                'jadwal': detail_ekskul.get('jadwal_deskripsi', 'N/A'),
                                'status_pendaftaran': reg['status_pendaftaran'],
                                'tanggal_pendaftaran': reg.get('tanggal_pendaftaran') 
                            })
            
            return render_template('murid/ekskul_saya.html', 
                                    list_ekskul_diikuti=data_ekskul_diikuti, 
                                    nama_murid=session.get('nama_lengkap'))
        @self.app.route('/murid/ekskul/detail/<int:ekskul_id>')
        @self.murid_login_required
        def detail_ekskul_murid(ekskul_id):
            murid_id = session.get('user_id') # Untuk validasi atau personalisasi di masa depan
            
            ekskul_info = self.con.get_ekskul_by_id(ekskul_id)
            if not ekskul_info:
                flash('Ekstrakurikuler tidak ditemukan.', 'danger')
                return redirect(url_for('ekskul_saya_murid')) # atau ke dashboard murid

            # Pastikan ekskul aktif, atau murid memang terdaftar jika ada aturan khusus
            # Untuk sekarang, kita asumsikan jika bisa diakses, boleh dilihat detailnya
            # if not ekskul_info['status_aktif']:
            #     # Logika jika ekskul tidak aktif tapi murid masih terdaftar
            #     pass

            materi_list = self.con.get_materi_by_ekskul_id(ekskul_id)

            return render_template('murid/detail_ekskul_murid.html',
                                    ekskul=ekskul_info,
                                    materi_list=materi_list,
                                    nama_murid=session.get('nama_lengkap'))

        @self.app.route('/murid/absensi-ekskul')
        @self.murid_login_required
        def lihat_absensi_ekskul_saya():
            murid_id = session.get('user_id')
            nama_murid = session.get('nama_lengkap')
            tahun_ajaran_aktif = self.con.get_tahun_ajaran_aktif()

            if not tahun_ajaran_aktif:
                flash("Tidak dapat menentukan tahun ajaran aktif. Hubungi admin.", "warning")
                return redirect(url_for('dashboard_murid')) # Atau halaman lain

            raw_attendance_records = self.con.get_my_attendance_records(murid_id, tahun_ajaran_aktif)
                
            attendance_by_ekskul = defaultdict(list)
            if raw_attendance_records:
                for record in raw_attendance_records:
                    # Salin record agar tidak mengubah data asli jika masih dipakai di tempat lain
                    processed_record = record.copy() 

                    # Proses jam_mulai_kegiatan jika itu timedelta
                    jam_mulai = processed_record.get('jam_mulai_kegiatan')
                    if isinstance(jam_mulai, datetime.timedelta):
                        # Ubah timedelta menjadi total detik
                        total_seconds = int(jam_mulai.total_seconds())
                        # Hitung jam dan menit
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        # Format menjadi HH:MM
                        processed_record['jam_mulai_kegiatan_str'] = f"{hours:02d}:{minutes:02d}"
                    elif jam_mulai: # Jika sudah objek time atau datetime (jarang terjadi jika error timedelta)
                        # Cek apakah punya strftime untuk keamanan
                        if hasattr(jam_mulai, 'strftime'):
                            processed_record['jam_mulai_kegiatan_str'] = jam_mulai.strftime('%H:%M')
                        else: # Jika tipe tidak dikenal, tampilkan apa adanya
                            processed_record['jam_mulai_kegiatan_str'] = str(jam_mulai)
                    else:
                        processed_record['jam_mulai_kegiatan_str'] = '-'
                    
                    # Hapus field asli jika mau, agar tidak bingung di template, atau biarkan
                    # del processed_record['jam_mulai_kegiatan'] 

                    attendance_by_ekskul[processed_record['nama_ekskul']].append(processed_record)
            
            return render_template('murid/absensi_ekskul_saya.html',
                                    nama_murid=nama_murid,
                                    attendance_by_ekskul=attendance_by_ekskul,
                                    tahun_ajaran_aktif=tahun_ajaran_aktif)
        
        @self.app.route('/murid/profil/edit', methods=['GET', 'POST'])
        @self.murid_login_required
        def edit_profil_murid(): # Fungsi ini didefinisikan di dalam routes()
                murid_id = session.get('user_id')
                # Ambil data pengguna dari database untuk ditampilkan atau divalidasi
                user_sekarang = self.con.get_user_by_id(murid_id)

                if not user_sekarang:
                    flash("Gagal memuat data profil Anda. Silakan login kembali.", "danger")
                    return redirect(url_for('login'))

                if request.method == 'POST':
                    nama_lengkap_baru = request.form.get('nama_lengkap', '').strip()
                    email_baru = request.form.get('email', '').strip()
                    # Username dan nomor induk tidak diubah oleh murid, jadi kita tidak ambil dari form untuk diupdate

                    current_password = request.form.get('current_password', '')
                    new_password = request.form.get('new_password', '')
                    confirm_new_password = request.form.get('confirm_new_password', '')

                    # Data form untuk dikirim kembali ke template jika ada error validasi
                    form_data_for_template = {
                        'nama_lengkap': nama_lengkap_baru,
                        'email': email_baru,
                        'username': user_sekarang['username'], # Ambil dari user_sekarang
                        'nomor_induk': user_sekarang.get('nomor_induk', '') # Ambil dari user_sekarang
                        # Jangan sertakan password di sini
                    }

                    if not nama_lengkap_baru or not email_baru:
                        flash('Nama Lengkap dan Email wajib diisi.', 'danger')
                        return render_template('murid/edit_profil_murid.html', 
                                               user_data=form_data_for_template, 
                                               nama_murid=user_sekarang['nama_lengkap'])

                    data_to_update = {
                        'nama_lengkap': nama_lengkap_baru,
                        'email': email_baru
                    }
                    password_changed_message_part = ""

                    # Logika untuk update password
                    if new_password: # Hanya proses jika field password baru diisi
                        if not current_password:
                            flash('Masukkan password saat ini untuk mengubah password.', 'warning')
                            return render_template('murid/edit_profil_murid.html', 
                                                   user_data=form_data_for_template, 
                                                   nama_murid=user_sekarang['nama_lengkap'])
                        
                        if not check_password_hash(user_sekarang['password_hash'], current_password):
                            flash('Password saat ini salah.', 'danger')
                            return render_template('murid/edit_profil_murid.html', 
                                                   user_data=form_data_for_template, 
                                                   nama_murid=user_sekarang['nama_lengkap'])

                        if new_password != confirm_new_password:
                            flash('Password baru dan konfirmasi password tidak cocok.', 'danger')
                            return render_template('murid/edit_profil_murid.html', 
                                                   user_data=form_data_for_template, 
                                                   nama_murid=user_sekarang['nama_lengkap'])
                        
                        # Validasi tambahan untuk password baru (misalnya panjang minimal) bisa ditambahkan di sini
                        # if len(new_password) < 6:
                        #     flash('Password baru minimal 6 karakter.', 'danger')
                        #     return render_template('murid/edit_profil_murid.html', user_data=form_data_for_template, nama_murid=user_sekarang['nama_lengkap'])

                        data_to_update['password'] = new_password # Password akan di-hash di metode update_user
                        password_changed_message_part = " Password Anda juga telah diubah."
                    
                    # Panggil metode update_user dari Config.py
                    # Metode ini mengupdate field yang ada di data_to_update
                    if self.con.update_user(murid_id, data_to_update):
                        # Update session jika nama_lengkap atau email (jika disimpan di session) berubah
                        session['nama_lengkap'] = nama_lengkap_baru
                        # session['email'] = email_baru # Jika email juga disimpan di session

                        flash(f"Profil berhasil diperbarui.{password_changed_message_part}", 'success')
                        return redirect(url_for('dashboard_murid')) # Arahkan ke dashboard setelah sukses
                    else:
                        flash('Gagal memperbarui profil. Terjadi kesalahan pada server.', 'danger')
                        # Jika update_user gagal, render kembali form dengan data yang sudah diisi
                        return render_template('murid/edit_profil_murid.html', 
                                               user_data=form_data_for_template, 
                                               nama_murid=user_sekarang['nama_lengkap'])
                
                # Ini adalah return untuk GET request (saat halaman pertama kali dimuat)
                # user_sekarang sudah berisi data dari DB
                return render_template('murid/edit_profil_murid.html', 
                                       user_data=user_sekarang, 
                                       nama_murid=user_sekarang['nama_lengkap'])

    def run(self):
        self.app.run(debug=True, host='0.0.0.0', port=5001) 

if __name__ == "__main__":
    portal = Portal()
    portal.run()