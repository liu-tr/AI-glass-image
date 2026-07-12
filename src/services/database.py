import json
import os
from datetime import datetime


class JSONDatabase:
    def __init__(self, db_path="data/designs.json"):
        self.db_path = db_path
        self._ensure_dir()

    def _ensure_dir(self):
        """确保数据目录及文件存在"""
        dir_name = os.path.dirname(self.db_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        if not os.path.exists(self.db_path):
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False)

    def _read(self):
        with open(self.db_path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)

    def _write(self, data):
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_design(self, prompt, images):
        """添加新设计方案"""
        design = {
            "id": f"design_{int(datetime.now().timestamp() * 1000)}",
            "prompt": prompt,
            "images": images,
            "selected_image": None,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "optimization_result": None
        }
        data = self._read()
        data.append(design)
        self._write(data)
        return design

    def get_design(self, design_id):
        """获取单个设计方案"""
        data = self._read()
        return next((d for d in data if d["id"] == design_id), None)

    def update_design(self, design_id, updates):
        """更新设计方案"""
        data = self._read()
        for d in data:
            if d["id"] == design_id:
                d.update(updates)
                break
        self._write(data)

    def delete_design(self, design_id):
        """删除设计方案"""
        data = self._read()
        data = [d for d in data if d["id"] != design_id]
        self._write(data)

    def get_all_designs(self):
        """获取所有设计方案"""
        return self._read()
