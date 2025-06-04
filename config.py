import pymysql
from werkzeug.security import generate_password_hash # Diperlukan jika hashing dilakukan di sini

class Config:
    def __init__(self):
        self.db_host = 'localhost'
        self.db_user = 'root'
        self.db_password = ''
        self.db_name = 'db_portal'
        # self.mysql = pymysql.connect(...) # Anda sudah punya ini

    # Helper method untuk mendapatkan koneksi baru
    # Penting: Mengelola koneksi dengan baik (buka saat dibutuhkan, tutup setelah selesai)
    # adalah kunci. Di aplikasi web, seringkali koneksi dibuat per request.
    def _get_connection(self):
        return pymysql.connect(
            host=self.db_host,
            user=self.db_user,
            password=self.db_password,
            database=self.db_name,
            cursorclass=pymysql.cursors.DictCursor  # Hasil query sebagai dictionary
        )

    def check_db_connection(self):
        try:
            conn = self._get_connection()
            conn.ping(reconnect=True) # Coba ping server
            conn.close()
            return True
        except pymysql.MySQLError:
            return False

    # --- User Management ---
    def get_user_by_username(self, username):
        conn = self._get_connection()
        user = None
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM Pengguna WHERE username = %s"
                cursor.execute(sql, (username,))
                user = cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"Error fetching user by username: {e}")
        finally:
            conn.close()
        return user

    def get_user_by_id(self, user_id):
        conn = self._get_connection()
        user = None
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM Pengguna WHERE id_pengguna = %s"
                cursor.execute(sql, (user_id,))
                user = cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"Error fetching user by id: {e}")
        finally:
            conn.close()
        return user

    def get_users_by_role(self, peran):
        conn = self._get_connection()
        users = []
        try:
            with conn.cursor() as cursor:
                # Query ini mengambil semua kolom dari tabel Pengguna
                sql = "SELECT * FROM Pengguna WHERE peran = %s ORDER BY nama_lengkap"
                cursor.execute(sql, (peran,))
                users = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error in get_users_by_role for role '{peran}': {e}")
        finally:
            if conn.open: conn.close() # Pastikan koneksi ditutup
        return users
    
    def get_all_users(self):
        conn = self._get_connection()
        users = []
        try:
            with conn.cursor() as cursor:
                # Mengurutkan berdasarkan peran lalu nama untuk tampilan yang lebih baik
                sql = "SELECT * FROM Pengguna ORDER BY FIELD(peran, 'admin', 'guru', 'murid'), nama_lengkap"
                cursor.execute(sql)
                users = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching all users: {e}")
        finally:
            conn.close()
        return users

    def add_user(self, user_data):
        # user_data adalah dictionary {'username': '...', 'password': '...', ...}
        conn = self._get_connection()
        new_user_id = None
        try:
            with conn.cursor() as cursor:
                # Hash password sebelum disimpan
                hashed_password = generate_password_hash(user_data['password'])
                sql = """INSERT INTO Pengguna 
                         (username, password_hash, nama_lengkap, email, peran, nomor_induk, status_aktif) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (
                    user_data['username'],
                    hashed_password,
                    user_data['nama_lengkap'],
                    user_data['email'],
                    user_data['peran'],
                    user_data.get('nomor_induk'), # .get() untuk field opsional
                    user_data.get('status_aktif', True)
                ))
                conn.commit()
                new_user_id = cursor.lastrowid # Mendapatkan ID dari user yang baru saja di-insert
        except pymysql.MySQLError as e:
            print(f"Error adding user: {e}")
            conn.rollback() # Penting untuk rollback jika terjadi error
        finally:
            conn.close()
        return new_user_id
    
    def update_user(self, user_id, user_data):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                # Siapkan query dasar
                sql_parts = []
                params = []
                
                if 'username' in user_data and user_data['username']:
                    sql_parts.append("username = %s")
                    params.append(user_data['username'])
                if 'nama_lengkap' in user_data and user_data['nama_lengkap']:
                    sql_parts.append("nama_lengkap = %s")
                    params.append(user_data['nama_lengkap'])
                if 'email' in user_data and user_data['email']:
                    sql_parts.append("email = %s")
                    params.append(user_data['email'])
                if 'peran' in user_data and user_data['peran']:
                    sql_parts.append("peran = %s")
                    params.append(user_data['peran'])
                if 'nomor_induk' in user_data: # Bisa jadi string kosong atau None
                    sql_parts.append("nomor_induk = %s")
                    params.append(user_data['nomor_induk'])
                if 'status_aktif' in user_data: # Ini boolean
                    sql_parts.append("status_aktif = %s")
                    params.append(bool(user_data['status_aktif']))

                # Update password jika diberikan dan tidak kosong
                if 'password' in user_data and user_data['password']:
                    hashed_password = generate_password_hash(user_data['password'])
                    sql_parts.append("password_hash = %s")
                    params.append(hashed_password)
                
                if not sql_parts: # Tidak ada yang diupdate
                    return True 

                sql = f"UPDATE Pengguna SET {', '.join(sql_parts)} WHERE id_pengguna = %s"
                params.append(user_id)
                
                cursor.execute(sql, tuple(params))
                conn.commit()
                return True # Berhasil
        except pymysql.MySQLError as e:
            print(f"Error updating user {user_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_user(self, user_id):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                # Periksa dulu apakah user ini adalah satu-satunya admin, jika ya, mungkin jangan dihapus
                # (Logika ini bisa ditambahkan jika perlu)
                sql = "DELETE FROM Pengguna WHERE id_pengguna = %s"
                cursor.execute(sql, (user_id,))
                conn.commit()
                return cursor.rowcount > 0 # True jika ada baris yang terhapus
        except pymysql.MySQLError as e:
            print(f"Error deleting user {user_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def _create_default_admin_if_not_exists(self):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "SELECT 1 FROM Pengguna WHERE peran = 'admin' LIMIT 1"
                cursor.execute(sql)
                admin_exists = cursor.fetchone()
                
                if not admin_exists:
                    print("Tidak ada admin ditemukan. Membuat admin default...")
                    default_admin_data = {
                        'username': 'admin', 'password': 'adminpassword', 
                        'nama_lengkap': 'Administrator Utama', 'email': 'admin@example.com',
                        'peran': 'admin', 'nomor_induk': 'ADM001', 'status_aktif': True
                    }
                    self.add_user(default_admin_data)
                    print("Admin default (admin/adminpassword) telah dibuat.")
                else:
                    print("Akun admin sudah ada.")
        except pymysql.MySQLError as e:
            print(f"Error saat membuat admin default: {e}")
        finally:
            if conn.open: conn.close()

    # --- Extracurricular Management ---
    def get_all_ekskul(self):
        conn = self._get_connection()
        ekskul_list = []
        try:
            with conn.cursor() as cursor:
                # Query diubah untuk ORDER BY kategori, lalu nama_ekskul
                sql = """SELECT e.*, p.nama_lengkap AS nama_guru_pembina 
                         FROM Ekstrakurikuler e
                         LEFT JOIN Pengguna p ON e.id_guru_pembina = p.id_pengguna
                         ORDER BY e.kategori, e.nama_ekskul""" # PENTING: ORDER BY kategori
                cursor.execute(sql)
                ekskul_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error in get_all_ekskul: {e}")
        finally:
            if conn.open: conn.close()
        return ekskul_list

    def add_ekskul(self, ekskul_data):
        conn = self._get_connection()
        new_ekskul_id = None
        try:
            with conn.cursor() as cursor:
                sql = """INSERT INTO Ekstrakurikuler 
                            (nama_ekskul, deskripsi, kategori, id_guru_pembina, jadwal_deskripsi, lokasi, kuota_maksimal, status_aktif, url_logo_ekskul)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""" # Tambahkan 'kategori' di sini
                cursor.execute(sql, (
                    ekskul_data['nama_ekskul'],
                    ekskul_data.get('deskripsi'),
                    ekskul_data.get('kategori'), # Ambil nilai kategori
                    ekskul_data.get('id_guru_pembina'),
                    ekskul_data.get('jadwal_deskripsi'),
                    ekskul_data.get('lokasi'),
                    ekskul_data.get('kuota_maksimal'),
                    ekskul_data.get('status_aktif', True),
                    ekskul_data.get('url_logo_ekskul')
                ))
                conn.commit()
                new_ekskul_id = cursor.lastrowid
        except pymysql.MySQLError as e:
            print(f"Error adding ekskul: {e}")
            conn.rollback()
        finally:
            conn.close()
        return new_ekskul_id

    def get_ekskul_by_id(self, ekskul_id):
        conn = self._get_connection()
        ekskul_info = None
        try:
            with conn.cursor() as cursor:
                # Mengambil detail ekskul termasuk nama guru pembina
                sql = """SELECT e.*, p.nama_lengkap AS nama_guru_pembina
                         FROM Ekstrakurikuler e
                         LEFT JOIN Pengguna p ON e.id_guru_pembina = p.id_pengguna
                         WHERE e.id_ekskul = %s"""
                cursor.execute(sql, (ekskul_id,))
                ekskul_info = cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"Error fetching ekstrakurikuler by id {ekskul_id}: {e}")
        finally:
            conn.close()
        return ekskul_info

    def update_ekskul(self, ekskul_id, ekskul_data):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql_parts = []
                params = []

                # Tambahkan pengecekan untuk setiap field yang mungkin diupdate
                if 'nama_ekskul' in ekskul_data:
                    sql_parts.append("nama_ekskul = %s")
                    params.append(ekskul_data['nama_ekskul'])
                if 'deskripsi' in ekskul_data: # Boleh None atau string kosong
                    sql_parts.append("deskripsi = %s")
                    params.append(ekskul_data.get('deskripsi'))
                if 'kategori' in ekskul_data:
                    sql_parts.append("kategori = %s")
                    params.append(ekskul_data.get('kategori'))
                if 'id_guru_pembina' in ekskul_data: # Boleh None
                    sql_parts.append("id_guru_pembina = %s")
                    params.append(ekskul_data.get('id_guru_pembina'))
                if 'jadwal_deskripsi' in ekskul_data: # Tambahkan ini
                    sql_parts.append("jadwal_deskripsi = %s")
                    params.append(ekskul_data.get('jadwal_deskripsi'))
                if 'lokasi' in ekskul_data: # Tambahkan ini
                    sql_parts.append("lokasi = %s")
                    params.append(ekskul_data.get('lokasi'))
                if 'kuota_maksimal' in ekskul_data: # Boleh None
                    sql_parts.append("kuota_maksimal = %s")
                    params.append(ekskul_data.get('kuota_maksimal'))
                if 'status_aktif' in ekskul_data: # Ini boolean
                    sql_parts.append("status_aktif = %s")
                    params.append(bool(ekskul_data['status_aktif']))
                
                # --- INI BAGIAN PENTING UNTUK LOGO ---
                if 'url_logo_ekskul' in ekskul_data:
                    sql_parts.append("url_logo_ekskul = %s")
                    # Nilai bisa berupa nama file (string) atau None (jika logo dihapus)
                    params.append(ekskul_data.get('url_logo_ekskul')) 
                # --- AKHIR BAGIAN PENTING UNTUK LOGO ---

                if not sql_parts:
                    # Tidak ada field yang dikirim untuk diupdate, anggap sukses (tidak ada perubahan)
                    return True 

                sql = f"UPDATE Ekstrakurikuler SET {', '.join(sql_parts)}, updated_at = NOW() WHERE id_ekskul = %s"
                params.append(ekskul_id)
                
                # Debugging tambahan di config.py jika perlu:
                # print(f"DEBUG SQL Update Ekskul: {sql}")
                # print(f"DEBUG Params Update Ekskul: {tuple(params)}")

                cursor.execute(sql, tuple(params))
                conn.commit()
                return cursor.rowcount > 0 # Return True jika ada baris yang terupdate
        except pymysql.MySQLError as e:
            print(f"Error updating ekstrakurikuler {ekskul_id}: {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close() # Pastikan koneksi ditutup

    def delete_ekskul(self, ekskul_id):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                # Menghapus ekstrakurikuler.
                # Karena ada ON DELETE CASCADE pada PendaftaranEkskul(id_ekskul)
                # dan MateriEkskul(id_ekskul) di DDL kita,
                # maka pendaftaran dan materi terkait akan otomatis terhapus.
                sql = "DELETE FROM Ekstrakurikuler WHERE id_ekskul = %s"
                cursor.execute(sql, (ekskul_id,))
                conn.commit()
                # cursor.rowcount akan mengembalikan jumlah baris yang terpengaruh (terhapus)
                return cursor.rowcount > 0 # True jika ada baris yang terhapus
        except pymysql.MySQLError as e:
            print(f"Error deleting ekstrakurikuler {ekskul_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_ekskul_by_pembina(self, id_guru_pembina):
        """Mengambil semua ekstrakurikuler yang dibina oleh guru tertentu."""
        conn = self._get_connection()
        ekskul_list = []
        try:
            with conn.cursor() as cursor:
                sql = """SELECT id_ekskul, nama_ekskul, jadwal_deskripsi, lokasi 
                         FROM Ekstrakurikuler 
                         WHERE id_guru_pembina = %s AND status_aktif = TRUE
                         ORDER BY nama_ekskul"""
                cursor.execute(sql, (id_guru_pembina,))
                ekskul_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching ekskul by pembina {id_guru_pembina}: {e}")
        finally:
            conn.close()
        return ekskul_list

    # --- Extracurricular Registration Management ---
    def get_all_active_murid_exclude_ekskul(self, ekskul_id_to_check, tahun_ajaran_aktif):
        # Mengambil murid aktif yang belum terdaftar di ekskul_id_to_check pada tahun_ajaran_aktif
        conn = self._get_connection()
        murid_list = []
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT p.id_pengguna, p.nama_lengkap, p.nomor_induk
                    FROM Pengguna p
                    WHERE p.peran = 'murid' AND p.status_aktif = TRUE
                    AND p.id_pengguna NOT IN (
                        SELECT pe.id_murid
                        FROM PendaftaranEkskul pe
                        WHERE pe.id_ekskul = %s AND pe.tahun_ajaran = %s 
                              AND pe.status_pendaftaran IN ('Terdaftar', 'Disetujui', 'Menunggu Persetujuan')
                    )
                    ORDER BY p.nama_lengkap;
                """
                cursor.execute(sql, (ekskul_id_to_check, tahun_ajaran_aktif))
                murid_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching active murid for ekskul registration: {e}")
        finally:
            conn.close()
        return murid_list

    def register_student_for_ekskul(self, murid_id, ekskul_id, tahun_ajaran, 
                                    status_pendaftaran='Disetujui', 
                                    catatan_pendaftar="Didaftarkan oleh sistem"): # Ganti catatan_admin menjadi lebih umum
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                # Langkah 1: Dapatkan informasi kuota ekskul
                sql_get_ekskul_info = "SELECT kuota_maksimal, nama_ekskul FROM Ekstrakurikuler WHERE id_ekskul = %s"
                cursor.execute(sql_get_ekskul_info, (ekskul_id,))
                ekskul_info = cursor.fetchone()

                if not ekskul_info:
                    print(f"Ekskul ID {ekskul_id} tidak ditemukan.")
                    return "EKSKUL_NOT_FOUND" 

                kuota = ekskul_info.get('kuota_maksimal')
                nama_ekskul = ekskul_info.get('nama_ekskul')

                # Langkah 2: Cek kuota jika ada (tidak NULL dan > 0)
                if kuota is not None and kuota > 0:
                    sql_count_participants = """
                        SELECT COUNT(*) as jumlah_peserta 
                        FROM PendaftaranEkskul 
                        WHERE id_ekskul = %s AND tahun_ajaran = %s 
                        AND status_pendaftaran IN ('Disetujui', 'Terdaftar') 
                    """ # Hanya hitung yang statusnya aktif/disetujui
                    cursor.execute(sql_count_participants, (ekskul_id, tahun_ajaran))
                    jumlah_peserta_aktif = cursor.fetchone()['jumlah_peserta']

                    if jumlah_peserta_aktif >= kuota:
                        print(f"Kuota untuk Ekskul '{nama_ekskul}' (ID: {ekskul_id}) sudah penuh ({jumlah_peserta_aktif}/{kuota}).")
                        return "KUOTA_PENUH" # Kembalikan status spesifik

                # Langkah 3: Cek apakah murid sudah terdaftar (mencegah duplikasi)
                sql_check_duplikasi = """SELECT id_pendaftaran_ekskul, status_pendaftaran 
                                         FROM PendaftaranEkskul 
                                         WHERE id_murid = %s AND id_ekskul = %s AND tahun_ajaran = %s"""
                cursor.execute(sql_check_duplikasi, (murid_id, ekskul_id, tahun_ajaran))
                pendaftaran_lama = cursor.fetchone()
                
                if pendaftaran_lama:
                    # Jika sudah ada dan statusnya 'Berhenti' atau 'Ditolak', mungkin bisa diupdate/didaftarkan ulang
                    # Untuk saat ini, kita anggap tidak bisa jika sudah ada record apapun
                    print(f"Murid ID {murid_id} sudah memiliki record pendaftaran di Ekskul '{nama_ekskul}' untuk tahun {tahun_ajaran} dengan status {pendaftaran_lama['status_pendaftaran']}.")
                    return "SUDAH_TERDAFTAR"

                # Langkah 4: Jika semua pengecekan lolos, lakukan INSERT
                sql_insert = """INSERT INTO PendaftaranEkskul 
                                (id_murid, id_ekskul, tahun_ajaran, status_pendaftaran, catatan_admin_pembina)
                                VALUES (%s, %s, %s, %s, %s)"""
                cursor.execute(sql_insert, (murid_id, ekskul_id, tahun_ajaran, status_pendaftaran, catatan_pendaftar))
                conn.commit()
                return cursor.lastrowid # Mengembalikan ID pendaftaran baru jika berhasil
        except pymysql.MySQLError as e:
            print(f"Error in register_student_for_ekskul (murid:{murid_id}, ekskul:{ekskul_id}): {e}")
            conn.rollback()
            return False # Indikasi error umum
        finally:
            if conn.open: conn.close()

    def get_members_of_ekskul(self, ekskul_id, tahun_ajaran_aktif):
      conn = self._get_connection()
      members = []
      try:
          with conn.cursor() as cursor:
              # Mengambil murid yang status pendaftarannya 'Disetujui' atau 'Terdaftar'
              sql = """SELECT p.id_pengguna, p.nama_lengkap, p.nomor_induk, p.email, pe.status_pendaftaran, pe.id_pendaftaran_ekskul
                      FROM Pengguna p
                      JOIN PendaftaranEkskul pe ON p.id_pengguna = pe.id_murid
                      WHERE pe.id_ekskul = %s 
                        AND pe.tahun_ajaran = %s 
                        AND pe.status_pendaftaran IN ('Disetujui', 'Terdaftar') 
                      ORDER BY p.nama_lengkap"""
              cursor.execute(sql, (ekskul_id, tahun_ajaran_aktif))
              members = cursor.fetchall()
      except pymysql.MySQLError as e:
          print(f"Error fetching members of ekskul {ekskul_id}: {e}")
      finally:
          conn.close()
      return members

    def get_pendaftaran_ekskul_id(self, murid_id, ekskul_id, tahun_ajaran):
        """Mencari id_pendaftaran_ekskul berdasarkan murid, ekskul, dan tahun ajaran."""
        conn = self._get_connection()
        pendaftaran_id = None
        try:
            with conn.cursor() as cursor:
                sql = """SELECT id_pendaftaran_ekskul 
                         FROM PendaftaranEkskul
                         WHERE id_murid = %s AND id_ekskul = %s AND tahun_ajaran = %s
                         AND status_pendaftaran IN ('Disetujui', 'Terdaftar') 
                         LIMIT 1""" # Asumsi hanya ada satu pendaftaran aktif per ekskul per tahun
                cursor.execute(sql, (murid_id, ekskul_id, tahun_ajaran))
                result = cursor.fetchone()
                if result:
                    pendaftaran_id = result['id_pendaftaran_ekskul']
        except pymysql.MySQLError as e:
            print(f"Error fetching pendaftaran_ekskul_id: {e}")
        finally:
            conn.close()
        return pendaftaran_id

    def update_ekskul_registration_status(self, pendaftaran_id, new_status='Berhenti', catatan_admin="Dikeluarkan oleh Admin"):
        # Menggunakan pendaftaran_id untuk target yang lebih spesifik
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """UPDATE PendaftaranEkskul 
                         SET status_pendaftaran = %s, catatan_admin_pembina = %s
                         WHERE id_pendaftaran_ekskul = %s"""
                # Pastikan new_status adalah ENUM valid
                # ('Terdaftar', 'Menunggu Persetujuan', 'Disetujui', 'Ditolak', 'Berhenti')
                cursor.execute(sql, (new_status, catatan_admin, pendaftaran_id))
                conn.commit()
                return cursor.rowcount > 0
        except pymysql.MySQLError as e:
            print(f"Error updating ekskul registration status for ID {pendaftaran_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def add_materi_ekskul(self, data_materi):
        # data_materi: {'id_ekskul': ..., 'judul_materi': ..., 'deskripsi_materi': ..., 
        #               'tipe_konten': ..., 'path_konten_atau_link': ..., 
        #               'isi_konten_teks': ..., 'id_pengunggah': ...}
        conn = self._get_connection()
        new_id = None
        try:
            with conn.cursor() as cursor:
                sql = """INSERT INTO MateriEkskul 
                         (id_ekskul, judul_materi, deskripsi_materi, tipe_konten, 
                          path_konten_atau_link, isi_konten_teks, id_pengunggah)
                         VALUES (%s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (
                    data_materi['id_ekskul'],
                    data_materi['judul_materi'],
                    data_materi.get('deskripsi_materi'),
                    data_materi['tipe_konten'],
                    data_materi.get('path_konten_atau_link'), # Akan berisi path file, URL, atau kode embed
                    data_materi.get('isi_konten_teks'),      # Untuk tipe 'teks'
                    data_materi['id_pengunggah']
                ))
                conn.commit()
                new_id = cursor.lastrowid
        except pymysql.MySQLError as e:
            print(f"Error in add_materi_ekskul: {e}")
            conn.rollback()
        finally:
            if conn.open: conn.close()
        return new_id

    def get_all_materi_ekskul(self):
        # Mengambil semua materi, join dengan nama ekskul dan nama pengunggah
        conn = self._get_connection()
        materi_list = []
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        me.id_materi_ekskul, me.judul_materi, me.tipe_konten, 
                        me.tanggal_unggah, 
                        e.nama_ekskul,
                        p.nama_lengkap AS nama_pengunggah
                    FROM MateriEkskul me
                    JOIN Ekstrakurikuler e ON me.id_ekskul = e.id_ekskul
                    JOIN Pengguna p ON me.id_pengunggah = p.id_pengguna
                    ORDER BY me.tanggal_unggah DESC
                """
                cursor.execute(sql)
                materi_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error in get_all_materi_ekskul: {e}")
        finally:
            if conn.open: conn.close()
        return materi_list

    def get_materi_ekskul_by_id(self, id_materi_ekskul):
        conn = self._get_connection()
        materi = None
        try:
            with conn.cursor() as cursor:
                sql = """SELECT me.*, e.nama_ekskul 
                         FROM MateriEkskul me
                         JOIN Ekstrakurikuler e ON me.id_ekskul = e.id_ekskul
                         WHERE me.id_materi_ekskul = %s"""
                cursor.execute(sql, (id_materi_ekskul,))
                materi = cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"Error in get_materi_ekskul_by_id: {e}")
        finally:
            if conn.open: conn.close()
        return materi

    def update_materi_ekskul(self, id_materi_ekskul, data_materi):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql_parts = []
                params = []

                # Selalu update field dasar jika ada di data_materi
                if 'id_ekskul' in data_materi: 
                    sql_parts.append("id_ekskul = %s")
                    params.append(data_materi['id_ekskul'])
                if 'judul_materi' in data_materi: 
                    sql_parts.append("judul_materi = %s")
                    params.append(data_materi['judul_materi'])
                if 'deskripsi_materi' in data_materi: # deskripsi bisa string kosong
                    sql_parts.append("deskripsi_materi = %s")
                    params.append(data_materi['deskripsi_materi'])
                
                # Update tipe_konten jika berubah
                if 'tipe_konten' in data_materi:
                    current_tipe_konten = data_materi['tipe_konten']
                    sql_parts.append("tipe_konten = %s")
                    params.append(current_tipe_konten)

                    if current_tipe_konten in ['file', 'link', 'video_embed']:
                        # Jika path_konten_atau_link ada di data_materi (artinya ada file baru atau link baru)
                        # atau jika memang field ini dikirim kosong untuk mengosongkan
                        if 'path_konten_atau_link' in data_materi:
                            sql_parts.append("path_konten_atau_link = %s")
                            params.append(data_materi.get('path_konten_atau_link'))
                        sql_parts.append("isi_konten_teks = %s") # Selalu set pasangannya jadi NULL
                        params.append(None)
                    elif current_tipe_konten == 'teks':
                        if 'isi_konten_teks' in data_materi:
                            sql_parts.append("isi_konten_teks = %s")
                            params.append(data_materi.get('isi_konten_teks'))
                        sql_parts.append("path_konten_atau_link = %s") # Selalu set pasangannya jadi NULL
                        params.append(None)
                else:
                    # Tipe konten tidak diubah, hanya update path atau teks jika ada
                    if 'path_konten_atau_link' in data_materi:
                        sql_parts.append("path_konten_atau_link = %s")
                        params.append(data_materi.get('path_konten_atau_link'))
                    if 'isi_konten_teks' in data_materi:
                        sql_parts.append("isi_konten_teks = %s")
                        params.append(data_materi.get('isi_konten_teks'))


                if not sql_parts:
                    print("Tidak ada data valid untuk diupdate pada materi ekskul.")
                    return True # Anggap sukses jika tidak ada yang diubah

                sql_parts.append("updated_at = NOW()")
                
                sql_query = f"UPDATE MateriEkskul SET {', '.join(sql_parts)} WHERE id_materi_ekskul = %s"
                params.append(id_materi_ekskul)

                if sql_query.count('%s') != len(params):
                    print("ERROR KRITIS: Jumlah placeholder %s tidak cocok dengan jumlah parameter!")
                    # Jangan eksekusi query jika tidak cocok
                    conn.rollback() # Pastikan tidak ada perubahan parsial
                    return False

                cursor.execute(sql_query, tuple(params))
                conn.commit()
                return True
        except pymysql.MySQLError as e:
            print(f"Error in update_materi_ekskul for ID {id_materi_ekskul}: {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close()

    def delete_materi_ekskul(self, id_materi_ekskul):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                # Ambil detail materi dulu jika perlu menghapus file fisik
                cursor.execute("SELECT tipe_konten, path_konten_atau_link FROM MateriEkskul WHERE id_materi_ekskul = %s", (id_materi_ekskul,))
                materi_info = cursor.fetchone()

                sql_delete = "DELETE FROM MateriEkskul WHERE id_materi_ekskul = %s"
                cursor.execute(sql_delete, (id_materi_ekskul,))
                conn.commit()
                # Kembalikan info file jika ada, agar bisa dihapus di app.py
                return materi_info 
        except pymysql.MySQLError as e:
            print(f"Error in delete_materi_ekskul: {e}")
            conn.rollback()
            return None
        finally:
            if conn.open: conn.close()
    
    def get_materi_by_ekskul_id(self, id_ekskul):
        conn = self._get_connection()
        materi_list = []
        try:
            with conn.cursor() as cursor:
                # Join dengan tabel Pengguna untuk mendapatkan nama pengunggah
                sql = """
                    SELECT 
                        me.id_materi_ekskul, 
                        me.id_ekskul,
                        me.judul_materi, 
                        me.deskripsi_materi,
                        me.tipe_konten, 
                        me.path_konten_atau_link,
                        me.isi_konten_teks,
                        me.tanggal_unggah, 
                        p.nama_lengkap AS nama_pengunggah
                    FROM MateriEkskul me
                    JOIN Pengguna p ON me.id_pengunggah = p.id_pengguna
                    WHERE me.id_ekskul = %s
                    ORDER BY me.tanggal_unggah DESC
                """
                cursor.execute(sql, (id_ekskul,))
                materi_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error in get_materi_by_ekskul_id: {e}")
        finally:
            if conn.open: conn.close()
        return materi_list

    # --- Attendance Management ---
    def save_absensi_ekskul(self, id_pendaftaran_ekskul, tanggal_kegiatan, status_kehadiran, dicatat_oleh_id, catatan=None, jam_kegiatan=None):
        """Menyimpan atau mengupdate data absensi."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                # Menggunakan klausa ON DUPLICATE KEY UPDATE jika sudah ada absensi untuk tanggal tersebut
                # Ini memerlukan UNIQUE KEY pada (id_pendaftaran_ekskul, tanggal_kegiatan) di tabel AbsensiEkskul
                sql = """INSERT INTO AbsensiEkskul 
                            (id_pendaftaran_ekskul, tanggal_kegiatan, status_kehadiran, dicatat_oleh_id, catatan, jam_mulai_kegiatan)
                         VALUES (%s, %s, %s, %s, %s, %s) 
                         ON DUPLICATE KEY UPDATE 
                            status_kehadiran = VALUES(status_kehadiran), 
                            catatan = VALUES(catatan), 
                            dicatat_oleh_id = VALUES(dicatat_oleh_id),
                            jam_mulai_kegiatan = VALUES(jam_mulai_kegiatan),
                            updated_at = NOW()"""
                cursor.execute(sql, (
                    id_pendaftaran_ekskul,
                    tanggal_kegiatan,
                    status_kehadiran,
                    dicatat_oleh_id,
                    catatan,
                    jam_kegiatan # Bisa NULL jika tidak diisi
                ))
                conn.commit()
                return True
        except pymysql.MySQLError as e:
            print(f"Error saving absensi ekskul for pendaftaran ID {id_pendaftaran_ekskul}, tanggal {tanggal_kegiatan}: {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close()
    
    def get_all_absensi_ekskul_detailed(self, tahun_ajaran_filter=None, ekskul_id_filter=None, murid_id_filter=None, date_filter=None):
        """Mengambil semua data absensi dengan detail nama murid, ekskul, dan pencatat."""
        conn = self._get_connection()
        absensi_list = []
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        a.id_absensi_ekskul, 
                        p_murid.nama_lengkap AS nama_murid,
                        e.nama_ekskul,
                        a.tanggal_kegiatan,
                        a.jam_mulai_kegiatan,
                        a.status_kehadiran,
                        a.catatan,
                        p_pencatat.nama_lengkap AS nama_pencatat,
                        a.tanggal_dicatat,
                        pe.id_pendaftaran_ekskul, # Untuk link edit
                        pe.tahun_ajaran
                    FROM AbsensiEkskul a
                    JOIN PendaftaranEkskul pe ON a.id_pendaftaran_ekskul = pe.id_pendaftaran_ekskul
                    JOIN Pengguna p_murid ON pe.id_murid = p_murid.id_pengguna
                    JOIN Ekstrakurikuler e ON pe.id_ekskul = e.id_ekskul
                    LEFT JOIN Pengguna p_pencatat ON a.dicatat_oleh_id = p_pencatat.id_pengguna
                    WHERE 1=1 
                """
                params = []
                if tahun_ajaran_filter:
                    sql += " AND pe.tahun_ajaran = %s"
                    params.append(tahun_ajaran_filter)
                if ekskul_id_filter:
                    sql += " AND e.id_ekskul = %s"
                    params.append(ekskul_id_filter)
                if murid_id_filter:
                    sql += " AND p_murid.id_pengguna = %s"
                    params.append(murid_id_filter)
                if date_filter:
                    sql += " AND a.tanggal_kegiatan = %s"
                    params.append(date_filter)
                
                sql += " ORDER BY a.tanggal_kegiatan DESC, e.nama_ekskul, p_murid.nama_lengkap"
                
                cursor.execute(sql, tuple(params))
                absensi_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error in get_all_absensi_ekskul_detailed: {e}")
        finally:
            if conn.open: conn.close()
        return absensi_list

    def get_absensi_entry_for_edit(self, id_pendaftaran_ekskul, tanggal_kegiatan):
        """Mengambil satu entri absensi untuk di-edit, berdasarkan pendaftaran dan tanggal."""
        conn = self._get_connection()
        absensi_entry = None
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        a.status_kehadiran, a.catatan, a.jam_mulai_kegiatan,
                        pe.id_murid, pe.id_ekskul, pe.tahun_ajaran
                    FROM AbsensiEkskul a
                    JOIN PendaftaranEkskul pe ON a.id_pendaftaran_ekskul = pe.id_pendaftaran_ekskul
                    WHERE a.id_pendaftaran_ekskul = %s AND a.tanggal_kegiatan = %s
                """
                cursor.execute(sql, (id_pendaftaran_ekskul, tanggal_kegiatan))
                absensi_entry = cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"Error in get_absensi_entry_for_edit: {e}")
        finally:
            if conn.open: conn.close()
        return absensi_entry
        
    def delete_absensi_ekskul(self, id_absensi_ekskul):
        """Menghapus satu entri absensi berdasarkan ID uniknya."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "DELETE FROM AbsensiEkskul WHERE id_absensi_ekskul = %s"
                cursor.execute(sql, (id_absensi_ekskul,))
                conn.commit()
                return cursor.rowcount > 0 # True jika ada baris yang terhapus
        except pymysql.MySQLError as e:
            print(f"Error in delete_absensi_ekskul for ID {id_absensi_ekskul}: {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close()

    # --- Announcement Management ---
    def get_all_pengumuman(self):
        # Mengambil semua pengumuman, mungkin diurutkan berdasarkan tanggal terbaru
        # dan join dengan nama pembuat, nama kelas, nama ekskul untuk tampilan
        conn = self._get_connection()
        pengumuman_list = []
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        pnm.id_pengumuman, pnm.judul_pengumuman, pnm.isi_pengumuman, 
                        pnm.tanggal_publikasi, pnm.target_peran,
                        usr.nama_lengkap AS nama_pembuat,
                        eks.nama_ekskul AS nama_target_ekskul
                    FROM Pengumuman pnm
                    JOIN Pengguna usr ON pnm.id_pembuat = usr.id_pengguna
                    LEFT JOIN Ekstrakurikuler eks ON pnm.target_ekskul_id = eks.id_ekskul
                    ORDER BY pnm.tanggal_publikasi DESC
                """
                cursor.execute(sql)
                pengumuman_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error in get_all_pengumuman: {e}")
        finally:
            if conn.open: conn.close()
        return pengumuman_list
    
    def add_pengumuman(self, data_pengumuman):
        # data_pengumuman adalah dictionary: 
        # {'judul_pengumuman': '...', 'isi_pengumuman': '...', 'id_pembuat': ..., 
        #  'target_ekskul_id': ..., 'target_kelas_id': ..., 'target_peran': ...}
        conn = self._get_connection()
        new_id = None
        try:
            with conn.cursor() as cursor:
                sql = """INSERT INTO Pengumuman 
                         (judul_pengumuman, isi_pengumuman, id_pembuat, 
                          target_ekskul_id, target_peran)
                         VALUES (%s, %s, %s, %s, %s)"""
                cursor.execute(sql, (
                    data_pengumuman['judul_pengumuman'],
                    data_pengumuman['isi_pengumuman'],
                    data_pengumuman['id_pembuat'],
                    data_pengumuman.get('target_ekskul_id'), # Bisa None
                    data_pengumuman.get('target_peran')      # Bisa None
                ))
                conn.commit()
                new_id = cursor.lastrowid
        except pymysql.MySQLError as e:
            print(f"Error in add_pengumuman: {e}")
            conn.rollback()
        finally:
            if conn.open: conn.close()
        return new_id

    def get_pengumuman_by_id(self, id_pengumuman):
        conn = self._get_connection()
        pengumuman = None
        try:
            with conn.cursor() as cursor:
                # Mengambil detail pengumuman termasuk data target jika ada
                # dan nama pembuat
                sql = """
                    SELECT 
                        pnm.id_pengumuman, pnm.judul_pengumuman, pnm.isi_pengumuman,
                        pnm.id_pembuat, pnm.tanggal_publikasi, 
                        pnm.target_ekskul_id, pnm.target_peran,
                        usr.nama_lengkap AS nama_pembuat
                    FROM Pengumuman pnm
                    JOIN Pengguna usr ON pnm.id_pembuat = usr.id_pengguna
                    WHERE pnm.id_pengumuman = %s
                """
                cursor.execute(sql, (id_pengumuman,))
                pengumuman = cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"Error in get_pengumuman_by_id for ID {id_pengumuman}: {e}")
        finally:
            if conn.open: conn.close()
        return pengumuman

    def update_pengumuman(self, id_pengumuman, data_pengumuman):
        # data_pengumuman: {'judul_pengumuman': ..., 'isi_pengumuman': ..., 
        #                  'target_ekskul_id': ..., 'target_kelas_id': ..., 'target_peran': ...}
        # id_pembuat dan tanggal_publikasi biasanya tidak diubah saat edit.
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql_parts = []
                params = []

                if 'judul_pengumuman' in data_pengumuman:
                    sql_parts.append("judul_pengumuman = %s")
                    params.append(data_pengumuman['judul_pengumuman'])
                if 'isi_pengumuman' in data_pengumuman:
                    sql_parts.append("isi_pengumuman = %s")
                    params.append(data_pengumuman['isi_pengumuman'])
                
                # Target bisa diubah menjadi None jika dikosongkan dari form
                target_peran = data_pengumuman.get('target_peran')
                sql_parts.append("target_peran = %s")
                params.append(target_peran if target_peran and target_peran != "" else None)

                target_ekskul_id = data_pengumuman.get('target_ekskul_id')
                sql_parts.append("target_ekskul_id = %s")
                params.append(target_ekskul_id if target_ekskul_id else None) # Sudah int atau None dari app.py
                
                if not sql_parts:
                    return True # Tidak ada yang diupdate

                sql_parts.append("updated_at = NOW()") # Selalu update kolom updated_at

                sql_query = f"UPDATE Pengumuman SET {', '.join(sql_parts)} WHERE id_pengumuman = %s"
                params.append(id_pengumuman)
                
                cursor.execute(sql_query, tuple(params))
                conn.commit()
                return True
        except pymysql.MySQLError as e:
            print(f"Error in update_pengumuman for ID {id_pengumuman}: {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close()

    def delete_pengumuman(self, id_pengumuman):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "DELETE FROM Pengumuman WHERE id_pengumuman = %s"
                cursor.execute(sql, (id_pengumuman,))
                conn.commit()
                return cursor.rowcount > 0 # True jika ada baris yang terhapus
        except pymysql.MySQLError as e:
            print(f"Error in delete_pengumuman for ID {id_pengumuman}: {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close()

    def get_pengumuman_for_guru(self, id_guru_penerima=None):
        conn = self._get_connection()
        pengumuman_list = []
        try:
            with conn.cursor() as cursor:
                sql = """SELECT 
                                pnm.id_pengumuman, 
                                pnm.judul_pengumuman, 
                                pnm.isi_pengumuman, 
                                pnm.tanggal_publikasi, 
                                usr.nama_lengkap as nama_pembuat 
                            FROM Pengumuman pnm
                            LEFT JOIN Pengguna usr ON pnm.id_pembuat = usr.id_pengguna # <--- UBAH KE LEFT JOIN
                            WHERE pnm.target_peran = 'semua' OR pnm.target_peran = 'guru'
                            ORDER BY pnm.tanggal_publikasi DESC
                            LIMIT 5"""
                cursor.execute(sql)
                pengumuman_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error in get_pengumuman_for_guru: {e}")
        finally:
            if conn.open: conn.close()
        return pengumuman_list

    # --- General Utility ---
    def get_counts(self):
        conn = self._get_connection()
        # Tambahkan 'materi_ekskul' ke dictionary counts
        counts = {'users': 0, 'ekskul': 0, 'pengumuman': 0, 'materi_ekskul': 0} 
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as total FROM Pengguna")
                counts['users'] = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as total FROM Ekstrakurikuler")
                counts['ekskul'] = cursor.fetchone()['total']
                
                cursor.execute("SELECT COUNT(*) as total FROM Pengumuman")
                counts['pengumuman'] = cursor.fetchone()['total']
                
                # Query baru untuk menghitung total materi ekskul
                cursor.execute("SELECT COUNT(*) as total FROM MateriEkskul") 
                counts['materi_ekskul'] = cursor.fetchone()['total']
        except pymysql.MySQLError as e:
            print(f"Error getting counts: {e}")
            # Anda mungkin ingin mengembalikan None atau dictionary kosong jika ada error
            # return {'users': 0, 'kelas': 0, 'ekskul': 0, 'pengumuman': 0, 'materi_ekskul': 0}
        finally:
            if conn.open: conn.close()
        return counts
    
    def get_tahun_ajaran_aktif(self):
        """
        Placeholder: Mengambil tahun ajaran aktif.
        Implementasi sebenarnya mungkin mengambil dari tabel setting atau logika lain.
        """
        # Untuk contoh, kita kembalikan nilai hardcoded. Ganti dengan query database.
        # Misalnya:
        # conn = self._get_connection()
        # try:
        #     with conn.cursor() as cursor:
        #         sql = "SELECT nilai_setting FROM Settings WHERE nama_setting = 'tahun_ajaran_aktif' LIMIT 1"
        #         cursor.execute(sql)
        #         result = cursor.fetchone()
        #         if result:
        #             return result['nilai_setting']
        # except pymysql.MySQLError as e:
        #     print(f"Error fetching tahun ajaran aktif: {e}")
        # finally:
        #     if conn.open: conn.close()
        # return "TAHUN_DEFAULT" # Fallback
        return "2024/2025" # Ganti dengan implementasi yang benar

    def get_murid_options_for_guru_absen(self, id_guru_pembina, tahun_ajaran_aktif):
        """
        Mengambil daftar murid yang terdaftar (status Disetujui/Terdaftar) 
        di semua ekskul yang dibina oleh guru ini pada tahun ajaran aktif.
        Digunakan untuk mengisi dropdown nama siswa di form absensi.
        """
        conn = self._get_connection()
        murid_list = []
        try:
            with conn.cursor() as cursor:
                sql = """SELECT DISTINCT p.id_pengguna, p.nama_lengkap, p.nomor_induk
                         FROM Pengguna p
                         JOIN PendaftaranEkskul pe ON p.id_pengguna = pe.id_murid
                         JOIN Ekstrakurikuler e ON pe.id_ekskul = e.id_ekskul
                         WHERE e.id_guru_pembina = %s 
                           AND pe.tahun_ajaran = %s
                           AND pe.status_pendaftaran IN ('Disetujui', 'Terdaftar')
                           AND p.peran = 'murid' AND p.status_aktif = TRUE
                         ORDER BY p.nama_lengkap"""
                cursor.execute(sql, (id_guru_pembina, tahun_ajaran_aktif))
                murid_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching murid options for guru absen (pembina ID {id_guru_pembina}): {e}")
        finally:
            if conn.open: conn.close()
        return murid_list

    def get_all_active_murid(self): # Mungkin Anda perlu ini untuk dropdown
        conn = self._get_connection()
        murid_list = []
        try:
            with conn.cursor() as cursor:
                sql = "SELECT id_pengguna, nama_lengkap, nomor_induk FROM Pengguna WHERE peran = 'murid' AND status_aktif = TRUE ORDER BY nama_lengkap"
                cursor.execute(sql)
                murid_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching all active murid: {e}")
        finally:
            if conn.open: conn.close()
        return murid_list

    def get_pengumuman_for_role(self, peran_target, limit=5):
        """
        Mengambil pengumuman yang ditujukan untuk 'semua' atau 'peran_target' tertentu.
        """
        conn = self._get_connection()
        pengumuman_list = []
        try:
            with conn.cursor() as cursor:
                # Mengambil juga nama pembuat pengumuman
                sql = """
                    SELECT pnm.judul_pengumuman, pnm.isi_pengumuman, pnm.tanggal_publikasi,
                           usr.nama_lengkap AS nama_pembuat
                    FROM Pengumuman pnm
                    JOIN Pengguna usr ON pnm.id_pembuat = usr.id_pengguna
                    WHERE pnm.target_peran = 'semua' OR pnm.target_peran = %s
                    ORDER BY pnm.tanggal_publikasi DESC
                """
                params = [peran_target]
                if limit:
                    sql += " LIMIT %s"
                    params.append(limit)
                
                cursor.execute(sql, tuple(params))
                pengumuman_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching pengumuman for role {peran_target}: {e}")
        finally:
            if conn.open: conn.close()
        return pengumuman_list

    def get_ekskul_diikuti_murid_detail(self, murid_id, tahun_ajaran):
        """
        Mengambil detail ekstrakurikuler yang diikuti oleh murid tertentu
        pada tahun ajaran tertentu dengan status pendaftaran aktif.
        """
        conn = self._get_connection()
        ekskul_diikuti = []
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT e.id_ekskul, e.nama_ekskul, e.jadwal_deskripsi, e.lokasi,
                           p_pembina.nama_lengkap AS nama_pembina,
                           e.url_logo_ekskul,
                           pe.status_pendaftaran
                    FROM PendaftaranEkskul pe
                    JOIN Ekstrakurikuler e ON pe.id_ekskul = e.id_ekskul
                    LEFT JOIN Pengguna p_pembina ON e.id_guru_pembina = p_pembina.id_pengguna
                    WHERE pe.id_murid = %s 
                      AND pe.tahun_ajaran = %s
                      AND pe.status_pendaftaran IN ('Disetujui', 'Terdaftar') 
                    ORDER BY e.nama_ekskul
                """
                cursor.execute(sql, (murid_id, tahun_ajaran))
                ekskul_diikuti = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching ekskul diikuti by murid {murid_id} for TA {tahun_ajaran}: {e}")
        finally:
            if conn.open: conn.close()
        return ekskul_diikuti
    
    def get_pending_registrations_detailed(self, ekskul_id=None, id_guru_pembina=None):
        """
        Mengambil semua pendaftaran ekskul yang statusnya 'Menunggu Persetujuan'.
        Bisa difilter berdasarkan ekskul_id atau id_guru_pembina.
        """
        conn = self._get_connection()
        pending_list = []
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        pe.id_pendaftaran_ekskul,
                        pe.tanggal_pendaftaran,
                        pe.tahun_ajaran,
                        p_murid.id_pengguna AS id_murid,
                        p_murid.nama_lengkap AS nama_murid,
                        p_murid.nomor_induk AS nomor_induk_murid,
                        e.id_ekskul,
                        e.nama_ekskul,
                        p_pembina.nama_lengkap AS nama_pembina
                    FROM PendaftaranEkskul pe
                    JOIN Pengguna p_murid ON pe.id_murid = p_murid.id_pengguna
                    JOIN Ekstrakurikuler e ON pe.id_ekskul = e.id_ekskul
                    LEFT JOIN Pengguna p_pembina ON e.id_guru_pembina = p_pembina.id_pengguna
                    WHERE pe.status_pendaftaran = %s
                """
                params = ['Menunggu Persetujuan']

                if ekskul_id:
                    sql += " AND e.id_ekskul = %s"
                    params.append(ekskul_id)
                
                if id_guru_pembina:
                    sql += " AND e.id_guru_pembina = %s"
                    params.append(id_guru_pembina)
                
                sql += " ORDER BY pe.tanggal_pendaftaran ASC"
                
                cursor.execute(sql, tuple(params))
                pending_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching pending registrations: {e}")
        finally:
            if conn.open: conn.close()
        return pending_list
    
    def get_pendaftaran_ekskul_by_id(self, pendaftaran_id):
        conn = self._get_connection()
        pendaftaran = None
        try:
            with conn.cursor() as cursor:
                # Ambil juga id_ekskul dan tahun_ajaran untuk cek kuota
                sql = "SELECT * FROM PendaftaranEkskul WHERE id_pendaftaran_ekskul = %s"
                cursor.execute(sql, (pendaftaran_id,))
                pendaftaran = cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"Error fetching pendaftaran by ID {pendaftaran_id}: {e}")
        finally:
            if conn.open: conn.close()
        return pendaftaran

    def count_active_members_ekskul(self, ekskul_id, tahun_ajaran):
        conn = self._get_connection()
        count = 0
        try:
            with conn.cursor() as cursor:
                sql = """SELECT COUNT(*) as jumlah FROM PendaftaranEkskul 
                         WHERE id_ekskul = %s AND tahun_ajaran = %s 
                         AND status_pendaftaran IN ('Disetujui', 'Terdaftar')"""
                cursor.execute(sql, (ekskul_id, tahun_ajaran))
                result = cursor.fetchone()
                if result:
                    count = result['jumlah']
        except pymysql.MySQLError as e:
            print(f"Error counting active members for ekskul {ekskul_id}: {e}")
        finally:
            if conn.open: conn.close()
        return count
    
    def get_pendaftaran_by_murid(self, murid_id, tahun_ajaran):
        """
        Mengambil semua data pendaftaran ekstrakurikuler untuk murid tertentu
        pada tahun ajaran tertentu, terlepas dari status pendaftarannya.
        """
        conn = self._get_connection()
        pendaftaran_list = []
        try:
            with conn.cursor() as cursor:
                sql = """SELECT * FROM PendaftaranEkskul 
                         WHERE id_murid = %s AND tahun_ajaran = %s 
                         ORDER BY tanggal_pendaftaran DESC"""
                # Debug tambahan di Config.py jika diperlukan
                # print(f"DEBUG SQL (get_pendaftaran_by_murid): Query: {sql}, Params: ({murid_id}, {tahun_ajaran})")
                cursor.execute(sql, (murid_id, tahun_ajaran))
                pendaftaran_list = cursor.fetchall()
                # print(f"DEBUG SQL (get_pendaftaran_by_murid): Result: {pendaftaran_list}")
        except pymysql.MySQLError as e:
            print(f"Error fetching pendaftaran by murid ID {murid_id} for TA {tahun_ajaran}: {e}")
        finally:
            if conn.open: conn.close()
        return pendaftaran_list
    
    def get_my_attendance_records(self, murid_id, tahun_ajaran):
        """
        Mengambil semua catatan absensi seorang murid untuk semua ekskul yang diikutinya
        (status Disetujui/Terdaftar) pada tahun ajaran tertentu.
        """
        conn = self._get_connection()
        records = []
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        ae.tanggal_kegiatan,
                        ae.jam_mulai_kegiatan,
                        ae.status_kehadiran,
                        ae.catatan AS catatan_absensi,
                        e.nama_ekskul,
                        e.id_ekskul,
                        p_dicatat.nama_lengkap AS nama_pencatat
                    FROM AbsensiEkskul ae
                    JOIN PendaftaranEkskul pe ON ae.id_pendaftaran_ekskul = pe.id_pendaftaran_ekskul
                    JOIN Ekstrakurikuler e ON pe.id_ekskul = e.id_ekskul
                    LEFT JOIN Pengguna p_dicatat ON ae.dicatat_oleh_id = p_dicatat.id_pengguna
                    WHERE pe.id_murid = %s
                      AND pe.tahun_ajaran = %s
                      AND pe.status_pendaftaran IN ('Disetujui', 'Terdaftar')
                    ORDER BY e.nama_ekskul ASC, ae.tanggal_kegiatan DESC;
                """
                cursor.execute(sql, (murid_id, tahun_ajaran))
                records = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching my attendance records for murid_id {murid_id}, TA {tahun_ajaran}: {e}")
        finally:
            if conn.open: conn.close()
        return records
    
    def delete_pendaftaran_ekskul_by_id(self, pendaftaran_id):
        """Menghapus record pendaftaran ekskul berdasarkan ID pendaftarannya."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "DELETE FROM PendaftaranEkskul WHERE id_pendaftaran_ekskul = %s"
                cursor.execute(sql, (pendaftaran_id,))
                conn.commit()
                return cursor.rowcount > 0 # True jika ada baris yang terhapus
        except pymysql.MySQLError as e:
            print(f"Error deleting pendaftaran ekskul by ID {pendaftaran_id}: {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close()

    # Anda juga akan menggunakan kembali metode-metode yang sudah ada dari Admin
    # untuk fitur pengelolaan peserta ekskul oleh guru, misalnya:
    # - get_ekskul_by_id(ekskul_id)
    # - get_members_of_ekskul(ekskul_id, tahun_ajaran)
    # - get_all_active_murid_exclude_ekskul(ekskul_id, tahun_ajaran)
    # - register_student_for_ekskul(murid_id, ekskul_id, tahun_ajaran, ...)
    # - update_ekskul_registration_status(pendaftaran_id, ...)
    
    # Pastikan metode ini sudah ada (dari implementasi Admin)

    # --- Anda perlu menambahkan metode lain sesuai kebutuhan ---
    # Misalnya: update_user, delete_user, get_kelas_by_id, update_kelas, dst.