import calendar
import os
import platform
import sys
import urllib.request

import mysql.connector

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


driver = None

total_scrolls = 500
current_scrolls = 0
scroll_time = 5
old_height = 0

def check_height():
    new_height = driver.execute_script("return document.body.scrollHeight")
    return new_height != old_height


def scroll():
    global old_height
    current_scrolls = 0

    while (True):
        try:
            if current_scrolls == total_scrolls:
                return

            old_height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            WebDriverWait(driver, scroll_time, 0.05).until(lambda driver: check_height())
            current_scrolls += 1
        except TimeoutException:
            break

    return


def get_status(x):
    status = ""
    try:
        status = x.find_element_by_xpath(".//div[@class='_5pbx userContent']").text
    except:
        try:
            status = x.find_element_by_xpath(".//div[@class='userContent']").text
        except:
            pass
    return status


def get_div_links(x, tag):
    try:
        temp = x.find_element_by_xpath(".//div[@class='_3x-2']")
        return temp.find_element_by_tag_name(tag)
    except:
        return ""


def get_title_links(title):
    l = title.find_elements_by_tag_name('a')
    return l[-1].text, l[-1].get_attribute('href')


def get_title(x):
    title = ""
    try:
        title = x.find_element_by_xpath(".//span[@class='fwb fcg']")
    except:
        try:
            title = x.find_element_by_xpath(".//span[@class='fcg']")
        except:
            try:
                title = x.find_element_by_xpath(".//span[@class='fwn fcg']")
            except:
                pass
    finally:
        return title


def get_time(x):
    time = ""
    try:
        time = x.find_element_by_tag_name('abbr').get_attribute('title')
        time = str("%02d" % int(time.split(", ")[1].split()[1]), ) + "-" + str(
            ("%02d" % (int((list(calendar.month_abbr).index(time.split(", ")[1].split()[0][:3]))),))) + "-" + \
               time.split()[3] + " " + str("%02d" % int(time.split()[5].split(":")[0])) + ":" + str(
            time.split()[5].split(":")[1])
    except:
        pass

    finally:
        return time


def write_to_db(elements):
    try:
        # f = open(filename, "w", newline='\r\n')
        # f.writelines('TIME || TYPE  || TITLE || STATUS  ||   LINKS(Shared Posts/Shared Links etc) ' + '\n' + '\n')

        for x in elements:
            try:
                video_link = " "
                title = " "
                status = " "
                link = ""
                img = " "
                time = " "

                time = get_time(x)
                
                title = get_title(x)
                if title.text.find("shared a memory") != -1:
                    x = x.find_element_by_xpath(".//div[@class='_1dwg _1w_m']")
                    title = get_title(x)

                status = get_status(x)
                if title.text == driver.find_element_by_id("fb-timeline-cover-name").text:
                    if status == '':
                        temp = get_div_links(x, "img")
                        if temp == '':
                            link = get_div_links(x, "a").get_attribute('href')
                            type = "status update without text"
                        else:
                            type = 'life event'
                            link = get_div_links(x, "a").get_attribute('href')
                            status = get_div_links(x, "a").text
                    else:
                        type = "status update"
                        if get_div_links(x, "a") != '':
                            link = get_div_links(x, "a").get_attribute('href')

                elif title.text.find(" shared ") != -1:

                    x1, link = get_title_links(title)
                    type = "shared " + x1

                elif title.text.find(" at ") != -1 or title.text.find(" in ") != -1:
                    if title.text.find(" at ") != -1:
                        x1, link = get_title_links(title)
                        type = "check in"
                    elif title.text.find(" in ") != 1:
                        status = get_div_links(x, "a").text

                elif title.text.find(" added ") != -1 and title.text.find("photo") != -1:
                    type = "added photo"
                    link = get_div_links(x, "a").get_attribute('href')

                elif title.text.find(" added ") != -1 and title.text.find("video") != -1:
                    type = "added video"
                    link = get_div_links(x, "a").get_attribute('href')

                else:
                    type = "others"

                if not isinstance(title, str):
                    title = title.text

                sql = "INSERT INTO posts (title, textContent, time_stamp) VALUES (%s, %s, %s)"
                val = (str(title), str(status), str(time))
                mycursor.execute(sql, val)

                mydb.commit()

                print(mycursor.rowcount, "record inserted.")

            except:
                print("Element exception")
                pass

        f.close()
    except:
        print("Exception (extract_and_write_posts)", sys.exc_info()[0])

    return


def scrap_data(id, elements_path, file_names):

    try:
        driver.get(id)
        scroll()
        data = driver.find_elements_by_xpath(elements_path)
        write_to_db(data)

    except:
        print("Exception (scrap_data)", sys.exc_info()[0])


def create_original_link(url):
    if url.find(".php") != -1:
        original_link = "https://en-gb.facebook.com/" + ((url.split("="))[1])

        if original_link.find("&") != -1:
            original_link = original_link.split("&")[0]

    elif url.find("fnr_t") != -1:
        original_link = "https://en-gb.facebook.com/" + ((url.split("/"))[-1].split("?")[0])
    elif url.find("_tab") != -1:
        original_link = "https://en-gb.facebook.com/" + (url.split("?")[0]).split("/")[-1]
    else:
        original_link = url

    return original_link


def scrap_profile(ids):
    folder = os.path.join(os.getcwd(), "Data")

    if not os.path.exists(folder):
        os.mkdir(folder)

    os.chdir(folder)

    for id in ids:

        driver.get(id)
        url = driver.current_url
        id = create_original_link(url)

        print("\nScraping:", id)

        try:
            if not os.path.exists(os.path.join(folder, id.split('/')[-1])):
                os.mkdir(os.path.join(folder, id.split('/')[-1]))
            else:
                print("A folder with the same profile name already exists."
                      " Kindly remove that folder first and then run this code.")
                continue
            os.chdir(os.path.join(folder, id.split('/')[-1]))
        except:
            print("Some error occurred in creating the profile directory.")
            continue


        print("----------------------------------------")
        print("Posts:")
        elements_path = "//div[@class='_4-u2 mbm _4mrt _5jmm _5pat _5v3q _4-u8']"

        file_names = "Posts.txt"

        scrap_data(id, elements_path, file_names)
        print("Posts(Statuses) Done")
        print("----------------------------------------")
        
    print("\nProcess Completed.")

    return


def login(email, password):

    try:
        global driver

        options = Options()

        options.add_argument("--disable-notifications")
        options.add_argument("--disable-infobars")
        options.add_argument("--mute-audio")

        driver = webdriver.Chrome(executable_path="./chromedriver", chrome_options=options)

        driver.get("https://en-gb.facebook.com")
        driver.maximize_window()

        driver.find_element_by_name('email').send_keys(email)
        driver.find_element_by_name('pass').send_keys(password)
        driver.find_element_by_id('loginbutton').click()

    except Exception as e:
        print("There's some error in log in.")
        print(sys.exc_info()[0])
        exit()


def initDatabase():

    global mydb
    global mycursor

    import mysql.connector

    mydb = mysql.connector.connect(
        host = 'localhost',
        user = 'root',
        password = 'password',
        database = 'scrapingDB'
    )

    mycursor = mydb.cursor()
    #mycursor.execute("CREATE TABLE posts (title VARCHAR(255), textContent VARCHAR(255), time_stamp VARCHAR(255))")

    mycursor.execute("SHOW TABLES")

    for x in mycursor:
        print(x)





def main():
    ids = ["https://en-gb.facebook.com/" + line.split("/")[-1] for line in open("input.txt", newline='\n')]

    if len(ids) > 0:
        #email = input('\nEnter your Facebook Email: ')
        #password = input('Enter your Facebook Password: ')
        email = "adityamaniar24@gmail.com"
        password = "aditya"

        print("\nStarting Scraping...")

        login(email, password)
        initDatabase()
        scrap_profile(ids)
        driver.close()
    else:
        print("Input file is empty")

main()
