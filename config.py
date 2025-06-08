import pymysql
from werkzeug.security import generate_password_hash 

class Config:
    def __init__(self):
        self.db_host = 'localhost'
        self.db_user = 'root'
        self.db_password = ''
        self.db_name = 'db_portal'
 
    def _get_connection(self):
        return pymysql.connect(
            host=self.db_host,
            user=self.db_user,
            password=self.db_password,
            database=self.db_name,
            cursorclass=pymysql.cursors.DictCursor
        )

    def check_db_connection(self):
        try:
            conn = self._get_connection()
            conn.ping(reconnect=True)
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

    def get_user_by_email(self, email_user):
        conn = self._get_connection()
        user = None
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM Pengguna WHERE email = %s"
                cursor.execute(sql, (email_user,))
                user = cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"Error fetching user by id: {e}")
        finally:
            conn.close()
        return user

    def get_user_by_nomor_induk(self, nomor_induk, peran):
        conn = self._get_connection()
        user = None
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM Pengguna WHERE nomor_induk = %s AND peran = %s"
                cursor.execute(sql, (nomor_induk, peran))
                user = cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"Error fetching user by nomor induk dan peran: {e}")
        finally:
            conn.close()
        return user

    def get_users_by_role(self, peran):
        conn = self._get_connection()
        users = []
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM Pengguna WHERE peran = %s ORDER BY nama_lengkap"
                cursor.execute(sql, (peran,))
                users = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error in get_users_by_role for role '{peran}': {e}")
        finally:
            if conn.open: conn.close()
        return users
    
    def get_all_users(self):
        conn = self._get_connection()
        users = []
        try:
            with conn.cursor() as cursor:
                sql = "SELECT * FROM Pengguna ORDER BY FIELD(peran, 'admin', 'guru', 'murid'), nama_lengkap"
                cursor.execute(sql)
                users = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching all users: {e}")
        finally:
            conn.close()
        return users

    def add_user(self, user_data):
        conn = self._get_connection()
        new_user_id = None
        try:
            with conn.cursor() as cursor:
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
                    user_data.get('nomor_induk'), 
                    user_data.get('status_aktif', True)
                ))
                conn.commit()
                new_user_id = cursor.lastrowid 
        except pymysql.MySQLError as e:
            print(f"Error adding user: {e}")
            conn.rollback()
        finally:
            conn.close()
        return new_user_id
    
    def update_user(self, user_id, user_data):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
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
                if 'nomor_induk' in user_data:
                    sql_parts.append("nomor_induk = %s")
                    params.append(user_data['nomor_induk'])
                if 'status_aktif' in user_data:
                    sql_parts.append("status_aktif = %s")
                    params.append(bool(user_data['status_aktif']))
                if 'password' in user_data and user_data['password']:
                    hashed_password = generate_password_hash(user_data['password'])
                    sql_parts.append("password_hash = %s")
                    params.append(hashed_password)
                if not sql_parts: 
                    return True 
                sql = f"UPDATE Pengguna SET {', '.join(sql_parts)} WHERE id_pengguna = %s"
                params.append(user_id)
                cursor.execute(sql, tuple(params))
                conn.commit()
                return True 
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
                sql = "DELETE FROM Pengguna WHERE id_pengguna = %s"
                cursor.execute(sql, (user_id,))
                conn.commit()
                return cursor.rowcount > 0
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
                    print("Tidak ada admin ditemukan. Membuat admin default.")
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

    def get_all_ekskul(self):
        conn = self._get_connection()
        ekskul_list = []
        try:
            with conn.cursor() as cursor:
                sql = """SELECT e.*, p.nama_lengkap AS nama_guru_pembina 
                         FROM Ekstrakurikuler e
                         LEFT JOIN Pengguna p ON e.id_guru_pembina = p.id_pengguna
                         ORDER BY e.kategori, e.nama_ekskul""" 
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
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                cursor.execute(sql, (
                    ekskul_data['nama_ekskul'],
                    ekskul_data.get('deskripsi'),
                    ekskul_data.get('kategori'), 
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
                if 'nama_ekskul' in ekskul_data:
                    sql_parts.append("nama_ekskul = %s")
                    params.append(ekskul_data['nama_ekskul'])
                if 'deskripsi' in ekskul_data: 
                    sql_parts.append("deskripsi = %s")
                    params.append(ekskul_data.get('deskripsi'))
                if 'kategori' in ekskul_data:
                    sql_parts.append("kategori = %s")
                    params.append(ekskul_data.get('kategori'))
                if 'id_guru_pembina' in ekskul_data: 
                    sql_parts.append("id_guru_pembina = %s")
                    params.append(ekskul_data.get('id_guru_pembina'))
                if 'jadwal_deskripsi' in ekskul_data: 
                    sql_parts.append("jadwal_deskripsi = %s")
                    params.append(ekskul_data.get('jadwal_deskripsi'))
                if 'lokasi' in ekskul_data: 
                    sql_parts.append("lokasi = %s")
                    params.append(ekskul_data.get('lokasi'))
                if 'kuota_maksimal' in ekskul_data: 
                    sql_parts.append("kuota_maksimal = %s")
                    params.append(ekskul_data.get('kuota_maksimal'))
                if 'status_aktif' in ekskul_data: 
                    sql_parts.append("status_aktif = %s")
                    params.append(bool(ekskul_data['status_aktif']))
                if 'url_logo_ekskul' in ekskul_data:
                    sql_parts.append("url_logo_ekskul = %s")
                    params.append(ekskul_data.get('url_logo_ekskul')) 
                if not sql_parts:
                    return True 
                sql = f"UPDATE Ekstrakurikuler SET {', '.join(sql_parts)}, updated_at = NOW() WHERE id_ekskul = %s"
                params.append(ekskul_id)
                cursor.execute(sql, tuple(params))
                conn.commit()
                return cursor.rowcount > 0 
        except pymysql.MySQLError as e:
            print(f"Error updating ekstrakurikuler {ekskul_id}: {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close()

    def delete_ekskul(self, ekskul_id):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "DELETE FROM Ekstrakurikuler WHERE id_ekskul = %s"
                cursor.execute(sql, (ekskul_id,))
                conn.commit()
                return cursor.rowcount > 0
        except pymysql.MySQLError as e:
            print(f"Error deleting ekstrakurikuler {ekskul_id}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_ekskul_by_pembina(self, id_guru_pembina):
        conn = self._get_connection()
        ekskul_list = []
        tahun_ajaran_aktif = self.get_tahun_ajaran_aktif() 
        try:
            with conn.cursor() as cursor:
                sql = """SELECT 
                            e.id_ekskul, 
                            e.nama_ekskul, 
                            e.jadwal_deskripsi, 
                            e.lokasi,
                            (SELECT COUNT(*) 
                             FROM PendaftaranEkskul pe 
                             WHERE pe.id_ekskul = e.id_ekskul 
                               AND pe.tahun_ajaran = %s 
                               AND pe.status_pendaftaran IN ('Disetujui', 'Terdaftar')) AS jumlah_peserta
                        FROM Ekstrakurikuler e
                        WHERE e.id_guru_pembina = %s AND e.status_aktif = TRUE
                        ORDER BY e.nama_ekskul"""
                cursor.execute(sql, (tahun_ajaran_aktif, id_guru_pembina))
                ekskul_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching ekskul by pembina {id_guru_pembina}: {e}")
        finally:
            conn.close()
        return ekskul_list

    def get_all_active_murid_exclude_ekskul(self, ekskul_id_to_check, tahun_ajaran_aktif):
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
                                    catatan_pendaftar="Didaftarkan oleh sistem"):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql_get_ekskul_info = "SELECT kuota_maksimal, nama_ekskul FROM Ekstrakurikuler WHERE id_ekskul = %s"
                cursor.execute(sql_get_ekskul_info, (ekskul_id,))
                ekskul_info = cursor.fetchone()
                if not ekskul_info:
                    print(f"Ekskul ID {ekskul_id} tidak ditemukan.")
                    return "EKSKUL_NOT_FOUND" 

                kuota = ekskul_info.get('kuota_maksimal')
                nama_ekskul = ekskul_info.get('nama_ekskul')
                if kuota is not None and kuota > 0:
                    sql_count_participants = """
                        SELECT COUNT(*) as jumlah_peserta 
                        FROM PendaftaranEkskul 
                        WHERE id_ekskul = %s AND tahun_ajaran = %s 
                        AND status_pendaftaran IN ('Disetujui', 'Terdaftar') 
                    """ 
                    cursor.execute(sql_count_participants, (ekskul_id, tahun_ajaran))
                    jumlah_peserta_aktif = cursor.fetchone()['jumlah_peserta']
                    if jumlah_peserta_aktif >= kuota:
                        print(f"Kuota untuk Ekskul '{nama_ekskul}' (ID: {ekskul_id}) sudah penuh ({jumlah_peserta_aktif}/{kuota}).")
                        return "KUOTA_PENUH" 
                    
                sql_check_duplikasi = """SELECT id_pendaftaran_ekskul, status_pendaftaran 
                                         FROM PendaftaranEkskul 
                                         WHERE id_murid = %s AND id_ekskul = %s AND tahun_ajaran = %s"""
                cursor.execute(sql_check_duplikasi, (murid_id, ekskul_id, tahun_ajaran))
                pendaftaran_lama = cursor.fetchone()
                
                if pendaftaran_lama:
                    print(f"Murid ID {murid_id} sudah memiliki record pendaftaran di Ekskul '{nama_ekskul}' untuk tahun {tahun_ajaran} dengan status {pendaftaran_lama['status_pendaftaran']}.")
                    return "SUDAH_TERDAFTAR"
                
                sql_insert = """INSERT INTO PendaftaranEkskul 
                                (id_murid, id_ekskul, tahun_ajaran, status_pendaftaran, catatan_admin_pembina)
                                VALUES (%s, %s, %s, %s, %s)"""
                cursor.execute(sql_insert, (murid_id, ekskul_id, tahun_ajaran, status_pendaftaran, catatan_pendaftar))
                conn.commit()
                return cursor.lastrowid
        except pymysql.MySQLError as e:
            print(f"Error in register_student_for_ekskul (murid:{murid_id}, ekskul:{ekskul_id}): {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close()

    def get_members_of_ekskul(self, ekskul_id, tahun_ajaran_aktif):
      conn = self._get_connection()
      members = []
      try:
          with conn.cursor() as cursor:
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
            print(f"Error fetching pendaftaran_ekskul_id: {e}")
        finally:
            conn.close()
        return pendaftaran_id

    def update_ekskul_registration_status(self, pendaftaran_id, new_status='Berhenti', catatan_admin="Dikeluarkan oleh Admin"):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """UPDATE PendaftaranEkskul 
                         SET status_pendaftaran = %s, catatan_admin_pembina = %s
                         WHERE id_pendaftaran_ekskul = %s"""
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
                    data_materi.get('path_konten_atau_link'),
                    data_materi.get('isi_konten_teks'),
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
                if 'id_ekskul' in data_materi: 
                    sql_parts.append("id_ekskul = %s")
                    params.append(data_materi['id_ekskul'])
                if 'judul_materi' in data_materi: 
                    sql_parts.append("judul_materi = %s")
                    params.append(data_materi['judul_materi'])
                if 'deskripsi_materi' in data_materi: 
                    sql_parts.append("deskripsi_materi = %s")
                    params.append(data_materi['deskripsi_materi'])
                if 'tipe_konten' in data_materi:
                    current_tipe_konten = data_materi['tipe_konten']
                    sql_parts.append("tipe_konten = %s")
                    params.append(current_tipe_konten)

                    if current_tipe_konten in ['file', 'link', 'video_embed']:
                        if 'path_konten_atau_link' in data_materi:
                            sql_parts.append("path_konten_atau_link = %s")
                            params.append(data_materi.get('path_konten_atau_link'))
                        sql_parts.append("isi_konten_teks = %s")
                        params.append(None)
                    elif current_tipe_konten == 'teks':
                        if 'isi_konten_teks' in data_materi:
                            sql_parts.append("isi_konten_teks = %s")
                            params.append(data_materi.get('isi_konten_teks'))
                        sql_parts.append("path_konten_atau_link = %s")
                        params.append(None)
                else:
                    if 'path_konten_atau_link' in data_materi:
                        sql_parts.append("path_konten_atau_link = %s")
                        params.append(data_materi.get('path_konten_atau_link'))
                    if 'isi_konten_teks' in data_materi:
                        sql_parts.append("isi_konten_teks = %s")
                        params.append(data_materi.get('isi_konten_teks'))

                if not sql_parts:
                    print("Tidak ada data valid untuk diupdate pada materi ekskul.")
                    return True 

                sql_parts.append("updated_at = NOW()")
                
                sql_query = f"UPDATE MateriEkskul SET {', '.join(sql_parts)} WHERE id_materi_ekskul = %s"
                params.append(id_materi_ekskul)

                if sql_query.count('%s') != len(params):
                    print("ERROR KRITIS: Jumlah placeholder %s tidak cocok dengan jumlah parameter!")
                    conn.rollback() 
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
                cursor.execute("SELECT tipe_konten, path_konten_atau_link FROM MateriEkskul WHERE id_materi_ekskul = %s", (id_materi_ekskul,))
                materi_info = cursor.fetchone()
                sql_delete = "DELETE FROM MateriEkskul WHERE id_materi_ekskul = %s"
                cursor.execute(sql_delete, (id_materi_ekskul,))
                conn.commit()
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

    def save_absensi_ekskul(self, id_pendaftaran_ekskul, tanggal_kegiatan, status_kehadiran, dicatat_oleh_id, catatan=None, jam_kegiatan=None):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
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
                    jam_kegiatan 
                ))
                conn.commit()
                return True
        except pymysql.MySQLError as e:
            print(f"Error saving absensi ekskul for pendaftaran ID {id_pendaftaran_ekskul}, tanggal {tanggal_kegiatan}: {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close()
    
    def get_absensi_by_guru(self, guru_id, filters={}):
        """
        Mengambil daftar absensi yang dicatat oleh seorang guru, dengan opsi filter.
        """
        conn = self._get_connection()
        absensi_list = []
        try:
            with conn.cursor() as cursor:
                sql = """
                    SELECT 
                        ae.id_absensi_ekskul,
                        ae.tanggal_kegiatan,
                        ae.jam_mulai_kegiatan,
                        ae.status_kehadiran,
                        ae.catatan,
                        p_murid.nama_lengkap AS nama_murid,
                        e.nama_ekskul,
                        ae.dicatat_oleh_id
                    FROM AbsensiEkskul ae
                    JOIN PendaftaranEkskul pe ON ae.id_pendaftaran_ekskul = pe.id_pendaftaran_ekskul
                    JOIN Pengguna p_murid ON pe.id_murid = p_murid.id_pengguna
                    JOIN Ekstrakurikuler e ON pe.id_ekskul = e.id_ekskul
                    WHERE ae.dicatat_oleh_id = %s
                """
                params = [guru_id]

                if filters.get('start_date'):
                    sql += " AND ae.tanggal_kegiatan >= %s"
                    params.append(filters['start_date'])
                if filters.get('end_date'):
                    sql += " AND ae.tanggal_kegiatan <= %s"
                    params.append(filters['end_date'])
                if filters.get('id_ekskul'):
                    sql += " AND e.id_ekskul = %s"
                    params.append(filters['id_ekskul'])
                if filters.get('id_murid'):
                    sql += " AND p_murid.id_pengguna = %s"
                    params.append(filters['id_murid'])
                if filters.get('status_kehadiran'):
                    sql += " AND ae.status_kehadiran = %s"
                    params.append(filters['status_kehadiran'])
                
                sql += " ORDER BY ae.tanggal_kegiatan DESC, e.nama_ekskul, p_murid.nama_lengkap"
                
                cursor.execute(sql, tuple(params))
                absensi_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching absensi by guru {guru_id}: {e}")
        finally:
            if conn.open: conn.close()
        return absensi_list

    def get_absensi_by_id(self, id_absensi):
        """
        Mengambil satu data absensi berdasarkan ID primernya.
        """
        conn = self._get_connection()
        absensi_info = None
        try:
            with conn.cursor() as cursor:
                sql = "SELECT *, dicatat_oleh_id as id_guru_pencatat FROM AbsensiEkskul WHERE id_absensi_ekskul = %s"
                cursor.execute(sql, (id_absensi,))
                absensi_info = cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"Error fetching absensi by ID {id_absensi}: {e}")
        finally:
            if conn.open: conn.close()
        return absensi_info

    def update_absensi(self, id_absensi, data_update):
        """
        Memperbarui data absensi yang sudah ada.
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql_parts = []
                params = []
                
                if 'tanggal_kegiatan' in data_update and data_update['tanggal_kegiatan']:
                    sql_parts.append("tanggal_kegiatan = %s")
                    params.append(data_update['tanggal_kegiatan'])
                if 'status_kehadiran' in data_update and data_update['status_kehadiran']:
                    sql_parts.append("status_kehadiran = %s")
                    params.append(data_update['status_kehadiran'])
                if 'jam_kegiatan' in data_update:
                    sql_parts.append("jam_mulai_kegiatan = %s")
                    params.append(data_update['jam_kegiatan'])
                if 'catatan' in data_update:
                    sql_parts.append("catatan = %s")
                    params.append(data_update['catatan'])

                if not sql_parts:
                    return True 

                sql_parts.append("updated_at = NOW()")
                
                sql = f"UPDATE AbsensiEkskul SET {', '.join(sql_parts)} WHERE id_absensi_ekskul = %s"
                params.append(id_absensi)
                
                cursor.execute(sql, tuple(params))
                conn.commit()
                return cursor.rowcount > 0
        except pymysql.MySQLError as e:
            print(f"Error updating absensi {id_absensi}: {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close()

    def get_all_absensi_ekskul_detailed(self, tahun_ajaran_filter=None, ekskul_id_filter=None, murid_id_filter=None, date_filter=None):
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
                        pe.id_pendaftaran_ekskul,
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
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "DELETE FROM AbsensiEkskul WHERE id_absensi_ekskul = %s"
                cursor.execute(sql, (id_absensi_ekskul,))
                conn.commit()
                return cursor.rowcount > 0 
        except pymysql.MySQLError as e:
            print(f"Error in delete_absensi_ekskul for ID {id_absensi_ekskul}: {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close()

    def get_all_pengumuman(self):
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
                    data_pengumuman.get('target_ekskul_id'),
                    data_pengumuman.get('target_peran')
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
                target_peran = data_pengumuman.get('target_peran')
                sql_parts.append("target_peran = %s")
                params.append(target_peran if target_peran and target_peran != "" else None)
                target_ekskul_id = data_pengumuman.get('target_ekskul_id')
                sql_parts.append("target_ekskul_id = %s")
                params.append(target_ekskul_id if target_ekskul_id else None)
                if not sql_parts:
                    return True 
                sql_parts.append("updated_at = NOW()") 
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
                return cursor.rowcount > 0 
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
                            LEFT JOIN Pengguna usr ON pnm.id_pembuat = usr.id_pengguna
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

    def get_counts(self):
        conn = self._get_connection()
        counts = {'users': 0, 'ekskul': 0, 'pengumuman': 0, 'materi_ekskul': 0} 
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as total FROM Pengguna")
                counts['users'] = cursor.fetchone()['total']
                cursor.execute("SELECT COUNT(*) as total FROM Ekstrakurikuler")
                counts['ekskul'] = cursor.fetchone()['total']
                cursor.execute("SELECT COUNT(*) as total FROM Pengumuman")
                counts['pengumuman'] = cursor.fetchone()['total']
                cursor.execute("SELECT COUNT(*) as total FROM MateriEkskul") 
                counts['materi_ekskul'] = cursor.fetchone()['total']
        except pymysql.MySQLError as e:
            print(f"Error getting counts: {e}")
        finally:
            if conn.open: conn.close()
        return counts
    
    def get_tahun_ajaran_aktif(self):
        return "2024/2025" 

    def get_murid_options_for_guru_absen(self, id_guru_pembina, tahun_ajaran_aktif):
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

    def get_all_active_murid(self):
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
        conn = self._get_connection()
        pengumuman_list = []
        try:
            with conn.cursor() as cursor:
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
                cursor.execute(sql, (murid_id, tahun_ajaran))
                pendaftaran_list = cursor.fetchall()
        except pymysql.MySQLError as e:
            print(f"Error fetching pendaftaran by murid ID {murid_id} for TA {tahun_ajaran}: {e}")
        finally:
            if conn.open: conn.close()
        return pendaftaran_list
    
    def get_my_attendance_records(self, murid_id, tahun_ajaran):
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
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "DELETE FROM PendaftaranEkskul WHERE id_pendaftaran_ekskul = %s"
                cursor.execute(sql, (pendaftaran_id,))
                conn.commit()
                return cursor.rowcount > 0 
        except pymysql.MySQLError as e:
            print(f"Error deleting pendaftaran ekskul by ID {pendaftaran_id}: {e}")
            conn.rollback()
            return False
        finally:
            if conn.open: conn.close()