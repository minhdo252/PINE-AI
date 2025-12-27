# database.py
import sqlite3
import datetime
import json
import os

DB_NAME = "vnpt_call_center.db"

# --- 20 DATA MẪU (SOURCE OF TRUTH) ---
# Tôi đã gộp 3 nhóm A, B, C của bạn vào đây
INITIAL_DATA = [
  {"customer_id": "CUS_001", "call_id": "CALL_0001", "call_timestamp": "2025-01-20T08:15:00+07:00", "call_duration_seconds": 78, "intent": "network_issue", "sentiment": "positive", "ai_resolved": True, "upsell_success": False, "csat": 5, "cost_per_call_vnd": 2350},
  {"customer_id": "CUS_002", "call_id": "CALL_0002", "call_timestamp": "2025-01-20T08:35:00+07:00", "call_duration_seconds": 92, "intent": "cancel_package", "sentiment": "neutral", "ai_resolved": True, "upsell_success": True, "csat": 4, "cost_per_call_vnd": 2480},
  {"customer_id": "CUS_003", "call_id": "CALL_0003", "call_timestamp": "2025-01-20T09:05:00+07:00", "call_duration_seconds": 110, "intent": "competitor", "sentiment": "negative", "ai_resolved": False, "upsell_success": False, "csat": 3, "cost_per_call_vnd": 2650},
  {"customer_id": "CUS_004", "call_id": "CALL_0004", "call_timestamp": "2025-01-20T09:40:00+07:00", "call_duration_seconds": 70, "intent": "network_issue", "sentiment": "positive", "ai_resolved": True, "upsell_success": False, "csat": 5, "cost_per_call_vnd": 2300},
  {"customer_id": "CUS_005", "call_id": "CALL_0005", "call_timestamp": "2025-01-20T10:10:00+07:00", "call_duration_seconds": 88, "intent": "cancel_package", "sentiment": "neutral", "ai_resolved": True, "upsell_success": True, "csat": 4, "cost_per_call_vnd": 2450},
  {"customer_id": "CUS_006", "call_id": "CALL_0006", "call_timestamp": "2025-01-20T10:45:00+07:00", "call_duration_seconds": 80, "intent": "network_issue", "sentiment": "positive", "ai_resolved": True, "upsell_success": False, "csat": 5, "cost_per_call_vnd": 2380},
  {"customer_id": "CUS_007", "call_id": "CALL_0007", "call_timestamp": "2025-01-18T14:20:00+07:00", "call_duration_seconds": 95, "intent": "cancel_package", "sentiment": "neutral", "ai_resolved": True, "upsell_success": True, "csat": 4, "cost_per_call_vnd": 2500},
  {"customer_id": "CUS_008", "call_id": "CALL_0008", "call_timestamp": "2025-01-18T16:05:00+07:00", "call_duration_seconds": 72, "intent": "network_issue", "sentiment": "positive", "ai_resolved": True, "upsell_success": False, "csat": 5, "cost_per_call_vnd": 2320},
  {"customer_id": "CUS_009", "call_id": "CALL_0009", "call_timestamp": "2025-01-17T10:30:00+07:00", "call_duration_seconds": 105, "intent": "competitor", "sentiment": "negative", "ai_resolved": False, "upsell_success": False, "csat": 3, "cost_per_call_vnd": 2680},
  {"customer_id": "CUS_010", "call_id": "CALL_0010", "call_timestamp": "2025-01-17T15:10:00+07:00", "call_duration_seconds": 85, "intent": "network_issue", "sentiment": "positive", "ai_resolved": True, "upsell_success": False, "csat": 5, "cost_per_call_vnd": 2400},
  {"customer_id": "CUS_011", "call_id": "CALL_0011", "call_timestamp": "2025-01-16T09:45:00+07:00", "call_duration_seconds": 90, "intent": "cancel_package", "sentiment": "neutral", "ai_resolved": True, "upsell_success": True, "csat": 4, "cost_per_call_vnd": 2480},
  {"customer_id": "CUS_012", "call_id": "CALL_0012", "call_timestamp": "2025-01-16T11:20:00+07:00", "call_duration_seconds": 76, "intent": "network_issue", "sentiment": "positive", "ai_resolved": True, "upsell_success": False, "csat": 5, "cost_per_call_vnd": 2350},
  {"customer_id": "CUS_013", "call_id": "CALL_0013", "call_timestamp": "2025-01-15T14:55:00+07:00", "call_duration_seconds": 108, "intent": "competitor", "sentiment": "negative", "ai_resolved": False, "upsell_success": False, "csat": 3, "cost_per_call_vnd": 2620},
  {"customer_id": "CUS_014", "call_id": "CALL_0014", "call_timestamp": "2025-01-15T16:40:00+07:00", "call_duration_seconds": 82, "intent": "network_issue", "sentiment": "positive", "ai_resolved": True, "upsell_success": False, "csat": 5, "cost_per_call_vnd": 2380},
  {"customer_id": "CUS_015", "call_id": "CALL_0015", "call_timestamp": "2025-01-10T10:15:00+07:00", "call_duration_seconds": 88, "intent": "cancel_package", "sentiment": "neutral", "ai_resolved": True, "upsell_success": True, "csat": 4, "cost_per_call_vnd": 2450},
  {"customer_id": "CUS_016", "call_id": "CALL_0016", "call_timestamp": "2025-01-08T14:30:00+07:00", "call_duration_seconds": 74, "intent": "network_issue", "sentiment": "positive", "ai_resolved": True, "upsell_success": False, "csat": 5, "cost_per_call_vnd": 2350},
  {"customer_id": "CUS_017", "call_id": "CALL_0017", "call_timestamp": "2025-01-05T09:50:00+07:00", "call_duration_seconds": 112, "intent": "competitor", "sentiment": "negative", "ai_resolved": False, "upsell_success": False, "csat": 3, "cost_per_call_vnd": 2700},
  {"customer_id": "CUS_018", "call_id": "CALL_0018", "call_timestamp": "2025-01-04T15:05:00+07:00", "call_duration_seconds": 80, "intent": "network_issue", "sentiment": "positive", "ai_resolved": True, "upsell_success": False, "csat": 5, "cost_per_call_vnd": 2380},
  {"customer_id": "CUS_019", "call_id": "CALL_0019", "call_timestamp": "2025-01-03T11:40:00+07:00", "call_duration_seconds": 96, "intent": "cancel_package", "sentiment": "neutral", "ai_resolved": True, "upsell_success": True, "csat": 4, "cost_per_call_vnd": 2500},
  {"customer_id": "CUS_020", "call_id": "CALL_0020", "call_timestamp": "2024-12-28T16:10:00+07:00", "call_duration_seconds": 85, "intent": "network_issue", "sentiment": "positive", "ai_resolved": True, "upsell_success": False, "csat": 5, "cost_per_call_vnd": 2400}
]

class Database:
    def __init__(self):
        self.conn = None
        self._init_db()

    def _get_conn(self):
        # Kết nối tới file SQLite, check_same_thread=False để dùng với FastAPI async
        return sqlite3.connect(DB_NAME, check_same_thread=False)

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Tạo bảng nếu chưa có
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id TEXT,
                call_id TEXT,
                call_timestamp DATETIME,
                duration INTEGER,
                intent TEXT,
                sentiment TEXT,
                ai_resolved BOOLEAN,
                upsell BOOLEAN,
                csat INTEGER,
                cost INTEGER
            )
        ''')
        
        # Kiểm tra xem có dữ liệu chưa
        cursor.execute("SELECT count(*) FROM calls")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print(" [DB] Database trống. Đang nạp 20 bản ghi mẫu...")
            self._seed_data(cursor)
            conn.commit()
        
        conn.close()

    def _seed_data(self, cursor):
        for item in INITIAL_DATA:
            cursor.execute('''
                INSERT INTO calls (customer_id, call_id, call_timestamp, duration, intent, sentiment, ai_resolved, upsell, csat, cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['customer_id'],
                item['call_id'],
                item['call_timestamp'],
                item['call_duration_seconds'],
                item['intent'],
                item['sentiment'],
                item['ai_resolved'],
                item['upsell_success'],
                item['csat'],
                item['cost_per_call_vnd']
            ))

    # --- HÀM THÊM MỚI (Dùng cho Live Call) ---
    def add_call(self, customer_id, duration, intent, sentiment, ai_resolved, upsell, cost):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Tạo call_id tự động (LIVE_timestamp)
        call_id = f"LIVE_{int(datetime.datetime.now().timestamp())}"
        timestamp = datetime.datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO calls (customer_id, call_id, call_timestamp, duration, intent, sentiment, ai_resolved, upsell, csat, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (customer_id, call_id, timestamp, duration, intent, sentiment, ai_resolved, upsell, cost['csat'], cost['value']))
        # Lưu ý: tham số cost ở đây tôi tách ra dict csat/value ở logic_flow (xem bước 2)
        
        conn.commit()
        conn.close()
    # [THÊM MỚI] Hàm cập nhật đánh giá thực tế từ người dùng
    def update_call_rating(self, customer_id, stars, note):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 1. Tìm ID cuộc gọi mới nhất của khách hàng này
            cursor.execute('''
                SELECT id FROM calls 
                WHERE customer_id = ? 
                ORDER BY call_timestamp DESC 
                LIMIT 1
            ''', (str(customer_id),))
            
            row = cursor.fetchone()
            
            if row:
                call_id_db = row[0]
                # 2. Cập nhật điểm CSAT và ghi chú (nếu muốn lưu note thì cần thêm cột note vào bảng, tạm thời ta chỉ update CSAT)
                # Lưu ý: Nếu bạn muốn lưu cả 'note', bạn cần ALTER TABLE hoặc tạo lại DB mới có cột 'note'.
                # Ở đây tôi giả định chỉ update CSAT cho đơn giản.
                cursor.execute('''
                    UPDATE calls 
                    SET csat = ? 
                    WHERE id = ?
                ''', (int(stars), call_id_db))
                
                conn.commit()
                print(f" [DB] Đã cập nhật CSAT={stars} cho khách {customer_id} (DB ID: {call_id_db})")
            else:
                print(f" [DB] Không tìm thấy cuộc gọi nào của khách {customer_id} để update.")
                
        except Exception as e:
            print(f" [DB Error] Update Rating: {e}")
        finally:
            conn.close()
    # --- HÀM LẤY DỮ LIỆU CHO DASHBOARD ---
    def get_all_calls(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Lấy tất cả, sắp xếp mới nhất lên đầu
        cursor.execute("SELECT * FROM calls ORDER BY call_timestamp DESC")
        rows = cursor.fetchall()
        
        # Convert tuple sang list of dict để trả về JSON
        result = []
        for r in rows:
            result.append({
                "id": r[1],          # customer_id
                "time": r[3],        # timestamp
                "dur": r[4],         # duration
                "intent": r[5],
                "sent": r[6],
                "ai": bool(r[7]),
                "upsell": bool(r[8]),
                "csat": r[9],
                "cost": r[10]
            })
        
        conn.close()
        return result

# Khởi tạo singleton
db = Database()