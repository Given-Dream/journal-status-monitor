"""
期刊状态监控主程序
负责登录IEEE和Elsevier，获取稿件状态，并根据时间发送每日报告或变化通知
"""
import time
import os
from typing import List, Dict, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from config import Config
from storage import ManuscriptStorage
from notification import EmailNotifier


class JournalMonitor:
    """期刊监控类"""
    
    def __init__(self):
        self.config = Config
        self.storage = ManuscriptStorage(Config.DATA_FILE)
        self.notifier = EmailNotifier()
        self.driver = None
    
    def _init_driver(self):
        """初始化浏览器驱动"""
        print("🌐 初始化浏览器...")
        
        chrome_options = Options()
        
        if self.config.HEADLESS:
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
        
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.implicitly_wait(10)
        
        print("✅ 浏览器初始化完成")
    
    def _close_driver(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            print("🔒 浏览器已关闭")
    
    def fetch_ieee_manuscripts(self) -> List[Dict]:
        """获取IEEE稿件列表"""
        if not self.config.IEEE_EMAIL or not self.config.IEEE_PASSWORD:
            print("⚠️  未配置IEEE账户，跳过")
            return []
        
        print("\n" + "=" * 50)
        print("📚 开始获取IEEE稿件状态...")
        print("=" * 50)
        
        manuscripts = []
        
        try:
            # 访问ScholarOne登录页面
            print("🔗 访问ScholarOne登录页面...")
            login_url = self.config.IEEE_URL
            print(f"🎯 目标网址: {login_url}")
            
            self.driver.get(login_url)
            time.sleep(2)
            
            # 输入用户名
            print("📝 输入登录信息...")
            try:
                # 尝试多种方式查找用户名输入框
                email_input = None
                try:
                    email_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.ID, "login"))
                    )
                except:
                    try:
                        email_input = self.driver.find_element(By.NAME, "login")
                    except:
                        try:
                            email_input = self.driver.find_element(By.XPATH, "//input[@type='text' or @type='email']")
                        except:
                            email_input = self.driver.find_element(By.XPATH, "//input[contains(@placeholder, 'User') or contains(@placeholder, 'ID')]")
                
                email_input.clear()
                email_input.send_keys(self.config.IEEE_EMAIL)
                print("✅ 用户名已输入")
                
                # 输入密码
                password_input = None
                try:
                    password_input = self.driver.find_element(By.ID, "password")
                except:
                    try:
                        password_input = self.driver.find_element(By.NAME, "password")
                    except:
                        password_input = self.driver.find_element(By.XPATH, "//input[@type='password']")
                
                password_input.clear()
                password_input.send_keys(self.config.IEEE_PASSWORD)
                print("✅ 密码已输入")
                
                # 点击登录按钮
                login_button = None
                try:
                    login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Log In')]")
                    print("✅ 通过按钮文本找到登录按钮")
                except:
                    try:
                        login_button = self.driver.find_element(By.XPATH, "//input[@value='Log In']")
                        print("✅ 通过input value找到登录按钮")
                    except:
                        try:
                            login_button = self.driver.find_element(By.NAME, "login")
                            print("✅ 通过name属性找到登录按钮")
                        except:
                            try:
                                buttons = self.driver.find_elements(By.XPATH, "//button | //input[@type='submit'] | //input[@type='button']")
                                for btn in buttons:
                                    btn_text = btn.text or btn.get_attribute('value') or ''
                                    if 'log in' in btn_text.lower():
                                        login_button = btn
                                        print(f"✅ 通过遍历找到登录按钮: {btn_text}")
                                        break
                                if not login_button:
                                    raise Exception("未找到登录按钮")
                            except:
                                print("⚠️  未找到登录按钮，尝试按Enter键")
                                password_input.send_keys("\n")
                                login_button = None
                
                if login_button:
                    login_button.click()
                    print("✅ 已点击登录按钮")
                else:
                    print("✅ 已按Enter键提交")
                
            except Exception as e:
                print(f"❌ 登录输入失败: {e}")
                print(f"📝 当前页面标题: {self.driver.title}")
                print(f"🔗 当前页面URL: {self.driver.current_url}")
                raise
            
            print("⏳ 等待登录...")
            time.sleep(5)
            
            # 检查是否登录成功
            if "ScholarOne" in self.driver.title or "Manuscripts" in self.driver.title:
                print("✅ IEEE登录成功")
                
                # 点击Author按钮进入作者仪表板
                print("👉 点击Author按钮...")
                try:
                    author_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.LINK_TEXT, "Author"))
                    )
                    author_button.click()
                    time.sleep(5)
                    print("✅ 已进入作者仪表板")
                except Exception as e:
                    print(f"⚠️  未找到Author按钮，尝试其他方式: {e}")
                    try:
                        author_link = self.driver.find_element(By.XPATH, "//a[contains(text(), 'Author') or contains(@href, 'author')]")
                        author_link.click()
                        time.sleep(5)
                    except:
                        print("⚠️  无法找到Author入口，尝试直接查找稿件")
                
                # 查找稿件列表
                print("🔍 正在查找稿件...")
                time.sleep(2)
                
                try:
                    # 查找表格行
                    manuscript_rows = self.driver.find_elements(By.XPATH, "//table//tr[@class='data' or @class='data-even' or @class='data-odd']")
                    if not manuscript_rows:
                        manuscript_rows = self.driver.find_elements(By.XPATH, "//table//tr[contains(@class, 'manuscript')]")
                    if not manuscript_rows:
                        all_rows = self.driver.find_elements(By.XPATH, "//table//tr[td]")
                        manuscript_rows = [row for row in all_rows if len(row.find_elements(By.TAG_NAME, "td")) >= 5]
                    
                    print(f"📄 找到 {len(manuscript_rows)} 行数据")
                    
                    for idx, row in enumerate(manuscript_rows):
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            if len(cells) < 5:
                                continue
                            
                            # 提取状态 (列2)
                            status_cell = cells[2]
                            status = "未知状态"
                            status_elements = status_cell.find_elements(By.XPATH, ".//a | .//button | .//span")
                            if status_elements:
                                for elem in status_elements:
                                    elem_text = elem.text.strip()
                                    if elem_text and elem_text not in ['Contact Journal', 'EIC:', 'ADM:']:
                                        status = elem_text
                            else:
                                status = status_cell.text.strip()
                            
                            # 提取ID (列3)
                            id_cell = cells[3]
                            manuscript_id = id_cell.text.strip()
                            if not manuscript_id:
                                id_elements = id_cell.find_elements(By.XPATH, ".//*")
                                for elem in id_elements:
                                    if elem.text.strip():
                                        manuscript_id = elem.text.strip()
                                        break
                            
                            # 提取标题 (列4)
                            title_cell = cells[4]
                            title = title_cell.text.strip()
                            if not title:
                                title_elements = title_cell.find_elements(By.XPATH, ".//a | .//span | .//div")
                                for elem in title_elements:
                                    if len(elem.text.strip()) > 5:
                                        title = elem.text.strip()
                                        break
                            
                            if manuscript_id and title:
                                manuscripts.append({
                                    'id': manuscript_id,
                                    'title': title,
                                    'status': status,
                                    'source': 'IEEE',
                                    'url': self.driver.current_url
                                })
                                print(f"  ✓ [{status}] {manuscript_id}: {title[:50]}...")
                            
                        except Exception as e:
                            print(f"  ❌ 解析行 {idx+1} 失败: {e}")
                            
                except Exception as e:
                    print(f"❌ 查找稿件列表失败: {e}")
            else:
                print(f"❌ 登录后页面标题不匹配: {self.driver.title}")
                
        except Exception as e:
            print(f"❌ 获取IEEE稿件失败: {e}")
            
        return manuscripts

    def fetch_elsevier_manuscripts(self) -> List[Dict]:
        """获取Elsevier稿件列表 (预留接口)"""
        if not self.config.ELSEVIER_EMAIL or not self.config.ELSEVIER_PASSWORD:
            print("⚠️  未配置Elsevier账户，跳过")
            return []
        
        # 目前主要支持IEEE，Elsevier逻辑可根据具体期刊页面进一步定制
        print("\n⚠️  Elsevier 自动获取功能暂未完全实现，请根据具体期刊页面定制。")
        return []

    def run(self):
        """执行监控任务"""
        try:
            self._init_driver()
            
            all_new_manuscripts = []
            
            # 获取IEEE稿件
            ieee_manuscripts = self.fetch_ieee_manuscripts()
            all_new_manuscripts.extend(ieee_manuscripts)
            
            # 获取Elsevier稿件
            elsevier_manuscripts = self.fetch_elsevier_manuscripts()
            all_new_manuscripts.extend(elsevier_manuscripts)
            
            print("\n" + "=" * 50)
            print(f"📊 本次共获取 {len(all_new_manuscripts)} 篇稿件")
            print("=" * 50)
            
            if not all_new_manuscripts:
                print("⚠️  未获取到任何稿件，请检查账户配置或页面结构")
                return

            # 对比状态变化并保存（保存时会自动清理超过7天的旧记录）
            print("🔍 正在对比状态变化...")
            changed_manuscripts = self.storage.compare_and_update(all_new_manuscripts)
            
            # 获取所有当前稿件（用于每日报告）
            current_all_manuscripts = self.storage.get_all_manuscripts()
            
            # 邮件通知逻辑
            is_daily_report = os.getenv('DAILY_REPORT', 'false').lower() == 'true'
            
            if is_daily_report:
                print("📊 每日报告模式：发送所有稿件状态")
                self.notifier.send_daily_report(current_all_manuscripts)
            elif changed_manuscripts:
                print(f"📬 检测到 {len(changed_manuscripts)} 篇稿件状态变化，发送通知邮件")
                self.notifier.send_change_notification(changed_manuscripts)
            else:
                print("✅ 所有稿件状态无变化，无需发送邮件")
                
            print("\n" + "✅" * 25)
            print("监控任务完成")
            print("✅" * 25)
            
        except Exception as e:
            print(f"❌ 监控任务执行失败: {e}")
        finally:
            self._close_driver()


if __name__ == "__main__":
    monitor = JournalMonitor()
    monitor.run()
