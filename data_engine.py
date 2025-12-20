import pandas as pd
import json
import os

class DataEngine:
    def __init__(self, csv_path="test_customer.csv", json_path="product_collection.json"):
        self.csv_path = csv_path
        self.json_path = json_path
        self.products = {}
        self.customers_df = None
        self._load_data()

    def _load_data(self):
        # 1. Nạp JSON Sản phẩm
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                product_list = json.load(f)
                self.products = {item['id']: item for item in product_list}
            print("✅ [DataEngine] Đã nạp JSON gói cước.")
        except Exception as e:
            print(f"❌ [DataEngine] Lỗi JSON: {e}")

        # 2. Nạp CSV Khách hàng
        try:
            self.customers_df = pd.read_csv(self.csv_path)
            # Ép kiểu Customer ID sang string để tìm kiếm chính xác
            self.customers_df['Customer ID'] = self.customers_df['Customer ID'].astype(str)
            # Xử lý khoảng trắng thừa ở cột id gói cước
            if 'id' in self.customers_df.columns:
                 self.customers_df['id'] = self.customers_df['id'].astype(str).str.strip()
            print("✅ [DataEngine] Đã nạp CSV khách hàng.")
        except Exception as e:
            print(f"❌ [DataEngine] Lỗi CSV: {e}")

    def get_full_context(self, customer_id):
        if self.customers_df is None: return None

        str_id = str(customer_id).strip()
        row = self.customers_df[self.customers_df['Customer ID'] == str_id]
        
        if row.empty:
            return None
        
        customer_data = row.iloc[0].to_dict()
        
        # --- XỬ LÝ LOGIC TÊN GỌI (VÌ CSV KHÔNG CÓ CỘT NAME) ---
        gender = str(customer_data.get('Gender', '')).lower()
        if 'female' in gender:
            display_name = "Chị"
        elif 'male' in gender:
            display_name = "Anh"
        else:
            display_name = "Quý khách"
        
        # Thêm trường hiển thị tên vào dict trả về
        customer_data['Display_Name'] = display_name

        # Lấy thông tin gói cước
        current_pkg_id = str(customer_data.get('id', '')).strip()
        pkg_info = self.products.get(current_pkg_id, {
            "name": f"Gói {current_pkg_id}", 
            "desc": "Không có mô tả",
            "price": 0
        })

        return {
            "customer": customer_data,
            "current_package": pkg_info
        }