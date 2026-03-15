"""
数据存储和状态对比模块
负责保存和读取稿件状态，检测变化，并定期清理旧数据
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ManuscriptStorage:
    """稿件存储类"""
    
    def __init__(self, data_file: str):
        self.data_file = data_file
        self._ensure_data_dir()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        data_dir = os.path.dirname(self.data_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
    
    def load_manuscripts(self) -> Dict:
        """加载已保存的稿件数据"""
        if not os.path.exists(self.data_file):
            return {}
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  读取数据文件失败: {e}")
            return {}
    
    def save_manuscripts(self, manuscripts: Dict):
        """保存稿件数据"""
        try:
            # 在保存前进行清理：删除超过 7 天未更新的稿件记录
            cleaned_data = self._cleanup_old_records(manuscripts)
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 数据已保存到 {self.data_file}")
        except Exception as e:
            print(f"❌ 保存数据失败: {e}")

    def _cleanup_old_records(self, manuscripts: Dict, days: int = 7) -> Dict:
        """
        清理超过指定天数未更新的稿件记录
        
        Args:
            manuscripts: 稿件数据字典
            days: 保留的天数，默认 7 天
            
        Returns:
            清理后的稿件数据字典
        """
        cleaned_data = {}
        now = datetime.now()
        threshold = now - timedelta(days=days)
        
        removed_count = 0
        for key, data in manuscripts.items():
            last_checked_str = data.get('last_checked')
            if not last_checked_str:
                cleaned_data[key] = data
                continue
                
            try:
                last_checked = datetime.strptime(last_checked_str, '%Y-%m-%d %H:%M:%S')
                if last_checked >= threshold:
                    cleaned_data[key] = data
                else:
                    removed_count += 1
                    print(f"🗑️  清理过期记录: {data.get('title', '未知标题')} (最后更新: {last_checked_str})")
            except ValueError:
                # 如果日期格式不对，保留数据以防误删
                cleaned_data[key] = data
        
        if removed_count > 0:
            print(f"🧹 共清理了 {removed_count} 条超过 {days} 天未更新的记录")
            
        return cleaned_data
    
    def compare_and_update(self, new_manuscripts: List[Dict]) -> List[Dict]:
        """
        对比新旧稿件状态，返回有变化的稿件
        
        Args:
            new_manuscripts: 新获取的稿件列表
        
        Returns:
            有状态变化的稿件列表
        """
        old_data = self.load_manuscripts()
        changed_manuscripts = []
        updated_data = old_data.copy() # 保留旧数据，以便进行增量更新和清理
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for manuscript in new_manuscripts:
            manuscript_id = manuscript.get('id')
            title = manuscript.get('title', '未知标题')
            current_status = manuscript.get('status', '未知状态')
            source = manuscript.get('source', '未知来源')
            
            # 构建唯一键
            key = f"{source}_{manuscript_id}"
            
            # 检查是否有旧记录
            if key in old_data:
                old_status = old_data[key].get('status')
                
                # 状态发生变化
                if old_status != current_status:
                    changed_manuscripts.append({
                        'id': manuscript_id,
                        'title': title,
                        'source': source,
                        'old_status': old_status,
                        'new_status': current_status,
                        'changed_at': current_time,
                        'url': manuscript.get('url', '')
                    })
                    print(f"📝 检测到状态变化: {title}")
                    print(f"   {old_status} → {current_status}")
            else:
                # 新稿件
                print(f"🆕 发现新稿件: {title} ({current_status})")
            
            # 更新数据
            updated_data[key] = {
                'id': manuscript_id,
                'title': title,
                'status': current_status,
                'source': source,
                'url': manuscript.get('url', ''),
                'last_checked': current_time,
                'first_seen': old_data.get(key, {}).get('first_seen', current_time)
            }
        
        # 保存更新后的数据（save_manuscripts 内部会调用 _cleanup_old_records）
        self.save_manuscripts(updated_data)
        
        return changed_manuscripts
    
    def get_all_manuscripts(self) -> List[Dict]:
        """获取所有稿件列表"""
        data = self.load_manuscripts()
        return list(data.values())
    
    def clear_data(self):
        """清空数据（用于测试）"""
        if os.path.exists(self.data_file):
            os.remove(self.data_file)
            print(f"🗑️  已清空数据文件: {self.data_file}")
