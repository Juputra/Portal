from flask import flash, redirect, render_template, request, url_for, session, get_flashed_messages
from werkzeug.utils import secure_filename
import os
from datetime import date, datetime, timedelta 

class AdminRoutes:
    def __init__(self, app, db_con, admin_login_required_decorator, cek_file):
        self.app = app
        self.db_con = db_con
        self.admin_login_required = admin_login_required_decorator
        self.allowed_file = cek_file

    def register_routes(self):
        @self.app.route('/admin/dashboard')
        @self.admin_login_required
        def dashboard_admin(): # ISI DAHSBOARD ADMIN
            counts = self.db_con.get_counts()
            gurus = self.db_con.get_users_by_role('guru')
            murids = self.db_con.get_users_by_role('murid')
            admins = self.db_con.get_users_by_role('admin')
            ekskul_list = self.db_con.get_all_ekskul()
            list_materi = self.db_con.get_all_materi_ekskul()
            pending_registrations = self.db_con.get_pending_registrations_detailed()
            list_pengumuman = self.db_con.get_all_pengumuman()
            raw_absensi_list = self.db_con.get_all_absensi_ekskul_detailed()
            absensi_list_processed = []
            for absen_item_raw in raw_absensi_list:
                absen_item = {}
                if hasattr(absen_item_raw, '_asdict'): 
                    absen_item = absen_item_raw._asdict().copy()
                elif isinstance(absen_item_raw, dict): 
                    absen_item = absen_item_raw.copy()
                else: 
                    absen_item = dict(absen_item_raw)

                jam_mulai = absen_item.get('jam_mulai_kegiatan')
                if jam_mulai is None:
                    absen_item['jam_mulai_kegiatan_formatted'] = '-'
                elif isinstance(jam_mulai, str): 
                    absen_item['jam_mulai_kegiatan_formatted'] = jam_mulai
                elif isinstance(jam_mulai, timedelta):  
                    total_seconds = int(jam_mulai.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    absen_item['jam_mulai_kegiatan_formatted'] = f"{hours:02d}:{minutes:02d}"
                elif hasattr(jam_mulai, 'strftime'): 
                    absen_item['jam_mulai_kegiatan_formatted'] = jam_mulai.strftime('%H:%M')
                else:
                    absen_item['jam_mulai_kegiatan_formatted'] = str(jam_mulai) 
                absensi_list_processed.append(absen_item)
            return render_template('admin/dashboard_admin.html', 
                                   jumlah_pengguna=counts.get('users',0), 
                                   jumlah_ekskul=counts.get('ekskul',0), 
                                   jumlah_pengumuman=counts.get('pengumuman',0),
                                   jumlah_materi_ekskul=counts.get('materi_ekskul',0),
                                   gurus=gurus, murids=murids, admins=admins,
                                   ekskul_list=ekskul_list, list_materi=list_materi,
                                   pending_registrations=pending_registrations,
                                   list_pengumuman=list_pengumuman,
                                   absensi_list=absensi_list_processed
                                  )

        @self.app.route('/admin/users')
        @self.admin_login_required
        def users_admin():
            gurus = self.db_con.get_users_by_role('guru')
            murids = self.db_con.get_users_by_role('murid')
            admins = self.db_con.get_users_by_role('admin')
            return render_template('admin/users_admin.html', gurus=gurus, murids=murids, admins=admins)

        @self.app.route('/admin/users/add', methods=['GET', 'POST'])
        @self.admin_login_required
        def add_user_admin():
            form_data_repopulate = request.form.to_dict() if request.method == 'POST' else {}
            if request.method == 'POST':
                user_data = {
                    'username': request.form.get('username','').strip(),
                    'password': request.form.get('password',''), 
                    'nama_lengkap': request.form.get('nama_lengkap','').strip(),
                    'email': request.form.get('email','').strip(),
                    'peran': request.form.get('peran',''),
                    'nomor_induk': request.form.get('nomor_induk','').strip() or None, 
                    'status_aktif': True 
                }
                form_data_repopulate.update(user_data)   
                if not all([user_data['username'], user_data['password'], user_data['nama_lengkap'], user_data['email'], user_data['peran']]):
                    flash('Semua field yang ditandai bintang (*) wajib diisi.', 'danger')
                elif self.db_con.get_user_by_username(user_data['username']):
                    flash(f"Username '{user_data['username']}' sudah digunakan.", 'danger')
                else:
                    user_id = self.db_con.add_user(user_data)
                    if user_id:
                        flash(f"Pengguna '{user_data['nama_lengkap']}' berhasil ditambahkan dengan ID: {user_id}!", 'success')
                        return redirect(url_for('users_admin')) 
                    else:
                        flash('Gagal menambahkan pengguna. Periksa log server untuk detail.', 'danger')
            return render_template('admin/user_form_admin.html', action='Tambah', user_data=form_data_repopulate)

        @self.app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
        @self.admin_login_required
        def edit_user_admin(user_id):
            user_to_edit = self.db_con.get_user_by_id(user_id)
            if not user_to_edit:
                flash(f"Pengguna dengan ID {user_id} tidak ditemukan.", 'danger')
                return redirect(url_for('users_admin')) 
            
            form_data_display = user_to_edit.copy()
            if 'password_hash' in form_data_display: del form_data_display['password_hash']
            if 'password' in form_data_display: del form_data_display['password']
            if request.method == 'POST':
                form_data_display.update(request.form.to_dict())
                status_aktif_form = 'status_aktif' in request.form
                user_data_update = {
                    'username': request.form.get('username','').strip(),
                    'nama_lengkap': request.form.get('nama_lengkap','').strip(),
                    'email': request.form.get('email','').strip(),
                    'peran': request.form.get('peran',''),
                    'nomor_induk': request.form.get('nomor_induk','').strip() or None,
                    'status_aktif': status_aktif_form
                }
                password_baru = request.form.get('password','').strip()
                if password_baru:
                    user_data_update['password'] = password_baru

                form_data_display.update(user_data_update)
                if 'password' in form_data_display and not password_baru : del form_data_display['password']

                if not all([user_data_update['username'], user_data_update['nama_lengkap'], user_data_update['email'], user_data_update['peran']]):
                    flash('Username, Nama Lengkap, Email, dan Peran wajib diisi.', 'danger')
                else:
                    if self.db_con.update_user(user_id, user_data_update):
                        flash(f"Data pengguna '{user_data_update['nama_lengkap']}' berhasil diupdate!", 'success')
                        return redirect(url_for('users_admin')) 
                    else:
                        flash('Gagal mengupdate data pengguna. Periksa log server.', 'danger')
            return render_template('admin/user_form_admin.html', action='Edit', user_data=form_data_display, cancel_url=url_for('users_admin'))
        
        @self.app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
        @self.admin_login_required
        def delete_user_admin(user_id):
            if session.get('user_id') == user_id: 
                flash("Anda tidak dapat menghapus akun Anda sendiri.", "danger")
                return redirect(url_for('users_admin'))

            user_to_delete = self.db_con.get_user_by_id(user_id)
            if not user_to_delete:
                flash(f"Pengguna dengan ID {user_id} tidak ditemukan.", 'danger')
                return redirect(url_for('users_admin'))

            if user_to_delete['peran'] == 'admin':
                admins = self.db_con.get_users_by_role('admin')
                if len(admins) <= 1: 
                    flash("Tidak dapat menghapus satu-satunya admin.", "danger")
                    return redirect(url_for('users_admin'))

            if self.db_con.delete_user(user_id):
                flash(f"Pengguna '{user_to_delete['nama_lengkap']}' berhasil dihapus.", 'success')
            else:
                flash(f"Gagal menghapus pengguna '{user_to_delete['nama_lengkap']}'. Periksa log server.", 'danger')
            return redirect(url_for('users_admin'))

        @self.app.route('/admin/ekskul')
        @self.admin_login_required
        def ekskul_admin():
            ekskul_list = self.db_con.get_all_ekskul()
            return render_template('admin/ekskul_admin.html', ekskul_list=ekskul_list) 

        @self.app.route('/admin/ekskul/add', methods=['GET', 'POST'])
        @self.admin_login_required
        def add_ekskul_admin():
            list_guru = self.db_con.get_users_by_role('guru')
            form_data_repopulate = {'status_aktif': True} 
            if request.method == 'POST':
                 form_data_repopulate.update(request.form.to_dict())

            if request.method == 'POST':
                id_guru_pembina_str = request.form.get('id_guru_pembina')
                kuota_maksimal_str = request.form.get('kuota_maksimal', '')

                ekskul_data = {
                    'nama_ekskul': request.form.get('nama_ekskul','').strip(),
                    'id_guru_pembina': int(id_guru_pembina_str) if id_guru_pembina_str and id_guru_pembina_str.isdigit() else None,
                    'jadwal_deskripsi': request.form.get('jadwal_deskripsi','').strip(),
                    'lokasi': request.form.get('lokasi','').strip(),
                    'kuota_maksimal': int(kuota_maksimal_str) if kuota_maksimal_str.isdigit() else None,
                    'deskripsi': request.form.get('deskripsi','').strip(),
                    'kategori': request.form.get('kategori','').strip(),
                    'status_aktif': 'status_aktif' in request.form,
                    'url_logo_ekskul': None 
                }
                form_data_repopulate.update(ekskul_data)
                if 'logo_file' in request.files:
                    file_logo = request.files['logo_file']
                    if file_logo and file_logo.filename != '':
                        if self.allowed_file(file_logo.filename, self.app.config['ALLOWED_LOGO_EXTENSIONS']):
                            logo_filename = secure_filename(file_logo.filename)
                            logo_upload_path = self.app.config['LOGO_UPLOAD_FOLDER']
                            if not os.path.exists(logo_upload_path):
                                os.makedirs(logo_upload_path, exist_ok=True)
                            save_path = os.path.join(logo_upload_path, logo_filename)
                            try:
                                file_logo.save(save_path)
                                ekskul_data['url_logo_ekskul'] = logo_filename
                                form_data_repopulate['url_logo_ekskul'] = logo_filename 
                                flash(f"Logo '{logo_filename}' berhasil diunggah.", 'info')
                            except Exception as e:
                                flash(f"Gagal menyimpan file logo: {e}", 'danger')
                        else:
                            flash('Format file logo tidak diizinkan. Logo tidak diunggah.', 'warning')

                if not ekskul_data['nama_ekskul']:
                    flash('Nama Ekstrakurikuler wajib diisi.', 'danger')
                else:
                    ekskul_id = self.db_con.add_ekskul(ekskul_data)
                    if ekskul_id:
                        flash(f"Ekstrakurikuler '{ekskul_data['nama_ekskul']}' berhasil ditambahkan!", 'success')
                        return redirect(url_for('ekskul_admin'))
                    else:
                        flash('Gagal menambahkan ekstrakurikuler. Periksa log server.', 'danger')
            return render_template('admin/ekskul_form_admin.html', 
                                   action='Tambah', 
                                   ekskul_data=form_data_repopulate, 
                                   list_guru=list_guru, 
                                   cancel_url=url_for('ekskul_admin'))

        @self.app.route('/admin/ekskul/edit/<int:ekskul_id>', methods=['GET', 'POST'])
        @self.admin_login_required
        def edit_ekskul_admin(ekskul_id):
            ekskul_saat_ini = self.db_con.get_ekskul_by_id(ekskul_id)
            if not ekskul_saat_ini:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan.", 'danger')
                return redirect(url_for('ekskul_admin'))

            list_guru = self.db_con.get_users_by_role('guru')
            form_data_display = ekskul_saat_ini.copy() 
            if request.method == 'POST':
                form_data_display.update(request.form.to_dict())
                id_guru_pembina_str = request.form.get('id_guru_pembina')
                kuota_maksimal_str = request.form.get('kuota_maksimal', '')
                ekskul_data_update = {
                    'nama_ekskul': request.form.get('nama_ekskul','').strip(),
                    'id_guru_pembina': int(id_guru_pembina_str) if id_guru_pembina_str and id_guru_pembina_str.isdigit() else None,
                    'jadwal_deskripsi': request.form.get('jadwal_deskripsi','').strip(),
                    'lokasi': request.form.get('lokasi','').strip(),
                    'kuota_maksimal': int(kuota_maksimal_str) if kuota_maksimal_str.isdigit() else None,
                    'deskripsi': request.form.get('deskripsi','').strip(),
                    'kategori': request.form.get('kategori','').strip(),
                    'status_aktif': 'status_aktif' in request.form
                }
                form_data_display.update(ekskul_data_update)
                logo_lama_filename = ekskul_saat_ini.get('url_logo_ekskul')
                if request.form.get('hapus_logo_sekarang') == '1': 
                    if logo_lama_filename:
                        path_logo_lama = os.path.join(self.app.config['LOGO_UPLOAD_FOLDER'], logo_lama_filename)
                        try:
                            if os.path.exists(path_logo_lama): os.remove(path_logo_lama)
                            flash(f"Logo lama '{logo_lama_filename}' berhasil dihapus.", 'info')
                        except Exception as e:
                            flash(f"Gagal menghapus file logo lama: {e}", 'warning')
                    ekskul_data_update['url_logo_ekskul'] = None
                    form_data_display['url_logo_ekskul'] = None 
                    logo_lama_filename = None

                if 'logo_file' in request.files:
                    file_logo_baru = request.files['logo_file']
                    if file_logo_baru and file_logo_baru.filename != '':
                        if self.allowed_file(file_logo_baru.filename, self.app.config['ALLOWED_LOGO_EXTENSIONS']):
                            logo_baru_filename = secure_filename(file_logo_baru.filename)
                            save_path_baru = os.path.join(self.app.config['LOGO_UPLOAD_FOLDER'], logo_baru_filename)
                            try:
                                file_logo_baru.save(save_path_baru)
                                ekskul_data_update['url_logo_ekskul'] = logo_baru_filename
                                form_data_display['url_logo_ekskul'] = logo_baru_filename
                                flash(f"Logo baru '{logo_baru_filename}' berhasil diunggah.", 'info')
                                if logo_lama_filename and logo_lama_filename != logo_baru_filename:
                                    path_logo_lama_hps = os.path.join(self.app.config['LOGO_UPLOAD_FOLDER'], logo_lama_filename)
                                    if os.path.exists(path_logo_lama_hps):
                                        try: os.remove(path_logo_lama_hps)
                                        except Exception as e: flash(f"Gagal menghapus logo lama saat replace: {e}", 'warning')
                            except Exception as e:
                                flash(f"Gagal menyimpan file logo baru: {e}", 'danger')
                                if 'url_logo_ekskul' in ekskul_data_update: del ekskul_data_update['url_logo_ekskul']
                                form_data_display['url_logo_ekskul'] = logo_lama_filename 
                        elif file_logo_baru.filename != '':
                            flash('Format file logo baru tidak diizinkan. Logo tidak diubah.', 'warning')
                elif 'url_logo_ekskul' not in ekskul_data_update: 
                    ekskul_data_update['url_logo_ekskul'] = logo_lama_filename 

                if not ekskul_data_update['nama_ekskul']:
                    flash('Nama Ekstrakurikuler wajib diisi.', 'danger')
                else:
                    if self.db_con.update_ekskul(ekskul_id, ekskul_data_update):
                        flash(f"Data Ekstrakurikuler '{ekskul_data_update['nama_ekskul']}' berhasil diupdate!", 'success')
                        return redirect(url_for('ekskul_admin'))
                    else:
                        flash('Gagal mengupdate data ekstrakurikuler. Periksa log server.', 'danger')
            return render_template('admin/ekskul_form_admin.html', action='Edit', ekskul_data=form_data_display, list_guru=list_guru, cancel_url=url_for('ekskul_admin')) 

        @self.app.route('/admin/ekskul/delete/<int:ekskul_id>', methods=['POST'])
        @self.admin_login_required
        def delete_ekskul_admin(ekskul_id):
            ekskul_to_delete = self.db_con.get_ekskul_by_id(ekskul_id)
            if not ekskul_to_delete:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan.",'danger')
                return redirect(url_for('ekskul_admin'))

            logo_filename = ekskul_to_delete.get('url_logo_ekskul')
            if logo_filename: 
                path_logo_fisik = os.path.join(self.app.config['LOGO_UPLOAD_FOLDER'], logo_filename)
                try:
                    if os.path.exists(path_logo_fisik):
                        os.remove(path_logo_fisik)
                        flash(f"File logo '{logo_filename}' berhasil dihapus dari server.", 'info')
                except Exception as e:
                    flash(f"Gagal menghapus file logo fisik '{logo_filename}': {e}", 'warning')
            
            if self.db_con.delete_ekskul(ekskul_id): 
                flash(f"Ekstrakurikuler '{ekskul_to_delete['nama_ekskul']}' dan data terkait berhasil dihapus dari database.", 'success')
            else:
                flash(f"Gagal menghapus '{ekskul_to_delete['nama_ekskul']}' dari database.", 'danger')
            return redirect(url_for('ekskul_admin'))

        @self.app.route('/admin/ekskul/detail/<int:ekskul_id>')
        @self.admin_login_required
        def ekskul_detail_admin(ekskul_id):
            ekskul_info = self.db_con.get_ekskul_by_id(ekskul_id)
            if not ekskul_info:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan.", 'danger')
                return redirect(url_for('ekskul_admin'))
            
            current_tahun_ajaran = self.db_con.get_tahun_ajaran_aktif() 
            members = self.db_con.get_members_of_ekskul(ekskul_id, current_tahun_ajaran)
            list_materi_ekskul = self.db_con.get_materi_by_ekskul_id(ekskul_id) 
            return render_template('admin/ekskul_detail_admin.html', 
                                   ekskul_info=ekskul_info, 
                                   members=members,
                                   list_materi=list_materi_ekskul,
                                   tahun_ajaran_display=current_tahun_ajaran,
                                   cancel_url=url_for('ekskul_admin')) 

        @self.app.route('/admin/ekskul/<int:ekskul_id>/register', methods=['GET', 'POST'])
        @self.admin_login_required
        def register_student_ekskul_admin(ekskul_id):
            ekskul_info = self.db_con.get_ekskul_by_id(ekskul_id)
            if not ekskul_info:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan.", 'danger')
                return redirect(url_for('ekskul_admin'))

            current_tahun_ajaran = self.db_con.get_tahun_ajaran_aktif()
            available_students = self.db_con.get_all_active_murid_exclude_ekskul(ekskul_id, current_tahun_ajaran)
            if request.method == 'POST':
                murid_id_to_register_str = request.form.get('id_murid')
                tahun_ajaran_form = request.form.get('tahun_ajaran', current_tahun_ajaran)
                if not murid_id_to_register_str or not tahun_ajaran_form:
                    flash("Pilih murid dan masukkan tahun ajaran.", "warning")
                else:
                    try:
                        murid_id_to_register = int(murid_id_to_register_str)
                        catatan_pendaftar = f"Didaftarkan oleh Admin: {session.get('nama_lengkap')}"
                        hasil_pendaftaran = self.db_con.register_student_for_ekskul(
                            murid_id_to_register, ekskul_id, tahun_ajaran_form, 
                            status_pendaftaran='Disetujui', 
                            catatan_pendaftar=catatan_pendaftar
                        )
                        if isinstance(hasil_pendaftaran, int):
                            murid_info = self.db_con.get_user_by_id(murid_id_to_register)
                            flash(f"Murid '{murid_info['nama_lengkap'] if murid_info else 'ID: '+str(murid_id_to_register)}' berhasil didaftarkan ke ekskul '{ekskul_info['nama_ekskul']}'.", 'success')
                            return redirect(url_for('ekskul_detail_admin', ekskul_id=ekskul_id))
                        elif hasil_pendaftaran == "KUOTA_PENUH":
                             flash(f"Gagal mendaftarkan murid. Kuota untuk ekskul '{ekskul_info['nama_ekskul']}' sudah penuh.", "warning")
                        elif hasil_pendaftaran == "SUDAH_TERDAFTAR":
                            murid_info = self.db_con.get_user_by_id(murid_id_to_register)
                            flash(f"Gagal mendaftarkan murid '{murid_info['nama_lengkap'] if murid_info else 'ID: '+str(murid_id_to_register)}'. Murid tersebut sudah memiliki record pendaftaran di ekskul '{ekskul_info['nama_ekskul']}' untuk tahun ajaran ini.", "warning")
                        elif hasil_pendaftaran == "EKSKUL_NOT_FOUND":
                            flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan saat proses pendaftaran.", 'danger')
                        else: 
                            flash(f"Gagal mendaftarkan murid ke ekskul '{ekskul_info['nama_ekskul']}'. Terjadi kesalahan pada sistem.", 'danger')

                    except ValueError:
                        flash("ID Murid tidak valid.", "danger")
                    except Exception as e:
                        flash(f"Terjadi kesalahan internal: {e}", "danger")
                return redirect(url_for('register_student_ekskul_admin', ekskul_id=ekskul_id))
            return render_template('admin/register_student_ekskul_form.html', 
                                   ekskul_info=ekskul_info, 
                                   available_students=available_students, 
                                   current_tahun_ajaran=current_tahun_ajaran,
                                   cancel_url=url_for('ekskul_detail_admin', ekskul_id=ekskul_id)) 

        @self.app.route('/admin/ekskul/remove_member/<int:pendaftaran_id>', methods=['POST'])
        @self.admin_login_required
        def remove_student_from_ekskul_admin(pendaftaran_id):
            ekskul_id_redirect = request.form.get('ekskul_id_redirect') 
            catatan_admin_pembina = f"Status diubah menjadi 'Berhenti' oleh Admin: {session.get('nama_lengkap')}"
            if self.db_con.update_ekskul_registration_status(pendaftaran_id, new_status='Berhenti', catatan_admin=catatan_admin_pembina):
                flash(f"Anggota ekskul (Pendaftaran ID: {pendaftaran_id}) statusnya diubah menjadi 'Berhenti'.", 'success')
            else:
                flash(f"Gagal mengubah status anggota ekskul. Periksa log server.", 'danger')
            
            if ekskul_id_redirect and ekskul_id_redirect.isdigit():
                return redirect(url_for('ekskul_detail_admin', ekskul_id=int(ekskul_id_redirect)))
            return redirect(url_for('ekskul_admin'))

        @self.app.route('/admin/materi_ekskul')
        @self.admin_login_required
        def materi_ekskul_admin():
            list_materi = self.db_con.get_all_materi_ekskul()
            return render_template('admin/materi_ekskul_admin.html', list_materi=list_materi) 

        @self.app.route('/admin/materi_ekskul/tambah', methods=['GET', 'POST'])
        @self.admin_login_required
        def tambah_materi_ekskul_admin():
            id_ekskul_default = request.args.get('id_ekskul_default', type=int)
            list_ekskul = self.db_con.get_all_ekskul()
            form_data_repopulate = {'id_ekskul': id_ekskul_default if id_ekskul_default and request.method == 'GET' else None}
            if request.method == 'POST':
                 form_data_repopulate.update(request.form.to_dict())

            if request.method == 'POST':
                id_ekskul_form = request.form.get('id_ekskul')
                judul_materi_form = request.form.get('judul_materi','').strip()
                deskripsi_materi_form = request.form.get('deskripsi_materi','').strip()
                tipe_konten_form = request.form.get('tipe_konten')
                form_data_repopulate.update({
                    'id_ekskul': int(id_ekskul_form) if id_ekskul_form and id_ekskul_form.isdigit() else None,
                    'judul_materi': judul_materi_form,
                    'deskripsi_materi': deskripsi_materi_form,
                    'tipe_konten': tipe_konten_form
                })
                path_konten_final = None
                isi_konten_teks_final = None
                save_to_db = False
                if not form_data_repopulate.get('id_ekskul') or not judul_materi_form or not tipe_konten_form:
                    flash("Ekskul, Judul Materi, dan Tipe Konten wajib diisi.", "danger")
                else:
                    if tipe_konten_form == 'file':
                        if 'file_konten' not in request.files or request.files['file_konten'].filename == '':
                            flash('File wajib diunggah jika tipe konten adalah file.', 'danger') 
                        else:
                            file = request.files['file_konten']
                            if file and self.allowed_file(file.filename, self.app.config['ALLOWED_EXTENSIONS']):
                                filename = secure_filename(file.filename)
                                file.save(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))
                                path_konten_final = filename
                                save_to_db = True
                                flash(f'File {filename} berhasil diunggah.', 'info')
                            elif file:
                                flash('Tipe file tidak diizinkan.', 'danger')
                    elif tipe_konten_form in ['link', 'video_embed']:
                        path_konten_final = request.form.get('path_konten_atau_link_url','').strip()
                        form_data_repopulate['path_konten_atau_link_url'] = path_konten_final 
                        if not path_konten_final:
                            flash('URL/Link atau Kode Embed Video wajib diisi.', 'danger')
                        else:
                            save_to_db = True
                    elif tipe_konten_form == 'teks':
                        isi_konten_teks_final = request.form.get('isi_konten_teks_area','').strip()
                        form_data_repopulate['isi_konten_teks_area'] = isi_konten_teks_final 
                        if not isi_konten_teks_final:
                            flash('Isi konten teks wajib diisi.', 'danger')
                        else:
                            save_to_db = True
                    else: 
                        flash('Tipe konten tidak valid dipilih.', 'danger')

                    if save_to_db:
                        data_materi_to_save = {
                            'id_ekskul': form_data_repopulate.get('id_ekskul'), 
                            'judul_materi': judul_materi_form,
                            'deskripsi_materi': deskripsi_materi_form, 
                            'tipe_konten': tipe_konten_form,
                            'path_konten_atau_link': path_konten_final,
                            'isi_konten_teks': isi_konten_teks_final,
                            'id_pengunggah': session['user_id']
                        }
                        materi_id = self.db_con.add_materi_ekskul(data_materi_to_save)
                        if materi_id:
                            flash("Materi ekstrakurikuler berhasil ditambahkan!", "success")
                            return redirect(url_for('materi_ekskul_admin'))
                        else:
                            flash("Gagal menambahkan materi ke database. Periksa log.", "danger")
            return render_template('admin/materi_ekskul_form_admin.html', 
                                   action="Tambah", 
                                   materi_data=form_data_repopulate, 
                                   list_ekskul=list_ekskul,
                                   cancel_url=url_for('materi_ekskul_admin')) 

        @self.app.route('/admin/materi_ekskul/edit/<int:id_materi_ekskul>', methods=['GET', 'POST'])
        @self.admin_login_required
        def edit_materi_ekskul_admin(id_materi_ekskul):
            materi_data_lama = self.db_con.get_materi_ekskul_by_id(id_materi_ekskul)
            if not materi_data_lama:
                flash("Materi ekstrakurikuler tidak ditemukan.", "danger")
                return redirect(url_for('materi_ekskul_admin')) 

            list_ekskul = self.db_con.get_all_ekskul()
            form_data_display = materi_data_lama.copy()
            if form_data_display.get('tipe_konten') in ['link', 'video_embed']:
                form_data_display['path_konten_atau_link_url'] = form_data_display.get('path_konten_atau_link')
            elif form_data_display.get('tipe_konten') == 'teks':
                form_data_display['isi_konten_teks_area'] = form_data_display.get('isi_konten_teks')

            if request.method == 'POST':
                form_data_display.update(request.form.to_dict()) 
                id_ekskul_form = request.form.get('id_ekskul')
                judul_materi_form = request.form.get('judul_materi','').strip()
                deskripsi_materi_form = request.form.get('deskripsi_materi','').strip()
                tipe_konten_form = request.form.get('tipe_konten')
                data_to_update = {
                    'id_ekskul': int(id_ekskul_form) if id_ekskul_form and id_ekskul_form.isdigit() else materi_data_lama['id_ekskul'],
                    'judul_materi': judul_materi_form if judul_materi_form else materi_data_lama['judul_materi'],
                    'deskripsi_materi': deskripsi_materi_form,
                    'tipe_konten': tipe_konten_form if tipe_konten_form else materi_data_lama['tipe_konten']
                }
                form_data_display.update(data_to_update)
                delete_old_file_flag = False
                old_file_name_from_db = materi_data_lama.get('path_konten_atau_link') if materi_data_lama.get('tipe_konten') == 'file' else None
                is_content_valid_overall = True 
                if data_to_update['tipe_konten'] == 'file':
                    if 'file_konten' in request.files and request.files['file_konten'].filename != '':
                        file = request.files['file_konten']
                        if self.allowed_file(file.filename, self.app.config['ALLOWED_EXTENSIONS']):
                            if old_file_name_from_db: delete_old_file_flag = True
                            filename = secure_filename(file.filename)
                            try:
                                file.save(os.path.join(self.app.config['UPLOAD_FOLDER'], filename))
                                data_to_update['path_konten_atau_link'] = filename
                                data_to_update['isi_konten_teks'] = None
                                form_data_display['path_konten_atau_link'] = filename 
                                flash(f'File baru {filename} berhasil diunggah.', 'info')
                            except Exception as e:
                                flash(f'Gagal menyimpan file baru: {e}','danger'); is_content_valid_overall = False
                        else:
                            flash('Tipe file baru tidak diizinkan.', 'danger'); is_content_valid_overall = False
                    elif materi_data_lama['tipe_konten'] == 'file': 
                        data_to_update['path_konten_atau_link'] = materi_data_lama['path_konten_atau_link']
                        data_to_update['isi_konten_teks'] = None
                    elif materi_data_lama['tipe_konten'] != 'file':
                        flash('File wajib diunggah jika tipe konten diubah menjadi "file".', 'danger'); is_content_valid_overall = False
                
                elif data_to_update['tipe_konten'] in ['link', 'video_embed']:
                    new_val = request.form.get('path_konten_atau_link_url','').strip()
                    form_data_display['path_konten_atau_link_url'] = new_val
                    if not new_val: flash('URL/Link atau Kode Embed wajib diisi.', 'danger'); is_content_valid_overall = False
                    else:
                        data_to_update['path_konten_atau_link'] = new_val
                        data_to_update['isi_konten_teks'] = None
                        if old_file_name_from_db: delete_old_file_flag = True
                
                elif data_to_update['tipe_konten'] == 'teks':
                    new_val = request.form.get('isi_konten_teks_area','').strip()
                    form_data_display['isi_konten_teks_area'] = new_val 
                    if not new_val: flash('Isi konten teks wajib diisi.', 'danger'); is_content_valid_overall = False
                    else:
                        data_to_update['isi_konten_teks'] = new_val
                        data_to_update['path_konten_atau_link'] = None
                        if old_file_name_from_db: delete_old_file_flag = True
                
                if not data_to_update.get('judul_materi') : 
                    flash("Judul Materi wajib diisi.", "danger"); is_content_valid_overall = False

                if is_content_valid_overall:
                    if self.db_con.update_materi_ekskul(id_materi_ekskul, data_to_update):
                        if delete_old_file_flag and old_file_name_from_db:
                            try:
                                file_to_remove_path = os.path.join(self.app.config['UPLOAD_FOLDER'], old_file_name_from_db)
                                if os.path.exists(file_to_remove_path):
                                    os.remove(file_to_remove_path)
                                    flash('File lama berhasil dihapus dari server.', 'info')
                            except OSError as e: flash(f'Gagal menghapus file lama: {e}', 'warning')
                        flash("Materi berhasil diperbarui!", "success")
                        return redirect(url_for('materi_ekskul_admin')) 
                    else: 
                        if not get_flashed_messages(category_filter=["danger"]): 
                             flash("Gagal memperbarui materi ke database.", "danger")
            return render_template('admin/materi_ekskul_form_admin.html', 
                                   action="Edit", 
                                   materi_data=form_data_display, 
                                   list_ekskul=list_ekskul, 
                                   id_materi_ekskul=id_materi_ekskul,
                                   cancel_url=url_for('materi_ekskul_admin')) 


        @self.app.route('/admin/materi_ekskul/hapus/<int:id_materi_ekskul>', methods=['POST'])
        @self.admin_login_required
        def hapus_materi_ekskul_admin(id_materi_ekskul):
            materi_info_deleted = self.db_con.delete_materi_ekskul(id_materi_ekskul)
            if materi_info_deleted:
                if materi_info_deleted['tipe_konten'] == 'file' and materi_info_deleted['path_konten_atau_link']:
                    try:
                        file_path_del = os.path.join(self.app.config['UPLOAD_FOLDER'], materi_info_deleted['path_konten_atau_link'])
                        if os.path.exists(file_path_del):
                            os.remove(file_path_del)
                            flash(f"File materi fisik '{materi_info_deleted['path_konten_atau_link']}' berhasil dihapus.", 'info')
                    except OSError as e:
                        flash(f"Gagal menghapus file fisik: {e}", "warning")
                flash("Materi ekstrakurikuler berhasil dihapus dari database!", "success")
            else:
                flash("Gagal menghapus materi ekstrakurikuler dari database.", "danger")
            return redirect(url_for('materi_ekskul_admin')) 

        @self.app.route('/admin/ekskul/pendaftaran')
        @self.admin_login_required
        def kelola_pendaftaran_ekskul_admin():
            pending_registrations = self.db_con.get_pending_registrations_detailed()
            return render_template('admin/kelola_pendaftaran_ekskul.html', 
                                   pending_registrations=pending_registrations,
                                   judul_halaman="Kelola Semua Pendaftaran Ekskul") 

        @self.app.route('/admin/ekskul/pendaftaran/<int:pendaftaran_id>/setujui', methods=['POST'])
        @self.admin_login_required
        def setujui_pendaftaran_admin(pendaftaran_id):
            pendaftaran_info = self.db_con.get_pendaftaran_ekskul_by_id(pendaftaran_id)
            if not pendaftaran_info:
                flash("Data pendaftaran tidak ditemukan.", "danger")
                return redirect(request.referrer or url_for('kelola_pendaftaran_ekskul_admin'))

            ekskul_info = self.db_con.get_ekskul_by_id(pendaftaran_info['id_ekskul'])
            catatan = f"Disetujui oleh Admin: {session.get('nama_lengkap')}"
            if ekskul_info and ekskul_info.get('kuota_maksimal') is not None:
                jumlah_peserta_aktif = self.db_con.count_active_members_ekskul(pendaftaran_info['id_ekskul'], pendaftaran_info['tahun_ajaran'])
                if jumlah_peserta_aktif >= ekskul_info['kuota_maksimal']:
                    flash(f"Kuota untuk ekskul '{ekskul_info['nama_ekskul']}' sudah penuh. Pendaftaran tidak dapat disetujui.", "warning")
                    self.db_con.update_ekskul_registration_status(pendaftaran_id, 'Ditolak', f"Ditolak otomatis karena kuota penuh saat approval oleh Admin: {session.get('nama_lengkap')}")
                    return redirect(request.referrer or url_for('kelola_pendaftaran_ekskul_admin'))

            if self.db_con.update_ekskul_registration_status(pendaftaran_id, 'Disetujui', catatan):
                flash('Pendaftaran berhasil disetujui.', 'success')
            else:
                flash('Gagal menyetujui pendaftaran.', 'danger')
            return redirect(request.referrer or url_for('kelola_pendaftaran_ekskul_admin'))

        @self.app.route('/admin/ekskul/pendaftaran/<int:pendaftaran_id>/tolak', methods=['POST'])
        @self.admin_login_required
        def tolak_pendaftaran_admin(pendaftaran_id):
            alasan = request.form.get('alasan_penolakan', 'Ditolak oleh Admin.')
            catatan = f"{alasan} (Admin: {session.get('nama_lengkap')})"
            if self.db_con.update_ekskul_registration_status(pendaftaran_id, 'Ditolak', catatan):
                flash('Pendaftaran berhasil ditolak.', 'success')
            else:
                flash('Gagal menolak pendaftaran.', 'danger')
            return redirect(request.referrer or url_for('kelola_pendaftaran_ekskul_admin'))

        @self.app.route('/admin/pengumuman')
        @self.admin_login_required
        def pengumuman_admin():
            list_pengumuman = self.db_con.get_all_pengumuman()
            return render_template('admin/pengumuman_admin.html', list_pengumuman=list_pengumuman)

        @self.app.route('/admin/pengumuman/tambah', methods=['GET', 'POST'])
        @self.admin_login_required
        def tambah_pengumuman_admin():
            list_ekskul = self.db_con.get_all_ekskul()
            form_data_repopulate = {} 
            if request.method == 'POST':
                form_data_repopulate = request.form.to_dict()
                judul = request.form.get('judul_pengumuman','').strip()
                isi = request.form.get('isi_pengumuman','').strip()
                target_peran_form = request.form.get('target_peran')
                target_peran_db = target_peran_form if target_peran_form and target_peran_form in ['admin', 'guru', 'murid'] else None
                if target_peran_form == "semua":
                     target_peran_db = 'semua'
                elif not target_peran_form :
                    target_peran_db = 'semua'
                target_ekskul_id_str = request.form.get('target_ekskul_id')
                target_ekskul_id = int(target_ekskul_id_str) if target_ekskul_id_str and target_ekskul_id_str.isdigit() else None
                form_data_repopulate['target_peran'] = target_peran_db 
                form_data_repopulate['target_ekskul_id'] = target_ekskul_id
                if not judul or not isi:
                    flash("Judul dan Isi pengumuman wajib diisi.", "danger")
                else:
                    data_pengumuman = {
                        'judul_pengumuman': judul, 'isi_pengumuman': isi,
                        'id_pembuat': session['user_id'],
                        'target_peran': target_peran_db,
                        'target_ekskul_id': target_ekskul_id
                    }
                    pengumuman_id = self.db_con.add_pengumuman(data_pengumuman)
                    if pengumuman_id:
                        flash("Pengumuman berhasil ditambahkan!", "success")
                        return redirect(url_for('pengumuman_admin'))
                    else:
                        flash("Gagal menambahkan pengumuman. Periksa log server.", "danger")
            return render_template('admin/pengumuman_form_admin.html', 
                                   action="Tambah", 
                                   pengumuman_data=form_data_repopulate,
                                   list_ekskul=list_ekskul,
                                   cancel_url=url_for('pengumuman_admin'))

        @self.app.route('/admin/pengumuman/edit/<int:id_pengumuman>', methods=['GET', 'POST'])
        @self.admin_login_required
        def edit_pengumuman_admin(id_pengumuman):
            pengumuman_to_edit = self.db_con.get_pengumuman_by_id(id_pengumuman)
            if not pengumuman_to_edit:
                flash(f"Pengumuman dengan ID {id_pengumuman} tidak ditemukan.", "danger")
                return redirect(url_for('pengumuman_admin'))

            list_ekskul = self.db_con.get_all_ekskul()
            form_data_display = pengumuman_to_edit.copy() 
            if request.method == 'POST':
                form_data_display.update(request.form.to_dict()) 
                judul = request.form.get('judul_pengumuman','').strip()
                isi = request.form.get('isi_pengumuman','').strip()
                target_peran_form = request.form.get('target_peran')
                target_peran_db = target_peran_form if target_peran_form and target_peran_form in ['admin', 'guru', 'murid'] else None
                if target_peran_form == "semua": 
                     target_peran_db = 'semua'
                elif not target_peran_form :
                    target_peran_db = 'semua'
                target_ekskul_id_str = request.form.get('target_ekskul_id')
                target_ekskul_id = int(target_ekskul_id_str) if target_ekskul_id_str and target_ekskul_id_str.isdigit() else None
                form_data_display['target_peran'] = target_peran_db
                form_data_display['target_ekskul_id'] = target_ekskul_id
                if not judul or not isi:
                    flash("Judul dan Isi pengumuman wajib diisi.", "danger")
                else:
                    data_pengumuman_update = {
                        'judul_pengumuman': judul, 'isi_pengumuman': isi,
                        'target_peran': target_peran_db,
                        'target_ekskul_id': target_ekskul_id
                    }
                    if self.db_con.update_pengumuman(id_pengumuman, data_pengumuman_update):
                        flash("Pengumuman berhasil diperbarui!", "success")
                        return redirect(url_for('pengumuman_admin'))
                    else:
                        flash("Gagal memperbarui pengumuman. Periksa log server.", "danger")
            return render_template('admin/pengumuman_form_admin.html', 
                                   action="Edit", 
                                   pengumuman_data=form_data_display,
                                   list_ekskul=list_ekskul,
                                   id_pengumuman=id_pengumuman,
                                   cancel_url=url_for('pengumuman_admin')) 

        @self.app.route('/admin/pengumuman/hapus/<int:id_pengumuman>', methods=['POST'])
        @self.admin_login_required
        def hapus_pengumuman_admin(id_pengumuman):
            pengumuman_to_delete = self.db_con.get_pengumuman_by_id(id_pengumuman)
            judul_pengumuman = pengumuman_to_delete['judul_pengumuman'] if pengumuman_to_delete else f"ID {id_pengumuman}"

            if self.db_con.delete_pengumuman(id_pengumuman):
                flash(f"Pengumuman '{judul_pengumuman}' berhasil dihapus.", "success")
            else:
                flash(f"Gagal menghapus pengumuman '{judul_pengumuman}'.", "danger")
            return redirect(url_for('pengumuman_admin'))

        @self.app.route('/admin/absensi_ekskul')
        @self.admin_login_required
        def list_absensi_ekskul_admin():
            raw_absensi_list = self.db_con.get_all_absensi_ekskul_detailed()
            absensi_list_processed = []
            for absen_item_raw in raw_absensi_list:
                absen_item = {} 
                if hasattr(absen_item_raw, '_asdict'): absen_item = absen_item_raw._asdict().copy()
                elif isinstance(absen_item_raw, dict): absen_item = absen_item_raw.copy()
                else: absen_item = dict(absen_item_raw)
                jam_mulai = absen_item.get('jam_mulai_kegiatan')
                if isinstance(jam_mulai, timedelta):
                    total_seconds = int(jam_mulai.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    absen_item['jam_mulai_kegiatan_formatted'] = f"{hours:02d}:{minutes:02d}"
                elif hasattr(jam_mulai, 'strftime'): 
                    absen_item['jam_mulai_kegiatan_formatted'] = jam_mulai.strftime('%H:%M')
                elif jam_mulai is not None: 
                     absen_item['jam_mulai_kegiatan_formatted'] = str(jam_mulai)
                else: 
                    absen_item['jam_mulai_kegiatan_formatted'] = '-'
                absensi_list_processed.append(absen_item)
            return render_template('admin/absensi_ekskul_list.html', absensi_list=absensi_list_processed) 
        
        @self.app.route('/admin/absensi_ekskul/manage', methods=['GET', 'POST'], defaults={'id_pendaftaran_ekskul': None, 'tanggal_kegiatan_str': None})
        @self.app.route('/admin/absensi_ekskul/manage/<int:id_pendaftaran_ekskul>/<tanggal_kegiatan_str>', methods=['GET', 'POST'])
        @self.admin_login_required
        def manage_absensi_ekskul_admin(id_pendaftaran_ekskul, tanggal_kegiatan_str):
            action = "Edit" if id_pendaftaran_ekskul and tanggal_kegiatan_str else "Tambah"
            default_tahun_ajaran_val = self.db_con.get_tahun_ajaran_aktif()
            default_tanggal_untuk_form = date.today().isoformat()
            form_data = {
                'id_murid': None, 'id_ekskul': None, 'status_kehadiran': 'Hadir',
                'tanggal_kegiatan': default_tanggal_untuk_form,
                'tahun_ajaran': default_tahun_ajaran_val,
                'jam_mulai_kegiatan': '', 'catatan': ''
            }
            original_db_data_for_edit = None
            if action == "Edit":
                try:
                    db_entry = self.db_con.get_absensi_entry_for_edit(id_pendaftaran_ekskul, tanggal_kegiatan_str)
                    if db_entry:
                        original_db_data_for_edit = dict(db_entry)
                        form_data.update({
                            'id_murid': db_entry.get('id_murid'),
                            'id_ekskul': db_entry.get('id_ekskul'),
                            'status_kehadiran': db_entry.get('status_kehadiran'),
                            'tanggal_kegiatan': tanggal_kegiatan_str, 
                            'tahun_ajaran': db_entry.get('tahun_ajaran', default_tahun_ajaran_val),
                            'jam_mulai_kegiatan': db_entry.get('jam_mulai_kegiatan') if db_entry.get('jam_mulai_kegiatan') else '',
                            'catatan': db_entry.get('catatan','')
                        })
                        default_tahun_ajaran_val = form_data['tahun_ajaran']
                        default_tanggal_untuk_form = tanggal_kegiatan_str
                    else:
                        flash("Data absensi yang akan diedit tidak ditemukan.", "warning")
                        return redirect(url_for('pengumuman_admin'))
                except ValueError:
                    flash("Format tanggal untuk edit tidak valid.", "danger")
                    return redirect(url_for('pengumuman_admin'))
                except Exception as e:
                    flash(f"Error mengambil data untuk diedit: {e}", "danger")
                    return redirect(url_for('pengumuman_admin'))

            if request.method == 'POST':
                admin_id = session['user_id']
                submitted_status_kehadiran = request.form.get('status_kehadiran')
                submitted_catatan_absen = request.form.get('catatan_absen', '')
                submitted_jam_kegiatan = request.form.get('jam_kegiatan') or None
                submitted_tanggal_kegiatan_form = request.form.get('tanggal_kegiatan') 
                submitted_tahun_ajaran_form = request.form.get('tahun_ajaran_pendaftaran') 
                submitted_id_murid_form_str = request.form.get('id_murid') 
                submitted_id_ekskul_form_str = request.form.get('id_ekskul') 
                form_data_on_post_error = form_data.copy() 

                if action == "Edit":
                    if original_db_data_for_edit:
                        form_data_on_post_error['id_murid'] = original_db_data_for_edit.get('id_murid')
                        form_data_on_post_error['id_ekskul'] = original_db_data_for_edit.get('id_ekskul')
                        form_data_on_post_error['tanggal_kegiatan'] = tanggal_kegiatan_str 
                        form_data_on_post_error['tahun_ajaran'] = original_db_data_for_edit.get('tahun_ajaran')
                    form_data_on_post_error['status_kehadiran'] = submitted_status_kehadiran
                    form_data_on_post_error['catatan'] = submitted_catatan_absen
                    form_data_on_post_error['jam_mulai_kegiatan'] = submitted_jam_kegiatan if submitted_jam_kegiatan else ''
                else: 
                    form_data_on_post_error.update({
                        'id_murid': int(submitted_id_murid_form_str) if submitted_id_murid_form_str and submitted_id_murid_form_str.isdigit() else None,
                        'id_ekskul': int(submitted_id_ekskul_form_str) if submitted_id_ekskul_form_str and submitted_id_ekskul_form_str.isdigit() else None,
                        'status_kehadiran': submitted_status_kehadiran,
                        'tanggal_kegiatan': submitted_tanggal_kegiatan_form,
                        'tahun_ajaran': submitted_tahun_ajaran_form, 
                        'catatan': submitted_catatan_absen,
                        'jam_mulai_kegiatan': submitted_jam_kegiatan if submitted_jam_kegiatan else ''
                    })
                validation_passed = True
                if action == "Tambah" and (not form_data_on_post_error.get('id_murid') or \
                                        not form_data_on_post_error.get('id_ekskul') or \
                                        not submitted_status_kehadiran or \
                                        not submitted_tanggal_kegiatan_form or \
                                        not submitted_tahun_ajaran_form): 
                    flash("Untuk Tambah: Murid, Ekskul, Status, Tanggal Kegiatan, dan Tahun Ajaran Pendaftaran Murid wajib diisi.", 'danger')
                    validation_passed = False
                elif action == "Edit" and not submitted_status_kehadiran: 
                    flash("Status Kehadiran wajib diisi saat mengedit.", 'danger')
                    validation_passed = False
                
                if validation_passed:
                    current_id_pendaftaran_to_save = id_pendaftaran_ekskul 
                    tanggal_kegiatan_to_save = tanggal_kegiatan_str 

                    if action == "Tambah":
                        current_id_pendaftaran_to_save = self.db_con.get_pendaftaran_ekskul_id(
                            form_data_on_post_error.get('id_murid'), 
                            form_data_on_post_error.get('id_ekskul'), 
                            form_data_on_post_error.get('tahun_ajaran') 
                        )
                        tanggal_kegiatan_to_save = submitted_tanggal_kegiatan_form
                    
                    if current_id_pendaftaran_to_save:
                        if self.db_con.save_absensi_ekskul(
                            current_id_pendaftaran_to_save, 
                            tanggal_kegiatan_to_save, 
                            submitted_status_kehadiran, 
                            admin_id, 
                            submitted_catatan_absen, 
                            submitted_jam_kegiatan
                        ):
                            flash(f"Data absensi berhasil di{action.lower()}kan.", "success")
                            return redirect(url_for('list_absensi_ekskul_admin')) 
                        else:
                            flash("Gagal menyimpan data absensi ke database. Mungkin sudah ada entri untuk murid ini di tanggal kegiatan yang sama.", "danger")
                    elif action == "Tambah":
                        flash(f"Murid tidak terdaftar (atau status pendaftaran tidak aktif) di ekstrakurikuler '{form_data_on_post_error.get('id_ekskul')}' pada tahun ajaran pendaftaran '{form_data_on_post_error.get('tahun_ajaran')}'.", "warning")
                form_data = form_data_on_post_error
            list_ekskul = self.db_con.get_all_ekskul() 
            all_murid = self.db_con.get_all_active_murid()
            final_form_data_for_template = {
                'id_murid': form_data.get('id_murid'),
                'id_ekskul': form_data.get('id_ekskul'),
                'status_kehadiran': form_data.get('status_kehadiran', 'Hadir'),
                'tanggal_kegiatan': form_data.get('tanggal_kegiatan', default_tanggal_untuk_form),
                'tahun_ajaran': form_data.get('tahun_ajaran', default_tahun_ajaran_val), 
                'jam_mulai_kegiatan': form_data.get('jam_mulai_kegiatan', ''),
                'catatan': form_data.get('catatan', '')
            }
            return render_template('admin/absensi_ekskul_form_admin.html', 
                                   action=action, 
                                   absensi_data=final_form_data_for_template, 
                                   list_ekskul=list_ekskul, 
                                   list_murid=all_murid,
                                   default_tahun_ajaran=default_tahun_ajaran_val, 
                                   default_tanggal_absen=default_tanggal_untuk_form, 
                                   id_pendaftaran_ekskul_edit=id_pendaftaran_ekskul, 
                                   tanggal_kegiatan_edit=tanggal_kegiatan_str, 
                                   cancel_url=url_for('list_absensi_ekskul_admin')) 

        @self.app.route('/admin/absensi_ekskul/hapus/<int:id_absensi_ekskul>', methods=['POST'])
        @self.admin_login_required
        def hapus_absensi_ekskul_admin(id_absensi_ekskul):
            if self.db_con.delete_absensi_ekskul(id_absensi_ekskul):
                flash("Entri absensi berhasil dihapus.", "success")
            else:
                flash("Gagal menghapus entri absensi.", "danger")
            return redirect(url_for('absensi_ekskul_list'))