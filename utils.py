""" Libraries """
import io
import os
import time
import winsound
import requests
import datetime
import numpy as np
from model import id_to_word, process_image


""" Functions """
class BrowserStuckError(Exception):
    pass


class CourseTakenException(Exception):
    pass


def beep_sound():
    for _ in range(5):
        winsound.Beep(800, 800)
        time.sleep(0.2)
    return


def send_LineNotification(access_token, message):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    params = {"message": message}
    requests.post(
        "https://notify-api.line.me/api/notify",
        headers=headers, params=params
    )
    return


def my_time_str(start_time=None):
    if start_time is not None:
        interval = time.time() - start_time
        return f"{datetime.datetime.now().strftime(f'%H:%M:%S')} | {int(interval//60):>2}min {int(interval%60):>2}sec"
    else:
        return f"{datetime.datetime.now().strftime(f'%H:%M:%S')}"


def read_account():
    try:
        with open("account.txt", "r", encoding="utf-8") as txt_file:
            lines = txt_file.readlines()
            if len(lines) < 3: raise Exception
            username = lines[0].strip('\n')
            password = lines[1].strip('\n')
            courses  = list(filter(lambda id: '#' not in id, [ id.strip('\n').strip() for id in lines[2:] ]))
            if ' ' in courses[0]:
                course_ids   = [ course.split(' ')[0] for course in courses ]
                course_names = [ course.split(' ')[1] for course in courses ]
            else:
                course_ids   = courses
                course_names = None
            return username, password, course_ids, course_names
    except:
        with open("account.txt", "w", encoding="utf-8") as txt_file:
            txt_file.write("UsernameHere\nPasswordHere\nCourse_1_Id Course_1_Name\nCourse_2_Id Course_2_Name...")
        print("\nThe file 'account.txt' are created.")
        print("Please edit it before run this program again.\n")


def wait_until_9_am():
    while True:
        hour = int(datetime.datetime.now().strftime(f'%H'))
        if hour >= 9: break
        os.system("cls")
        print(f"{my_time_str()} | Waiting until 9 AM...\n")
        time.sleep(1)


def wait_to_click(element):
    for _ in range(25):
        try:
            element.click()
            time.sleep(1)
            return
        except:
            time.sleep(0.2)
    raise BrowserStuckError


def wait_for_url(driver, url_content):
    for _ in range(20):
        time.sleep(0.25)
        if url_content in driver.current_url: return
    raise BrowserStuckError


def wait_and_find_element_by_id(driver, id):
    for _ in range(50):
        try:
            element = driver.find_element_by_id(id)
            return element
        except:
            time.sleep(0.2)
    raise BrowserStuckError
    

def wait_appeared_element_by_id(driver):
    for _ in range(30):
        try:
            driver.find_element_by_id("button-1017-btnEl")  # 「下一頁」按鈕
            return True
        except:
            pass
        try:
            driver.find_element_by_id("button-1005-btnEl")  # 「OK」按鈕
            return False
        except:
            time.sleep(0.5)
    raise BrowserStuckError


def wait_element_text_by_id(driver, id, texts):
    for _ in range(100):
        try:
            element = driver.find_element_by_id(id)
            for i, text in enumerate(texts):
                if text in element.text: return i  # return condition id
            raise CourseTakenException
        except:
            time.sleep(0.2)
    raise BrowserStuckError


def wait_for_validate_code_img(driver):
    for _ in range(25):
        if len(driver.find_elements_by_class_name("x-component-default")) == 10:
            return
        time.sleep(0.2)
    raise BrowserStuckError


def wait_for_validate_code_button(driver, button):
    for _ in range(25):
        buttons = driver.find_elements_by_class_name("x-btn-button")
        if len(buttons) == 19:
            if button == "confirm": return buttons[17]
            else                  : return buttons[18]
        time.sleep(0.2)
    raise BrowserStuckError


def get_validate_code_img(driver):
    for request in reversed(driver.requests):
        if "RandImage" in request.url:
            if request.response == None: return None
            else: return process_image(io.BytesIO(request.response.body))
    return None 


def my_predict(model, image):
    image = np.array(np.expand_dims(image, axis=2), dtype=np.float)
    image = np.array([image])
    validate_code = model.predict(image)
    validate_code = np.squeeze(np.argmax(validate_code, axis=2))
    validate_code = [ id_to_word[id] for id in validate_code ]
    return validate_code


number_map = { str(i): i for i in range(10) }
def process_validate_code(validate_code):
    if '=' in validate_code:
        number_1 = number_map[validate_code[0]]
        number_2 = number_map[validate_code[2]]
        if   validate_code[1] == '+': return number_1 + number_2
        elif validate_code[1] == '-': return number_1 - number_2
        elif validate_code[1] == '*': return number_1 * number_2
    else:
        return ''.join(validate_code)


def login(driver, username, password, model):
    driver.get("https://cos3s.ntnu.edu.tw/AasEnrollStudent/LoginCheckCtrl?language=TW")

    # 驗證碼: 正確 或 錯誤
    while True:
        
        # 驗證碼破圖
        validate_code_img_broken_time = 0
        while True:
            validate_code_img = get_validate_code_img(driver)
            if validate_code_img is not None: break
            else:
                wait_to_click(wait_and_find_element_by_id(driver, "redoValidateCodeButton-btnEl"))  # 「重新產生」按鈕
                retry_time = validate_code_img_broken_time * 2 + 3
                print(f"{my_time_str()} - Login: Validate code image broken. Retry in {retry_time} seconds.")
                time.sleep(retry_time)
                validate_code_img_broken_time += 1

        validate_code = my_predict(model, validate_code_img)
        validate_code = process_validate_code(validate_code)
        wait_and_find_element_by_id(driver, "validateCode-inputEl").send_keys(validate_code)

        wait_and_find_element_by_id(driver, "userid-inputEl").clear()
        wait_and_find_element_by_id(driver, "userid-inputEl").send_keys(username)
        wait_and_find_element_by_id(driver, "password-inputEl").send_keys(password)
        wait_to_click(wait_and_find_element_by_id(driver, "button-1016-btnEl"))  # 「登入」按鈕

        if wait_appeared_element_by_id(driver): break

        wait_to_click(wait_and_find_element_by_id(driver, "button-1005-btnEl"))  # 「OK」按鈕
        print(f"{my_time_str()} - Login: Validate code '{validate_code}' incorrect. Retry in 3 seconds.\n")
        time.sleep(3)
        wait_to_click(wait_and_find_element_by_id(driver, "redoValidateCodeButton-btnEl"))  # 「重新產生」按鈕

    try:
        wait_to_click(wait_and_find_element_by_id(driver, "button-1005-btnEl"))  # 教程學生的「ok」按鈕
    except:
        pass

    wait_to_click(wait_and_find_element_by_id(driver, "button-1017-btnEl"))  # 「下一頁」按鈕
    wait_and_find_element_by_id(driver, "now")
    driver.execute_script("document.getElementById('now').parentElement.remove()")  # 移除計時器
    driver.switch_to.frame(wait_and_find_element_by_id(driver, "stfseldListDo"))
    wait_to_click(wait_and_find_element_by_id(driver, "add-btnEl"))  # 「加選」按鈕
    return