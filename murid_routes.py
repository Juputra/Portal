from flask import flash, redirect, render_template, request, url_for, session, get_flashed_messages
from werkzeug.security import check_password_hash
from collections import defaultdict
import os
from datetime import date, datetime, timedelta 

class MuridRoutes:
    def __init__(self, app, db_con, murid_login_required_decorator):
        self.app = app
        self.db_con = db_con
        self.murid_login_required = murid_login_required_decorator

    def register_routes(self):
        @self.app.route('/registrasi-murid', methods=['GET'])
        def form_registrasi_murid(): # KALO UDA LOGIN BAKAL KE DASHBOARD SESUAI ROLE
            if 'user_id' in session:
                peran = session.get('peran')
                if peran == 'admin': return redirect(url_for('dashboard_admin'))
                if peran == 'guru': return redirect(url_for('dashboard_guru'))
                if peran == 'murid': return redirect(url_for('dashboard_murid'))
                session.clear()
                return redirect(url_for('login')) # KALO AKUNNYA GA ADA 
            return render_template('murid/register_murid.html')

        @self.app.route('/registrasi-murid/submit', methods=['POST'])
        def submit_registrasi_murid(): # ISI FORM REGISTRASI MURID
            if 'user_id' in session:
                return redirect(url_for('index'))
            nama_lengkap = request.form.get('nama_lengkap', '').strip()
            nomor_induk = request.form.get('nomor_induk', '').strip()
            email = request.form.get('email', '').strip()
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not all([nama_lengkap, nomor_induk, email, username, password, confirm_password]):
                flash('Semua field yang ditandai bintang (*) wajib diisi.', 'danger')
                return render_template('murid/register_murid.html', **request.form)

            if password != confirm_password:
                flash('Password dan Konfirmasi Password tidak cocok.', 'danger')
                return render_template('murid/register_murid.html', **request.form)
            
            if self.db_con.get_user_by_username(username):
                flash(f"Username '{username}' sudah digunakan. Silakan pilih username lain.", 'danger')
                return render_template('murid/register_murid.html', **request.form)

            if self.db_con.get_user_by_email(email): 
                flash(f"Email '{email}' sudah terdaftar.", 'danger')
                return render_template('register_murid.html', **request.form)

            if self.db_con.get_user_by_nomor_induk_and_role(nomor_induk, 'murid'): 
                flash(f"Nomor Induk '{nomor_induk}' sudah terdaftar.", 'danger')
                return render_template('register_murid.html', **request.form)

            user_data = {
                'username': username,
                'password': password, 
                'nama_lengkap': nama_lengkap,
                'email': email,
                'peran': 'murid', 
                'nomor_induk': nomor_induk,
                'status_aktif': True 
            }

            user_id = self.db_con.add_user(user_data) # Panggil metode add_user dari Config Anda
            if user_id:
                flash(f"Registrasi berhasil! Selamat datang, {nama_lengkap}. Silakan login.", 'success')
                return redirect(url_for('login'))
            else:
                flash('Registrasi gagal. Terjadi kesalahan pada server. Silakan coba lagi nanti.', 'danger')
                return render_template('murid/register_murid.html', **request.form)

        @self.app.route('/murid/dashboard')
        @self.murid_login_required 
        def dashboard_murid(): # ISI DASHBOARD MURID
            murid_id = session.get('user_id')
            nama_murid = session.get('nama_lengkap')
            tahun_ajaran_aktif = self.db_con.get_tahun_ajaran_aktif() 
            if not tahun_ajaran_aktif:
                flash("Tidak dapat menentukan tahun ajaran aktif. Hubungi admin.", "warning")

            pengumuman_list = self.db_con.get_pengumuman_for_role('murid', limit=5)

            ekskul_diikuti_list = [] 
            if murid_id and tahun_ajaran_aktif:
                ekskul_diikuti_list = self.db_con.get_ekskul_diikuti_murid_detail(murid_id, tahun_ajaran_aktif)

            materi_per_ekskul = {} 
            if ekskul_diikuti_list:
                for ekskul in ekskul_diikuti_list:
                    materi_list_untuk_ekskul_ini = self.db_con.get_materi_by_ekskul_id(ekskul['id_ekskul'])
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
        def lihat_ekskul_murid(): # LIHAT DAFTAR EKSKUL YANG TERSEDIA
            murid_id = session.get('user_id')
            tahun_ajaran_aktif = self.db_con.get_tahun_ajaran_aktif()
            list_ekskul_tersedia = self.db_con.get_all_ekskul() 
            ekskul_sudah_diikuti = []
            if hasattr(self.db_con, 'get_ekskul_diikuti_murid_detail'):
                ekskul_sudah_diikuti = self.db_con.get_ekskul_diikuti_murid_detail(murid_id, tahun_ajaran_aktif)

            ids_ekskul_sudah_diikuti = [e['id_ekskul'] for e in ekskul_sudah_diikuti] if ekskul_sudah_diikuti else []

            return render_template('murid/lihat_ekskul.html', 
                                   list_ekskul=list_ekskul_tersedia,
                                   ids_ekskul_sudah_diikuti=ids_ekskul_sudah_diikuti,
                                   tahun_ajaran_aktif=tahun_ajaran_aktif,
                                   nama_murid=session.get('nama_lengkap'))

        @self.app.route('/murid/ekskul/<int:ekskul_id>/daftar', methods=['POST'])
        @self.murid_login_required
        def daftar_ekskul_murid(ekskul_id): # DAFTAR KE EKSKUL
            murid_id = session.get('user_id')
            nama_murid = session.get('nama_lengkap')
            tahun_ajaran = request.form.get('tahun_ajaran')
            if not tahun_ajaran:
                flash('Tahun ajaran tidak valid.', 'danger')
                return redirect(url_for('lihat_ekskul_murid'))
            catatan_pendaftar = f"Didaftarkan oleh murid: {nama_murid}"
            status_awal_pendaftaran = 'Menunggu Persetujuan' # Atau 'Terdaftar'
            hasil_pendaftaran = self.db_con.register_student_for_ekskul(
                murid_id, ekskul_id, tahun_ajaran,
                status_pendaftaran=status_awal_pendaftaran,
                catatan_pendaftar=catatan_pendaftar
            )
            ekskul_info = self.db_con.get_ekskul_by_id(ekskul_id)
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
        def ekskul_saya_murid(): # LIHAT EKSKUL YANG MURID IKUTI
            murid_id = session.get('user_id')
            tahun_ajaran_aktif = self.db_con.get_tahun_ajaran_aktif()
            data_ekskul_diikuti = []
            if hasattr(self.db_con, 'get_pendaftaran_by_murid'):
                all_my_registrations = self.db_con.get_pendaftaran_by_murid(murid_id, tahun_ajaran_aktif)
                if all_my_registrations:
                    for reg in all_my_registrations:
                        detail_ekskul = self.db_con.get_ekskul_by_id(reg['id_ekskul']) 
                        if detail_ekskul:
                            data_ekskul_diikuti.append({
                                'id_ekskul': detail_ekskul['id_ekskul'], 
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
            murid_id = session.get('user_id') 
            ekskul_info = self.db_con.get_ekskul_by_id(ekskul_id)
            if not ekskul_info:
                flash('Ekstrakurikuler tidak ditemukan.', 'danger')
                return redirect(url_for('ekskul_saya_murid')) 

            materi_list = self.db_con.get_materi_by_ekskul_id(ekskul_id)
            return render_template('murid/detail_ekskul_murid.html',
                                    ekskul=ekskul_info,
                                    materi_list=materi_list,
                                    nama_murid=session.get('nama_lengkap'))

        @self.app.route('/murid/absensi-ekskul')
        @self.murid_login_required
        def lihat_absensi_ekskul_saya(): # LIHAT ABSENSI EKSKUL MURID
            murid_id = session.get('user_id')
            nama_murid = session.get('nama_lengkap')
            tahun_ajaran_aktif = self.db_con.get_tahun_ajaran_aktif()
            if not tahun_ajaran_aktif:
                flash("Tidak dapat menentukan tahun ajaran aktif. Hubungi admin.", "warning")
                return redirect(url_for('dashboard_murid'))

            raw_attendance_records = self.db_con.get_my_attendance_records(murid_id, tahun_ajaran_aktif)
            attendance_by_ekskul = defaultdict(list)
            if raw_attendance_records:
                for record in raw_attendance_records:
                    processed_record = record.copy() 
                    jam_mulai = processed_record.get('jam_mulai_kegiatan')
                    if isinstance(jam_mulai, timedelta):
                        total_seconds = int(jam_mulai.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        processed_record['jam_mulai_kegiatan_str'] = f"{hours:02d}:{minutes:02d}"
                    elif jam_mulai: 
                        if hasattr(jam_mulai, 'strftime'):
                            processed_record['jam_mulai_kegiatan_str'] = jam_mulai.strftime('%H:%M')
                        else: 
                            processed_record['jam_mulai_kegiatan_str'] = str(jam_mulai)
                    else:
                        processed_record['jam_mulai_kegiatan_str'] = '-'

                    attendance_by_ekskul[processed_record['nama_ekskul']].append(processed_record)
            
            return render_template('murid/absensi_ekskul_saya.html',
                                    nama_murid=nama_murid,
                                    attendance_by_ekskul=attendance_by_ekskul,
                                    tahun_ajaran_aktif=tahun_ajaran_aktif)
        
        @self.app.route('/murid/profil/edit', methods=['GET', 'POST'])
        @self.murid_login_required
        def edit_profil_murid(): # EDIT PROFIL MURID
                murid_id = session.get('user_id')
                user_sekarang = self.db_con.get_user_by_id(murid_id)
                if not user_sekarang:
                    flash("Gagal memuat data profil Anda. Silakan login kembali.", "danger")
                    return redirect(url_for('login'))

                if request.method == 'POST':
                    nama_lengkap_baru = request.form.get('nama_lengkap', '').strip()
                    email_baru = request.form.get('email', '').strip()
                    current_password = request.form.get('current_password', '')
                    new_password = request.form.get('new_password', '')
                    confirm_new_password = request.form.get('confirm_new_password', '')
                    form_data_for_template = {
                        'nama_lengkap': nama_lengkap_baru,
                        'email': email_baru,
                        'username': user_sekarang['username'], 
                        'nomor_induk': user_sekarang.get('nomor_induk', '') 
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
                    if new_password: 
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

                        data_to_update['password'] = new_password 
                        password_changed_message_part = " Password Anda juga telah diubah."
                    
                    if self.db_con.update_user(murid_id, data_to_update):
                        session['nama_lengkap'] = nama_lengkap_baru
                        flash(f"Profil berhasil diperbarui.{password_changed_message_part}", 'success')
                        return redirect(url_for('dashboard_murid'))
                    else:
                        flash('Gagal memperbarui profil. Terjadi kesalahan pada server.', 'danger')
                        return render_template('murid/edit_profil_murid.html', 
                                               user_data=form_data_for_template, 
                                               nama_murid=user_sekarang['nama_lengkap'])
                
                return render_template('murid/edit_profil_murid.html', 
                                       user_data=user_sekarang, 
                                       nama_murid=user_sekarang['nama_lengkap'])