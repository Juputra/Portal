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

                # ... (penanganan field lain seperti nama_ekskul, deskripsi, dll.) ...
                if 'nama_ekskul' in ekskul_data: sql_parts.append("nama_ekskul = %s"); params.append(ekskul_data['nama_ekskul'])
                if 'deskripsi' in ekskul_data: sql_parts.append("deskripsi = %s"); params.append(ekskul_data.get('deskripsi'))
                if 'kategori' in ekskul_data: # Tambahkan ini
                    sql_parts.append("kategori = %s")
                    params.append(ekskul_data.get('kategori'))
                if 'id_guru_pembina' in ekskul_data: sql_parts.append("id_guru_pembina = %s"); params.append(ekskul_data.get('id_guru_pembina'))
                # ... (lanjutkan untuk field lain: jadwal_deskripsi, lokasi, dll.) ...

                if not sql_parts:
                    return True 

                sql = f"UPDATE Ekstrakurikuler SET {', '.join(sql_parts)}, updated_at = NOW() WHERE id_ekskul = %s"
                params.append(ekskul_id)

                cursor.execute(sql, tuple(params))
                conn.commit()
                return True # Berhasil
        # ekskul_data adalah dictionary yang berisi field yang akan diupdate
        # Contoh: {'nama_ekskul': 'Basket Baru', 'lokasi': 'Lapangan Utama', ...}
        except pymysql.MySQLError as e:
            print(f"Error updating ekstrakurikuler {ekskul_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

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

    def get_all_kelas(self):
        conn = self._get_connection()
        kelas_list = []
        try:
            with conn.cursor() as cursor:
                # Menggunakan LEFT JOIN untuk tetap menampilkan kelas meskipun tidak ada wali kelas
                sql = """SELECT k.*, p.nama_lengkap AS nama_wali_kelas 
                         FROM Kelas k 
                         LEFT JOIN Pengguna p ON k.id_wali_kelas = p.id_pengguna
                         ORDER BY k.nama_kelas"""
                cursor.execute(sql)
                kelas_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching all kelas: {e}")
        finally:
            conn.close()
        return kelas_list

    def add_kelas(self, kelas_data):
        conn = self._get_connection()
        new_kelas_id = None
        try:
            with conn.cursor() as cursor:
                sql = """INSERT INTO Kelas (nama_kelas, tahun_ajaran, id_wali_kelas, deskripsi)
                         VALUES (%s, %s, %s, %s)"""
                cursor.execute(sql, (
                    kelas_data['nama_kelas'],
                    kelas_data['tahun_ajaran'],
                    kelas_data.get('id_wali_kelas'), # Bisa NULL
                    kelas_data.get('deskripsi')
                ))
                conn.commit()
                new_kelas_id = cursor.lastrowid
        except pymysql.MySQLError as e:
            print(f"Error adding kelas: {e}")
            conn.rollback()
        finally:
            conn.close()
        return new_kelas_id

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

    def get_kelas_by_id(self, kelas_id):
      conn = self._get_connection()
      kelas_info = None
      try:
        with conn.cursor() as cursor:
            sql = """SELECT k.*, p.nama_lengkap AS nama_wali_kelas 
                     FROM Kelas k 
                     LEFT JOIN Pengguna p ON k.id_wali_kelas = p.id_pengguna 
                     WHERE k.id_kelas = %s"""
            cursor.execute(sql, (kelas_id,))
            kelas_info = cursor.fetchone()
      except pymysql.MySQLError as e:
        print(f"Error fetching kelas by id: {e}")
      finally:
        conn.close()
      return kelas_info

    def get_students_in_class(self, kelas_id):
      conn = self._get_connection()
      students = []
      try:
          with conn.cursor() as cursor:
            # Ambil siswa yang status enrollmentnya 'aktif'
            sql = """SELECT p.id_pengguna, p.nama_lengkap, p.nomor_induk, p.email 
                     FROM Pengguna p
                     JOIN EnrollmentMurid em ON p.id_pengguna = em.id_murid
                     WHERE em.id_kelas = %s AND p.peran = 'murid' AND em.status_enrollment = 'aktif'
                     ORDER BY p.nama_lengkap"""
            cursor.execute(sql, (kelas_id,))
            students = cursor.fetchall()
      except pymysql.MySQLError as e:
        print(f"Error fetching students in class: {e}")
      finally:
        conn.close()
      return students

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

    def get_all_active_murid_exclude_kelas(self, kelas_id_to_check, tahun_ajaran_aktif):
        # Metode ini mengambil semua murid aktif yang BELUM terdaftar di kelas_id_to_check
        # PADA tahun_ajaran_aktif. Ini untuk dropdown agar tidak menampilkan murid yang sudah ada di kelas tsb.
        # Atau, bisa juga mengambil murid yang belum terdaftar di kelas MANAPUN pada tahun ajaran tsb.
        # Ini contoh yang lebih sederhana: mengambil semua murid aktif.
        # Anda mungkin perlu query yang lebih kompleks untuk kasus nyata.
        conn = self._get_connection()
        murid_list = []
        try:
            with conn.cursor() as cursor:
                # Ambil semua murid aktif yang belum ada di kelas spesifik ini pada tahun ajaran ini
                sql = """
                    SELECT p.id_pengguna, p.nama_lengkap, p.nomor_induk
                    FROM Pengguna p
                    WHERE p.peran = 'murid' AND p.status_aktif = TRUE
                    AND p.id_pengguna NOT IN (
                        SELECT em.id_murid
                        FROM EnrollmentMurid em
                        WHERE em.id_kelas = %s AND em.tahun_ajaran = %s AND em.status_enrollment = 'aktif'
                    )
                    ORDER BY p.nama_lengkap;
                """
                # Jika Anda ingin mengambil murid yang belum terdaftar di kelas MANAPUN pada tahun ajaran ini:
                # sql = """
                #     SELECT p.id_pengguna, p.nama_lengkap, p.nomor_induk
                #     FROM Pengguna p
                #     LEFT JOIN EnrollmentMurid em ON p.id_pengguna = em.id_murid AND em.tahun_ajaran = %s AND em.status_enrollment = 'aktif'
                #     WHERE p.peran = 'murid' AND p.status_aktif = TRUE AND em.id_kelas IS NULL
                #     ORDER BY p.nama_lengkap;
                # """
                # Untuk query di atas (yang belum terdaftar di kelas MANAPUN), parameternya hanya (tahun_ajaran_aktif,)
                cursor.execute(sql, (kelas_id_to_check, tahun_ajaran_aktif))
                murid_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching active murid for enrollment: {e}")
        finally:
            conn.close()
        return murid_list

    def enroll_student_to_class(self, murid_id, kelas_id, tahun_ajaran, status_enrollment='aktif'):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                # Cek dulu apakah murid sudah terdaftar di kelas ini pada tahun ajaran ini
                # Sebenarnya UNIQUE constraint di DB sudah menangani ini, tapi cek di sini bisa memberi feedback lebih baik
                sql_check = "SELECT 1 FROM EnrollmentMurid WHERE id_murid = %s AND id_kelas = %s AND tahun_ajaran = %s"
                cursor.execute(sql_check, (murid_id, kelas_id, tahun_ajaran))
                if cursor.fetchone():
                    print(f"Murid ID {murid_id} sudah terdaftar di Kelas ID {kelas_id} untuk tahun ajaran {tahun_ajaran}.")
                    return False # Indikasi sudah ada / gagal

                sql = """INSERT INTO EnrollmentMurid (id_murid, id_kelas, tahun_ajaran, status_enrollment)
                         VALUES (%s, %s, %s, %s)"""
                cursor.execute(sql, (murid_id, kelas_id, tahun_ajaran, status_enrollment))
                conn.commit()
                return True # Berhasil
        except pymysql.MySQLError as e:
            print(f"Error enrolling student {murid_id} to class {kelas_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
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

    def register_student_for_ekskul(self, murid_id, ekskul_id, tahun_ajaran, status_pendaftaran='Disetujui', catatan_admin="Didaftarkan oleh Admin"):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                # Cek duplikasi
                sql_check = "SELECT 1 FROM PendaftaranEkskul WHERE id_murid = %s AND id_ekskul = %s AND tahun_ajaran = %s"
                cursor.execute(sql_check, (murid_id, ekskul_id, tahun_ajaran))
                if cursor.fetchone():
                    print(f"Murid ID {murid_id} sudah terdaftar/menunggu di Ekskul ID {ekskul_id} untuk tahun ajaran {tahun_ajaran}.")
                    return False

                sql = """INSERT INTO PendaftaranEkskul 
                         (id_murid, id_ekskul, tahun_ajaran, status_pendaftaran, catatan_admin_pembina)
                         VALUES (%s, %s, %s, %s, %s)"""
                cursor.execute(sql, (murid_id, ekskul_id, tahun_ajaran, status_pendaftaran, catatan_admin))
                conn.commit()
                return True # Berhasil
        except pymysql.MySQLError as e:
            print(f"Error registering student {murid_id} for ekskul {ekskul_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

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

    def update_enrollment_status(self, murid_id, kelas_id, tahun_ajaran, new_status='dropout'):
        # Atau bisa juga menggunakan enrollment_id jika itu lebih mudah didapat dari template
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """UPDATE EnrollmentMurid 
                         SET status_enrollment = %s 
                         WHERE id_murid = %s AND id_kelas = %s AND tahun_ajaran = %s"""
                # Pastikan new_status adalah salah satu nilai ENUM yang valid
                # ('aktif', 'lulus', 'pindah', 'dropout')
                # Anda mungkin perlu menambahkan status baru ke DDL jika 'dropout' atau 'pindah' tidak cocok
                cursor.execute(sql, (new_status, murid_id, kelas_id, tahun_ajaran))
                conn.commit()
                return cursor.rowcount > 0 # True jika ada baris yang terupdate
        except pymysql.MySQLError as e:
            print(f"Error updating enrollment status for murid {murid_id} in class {kelas_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()


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

    def delete_kelas(self, kelas_id):
      conn = self._get_connection()
      try:
          with conn.cursor() as cursor:
              # DDL kita untuk EnrollmentMurid memiliki ON DELETE CASCADE pada fk_kelas.
              # Jadi, menghapus kelas akan otomatis menghapus enrollment murid di kelas tersebut.
              sql = "DELETE FROM Kelas WHERE id_kelas = %s"
              cursor.execute(sql, (kelas_id,))
              conn.commit()
              return cursor.rowcount > 0 # True jika ada baris yang terhapus
      except pymysql.MySQLError as e:
          print(f"Error deleting kelas {kelas_id}: {e}")
          conn.rollback()
          return False
      finally:
          conn.close()

    def get_counts(self):
        # Implementasi: SELECT COUNT(*) FROM Pengguna; SELECT COUNT(*) FROM Kelas; dst.
        # Ini adalah contoh sederhana, Anda bisa membuatnya lebih efisien
        conn = self._get_connection()
        counts = {'users': 0, 'kelas': 0, 'ekskul': 0}
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as total FROM Pengguna")
                counts['users'] = cursor.fetchone()['total']
                cursor.execute("SELECT COUNT(*) as total FROM Kelas")
                counts['kelas'] = cursor.fetchone()['total']
                cursor.execute("SELECT COUNT(*) as total FROM Ekstrakurikuler")
                counts['ekskul'] = cursor.fetchone()['total']
        except pymysql.MySQLError as e:
            print(f"Error getting counts: {e}")
        finally:
            conn.close()
        return counts

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

    def get_pengumuman_for_guru(self, id_guru_penerima=None):
        """
        Mengambil pengumuman umum dan yang ditargetkan untuk guru.
        Untuk kesederhanaan, kita ambil semua pengumuman yang target_peran nya 'guru' atau 'semua'.
        Anda bisa membuat ini lebih kompleks jika ada target_kelas_id atau target_ekskul_id yang relevan.
        """
        conn = self._get_connection()
        pengumuman_list = []
        try:
            with conn.cursor() as cursor:
                # Ambil pengumuman yang targetnya 'semua' atau 'guru'
                # Diurutkan berdasarkan tanggal publikasi terbaru
                sql = """SELECT judul_pengumuman, isi_pengumuman, tanggal_publikasi 
                         FROM Pengumuman 
                         WHERE target_peran = 'semua' OR target_peran = 'guru'
                         ORDER BY tanggal_publikasi DESC
                         LIMIT 5""" # Ambil 5 terbaru sebagai contoh
                cursor.execute(sql)
                pengumuman_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching pengumuman for guru: {e}")
        finally:
            conn.close()
        return pengumuman_list

    def get_murid_options_for_guru_absen(self, id_guru_pembina):
        """
        Mengambil daftar murid yang bisa diabsen oleh guru.
        Untuk V1, kita ambil semua murid yang terdaftar di ekskul yang dibina oleh guru ini.
        Ini bisa jadi daftar yang panjang jika seorang guru membina banyak ekskul dengan banyak murid.
        Alternatif: Ambil semua murid aktif di sekolah, lalu guru memilih ekskul saat absen.
        HTML Anda (test.html) mengisi dropdown murid dari JS lokal.
        Untuk integrasi server, mari kita sediakan daftar murid dari ekskul yang dibina guru.
        """
        conn = self._get_connection()
        murid_list = []
        try:
            with conn.cursor() as cursor:
                # Ambil semua murid unik yang terdaftar (status Disetujui/Terdaftar)
                # di ekskul yang dibina oleh guru ini pada tahun ajaran 'aktif' (asumsi)
                # Anda perlu logika untuk menentukan tahun_ajaran_aktif
                tahun_ajaran_aktif = "2024/2025" # GANTI DENGAN LOGIKA TAHUN AJARAN AKTIF
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
            conn.close()
        return murid_list

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

    def save_absensi_ekskul(self, id_pendaftaran_ekskul, tanggal_kegiatan, status_kehadiran, dicatat_oleh_id, catatan=None):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                # Cek apakah sudah ada absensi untuk pendaftaran ini di tanggal ini
                # (UNIQUE KEY di DB akan mencegah duplikasi, tapi cek di sini bisa untuk update jika perlu)
                sql_check_or_insert = """
                    INSERT INTO AbsensiEkskul 
                        (id_pendaftaran_ekskul, tanggal_kegiatan, status_kehadiran, dicatat_oleh_id, catatan, jam_mulai_kegiatan)
                    VALUES (%s, %s, %s, %s, %s, CURTIME()) 
                    ON DUPLICATE KEY UPDATE 
                        status_kehadiran = VALUES(status_kehadiran), 
                        catatan = VALUES(catatan), 
                        dicatat_oleh_id = VALUES(dicatat_oleh_id),
                        jam_mulai_kegiatan = VALUES(jam_mulai_kegiatan) 
                        # Anda mungkin ingin mencatat updated_at juga
                """
                # jam_mulai_kegiatan diisi CURTIME() sebagai contoh, bisa diambil dari form jika ada
                cursor.execute(sql_check_or_insert, (
                    id_pendaftaran_ekskul,
                    tanggal_kegiatan,
                    status_kehadiran,
                    dicatat_oleh_id,
                    catatan
                ))
                conn.commit()
                return True
        except pymysql.MySQLError as e:
            print(f"Error saving absensi ekskul for pendaftaran ID {id_pendaftaran_ekskul}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_ekskul_by_pembina(self, id_guru_pembina):
        """Mengambil semua ekstrakurikuler yang dibina oleh guru tertentu dan aktif."""
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
            if conn.open: conn.close()
        return ekskul_list

    def get_pengumuman_for_guru(self, id_guru_penerima=None): # id_guru_penerima bisa digunakan untuk personalisasi nanti
        """Mengambil pengumuman umum dan yang ditargetkan untuk guru."""
        conn = self._get_connection()
        pengumuman_list = []
        try:
            with conn.cursor() as cursor:
                # Ambil pengumuman yang targetnya 'semua' atau 'guru'
                # Diurutkan berdasarkan tanggal publikasi terbaru
                sql = """SELECT id_pengumuman, judul_pengumuman, isi_pengumuman, tanggal_publikasi 
                         FROM Pengumuman 
                         WHERE target_peran = 'semua' OR target_peran = 'guru'
                         ORDER BY tanggal_publikasi DESC
                         LIMIT 5""" # Ambil 5 terbaru sebagai contoh
                cursor.execute(sql)
                pengumuman_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching pengumuman for guru: {e}")
        finally:
            if conn.open: conn.close()
        return pengumuman_list

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

    def get_pendaftaran_ekskul_id(self, murid_id, ekskul_id, tahun_ajaran):
        """Mencari id_pendaftaran_ekskul berdasarkan murid, ekskul, dan tahun ajaran yang aktif terdaftar."""
        conn = self._get_connection()
        pendaftaran_id = None
        try:
            with conn.cursor() as cursor:
                sql = """SELECT id_pendaftaran_ekskul 
                         FROM PendaftaranEkskul
                         WHERE id_murid = %s AND id_ekskul = %s AND tahun_ajaran = %s
                         AND status_pendaftaran IN ('Disetujui', 'Terdaftar') 
                         LIMIT 1"""
                cursor.execute(sql, (murid_id, ekskul_id, tahun_ajaran))
                result = cursor.fetchone()
                if result:
                    pendaftaran_id = result['id_pendaftaran_ekskul']
        except pymysql.MySQLError as e:
            print(f"Error fetching pendaftaran_ekskul_id (murid:{murid_id}, ekskul:{ekskul_id}, thn:{tahun_ajaran}): {e}")
        finally:
            if conn.open: conn.close()
        return pendaftaran_id

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

    # Anda juga akan menggunakan kembali metode-metode yang sudah ada dari Admin
    # untuk fitur pengelolaan peserta ekskul oleh guru, misalnya:
    # - get_ekskul_by_id(ekskul_id)
    # - get_members_of_ekskul(ekskul_id, tahun_ajaran)
    # - get_all_active_murid_exclude_ekskul(ekskul_id, tahun_ajaran)
    # - register_student_for_ekskul(murid_id, ekskul_id, tahun_ajaran, ...)
    # - update_ekskul_registration_status(pendaftaran_id, ...)
    
    # Pastikan metode ini sudah ada (dari implementasi Admin)
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

    # --- Anda perlu menambahkan metode lain sesuai kebutuhan ---
    # Misalnya: update_user, delete_user, get_kelas_by_id, update_kelas, dst.