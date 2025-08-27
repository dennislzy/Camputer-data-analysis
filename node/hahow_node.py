from langchain_core.tools import tool
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from urllib.parse import quote
import time

@tool
def scrape_hahow_courses(category: str, max_results: int = 3) -> list:
    """
    爬取 Hahow 網站上指定類別的課程資料
    
    參數:
        category (str): 課程類別關鍵字 (如: "程式設計", "設計", "語言學習" 等)
        max_results (int): 要獲取的課程數量，預設為3
    
    回傳:
        list: 包含課程詳細資料的列表
    """
    
    # 設置 Chrome 選項
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = None
    
    try:
        # 初始化 WebDriver
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.set_page_load_timeout(30)
        
        # 搜尋 URL
        encoded_category = quote(category)
        search_url = f"https://hahow.in/search?query={encoded_category}"
        
        # 載入頁面
        driver.get(search_url)
        
        # 等待頁面載入完成
        wait = WebDriverWait(driver, 20)
        
        # 等待課程卡片出現
        try:
            course_elements = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[data-testid="salesProductCard"]'))
            )
            
        except TimeoutException:
            # 備用選擇器
            alternative_selectors = [
                'a[href*="/courses/"]',
                '.sc-182wmlr-0',
                '[class*="salesProductCard"]'
            ]
            
            course_elements = []
            for selector in alternative_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        course_elements = elements
                        break
                except:
                    continue
        
        if not course_elements:
            return []
        
        courses_data = []
        processed_urls = set()
        
        for i, element in enumerate(course_elements[:max_results]):
            try:
                course_info = extract_course_info(element)
                
                if course_info and course_info.get('url') and course_info['url'] not in processed_urls:
                    courses_data.append(course_info)
                    processed_urls.add(course_info['url'])
                
                time.sleep(0.5)
                
            except Exception as e:
                continue
        
        return courses_data
        
    except Exception as e:
        return []
    finally:
        if driver:
            driver.quit()

def extract_course_info(element):
    """
    提取課程資訊
    """
    course_info = {}
    
    try:
        # 獲取課程連結
        href = element.get_attribute('href')
        if not href:
            return None
        
        course_info['url'] = href
        
        # 獲取課程標題
        try:
            title_element = element.find_element(By.CSS_SELECTOR, 'h2')
            title = title_element.text.strip()
            if title.startswith('課程'):
                title = title[2:].strip()
            course_info['title'] = title
        except:
            course_info['title'] = '未取得標題'
        
        # 獲取講師資訊
        try:
            instructor_element = element.find_element(By.CSS_SELECTOR, '.sc-cz4ap1-1')
            course_info['instructor'] = instructor_element.text.strip()
        except:
            course_info['instructor'] = '未知講師'
        
        # 獲取評分
        try:
            rating_element = element.find_element(By.CSS_SELECTOR, '.sc-wwz27q-2')
            rating_count_element = element.find_element(By.CSS_SELECTOR, '.sc-wwz27q-3')
            rating = rating_element.text.strip()
            rating_count = rating_count_element.text.strip()
            course_info['rating'] = f"{rating} {rating_count}"
        except:
            course_info['rating'] = '無評分'
        
        # 獲取課程時長
        try:
            duration_element = element.find_element(By.CSS_SELECTOR, '.sc-fhisnz-2')
            course_info['duration'] = duration_element.text.strip()
        except:
            course_info['duration'] = '未知時長'
        
        # 獲取學生人數
        try:
            students_element = element.find_element(By.CSS_SELECTOR, '.sc-1xpurhu-2')
            course_info['students'] = f"{students_element.text.strip()} 人"
        except:
            course_info['students'] = '未知人數'
        
        # 獲取價格
        try:
            price_element = element.find_element(By.CSS_SELECTOR, '.sc-jl1t82-0')
            price_text = price_element.text.strip()
            course_info['price'] = price_text
        except:
            course_info['price'] = '未知價格'
        
        
        return course_info
        
    except Exception as e:
        return None