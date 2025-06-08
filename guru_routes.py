from flask import flash, redirect, render_template, request, url_for, session, get_flashed_messages, make_response
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash
import os
from datetime import date, datetime, timedelta 
import pdfkit

class GuruRoutes:
    def __init__(self, app, db_con, guru_login_required_decorator, cek_guru_pembina, cek_file):
        self.app = app
        self.db_con = db_con 
        self.guru_login_required = guru_login_required_decorator
        self.cek_guru_pembina_ekskul = cek_guru_pembina 
        self.cek_file = cek_file 

    def register_routes(self):
        @self.app.route('/guru/dashboard') # NAMA ROUTE UNTUK DASHBOARD
        @self.guru_login_required 
        def dashboard_guru(): # DASHBOARD GURU
            guru_id = session.get('user_id') # UNTUK MENDAPATKAN ID GURU
            nama_guru = session.get('nama_lengkap') # UNTUK MENDAPATKAN NAMA GURU 
            info_terbaru_guru = self.db_con.get_pengumuman_for_guru(guru_id) # UNTUK MENDAPATKAN PENGUMUMAN TERBARU UNTUK GURU
            jadwal_ekskul_guru = self.db_con.get_ekskul_by_pembina(guru_id) # UNTUK MENDAPATKAN JADWAL EKSKUL YANG DIBINA GURU
            tahun_ajaran_aktif = self.db_con.get_tahun_ajaran_aktif()

            return render_template('guru/dashboard_guru.html', 
                                nama_guru=nama_guru,
                                jadwal_ekskul=jadwal_ekskul_guru,
                                info_terbaru=info_terbaru_guru,
                                tahun_ajaran_aktif=tahun_ajaran_aktif)

        @self.app.route('/guru/ekskul/detail/<int:ekskul_id>') # NAMA ROUTE UNTUK DETAIL SUATU EKSKUL
        @self.guru_login_required
        def detail_ekskul_guru(ekskul_id):
            guru_id = session.get('user_id')
            ekskul_info = self.db_con.get_ekskul_by_id(ekskul_id)
            if not ekskul_info:
                flash(f"Ekstrakurikuler dengan ID {ekskul_id} tidak ditemukan.", 'danger')
                return redirect(url_for('list_all_ekskul_guru'))

            materi_list = self.db_con.get_materi_by_ekskul_id(ekskul_id) # UNTUK MENAMPILKAN MATERI SESUAI EKSKUL YANG DIPILIH
            tahun_ajaran_aktif = self.db_con.get_tahun_ajaran_aktif()
            members = self.db_con.get_members_of_ekskul(ekskul_id, tahun_ajaran_aktif) # UNTUK MENDAPATKAN DAFTAR ANGGOTA EKSKUL
            is_pembina = (guru_id == ekskul_info.get('id_guru_pembina'))
            return render_template('guru/detail_ekskul_guru.html',
                                   ekskul_info=ekskul_info,
                                   materi_list=materi_list,
                                   members=members,
                                   is_pembina=is_pembina,
                                   nama_guru=session.get('nama_lengkap'),
                                   tahun_ajaran_aktif=tahun_ajaran_aktif)
        
        @self.app.route('/guru/absen/submit', methods=['POST'])# NAMA ROUTE UNTUK SUBMIT ABSEN DARI GURU
        @self.guru_login_required
        def submit_absen_guru():
            guru_id = session.get('user_id')
            try:
                murid_id = request.form.get('id_murid')
                ekskul_id = request.form.get('id_ekskul')
                status_kehadiran = request.form.get('status_kehadiran')
                tanggal_kegiatan = request.form.get('tanggal_kegiatan')
                tahun_ajaran = request.form.get('tahun_ajaran')
                if not all([murid_id, ekskul_id, status_kehadiran, tanggal_kegiatan, tahun_ajaran]) or \
                not murid_id.isdigit() or not ekskul_id.isdigit():
                    flash("Data absen tidak lengkap atau ID tidak valid. Murid, Ekskul, Status, Tanggal, dan Tahun Ajaran wajib diisi.", 'danger')
                    return redirect(url_for('kelola_absensi_guru'))

                murid_id = int(murid_id)
                ekskul_id = int(ekskul_id)
                is_pembina_for_absen, _ = self.cek_guru_pembina_ekskul(ekskul_id) 
                if not is_pembina_for_absen:
                    return redirect(url_for('kelola_absensi_guru'))

                catatan = request.form.get('catatan_absen', '')
                jam_kegiatan = request.form.get('jam_kegiatan') or None
                id_pendaftaran_ekskul = self.db_con.get_pendaftaran_ekskul_id(murid_id, ekskul_id, tahun_ajaran)
                if id_pendaftaran_ekskul:
                    if self.db_con.save_absensi_ekskul(id_pendaftaran_ekskul, tanggal_kegiatan, status_kehadiran, guru_id, catatan, jam_kegiatan):
                        flash("Data absensi berhasil disimpan/diperbarui.", "success")
                    else:
                        flash("Gagal menyimpan data absensi. Terjadi kesalahan pada database.", "danger")
                else:
                    flash(f"Murid tidak terdaftar secara aktif di ekstrakurikuler tersebut pada tahun ajaran {tahun_ajaran}.", "warning")
            except ValueError:
                flash("ID Murid atau ID Ekskul tidak valid.", "danger")
            except Exception as e:
                flash(f"Terjadi kesalahan internal saat submit absen: {e}", "danger")
                print(f"Error saat submit absen oleh guru: {e}") 
            return redirect(url_for('kelola_absensi_guru'))

        @self.app.route('/guru/absensi', methods=['GET'])
        @self.guru_login_required
        def kelola_absensi_guru():
            guru_id = session.get('user_id')
            tahun_ajaran_aktif = self.db_con.get_tahun_ajaran_aktif()
            ekskul_guru = self.db_con.get_ekskul_by_pembina(guru_id)
            murid_binaan = self.db_con.get_murid_options_for_guru_absen(guru_id, tahun_ajaran_aktif)
            return render_template('guru/kelola_absensi_guru.html',
                                ekskul_guru=ekskul_guru,
                                murid_binaan=murid_binaan,
                                default_tanggal_absen=date.today().isoformat(),
                                nama_guru=session.get('nama_lengkap'))

        @self.app.route('/guru/ekskul/pendaftaran/<int:pendaftaran_id>/setujui', methods=['POST'])
        @self.guru_login_required
        def setujui_pendaftaran_guru(pendaftaran_id):
            guru_id = session.get('user_id')
            pendaftaran_info = self.db_con.get_pendaftaran_ekskul_by_id(pendaftaran_id)
            if not pendaftaran_info:
                flash("Data pendaftaran tidak ditemukan.", "danger")
                return redirect(request.referrer or url_for('dashboard_guru'))
            
            is_pembina_of_ekskul, ekskul_info = self.cek_guru_pembina_ekskul(pendaftaran_info['id_ekskul'])
            if not is_pembina_of_ekskul:
                return redirect(request.referrer or url_for('dashboard_guru'))
            
            if ekskul_info and ekskul_info.get('kuota_maksimal') is not None:
                jumlah_peserta_aktif = self.db_con.count_active_members_ekskul(pendaftaran_info['id_ekskul'], pendaftaran_info['tahun_ajaran'])
                if jumlah_peserta_aktif >= ekskul_info['kuota_maksimal']:
                    flash(f"Kuota untuk ekskul '{ekskul_info['nama_ekskul']}' sudah penuh. Pendaftaran tidak dapat disetujui.", "warning")
                    self.db_con.update_ekskul_registration_status(pendaftaran_id, 'Ditolak', f"Ditolak otomatis karena kuota penuh saat approval oleh Guru: {session.get('nama_lengkap')}")
                    return redirect(request.referrer or url_for('dashboard_guru'))
            
            catatan = f"Disetujui oleh Guru Pembina: {session.get('nama_lengkap')}"
            if self.db_con.update_ekskul_registration_status(pendaftaran_id, 'Disetujui', catatan):
                flash('Pendaftaran berhasil disetujui.', 'success')
            else:
                flash('Gagal menyetujui pendaftaran.', 'danger')
            return redirect(request.referrer or url_for('dashboard_guru'))

        @self.app.route('/guru/ekskul/pendaftaran/<int:pendaftaran_id>/tolak', methods=['POST'])
        @self.guru_login_required
        def tolak_pendaftaran_guru(pendaftaran_id):
            pendaftaran_info = self.db_con.get_pendaftaran_ekskul_by_id(pendaftaran_id)
            if not pendaftaran_info:
                flash("Data pendaftaran tidak ditemukan.", "danger")
                return redirect(request.referrer or url_for('dashboard_guru'))

            is_pembina_of_ekskul, _ = self.cek_guru_pembina_ekskul(pendaftaran_info['id_ekskul'])
            if not is_pembina_of_ekskul:
                return redirect(request.referrer or url_for('dashboard_guru'))

            alasan = request.form.get('alasan_penolakan_guru', 'Ditolak oleh Guru Pembina.')
            catatan = f"{alasan} (Guru: {session.get('nama_lengkap')})"
            if self.db_con.update_ekskul_registration_status(pendaftaran_id, 'Ditolak', catatan):
                flash('Pendaftaran berhasil ditolak.', 'success')
            else:
                flash('Gagal menolak pendaftaran.', 'danger')
            return redirect(request.referrer or url_for('dashboard_guru'))

        @self.app.route('/guru/ekskul/saya')
        @self.guru_login_required
        def ekskul_saya():
            guru_id = session.get('user_id')
            ekskul_yang_dibina = self.db_con.get_ekskul_by_pembina(guru_id)
            if len(ekskul_yang_dibina) == 1:
                return redirect(url_for('kelola_peserta_ekskul_guru', ekskul_id=ekskul_yang_dibina[0]['id_ekskul']))
            return render_template('guru/ekskul_saya.html',
                                ekskul_list=ekskul_yang_dibina,
                                nama_guru=session.get('nama_lengkap'))

        @self.app.route('/guru/ekskul/<int:ekskul_id>/peserta')
        @self.guru_login_required
        def kelola_peserta_ekskul_guru(ekskul_id):
            is_pembina, ekskul_info = self.cek_guru_pembina_ekskul(ekskul_id)
            if not is_pembina:
                return redirect(url_for('dashboard_guru'))
            tahun_ajaran_aktif = self.db_con.get_tahun_ajaran_aktif() 
            current_members = self.db_con.get_members_of_ekskul(ekskul_id, tahun_ajaran_aktif)
            available_students_to_add = self.db_con.get_all_active_murid_exclude_ekskul(ekskul_id, tahun_ajaran_aktif)
            
            return render_template('guru/kelola_peserta_ekskul.html',
                                   ekskul_info=ekskul_info,
                                   members=current_members,
                                   available_students=available_students_to_add,
                                   tahun_ajaran_aktif=tahun_ajaran_aktif,
                                   nama_guru=session.get('nama_lengkap'))

        @self.app.route('/guru/ekskul/<int:ekskul_id>/add_peserta', methods=['POST'])
        @self.guru_login_required
        def add_peserta_ekskul_guru(ekskul_id):
            is_pembina, ekskul_info = self.cek_guru_pembina_ekskul(ekskul_id)
            if not is_pembina:
                 return redirect(url_for('dashboard_guru'))

            murid_id = request.form.get('id_murid')
            tahun_ajaran = request.form.get('tahun_ajaran') 
            if not murid_id or not tahun_ajaran or not murid_id.isdigit():
                flash("Murid dan tahun ajaran harus dipilih/diisi dengan benar.", "danger")
            else:
                murid_id = int(murid_id)
                catatan_pendaftar = f"Didaftarkan oleh Guru Pembina: {session.get('nama_lengkap')}"
                hasil_pendaftaran = self.db_con.register_student_for_ekskul(
                    murid_id, ekskul_id, tahun_ajaran, 
                    status_pendaftaran='Disetujui', 
                    catatan_pendaftar=catatan_pendaftar
                )
                if isinstance(hasil_pendaftaran, int): 
                    murid_info = self.db_con.get_user_by_id(murid_id)
                    flash(f"Murid '{murid_info['nama_lengkap'] if murid_info else 'ID '+str(murid_id)}' berhasil ditambahkan ke ekskul '{ekskul_info['nama_ekskul']}'.", "success")
                elif hasil_pendaftaran == "KUOTA_PENUH":
                    flash(f"Gagal menambahkan. Kuota untuk ekskul '{ekskul_info['nama_ekskul']}' sudah penuh.", "warning")
                elif hasil_pendaftaran == "SUDAH_TERDAFTAR":
                     murid_info = self.db_con.get_user_by_id(murid_id)
                     flash(f"Gagal menambahkan. Murid '{murid_info['nama_lengkap'] if murid_info else 'ID '+str(murid_id)}' sudah memiliki record pendaftaran di ekskul '{ekskul_info['nama_ekskul']}' untuk tahun ajaran ini.", "warning")
                elif hasil_pendaftaran == "EKSKUL_NOT_FOUND":
                    flash(f"Ekskul '{ekskul_info['nama_ekskul']}' tidak ditemukan.", "danger")
                else: 
                    flash("Gagal menambahkan murid. Terjadi kesalahan pada sistem.", "danger")
            return redirect(url_for('kelola_peserta_ekskul_guru', ekskul_id=ekskul_id))

        @self.app.route('/guru/ekskul/remove_peserta/<int:pendaftaran_id>', methods=['POST'])
        @self.guru_login_required
        def remove_peserta_ekskul_guru(pendaftaran_id):
            ekskul_id_redirect = request.form.get('ekskul_id_redirect') 
            pendaftaran_info = self.db_con.get_pendaftaran_ekskul_by_id(pendaftaran_id)
            if not pendaftaran_info:
                flash("Data pendaftaran tidak ditemukan.", "danger")
                return redirect(url_for('dashboard_guru'))
            is_pembina, _ = self.cek_guru_pembina_ekskul(pendaftaran_info['id_ekskul'])
            if not is_pembina:
                if ekskul_id_redirect and ekskul_id_redirect.isdigit():
                    return redirect(url_for('kelola_peserta_ekskul_guru', ekskul_id=int(ekskul_id_redirect)))
                return redirect(url_for('dashboard_guru'))
            catatan_admin = f"Dikeluarkan oleh Guru Pembina: {session.get('nama_lengkap')}"
            if self.db_con.update_ekskul_registration_status(pendaftaran_id, new_status='Berhenti', catatan_admin=catatan_admin):
                flash(f"Status pendaftaran (ID: {pendaftaran_id}) diubah menjadi 'Berhenti'.", "success")
            else:
                flash("Gagal mengubah status pendaftaran.", "danger")
            if ekskul_id_redirect and ekskul_id_redirect.isdigit():
                return redirect(url_for('kelola_peserta_ekskul_guru', ekskul_id=int(ekskul_id_redirect)))
            return redirect(url_for('dashboard_guru')) 
        
        @self.app.route('/guru/ekskul/<int:ekskul_id>/materi/tambah', methods=['GET', 'POST'])
        @self.guru_login_required
        def tambah_materi_ekskul_guru(ekskul_id):
            is_pembina, ekskul_info = self.cek_guru_pembina_ekskul(ekskul_id)
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
                            if file and self.cek_file(file.filename, self.app.config['ALLOWED_EXTENSIONS']):
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
                        materi_id = self.db_con.add_materi_ekskul(data_materi)
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
            is_pembina, ekskul_info = self.cek_guru_pembina_ekskul(ekskul_id)
            if not is_pembina:
                 return redirect(url_for('detail_ekskul_guru', ekskul_id=ekskul_id) if ekskul_info else url_for('dashboard_guru'))

            materi_data_lama = self.db_con.get_materi_ekskul_by_id(id_materi_ekskul)
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
                        if self.cek_file(file.filename, self.app.config['ALLOWED_EXTENSIONS']):
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
                    if self.db_con.update_materi_ekskul(id_materi_ekskul, data_to_update):
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
            is_pembina, ekskul_info_check = self.cek_guru_pembina_ekskul(ekskul_id) 
            if not is_pembina:
                return redirect(url_for('detail_ekskul_guru', ekskul_id=ekskul_id) if ekskul_info_check else url_for('dashboard_guru'))

            materi_info = self.db_con.get_materi_ekskul_by_id(id_materi_ekskul)
            if not materi_info or materi_info['id_ekskul'] != ekskul_id:
                flash("Materi tidak ditemukan atau tidak sesuai dengan ekskul ini.", "danger")
                return redirect(url_for('detail_ekskul_guru', ekskul_id=ekskul_id))

            materi_info_deleted = self.db_con.delete_materi_ekskul(id_materi_ekskul)
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

        @self.app.route('/guru/profil/edit', methods=['GET', 'POST'])
        @self.guru_login_required
        def edit_profil_guru(): 
                    guru_id = session.get('user_id')
                    user_sekarang = self.db_con.get_user_by_id(guru_id)
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
                            return render_template('guru/edit_profil_guru.html', user_data=form_data_for_template, nama_guru=user_sekarang['nama_lengkap'])

                        data_to_update = {
                            'nama_lengkap': nama_lengkap_baru,
                            'email': email_baru
                        }
                        password_changed_message_part = ""
                        if new_password:
                            if not current_password:
                                flash('Masukkan password saat ini untuk mengubah password.', 'warning')
                                return render_template('guru/edit_profil_guru.html', 
                                                    user_data=form_data_for_template, 
                                                    nama_guru=user_sekarang['nama_lengkap'])
                            
                            if not check_password_hash(user_sekarang['password_hash'], current_password):
                                flash('Password saat ini salah.', 'danger')
                                return render_template('guru/edit_profil_guru.html', 
                                                    user_data=form_data_for_template, 
                                                    nama_guru=user_sekarang['nama_lengkap'])

                            if new_password != confirm_new_password:
                                flash('Password baru dan konfirmasi password tidak cocok.', 'danger')
                                return render_template('guru/edit_profil_guru.html', 
                                                    user_data=form_data_for_template, 
                                                    nama_guru=user_sekarang['nama_lengkap'])

                            data_to_update['password'] = new_password 
                            password_changed_message_part = " Password Anda juga telah diubah."
                        if self.db_con.update_user(guru_id, data_to_update):
                            session['nama_lengkap'] = nama_lengkap_baru

                            flash(f"Profil berhasil diperbarui.{password_changed_message_part}", 'success')
                            return redirect(url_for('dashboard_guru')) 
                        else:
                            flash('Gagal memperbarui profil. Terjadi kesalahan pada server.', 'danger')
                            return render_template('guru/edit_profil_guru.html', 
                                                user_data=form_data_for_template, 
                                                nama_guru=user_sekarang['nama_lengkap'])
                    return render_template('guru/edit_profil_guru.html', 
                                        user_data=user_sekarang, 
                                        nama_guru=user_sekarang['nama_lengkap'])
        
        @self.app.route('/guru/ekskul/<int:ekskul_id>/peserta/cetak_pdf')
        @self.guru_login_required
        def cetak_daftar_peserta_pdf(ekskul_id):
            is_pembina, ekskul_info = self.cek_guru_pembina_ekskul(ekskul_id)
            if not is_pembina:
                flash("Anda tidak memiliki akses untuk mencetak data dari ekskul ini.", "danger")
                return redirect(url_for('dashboard_guru'))
            tahun_ajaran_aktif = self.db_con.get_tahun_ajaran_aktif()
            members = self.db_con.get_members_of_ekskul(ekskul_id, tahun_ajaran_aktif)
            tanggal_cetak = datetime.now().strftime("%d %B %Y, Pukul %H:%M:%S")
            rendered_html = render_template('guru/cetak_peserta.html', 
                                            ekskul_info=ekskul_info,
                                            members=members,
                                            tahun_ajaran_aktif=tahun_ajaran_aktif,
                                            tanggal_cetak=tanggal_cetak,
                                            nama_pembina=session.get('nama_lengkap'))
            path_wkhtmltopdf = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'
            if not os.path.exists(path_wkhtmltopdf):
                error_message = f"File wkhtmltopdf tidak ditemukan di path: {path_wkhtmltopdf}. Silakan periksa instalasi Anda."
                flash(error_message, "danger")
                print(error_message)
                return redirect(url_for('kelola_peserta_ekskul_guru', ekskul_id=ekskul_id))
            config = pdfkit.configuration(wkhtmltopdf=path_wkhtmltopdf)

            try:
                pdf = pdfkit.from_string(rendered_html, False, configuration=config, options={"enable-local-file-access": ""})
            except OSError as e:
                error_message = f"Gagal membuat PDF. Error dari wkhtmltopdf: {e}"
                flash(error_message, "danger")
                print(error_message)
                return redirect(url_for('kelola_peserta_ekskul_guru', ekskul_id=ekskul_id))
            safe_nama_ekskul = "".join([c for c in ekskul_info['nama_ekskul'] if c.isalnum() or c.isspace()]).rstrip()
            filename = f"Daftar Peserta - {safe_nama_ekskul}.pdf"
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'inline; filename="{filename}"'
            return response