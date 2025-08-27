from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
from selenium.webdriver.chrome.webdriver import WebDriver
from util.save_to_json import save_dict_to_json

class HahowScraper:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 10)
    
    def scroll_page(self):
        """漸進式滾動頁面直到沒有新內容"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        current_position = 0
        scroll_step = 300

        while current_position < last_height:
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(0.5)
            current_position += scroll_step
            last_height = self.driver.execute_script("return document.body.scrollHeight")
    
    def close_dialog_if_present(self):
        """關閉可能出現的對話框"""
        try:
            close_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Close"][data-bs-dismiss="modal"]'))
            )
            close_button.click()
            print("✅ 已關閉對話框")
        except TimeoutException:
            print("✅ 沒有對話框需要關閉")
    
    def extract_course_data(self, card_element):
        """從單個課程卡片提取資料"""
        try:
            course_data = {}
            
            # 提取課程名稱
            try:
                title_element = card_element.find_element(By.CSS_SELECTOR, 'h2')
                course_data["活動名稱"] = title_element.text.strip()
            except:
                course_data["活動名稱"] = "未知課程"
            
            # 提取講師名稱
            try:
                instructor_element = card_element.find_element(By.CSS_SELECTOR, '.sc-cz4ap1-1')
                course_data["講師"] = instructor_element.text.strip()
            except:
                course_data["講師"] = "未知講師"
            
            # 提取評分
            try:
                rating_element = card_element.find_element(By.CSS_SELECTOR, '.sc-wwz27q-2')
                course_data["評分"] = rating_element.text.strip()
            except:
                course_data["評分"] = "無評分"
            
            # 提取評分人數
            try:
                review_count_element = card_element.find_element(By.CSS_SELECTOR, '.sc-wwz27q-3')
                # 移除括號
                review_count = review_count_element.text.strip().replace('(', '').replace(')', '')
                course_data["評分人數"] = review_count
            except:
                course_data["評分人數"] = "0"
            
            # 提取課程時長
            try:
                duration_element = card_element.find_element(By.CSS_SELECTOR, '.sc-fhisnz-2')
                course_data["時間"] = duration_element.text.strip()
            except:
                course_data["時間"] = "未知時長"
            
            # 提取學員人數
            try:
                student_count_element = card_element.find_element(By.CSS_SELECTOR, '.sc-1xpurhu-2')
                course_data["學員人數"] = student_count_element.text.strip()
            except:
                course_data["學員人數"] = "0"
            
            # 提取價格
            try:
                price_element = card_element.find_element(By.CSS_SELECTOR, '.sc-jl1t82-3')
                price_text = price_element.text.strip()
                course_data["費用"] = price_text
            except:
                course_data["費用"] = "價格未知"
            
            # 提取課程連結
            try:
                link_element = card_element.find_element(By.XPATH, '//a[contains(@href, "/courses/")]')
                href = link_element.get_attribute('href')
                print('連結',href)
                course_data["課程連結"] = href if href else "無連結"
            except:
                course_data["課程連結"] = "無連結"
            
            # 檢查是否為熱門課程
            try:
                popular_tag = card_element.find_element(By.CSS_SELECTOR, '[data-testid="popularFeatureTag"]')
                course_data["標籤"] = ["熱門課程"]
            except:
                course_data["標籤"] = []
            
            # 提取課程圖片
            try:
                img_element = card_element.find_element(By.CSS_SELECTOR, 'img')
                course_data["課程圖片"] = img_element.get_attribute('src')
            except:
                course_data["課程圖片"] = "無圖片"
            
            return course_data
            
        except Exception as e:
            print(f"提取課程資料時出錯: {e}")
            return None

    def scrape_courses(self):
        """漸進式滑動頁面並爬取課程資料"""
        try:
            courses_data = []
            seen_urls = set()  # 用 URL 來判斷是否重複
            scroll_step = 500
            max_no_new_data_scrolls = 5
            no_new_data_count = 0
            
            print("開始爬取課程資料...")

            while True:
                # 滾動頁面
                self.driver.execute_script(f"window.scrollBy(0, {scroll_step});")
                time.sleep(2)  # 等待資料載入

                # 取得目前所有課程卡片
                course_cards = self.driver.find_elements(By.CSS_SELECTOR, 'a[data-testid="salesProductCard"]')
                
                # 檢查是否有新的課程卡片
                current_urls = set()
                for card in course_cards:
                    try:
                        url = card.get_attribute('href')
                        if url:
                            current_urls.add(url)
                    except:
                        continue

                new_urls = current_urls - seen_urls
                
                if not new_urls:
                    no_new_data_count += 1
                    print(f"第 {no_new_data_count} 次滑動沒有新資料...")
                else:
                    no_new_data_count = 0
                    seen_urls.update(new_urls)
                    print(f"發現 {len(new_urls)} 個新課程，總計 {len(seen_urls)} 個課程")

                if no_new_data_count >= max_no_new_data_scrolls:
                    print("連續多次沒有新資料，停止滑動")
                    break

            print(f"滑動完成，開始提取 {len(seen_urls)} 個課程的詳細資料...")

            # 重新獲取所有課程卡片並提取資料
            course_cards = self.driver.find_elements(By.CSS_SELECTOR, 'a[data-testid="salesProductCard"]')
            
            for i, card in enumerate(course_cards):
                try:
                    course_data = self.extract_course_data(card)
                    if course_data:
                        course_data["序號"] = i + 1
                        if course_data['活動名稱'] != '':
                            courses_data.append(course_data)
                        if (i + 1) % 10 == 0:
                            print(f"已處理 {i + 1} 個課程...")
                except Exception as e:
                    print(f"處理第 {i + 1} 個課程時出錯: {e}")
                    continue

            print(f"✅ 成功爬取 {len(courses_data)} 個課程資料")
            return courses_data

        except Exception as e:
            print(f"❌ 爬取課程時出錯: {e}")
            return []


if __name__ == '__main__':
    # 設置Chrome選項
    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    # 如果不想看到瀏覽器視窗，可以啟用無頭模式
    # chrome_options.add_argument('--headless')

    # 建立 driver
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # 可以爬取的分類清單
        categories = [
            "language",
            "music",
            "photography",
            "art",
            "humanities",
            "marketing",
            "programming",
            "finance-and-investment",
            "career-skills",
            "handmade",
            "lifestyle"
        ]

        total_courses = []

        for category in categories:
            print(f"\n🚀 開始爬取分類: {category}")
            
            # 前往分類頁面
            url = f"https://hahow.in/group/{category}"
            driver.get(url)
            
            # 等待頁面載入
            time.sleep(3)
            
            # 建立爬蟲實例
            scraper = HahowScraper(driver)
            
            # 關閉可能的對話框
            scraper.close_dialog_if_present()
            
            # 爬取課程資料
            courses = scraper.scrape_courses()
            
            # 為每個課程添加分類資訊
            for course in courses:
                course["分類"] = category
            
            total_courses.extend(courses)
            
            # 保存單個分類的資料
            # scraper.save_to_json(courses, category)
            
            print(f"✅ 分類 {category} 完成，共 {len(courses)} 個課程")
            
            # 短暫休息避免請求過於頻繁
            time.sleep(2)

        # 保存所有課程資料
        if total_courses:
            scraper = HahowScraper(driver)
            save_dict_to_json(total_courses, "all_courses")
            print(f"\n🎉 全部完成！總共爬取 {len(total_courses)} 個課程")
        
    except Exception as e:
        print(f"❌ 程式執行出錯: {e}")
    
    finally:
        # 關閉瀏覽器
        driver.quit()
        print("🔚 瀏覽器已關閉")