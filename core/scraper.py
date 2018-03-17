from bs4 import BeautifulSoup
from multiprocessing.dummy import Pool as ThreadPool 
from dateutil.parser import parse as parse_date
import requests
import threading
import time
import re
import csv


api_url = "https://egov.uscis.gov/casestatus/mycasestatus.do"

CASE_RECEIVED = "Case Was Received"
# On November 22, 2017, we received your Form I-765
CASE_BEING_REVIEWED = "Correspondence Was Received And USCIS Is Reviewing It"
# On March 9, 2018, we received your correspondence for Form I-765
CARD_MAILED = "Card Was Mailed To Me"
# On February 9, 2018, we mailed your new card for Receipt Number YSC1890050198 (No form type)
CARD_BEING_PRODUCED = "New Card Is Being Produced"
# On March 15, 2018, we ordered your new card for Receipt Number YSC1890050297 (No form type)

REQUEST_FOR_INITIAL_EVIDENCE_MAILED = "Request for Initial Evidence Was Mailed"
EVIDENCE_RECEIVED = "Response To USCIS' Request For Evidence Was Received"
CASE_BEING_REJECTED_WRONG_FEE = "Case Rejected Because I Sent An Incorrect Fee"
CASE_WITHDRAWN = "Withdrawal Acknowledgement Notice Was Sent"
CARD_NOT_ABLE_TO_DELIVER = "Notice Was Returned To USCIS Because The Post Office Could Not Deliver It"
FORM_DIDNT_SIGN = "Case Was Rejected Because I Did Not Sign My Form"
FORM_WRONG_VERSION = "Case Rejected Because The Version Of The Form I Sent Is No Longer Accepted"

cur_case_number = 50000
keep_workers_alive = True
worker_amount = 2

data_file = open('output.txt', 'a+')

def atomic_write(time_stamp, case_number, status):
    write_lock = threading.Lock()
    with write_lock:
        data_file.write("%s, %s, %s\n" %(case_number, time_stamp, status))
        date_file.flush()



def working_thread():
    global keep_workers_alive
    while keep_workers_alive:
        time.sleep(2)
        next_case_number = get_next_number()
        data = fetch_data(next_case_number)
        if data:
            status = data['status']
            status_date = get_status_date(data['content'])
            extracted_date = parse_date(status_date)
            year = extracted_date.year
            month = extracted_date.month
            day = extracted_date.day
            atomic_write("%04d%02d%02d" % (year, month, day),  next_case_number, status)
            print("Thread %s, Case number: %s  -> Status: %s on %04d%02d%02d" % (threading.get_ident(), next_case_number, data['status'], year, month, day))
            if status == CASE_RECEIVED:
                if is_OPT_receipt(data['content']):
                    pass
                else:
                    continue
            elif status == CASE_BEING_REVIEWED:
                if is_OPT_receipt(data['content']):
                    pass
                else:
                    continue
            elif status == CARD_BEING_PRODUCED:
                pass
            elif status == CARD_MAILED:
                pass
            else:
                # All problematic cases.
                continue

def is_OPT_receipt(content):
    if 'I-765' in content:
        return True
    return False

def get_status_date(content):
    m = re.search(r'On (\w+\s\d+,\s\d+),', content)
    return m.group(1)

def fetch_data(case_number):
    res = requests.post(api_url, data={
        'changeLocale':'',
        'completedActionsCurrentPage': '0',
        'upcomingActionsCurrentPage': '0',
        'appReceiptNum': case_number,
        'caseStatusSearchBtn': 'CHECK STATUS'
    })
    data_content = res.content
    
    soup = BeautifulSoup(data_content, 'html.parser')
    
    core_data = soup.find("div", {
        'class': 'rows text-center',
    })

    for error_msg in soup.find_all("h4"):
        if "Validation Error" in error_msg.get_text():
            # We reach the end, end all the workers. BYE BYE.
            global keep_workers_alive
            keep_workers_alive = False            

    if core_data:
        # Remove anchor tag

        # Get the status of the case
        status = core_data.find('h1').get_text()
        content = core_data.find('p').get_text()
        if status and content:
            return {
                'status': status,
                'content': content,
            }
        return None


def get_next_number():
    global cur_case_number
    lock = threading.Lock()
    with lock:
        cur_case_number += 1
        return "YSC1890%06d" % cur_case_number 


thread_list = []

for i in range(worker_amount):
    t = threading.Thread(target=working_thread, args=())
    t.setName("Thread #%d" % i)
    thread_list.append(t)

for thread in thread_list:
    time.sleep(1)
    thread.start()

for thread in thread_list:
    thread.join()

data_file.close()
print("DONE!")

#fetch_data("YSC1890228991")
#fetch_data(get_next_number())
