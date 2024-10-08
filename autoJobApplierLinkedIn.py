'''
Author:     Sai Vignesh Golla
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (C) 2024 Sai Vignesh Golla

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

'''


# Imports
import os
import csv
import re
import pyautogui
pyautogui.FAILSAFE = False
from random import choice, shuffle, randint
from datetime import datetime
from modules.open_chrome import open_chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, NoSuchWindowException
from setup.config import *
from modules.helpers import *
from modules.clickers_and_finders import *
from modules.validator import validate_config
if use_resume_generator:    from resume_generator import is_logged_in_GPT, login_GPT, open_resume_chat, create_custom_resume


#< Global Variables and logics

if run_in_background == True:
    pause_at_failed_question = False
    pause_before_submit = False
    run_non_stop = False

first_name = first_name.strip()
middle_name = middle_name.strip()
last_name = last_name.strip()
full_name = first_name + " " + middle_name + " " + last_name if middle_name else first_name + " " + last_name

useNewResume = False
randomly_answered_questions = set()

tabs_count = 1
easy_applied_count = 0
external_jobs_count = 0
failed_count = 0
skip_count = 0
dailyEasyApplyLimitReached = False

driver = None
wait = None
actions = None

g_working_on_page = start_page

re_experience = re.compile(r'[(]?\s*(\d+)\s*[)]?\s*[-to]*\s*\d*[+]*\s*year[s]?', re.IGNORECASE)
#>

# move to page function
def move_to_page(target_page):

    while True:
        wait.until(EC.presence_of_all_elements_located((By.XPATH, "//li[contains(@class, 'jobs-search-results__list-item')]")))
        pagination_element, cur_page_num = get_page_info()
        if pagination_element == None:
            print_lg("Couldn't find pagination element, probably at the end page of results!")
            return False
        print_lg(f"\n>-> Now on Page {cur_page_num} \n")
        if cur_page_num < target_page:
            try:
                pagination_element.find_element(By.XPATH, f"//button[@aria-label='Page {cur_page_num + 1}']").click()
            except NoSuchElementException:
                print_lg(f"\n>-> Didn't find Page {cur_page_num + 1}. Probably at the end page of results!\n")
                return False
        else:
            return True


#< Login Functions

# Function to check if user is logged-in in LinkedIn
def is_logged_in_LN():
    if driver.current_url == "https://www.linkedin.com/feed/": return True
    if try_linkText(driver, "Sign in"): return False
    if try_xp(driver, '//button[@type="submit" and contains(text(), "Sign in")]'):  return False
    if try_linkText(driver, "Join now"): return False
    print_lg("Didn't find Sign in link, so assuming user is logged in!")
    return True

# Function to login for LinkedIn
def login_LN():
    # Find the username and password fields and fill them with user credentials
    driver.get("https://www.linkedin.com/login")
    try:
        wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Forgot password?")))
        try:
            text_input_by_ID(driver, "username", username, 1)
        except Exception as e:
            print_lg("Couldn't find username field.")
            # print_lg(e)
        try:
            text_input_by_ID(driver, "password", password, 1)
        except Exception as e:
            print_lg("Couldn't find password field.")
            # print_lg(e)
        # Find the login submit button and click it
        driver.find_element(By.XPATH, '//button[@type="submit" and contains(text(), "Sign in")]').click()
    except Exception as e1:
        try:
            profile_button = find_by_class(driver, "profile__details")
            profile_button.click()
        except Exception as e2:
            # print_lg(e1, e2)
            print_lg("Couldn't Login!")

    try:
        # Wait until successful redirect, indicating successful login
        wait.until(EC.url_to_be("https://www.linkedin.com/feed/")) # wait.until(EC.presence_of_element_located((By.XPATH, '//button[normalize-space(.)="Start a post"]')))
        return print_lg("Login successful!")
    except Exception as e:
        print_lg("Seems like login attempt failed! Possibly due to wrong credentials or already logged in! Try logging in manually!")
        # print_lg(e)
        manual_login_retry(is_logged_in_LN, 2)
#>



# Function to get list of applied job's Job IDs
def get_applied_job_ids():
    job_ids = set()
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                job_ids.add(row[0])
    except FileNotFoundError:
        print_lg(f"The CSV file '{file_name}' does not exist.")
    return job_ids

# Function to get list of error job's Job IDs
def get_error_job_ids():
    error_job_ids = set()
    try:
        with open(failed_file_name, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                stack_trace = row[6]
                job_id = row[0]
                if "GetHandleVerifier [" in stack_trace:
                    if  job_id not in error_job_ids:
                        error_job_ids.add(row[0])
    except FileNotFoundError:
        print_lg(f"The CSV file '{failed_file_name}' does not exist.")
    return error_job_ids



# Function to apply job search filters
def apply_filters():
    try:
        recommended_wait = 1 if click_gap < 1 else 0

        wait.until(EC.presence_of_element_located((By.XPATH, '//button[normalize-space()="All filters"]'))).click()
        buffer(recommended_wait)

        wait_span_click(driver, sort_by)
        wait_span_click(driver, date_posted)
        buffer(recommended_wait)

        multi_sel(driver, experience_level) 
        multi_sel_noWait(driver, companies, actions)
        if experience_level or companies: buffer(recommended_wait)

        multi_sel(driver, job_type)
        multi_sel(driver, on_site)
        if job_type or on_site: buffer(recommended_wait)

        if easy_apply_only: boolean_button_click(driver, actions, "Easy Apply")
        
        multi_sel_noWait(driver, location)
        multi_sel_noWait(driver, industry)
        if location or industry: buffer(recommended_wait)

        multi_sel_noWait(driver, job_function)
        multi_sel_noWait(driver, job_titles)
        if job_function or job_titles: buffer(recommended_wait)

        if under_10_applicants: boolean_button_click(driver, actions, "Under 10 applicants")
        if in_your_network: boolean_button_click(driver, actions, "In your network")
        if fair_chance_employer: boolean_button_click(driver, actions, "Fair Chance Employer")

        wait_span_click(driver, salary)
        buffer(recommended_wait)
        
        multi_sel_noWait(driver, benefits)
        multi_sel_noWait(driver, commitments)
        if benefits or commitments: buffer(recommended_wait)

        show_results_button = driver.find_element(By.XPATH, '//button[contains(@aria-label, "Apply current filters to show")]')
        show_results_button.click()

    except Exception as e:
        print_lg("Setting the preferences failed!")
        # print_lg(e)



# Function to get pagination element and current page number
def get_page_info():
    try:
        #todo
        sleep(5)
        pagination_element = find_by_class(driver, "artdeco-pagination")
        scroll_to_view(driver, pagination_element)
        current_page = int(pagination_element.find_element(By.XPATH, "//li[contains(@class, 'active')]").text)
    except Exception as e:
        print_lg("Failed to find Pagination element, hence couldn't scroll till end!")
        pagination_element = None
        current_page = None
        # print_lg(e)
    return pagination_element, current_page



# Function to get job main details
def get_job_main_details(job, blacklisted_companies, rejected_jobs, error_jobs, applied_jobs):
    job_id = job.get_dom_attribute('data-occludable-job-id')

    if job_id:
        job_details_button = job.find_element(By.CLASS_NAME, "job-card-list__title")
        scroll_to_view(driver, job_details_button, True)
        title = job_details_button.text
        company = job.find_element(By.CLASS_NAME, "job-card-container__primary-description").text
        work_location = job.find_element(By.CLASS_NAME, "job-card-container__metadata-item").text
        applied = False
        try:
            if job.find_element(By.CLASS_NAME, "job-card-container__footer-job-state").text == "Applied":
                applied = True
        except:
            pass

    else:
        job_card_posting_wrapper = job.find_element(By.CLASS_NAME, "job-card-job-posting-card-wrapper")
        job_id = job_card_posting_wrapper.get_dom_attribute('data-job-id')
        job_details_button = job.find_element(By.CLASS_NAME, "job-card-job-posting-card-wrapper__card-link")
        scroll_to_view(driver, job_details_button, True)
        title = job.find_element(By.CLASS_NAME, "artdeco-entity-lockup__title").text
        company = job.find_element(By.CLASS_NAME, "artdeco-entity-lockup__subtitle").text
        work_location = job.find_element(By.CLASS_NAME, "artdeco-entity-lockup__caption").text
        applied = False
        try:
            if job.find_element(By.CLASS_NAME, "job-card-job-posting-card-wrapper__footer-items").text == "Applied":
                applied = True
        except:
            pass

    work_style = work_location[work_location.rfind('(')+1:work_location.rfind(')')]
    work_location = work_location[:work_location.rfind('(')].strip()
    # Skip if previously rejected due to blacklist or already applied
    skip = False

    if company in blacklisted_companies:
        print_lg(f'Skipping "{title} | {company}" job (Blacklisted Company). Job ID: {job_id}!')
        skip = True
    elif job_id in rejected_jobs: 
        print_lg(f'Skipping previously rejected "{title} | {company}" job. Job ID: {job_id}!')
        skip = True
    elif job_id in error_jobs:
        print_lg(f'Skipping error job to "{title} | {company}" job. Job ID: {job_id}!')
        skip = True
    elif "Intern" in title:
        print_lg(f'Skipping "{title} | {company}" job (Intern JOb). Job ID: {job_id}!')
        skip = True
    elif job_id in applied_jobs:
        print_lg(f'Skipping already applied to "{title} | {company}" job. Job ID: {job_id}!')
        skip = True

    if applied:
        skip = True
        print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')

    try:
        if not skip: job_details_button.click()
    except Exception as e:
        print_lg(f'Failed to click "{title} | {company}" job on details button. Job ID: {job_id}!')
        # print_lg(e)
        discard_job()
        job_details_button.click() # To pass the error outside
    buffer(click_gap)
    return (job_id,title,company,work_location,work_style,skip)


# Function to check for Blacklisted words in About Company
def check_blacklist(rejected_jobs,job_id,company,blacklisted_companies):
    jobs_top_card = try_find_by_classes(driver, ["job-details-jobs-unified-top-card__primary-description-container","job-details-jobs-unified-top-card__primary-description","jobs-unified-top-card__primary-description","jobs-details__main-content"])
    about_company_org = find_by_class(driver, "jobs-company__box")
    scroll_to_view(driver, about_company_org)
    about_company_org = about_company_org.text
    about_company = about_company_org.lower()
    skip_checking = False
    for word in about_company_good_words:
        if word.lower() in about_company:
            print_lg(f'Found the word "{word}". So, skipped checking for blacklist words.')
            skip_checking = True
            break
    if not skip_checking:
        for word in about_company_bad_words:
            if word.lower() in about_company:
                rejected_jobs.add(job_id)
                blacklisted_companies.add(company)
                raise ValueError(f'\n"{about_company_org}"\n\nContains "{word}".')
    buffer(click_gap)
    scroll_to_view(driver, jobs_top_card)
    return rejected_jobs, blacklisted_companies, jobs_top_card



# Function to extract years of experience required from About Job
def extract_years_of_experience(text):
    # Extract all patterns like '10+ years', '5 years', '3-5 years', etc.
    matches = re.findall(re_experience, text)
    if len(matches) == 0:
        print_lg(f'\n{text}\n\nCouldn\'t find experience requirement in About the Job!')
        return 0
    return max([int(match) for match in matches if int(match) <= 12])



# Function to upload resume
def upload_resume(modal, resume):
    try:
        modal.find_element(By.NAME, "file").send_keys(os.path.abspath(resume))
        return True, os.path.basename(default_resume_path)
    except: return False, "Previous resume"

#Function to select resume
def select_candidate_resume(modal, title, description):
    try:
        #select resume name
        title_low = title.lower()
        description_low = description.lower()
        resume_name = resume_dict['default']
        if 'angular' in title_low:
            resume_name = resume_dict['angular']
        elif 'laravel' in title_low or 'php' in title_low:
            resume_name = resume_dict['laravel']
        elif 'react' in title_low:
            resume_name = resume_dict['react']
        else:
            if 'angular' in description_low:
                resume_name = resume_dict['angular']
            elif 'laravel' in description_low:
                resume_name = resume_dict['laravel']
            elif 'react' in description_low:
                resume_name = resume_dict['react']
            else:
                resume_name = resume_dict['default']
        # check if selected originally

        all_resume_pdfs = modal.find_elements(By.CLASS_NAME, 'jobs-document-upload-redesign-card__container')
        for resume_option in all_resume_pdfs:
            option_text = resume_option.text
            if resume_name in option_text:
                if 'jobs-document-upload-redesign-card__container--selected' in resume_option.get_attribute('class'):
                    #alreday selected, do nothing
                    pass
                else:
                    resume_option.click()
                    buffer(1)
                return True, resume_name

        if try_xp(modal, '//div[contains(@class, "jobs-document-upload__show-more-less-button-container")]//button'):
            buffer(1)
            all_resume_pdfs = modal.find_elements(By.CLASS_NAME, 'jobs-document-upload-redesign-card__container')
            for resume_option in all_resume_pdfs:
                option_text = resume_option.text
                if resume_name in option_text:
                    resume_option.click()
                    buffer(1)
                    return True, resume_name

        return False, "Selecting Resume Error"
    except:
        return False, "Selecting Resume Error"
    pass
# Function to answer common questions for Easy Apply
def answer_common_questions(label, answer):
    if 'sponsorship' in label or 'visa' in label or 'sponsor ' in label: answer = require_visa
    return answer


# Function to answer the questions for Easy Apply
def answer_questions(questions_list, work_location):
    # Get all questions from the page
    all_questions = driver.find_elements(By.CLASS_NAME, "jobs-easy-apply-form-element")
    print(f"question count:{len(all_questions)}")
    for Question in all_questions:
        # Check if it's a select Question
        select = try_xp(Question, ".//select", False)
        if select:
            label_org = "Unknown"
            try:
                label = Question.find_element(By.TAG_NAME, "label")
                label_org = label.find_element(By.TAG_NAME, "span").text
            except: pass
            answer = 'Yes'
            label = label_org.lower()
            select = Select(select)
            selected_option = select.first_selected_option.text
            optionsText = []
            options = '"List of phone country codes"'
            if label != "phone country code":
                optionsText = [option.text for option in select.options]
                options = "".join([f' "{option}",' for option in optionsText])
            prev_answer = selected_option
            print("select " + label + ", " + selected_option)
            if overwrite_previous_answers or selected_option == "Select an option":
                if 'email' in label or 'phone' in label: answer = prev_answer
                elif 'gender' in label or 'sex' in label: answer = gender
                elif 'disability' in label: answer = disability_status
                elif 'proficiency' in label: answer = 'Professional'
                elif 'future require' in label: answer = require_visa
                elif 'authorized to work' in label: answer = authorized_to_work_usa
                else: answer = answer_common_questions(label,answer)
                try: select.select_by_visible_text(answer)
                except NoSuchElementException as e:
                    ''' <<<<<<<<<<<<<<<<<<  
                        Only works if options match exactly, implement logic to check if word in options... 
                        Also implement US voluntary self- identification
                    '''
                    print_lg(f'Failed to find an option with text "{answer}" for question labelled "{label_org}", answering randomly!')
                    select.select_by_index(randint(1, len(select.options)-1))
                    randomly_answered_questions.add((f'{label_org} [ {options} ]',"select"))
            questions_list.add((f'{label_org} [ {options} ]', select.first_selected_option.text, "select", prev_answer))
            continue

        # Check if it's a radio Question
        radio = try_xp(Question, './/fieldset[@data-test-form-builder-radio-button-form-component="true"]', False)
        if radio:
            print("found radio")
            prev_answer = None
            label = try_xp(radio, './/span[@data-test-form-builder-radio-button-form-component__title]', False)
            try: label = find_by_class(label, "visually-hidden", 2.0)
            except: pass
            label_org = label.text if label else "Unknown"
            answer = 'Yes'
            label = label_org.lower()

            label_org += ' [ '
            options = radio.find_elements(By.TAG_NAME, 'input')
            options_labels = []
            print(label)
            for option in options:
                id = option.get_attribute("id")
                option_label = try_xp(radio, f'.//label[@for="{id}"]', False)
                options_labels.append( f'"{option_label.text if option_label else "Unknown"}"<{option.get_attribute("value")}>' ) # Saving option as "label <value>"
                if option.is_selected(): prev_answer = options_labels[-1]
                label_org += f' {options_labels[-1]},'

            if label == "unknown":
                if "Male" in label_org and "Female" in label_org:
                    label = "unknown gender"
                if "veteran" in label_org or "Veteran" in label_org:
                    label = "unkown veteran"
                if "disability" in label_org or "Disability" in label_org:
                    label = "unkown disability"

            if overwrite_previous_answers or prev_answer is None:
                if 'citizenship' in label or 'employment eligibility' in label: answer = us_citizenship
                elif 'veteran' in label or 'protected' in label:
                    answer = veteran_status
                    if 'unknown' in label:
                        answer = 'I am not a protected veteran'
                elif 'gender' in label:
                    answer = gender
                    if 'unknown' in label:
                        answer = 'Male'
                elif 'disability' in label or 'handicapped' in label:
                    answer = disability_status
                    if 'unknown' in label:
                        answer = 'No, I Don\'t Have A Disability, Or A History/Record Of Having A Disability'
                elif 'future require' in label: answer = require_visa
                elif 'authorized to work' in label: answer = authorized_to_work_usa
                else: answer = answer_common_questions(label,answer)
                foundOption = try_xp(radio, f".//label[normalize-space()='{answer}']", False)
                if foundOption:
                    actions.move_to_element(foundOption).click().perform()
                else:
                    ele = options[0]
                    if answer == 'Decline':
                        answer = options_labels[0]
                        for phrase in ["Prefer not", "not want", "not wish"]:
                            foundOption = try_xp(radio, f".//label[normalize-space()='{phrase}']", False)
                            if foundOption:
                                answer = f'Decline ({phrase})'
                                ele = foundOption
                                break
                    actions.move_to_element(ele).click().perform()
                    if not foundOption: randomly_answered_questions.add((f'{label_org} ]',"radio"))
            else: answer = prev_answer
            questions_list.add((label_org+" ]", answer, "radio", prev_answer))
            continue

        # Check if it's a text question
        text = try_xp(Question, ".//input[@type='text']", False)
        if text:
            do_actions = False
            label = try_xp(Question, ".//label[@for]", False)
            try: label = label.find_element(By.CLASS_NAME,'visually-hidden')
            except: pass
            label_org = label.text if label else "Unknown"
            answer = "" # years_of_experience
            label = label_org.lower()

            prev_answer = text.get_attribute("value")
            placeholder = text.get_attribute('placeholder')
            class_names = text.get_attribute('class')
            if not prev_answer or overwrite_previous_answers:
                if 'experience' in label or 'years' in label:
                    if 'node.js' in label:
                        answer = years_of_experience_nodejs
                    elif 'react' in label:
                        answer = years_of_experience_reactjs
                    elif 'angular' in label:
                        answer = years_of_experience_angular
                    elif 'javascript' in label:
                        answer = years_of_experience_javascript
                    elif 'typescript' in label:
                        answer = years_of_experience_typecript
                    elif 'vue' in label:
                        answer = years_of_experience_vue
                    elif 'aws' in label:
                        answer = years_of_experience_aws
                    elif 'frontend' in label or 'front end' in label:
                        answer = years_of_experience_frontend
                    else:
                        answer = years_of_experience
                elif 'phone' in label or 'mobile' in label: answer = phone_number
                elif 'street' in label: answer = street
                elif 'city' in label or 'location' in label or 'address' in label:
                    answer = current_city if current_city else work_location
                    do_actions = True
                elif 'signature' in label: answer = full_name # 'signature' in label or 'legal name' in label or 'your name' in label or 'full name' in label: answer = full_name     # What if question is 'name of the city or university you attend, name of referral etc?'
                elif 'name' in label:
                    if 'full' in label: answer = full_name
                    elif 'first' in label and 'last' not in label: answer = first_name
                    elif 'middle' in label and 'last' not in label: answer = middle_name
                    elif 'last' in label and 'first' not in label: answer = last_name
                    elif 'employer' in label: answer = recent_employer
                    else: answer = full_name
                elif 'website' in label or 'blog' in label or 'portfolio' in label: answer = website
                elif 'salary' in label or 'compensation' in label: answer = desired_salary
                elif 'scale of 1-10' in label: answer = confidence_level
                elif 'headline' in label: answer = headline
                elif ('hear' in label or 'come across' in label) and 'this' in label and ('job' in label or 'position' in label): answer = "LinkedIn"
                elif 'state' in label or 'province' in label: answer = state
                elif 'zip' in label or 'postal' in label or 'code' in label: answer = zipcode
                elif 'country' in label: answer = country
                elif 'linkedin' in label: answer = linkedin_profile
                elif 'current company' in label: answer = current_company
                elif 'mm/dd/yyyy' in placeholder:
                    answer = datetime.today().strftime('%m/%d/%Y')
                elif 'notice period in days' in label:
                    answer = '0'
                elif 'authorization. select 1 for us citizen select 2 for green card select 3 for ead select 4 for others' in label:
                    answer = '2'
                elif 'hourly rate' in label or 'hour rate' in label or 'current rate' in label or 'expected rate' in label:
                    answer = hourly_rate
                else: answer = answer_common_questions(label, answer)
                if answer == "":
                    randomly_answered_questions.add((label_org, "text"))
                    if '-numeric' in class_names:
                        answer = '0'
                    else:
                        answer = "N/A"
                text.clear()
                text.send_keys(answer)
                if do_actions:
                    sleep(2)
                    actions.send_keys(Keys.ARROW_DOWN)
                    actions.send_keys(Keys.ENTER).perform()
            questions_list.add((label, text.get_attribute("value"), "text", prev_answer))
            continue

        # Check if it's a textarea question
        text_area = try_xp(Question, ".//textarea", False)
        if text_area:
            label = try_xp(Question, ".//label[@for]", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = ""
            prev_answer = text_area.get_attribute("value")

            if 'summary' in label: answer = summary
            elif 'cover' in label: answer = cover_letter
            text_area.clear()
            text_area.send_keys(answer)
            if answer == "":
                randomly_answered_questions.add((label_org, "textarea"))
            questions_list.add((label, text_area.get_attribute("value"), "textarea", prev_answer))
            continue

        # Check if it's a checkbox question
        checkbox = try_xp(Question, ".//input[@type='checkbox']", False)
        if checkbox:
            label = try_xp(Question, ".//span[@class='visually-hidden']", False)
            label_org = label.text if label else "Unknown"
            label = label_org.lower()
            answer = try_xp(Question, ".//label[@for]", False).text
            prev_answer = checkbox.is_selected()
            if not prev_answer: checkbox.click()
            questions_list.add((f'{label} ([X] {answer})', checkbox.is_selected(), "checkbox", prev_answer))
            continue


    # Select todays date
    try_xp(driver, "//button[contains(@aria-label, 'This is today')]")

    # Collect important skills
    # if 'do you have' in label and 'experience' in label and ' in ' in label -> Get word (skill) after ' in ' from label
    # if 'how many years of experience do you have in ' in label -> Get word (skill) after ' in '

    return questions_list




# Function to open new tab and save external job application links
def external_apply(pagination_element, job_id, job_link, resume, date_listed, application_link, screenshot_name):
    global tabs_count, dailyEasyApplyLimitReached

    if easy_apply_only:
        try:
            if "exceeded the daily application limit" in driver.find_element(By.CLASS_NAME, "artdeco-inline-feedback__message").text: dailyEasyApplyLimitReached = True
        except: pass
        print_lg("Easy apply failed I guess!")
        if pagination_element != None: return True, application_link, tabs_count
    try:
        wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(span, "Apply") and not(span[contains(@class, "disabled")])]'))).click()
        print_lg('Waiting for external link...')
        sleep(2)

        started_tryagain_for_external_link = False
        while True:
            windows = driver.window_handles
            tabs_count = len(windows)
            driver.switch_to.window(windows[-1])
            application_link = driver.current_url
            if application_link.startswith("https://www.linkedin.com/jobs/search/"):
                if started_tryagain_for_external_link:
                    # already waited for long time, so move to failed job
                    raise Exception("External link window is not opened")
                else:
                    # external link is not pop up, wait some times
                    print_lg('External link window is not opened. Waiting for 5s more...')
                    started_tryagain_for_external_link = True
                    sleep(5)
                    print_lg('Trying for Continue applying...')
                    wait.until(EC.element_to_be_clickable((By.XPATH, '//button[contains(span, "Continue applying") and not(span[contains(@class, "disabled")])]'))).click()

            else:
                break

        print_lg('Got the external application link "{}"'.format(application_link))
        print_lg('Closing external tab...')
        if close_tabs: driver.close()
        sleep(1)
        print_lg('Switching to linkedin tab...')
        driver.switch_to.window(linkedIn_tab)
        sleep(1)
        return False, application_link, tabs_count
    except Exception as e:
        # print_lg(e)
        print_lg("Failed to apply!")
        failed_job(job_id, job_link, resume, date_listed, "Probably didn't find Apply button or unable to switch tabs.", e, application_link, screenshot_name)
        global failed_count
        failed_count += 1
        return True, application_link, tabs_count




#< Failed attempts logging

# Function to update failed jobs list in excel
def failed_job(job_id, job_link, resume, date_listed, error, exception, application_link, screenshot_name):
    with open(failed_file_name, 'a', newline='', encoding='utf-8') as file:
        fieldnames = ['Job ID', 'Job Link', 'Resume Tried', 'Date listed', 'Date Tried', 'Assumed Reason', 'Stack Trace', 'External Job link', 'Screenshot Name']
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if file.tell() == 0: writer.writeheader()
        writer.writerow({'Job ID':job_id, 'Job Link':job_link, 'Resume Tried':resume, 'Date listed':date_listed, 'Date Tried':datetime.now(), 'Assumed Reason':error, 'Stack Trace':exception, 'External Job link':application_link, 'Screenshot Name':screenshot_name})
        file.close()


# Function to to take screenshot for debugging
def screenshot(driver, job_id, failedAt):
    screenshot_name = "{} - {} - {}.png".format( job_id, failedAt, str(datetime.now()) )
    path = logs_folder_path+"/screenshots/"+screenshot_name.replace(":",".")
    # special_chars = {'*', '"', '\\', '<', '>', ':', '|', '?'}
    # for char in special_chars:  path = path.replace(char, '-')
    driver.save_screenshot(path.replace("//","/"))
    return screenshot_name
#>



# Function to create or append to the CSV file, once the application is submitted successfully
def submitted_jobs(job_id, title, company, work_location, work_style, description, experience_required, skills, hr_name, hr_link, resume, reposted, date_listed, date_applied, job_link, application_link, questions_list, connect_request):
    with open(file_name, mode='a', newline='', encoding='utf-8') as csv_file:
        fieldnames = ['Job ID', 'Title', 'Company', 'Work Location', 'Work Style', 'About Job', 'Experience required', 'Skills required', 'HR Name', 'HR Link', 'Resume', 'Re-posted', 'Date Posted', 'Date Applied', 'Job Link', 'External Job link', 'Questions Found', 'Connect Request']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if csv_file.tell() == 0: writer.writeheader()
        writer.writerow({'Job ID':job_id, 'Title':title, 'Company':company, 'Work Location':work_location, 'Work Style':work_style,
                        'About Job':description, 'Experience required': experience_required, 'Skills required':skills,
                            'HR Name':hr_name, 'HR Link':hr_link, 'Resume':resume, 'Re-posted':reposted,
                            'Date Posted':date_listed, 'Date Applied':date_applied, 'Job Link':job_link,
                            'External Job link':application_link, 'Questions Found':questions_list, 'Connect Request':connect_request})
    csv_file.close()



# Function to discard the job application
def discard_job():
    actions.send_keys(Keys.ESCAPE).perform()
    wait_span_click(driver, 'Discard', 2)






# Function to apply to jobs
def apply_to_jobs(search_terms):
    #only search search_terms[0]
    applied_jobs = get_applied_job_ids()
    error_jobs = get_error_job_ids()
    rejected_jobs = set()
    blacklisted_companies = set()
    global current_city, failed_count, skip_count, easy_applied_count, external_jobs_count, tabs_count, pause_before_submit, pause_at_failed_question, useNewResume, g_working_on_page
    current_city = current_city.strip()

    if randomize_search_order:  shuffle(search_terms)
    for searchTerm in search_terms:
        driver.get(f"https://www.linkedin.com/jobs/search/?keywords={searchTerm}")
        print_lg("\n________________________________________________________________________________________________________________________\n")
        print_lg(f'\n>>>> Now searching for "{searchTerm}" <<<<\n\n')

        if search_location.strip():
            #todo
            sleep(5)
            print_lg(f'Setting search location as: "{search_location.strip()}"')
            search_location_ele = try_xp(driver, "//input[@aria-label='City, state, or zip code'and not(@disabled)]", False) #  and not(@aria-hidden='true')]")
            search_location_ele.clear()
            search_location_ele.send_keys(search_location.strip())
            sleep(2)
            actions.send_keys(Keys.ENTER).perform()

        apply_filters()

        current_count = 0
        try:
            # move to specific page
            if g_working_on_page > 1:
                if not move_to_page(g_working_on_page):
                    return False

            while current_count < switch_number:

                # Wait until job listings are loaded
                wait.until(EC.presence_of_all_elements_located((By.XPATH, "//li[contains(@class, 'jobs-search-results__list-item')]")))

                pagination_element, current_page = get_page_info()
                g_working_on_page = current_page
                # Find all job listings in current page
                buffer(3)
                job_listings = driver.find_elements(By.CLASS_NAME, "jobs-search-results__list-item")


                for job in job_listings:
                    if keep_screen_awake: pyautogui.press('shiftright')
                    if current_count >= switch_number: break
                    print_lg("\n-@-\n")

                    job_id,title,company,work_location,work_style,skip = get_job_main_details(job, blacklisted_companies, rejected_jobs, error_jobs, applied_jobs)

                    if skip: continue
                    # Redundant fail safe check for applied jobs!
                    try:
                        if job_id in applied_jobs or find_by_class(driver, "jobs-s-apply__application-link", 2):
                            print_lg(f'Already applied to "{title} | {company}" job. Job ID: {job_id}!')
                            continue
                        if job_id in error_jobs:
                            print_lg(f'Already marked as error job to "{title} | {company}" job. Job ID: {job_id}!')
                            continue
                    except Exception as e:
                        print_lg(f'Trying to Apply to "{title} | {company}" job. Job ID: {job_id}')

                    job_link = "https://www.linkedin.com/jobs/view/"+job_id
                    application_link = "Easy Applied"
                    date_applied = "Pending"
                    hr_link = "Unknown"
                    hr_name = "Unknown"
                    connect_request = "In Development" # Still in development
                    date_listed = "Unknown"
                    description = "Unknown"
                    experience_required = "Unknown"
                    skills = ""
                    resume = "Pending"
                    reposted = False
                    questions_list = None
                    screenshot_name = "Not Available"

                    try:
                        rejected_jobs, blacklisted_companies, jobs_top_card = check_blacklist(rejected_jobs,job_id,company,blacklisted_companies)
                    except ValueError as e:
                        print_lg(e, 'Skipping this job!\n')
                        failed_job(job_id, job_link, resume, date_listed, "Found Blacklisted words in About Company", e, "Skipped", screenshot_name)
                        skip_count += 1
                        continue
                    except Exception as e:
                        print_lg("Failed to scroll to About Company!")
                        # print_lg(e)



                    # Hiring Manager info
                    try:
                        hr_info_card = WebDriverWait(driver,2).until(EC.presence_of_element_located((By.CLASS_NAME, "hirer-card__hirer-information")))
                        hr_link = hr_info_card.find_element(By.TAG_NAME, "a").get_attribute("href")
                        hr_name = hr_info_card.find_element(By.TAG_NAME, "span").text
                        # if connect_hr:
                        #     driver.switch_to.new_window('tab')
                        #     driver.get(hr_link)
                        #     wait_span_click("More")
                        #     wait_span_click("Connect")
                        #     wait_span_click("Add a note")
                        #     message_box = driver.find_element(By.XPATH, "//textarea")
                        #     message_box.send_keys(connect_request_message)
                        #     if close_tabs: driver.close()
                        #     driver.switch_to.window(linkedIn_tab)
                        # def message_hr(hr_info_card):
                        #     if not hr_info_card: return False
                        #     hr_info_card.find_element(By.XPATH, ".//span[normalize-space()='Message']").click()
                        #     message_box = driver.find_element(By.XPATH, "//div[@aria-label='Write a message…']")
                        #     message_box.send_keys()
                        #     try_xp(driver, "//button[normalize-space()='Send']")
                    except Exception as e:
                        print_lg(f'HR info was not given for "{title}" with Job ID: {job_id}!')
                        # print_lg(e)


                    # Calculation of date posted
                    try:
                        # try: time_posted_text = find_by_class(driver, "jobs-unified-top-card__posted-date", 2).text
                        # except:
                        time_posted_text = jobs_top_card.find_element(By.XPATH, './/span[contains(normalize-space(), " ago")]').text
                        print("Time Posted: " + time_posted_text)
                        if time_posted_text.__contains__("Reposted"):
                            reposted = True
                            time_posted_text = time_posted_text.replace("Reposted", "")
                        date_listed = calculate_date_posted(time_posted_text)
                    except Exception as e:
                        print_lg("Failed to calculate the date posted!",e)

                    # Get job description
                    try:
                        found_masters = 0
                        description = find_by_class(driver, "jobs-box__html-content").text
                        descriptionLow = description.lower()
                        skip = False
                        for word in bad_words:
                            if word.lower() in descriptionLow:
                                message = f'\n{description}\n\nContains bad word "{word}". Skipping this job!\n'
                                reason = "Found a Bad Word in About Job"
                                skip = True
                                break

                        if not skip and skill_match_min_count > 0:
                            skills_elements = find_elements_by_class(driver, "job-details-how-you-match__skills-item-wrapper")
                            skills_elements_length = len(skills_elements)
                            print_lg(f"Skill Elements Count: {skills_elements_length}")
                            if skills_elements_length > 0:
                                skills_match_text = ""
                                skills_missing_text = ""
                                for element in skills_elements:
                                    element_text = element.text.lower()
                                    if "missing" in element_text:
                                        skills_missing_text = element_text
                                    else:
                                        skills_match_text = element_text

                                skills = skills_match_text + " : " + skills_missing_text
                                print_lg(skills)

                                if skills_match_text == "":
                                    message = f'\n{skills_match_text}\n\n. Skill does not Match. Skipping this job!\n'
                                    reason = "Skill does not Match"
                                    skip = True
                                else:
                                    match = re.search(r'(\d+)', skills_match_text)
                                    if match:
                                        skill_match_count = int(match.group(1))
                                        found_good_skill = False
                                        for good_skill in good_skills:
                                            if good_skill in skills_match_text:
                                                found_good_skill = True
                                                break
                                        if not found_good_skill:
                                            message = f'\n{skills_match_text}\n\n. Skill does not Match. Skipping this job!\n'
                                            reason = "Skill does not Match"
                                            skip = True
                                        else:
                                            miss = re.search(r'(\d+)', skills_missing_text)
                                            if miss:
                                                skill_miss_count = int(miss.group(1))
                                                if skill_match_count * 2 < skill_miss_count:
                                                    message = f'\n{skill_miss_count}\n\n. Skill does not Match. Skipping this job!\n'
                                                    reason = "Skill does not Match"
                                                    skip = True
                                    else:
                                        message = f'\n{skills_match_text}\n\n. Skill does not Match. Skipping this job!\n'
                                        reason = "Skill does not Match"
                                        skip = True
                        if not skip and security_clearance == False and ('clearance' in descriptionLow or 'secret' in descriptionLow):
                            message = f'\n{description}\n\nFound "Clearance" . Skipping this job!\n'
                            reason = "Asking for Security clearance"
                            skip = True
                        if not skip:
                            if did_masters and 'master' in descriptionLow:
                                print_lg(f'Found the word "master" in \n{description}')
                                found_masters = 2
                            experience_required = extract_years_of_experience(description)
                            if current_experience > -1 and experience_required > current_experience + found_masters:
                                message = f'\n{description}\n\nExperience required {experience_required} > Current Experience {current_experience + found_masters}. Skipping this job!\n'
                                reason = "Required experience is high"
                                skip = True
                        if skip:
                            print_lg(message)
                            failed_job(job_id, job_link, resume, date_listed, reason, message, "Skipped", screenshot_name)
                            rejected_jobs.add(job_id)
                            skip_count += 1
                            continue
                    except Exception as e:
                        if description == "Unknown":    print_lg("Unable to extract job description!")
                        else:
                            experience_required = "Error in extraction"
                            print_lg("Unable to extract years of experience required!")
                        # print_lg(e)

                    uploaded = False
                    # Case 1: Easy Apply Button
                    if wait_span_easy_apply_click(driver, "Easy Apply", 2, False):
                        if not skip and check_location_requirement:
                            try:
                                jobdetail_module_content_text = find_by_class(driver, "job-details-how-you-match-card__container").text
                                if "Your location does not match" in jobdetail_module_content_text:
                                    message = f'\n{jobdetail_module_content_text}\n\n". Skipping this job!\n'
                                    reason = "Not match country requirement in About Job"
                                    skip = True
                                    print_lg("Your location does not match")
                            except Exception as e:
                                 print_lg("Not found job-details-how-you-match-card__container")
                        if skip:
                            print_lg(message)
                            failed_job(job_id, job_link, resume, date_listed, reason, message, "Skipped", screenshot_name)
                            rejected_jobs.add(job_id)
                            skip_count += 1
                            continue

                        wait_span_easy_apply_click(driver, "Easy Apply", 2)

                        try: 
                            try:
                                errored = ""
                                modal = find_by_class(driver, "jobs-easy-apply-modal")
                                wait_span_click(modal, "Next", 1)
                                # if description != "Unknown":
                                #     resume = create_custom_resume(description)
                                resume = "Previous resume"
                                next_button = True
                                questions_list = set()
                                next_counter = 0
                                while next_button:
                                    next_counter += 1
                                    if next_counter >= 10:
                                        if pause_at_failed_question:
                                            screenshot(driver, job_id, "Needed manual intervention for failed question")
                                            pyautogui.alert("Couldn't answer one or more questions.\nPlease click \"Continue\" once done.\nDO NOT CLICK Back, Next or Review button in LinkedIn.\n\n\n\n\nYou can turn off \"Pause at failed question\" setting in config.py", "Help Needed", "Continue")
                                            next_counter = 1
                                            continue
                                        if questions_list: print_lg("Stuck for one or some of the following questions...", questions_list)
                                        screenshot_name = screenshot(driver, job_id, "Failed at questions")
                                        errored = "stuck"
                                        raise Exception("Seems like stuck in a continuous loop of next, probably because of new questions.")
                                    print(f"next_counter:{next_counter}")
                                    questions_list = answer_questions(questions_list, work_location)
                                    if not uploaded:
                                        if useNewResume:
                                            uploaded, resume = upload_resume(modal, default_resume_path)
                                        else:
                                            uploaded, resume = select_candidate_resume(modal, title, description)
                                    try: next_button = modal.find_element(By.XPATH, './/span[normalize-space(.)="Review"]') 
                                    except NoSuchElementException:  next_button = modal.find_element(By.XPATH, './/button[contains(span, "Next")]')
                                    try: next_button.click()
                                    except ElementClickInterceptedException: break    # Happens when it tries to click Next button in About Company photos section
                                    buffer(1)

                            except NoSuchElementException: errored = "nose"
                            finally:
                                if skills:
                                    print_lg("Skills...", skills)
                                if questions_list and errored != "stuck": 
                                    print_lg("Answered the following questions...", questions_list)
                                    print("\n\n" + "\n".join(str(question) for question in questions_list) + "\n\n")
                                wait_span_click(driver, "Review", 1, scrollTop=True)
                                cur_pause_before_submit = pause_before_submit
                                if errored != "stuck" and cur_pause_before_submit:
                                    decision = pyautogui.confirm('1. Please verify your information.\n2. If you edited something, please return to this final screen.\n3. DO NOT CLICK "Submit Application".\n\n\n\n\nYou can turn off "Pause before submit" setting in config.py\nTo TEMPORARILY disable pausing, click "Disable Pause"', "Confirm your information",["Disable Pause", "Discard Application", "Submit Application"])
                                    if decision == "Discard Application": raise Exception("Job application discarded by user!")
                                    pause_before_submit = False if "Disable Pause" == decision else True
                                    try_xp(modal, ".//span[normalize-space(.)='Review']")
                                if wait_span_click(driver, "Submit application", 2, scrollTop=True): 
                                    date_applied = datetime.now()
                                    if not wait_span_click(driver, "Done", 2): actions.send_keys(Keys.ESCAPE).perform()
                                elif errored != "stuck" and cur_pause_before_submit and "Yes" in pyautogui.confirm("You submitted the application, didn't you 😒?", "Failed to find Submit Application!", ["Yes", "No"]):
                                    date_applied = datetime.now()
                                    wait_span_click(driver, "Done", 2)
                                else:
                                    print_lg("Since, Submit Application failed, discarding the job application...")
                                    # if screenshot_name == "Not Available":  screenshot_name = screenshot(driver, job_id, "Failed to click Submit application")
                                    # else:   screenshot_name = [screenshot_name, screenshot(driver, job_id, "Failed to click Submit application")]
                                    if errored == "nose": raise Exception("Failed to click Submit application 😑")


                        except Exception as e:
                            print_lg("Failed to Easy apply!")
                            # print_lg(e)
                            critical_error_log("Somewhere in Easy Apply process",e)
                            failed_job(job_id, job_link, resume, date_listed, "Problem in Easy Applying", e, application_link, screenshot_name)
                            failed_count += 1
                            discard_job()
                            continue
                    else:
                        # Case 2: Apply externally
                        skip, application_link, tabs_count = external_apply(pagination_element, job_id, job_link, resume, date_listed, application_link, screenshot_name)
                        if dailyEasyApplyLimitReached:
                            print_lg("\n###############  Daily application limit for Easy Apply is reached!  ###############\n")
                            return
                        if skip: continue

                    submitted_jobs(job_id, title, company, work_location, work_style, description, experience_required, skills, hr_name, hr_link, resume, reposted, date_listed, date_applied, job_link, application_link, questions_list, connect_request)
                    if uploaded:   useNewResume = False

                    print_lg(f'Successfully saved "{title} | {company}" job. Job ID: {job_id} info')
                    current_count += 1
                    if application_link == "Easy Applied": easy_applied_count += 1
                    else:   external_jobs_count += 1
                    applied_jobs.add(job_id)



                # Switching to next page
                if pagination_element == None:
                    print_lg("Couldn't find pagination element, probably at the end page of results!")
                    break
                try:
                    pagination_element.find_element(By.XPATH, f"//button[@aria-label='Page {current_page+1}']").click()
                    print_lg(f"\n>-> Now on Page {current_page+1} \n")
                    if current_count > 20:
                        rest_min = randint(1, 3)
                        print_lg(f"\n>-> Sleeping for {rest_min}m \n")
                        sleep(rest_min * 60)
                        # sleep(60)
                    else:
                        sleep(5)
                except NoSuchElementException:
                    print_lg(f"\n>-> Didn't find Page {current_page+1}. Probably at the end page of results!\n")
                    return True

        except Exception as e:
            print_lg("Failed to find Job listings!")
            critical_error_log("In Applier", e)
            # print_lg(e)
    return False
        
def run(total_runs):
    if dailyEasyApplyLimitReached:
        return total_runs, True
    print_lg("\n########################################################################################################################\n")
    print_lg(f"Date and Time: {datetime.now()}")
    print_lg(f"Cycle number: {total_runs}")
    print_lg(f"Start Page: {g_working_on_page}")
    print_lg(f"Currently looking for jobs posted within '{date_posted}' and sorting them by '{sort_by}'")
    run_result = apply_to_jobs(search_terms)
    print_lg("########################################################################################################################\n")
    if not dailyEasyApplyLimitReached:
        print_lg("Sleeping for 5 min...")
        sleep(180)
        print_lg("Few more min... Gonna start with in next 2 min...")
        sleep(120)
    buffer(3)
    return total_runs + 1, run_result



chatGPT_tab = False
linkedIn_tab = False
def main():
    while run_non_stop:
        success = False
        try:
            global linkedIn_tab, tabs_count, useNewResume, driver, wait, actions
            alert_title = "Error Occurred. Closing Browser!"
            total_runs = 1
            validate_config()
            (driver, wait, actions) = open_chrome()

            if not os.path.exists(default_resume_path):
             #   pyautogui.alert(text='Your default resume "{}" is missing! Please update it\'s folder path "default_resume_path" in config.py\n\nOR\n\nAdd a resume with exact name and path (check for spelling mistakes including cases).\n\n\nFor now the bot will continue using your previous upload from LinkedIn!'.format(default_resume_path), title="Missing Resume", button="OK")
                useNewResume = False

            # Login to LinkedIn
            tabs_count = len(driver.window_handles)
            driver.get("https://www.linkedin.com/login")
            if not is_logged_in_LN(): login_LN()

            linkedIn_tab = driver.current_window_handle

            # Login to ChatGPT in a new tab for resume customization
            if use_resume_generator:
                try:
                    driver.switch_to.new_window('tab')
                    driver.get("https://chat.openai.com/")
                    if not is_logged_in_GPT(): login_GPT()
                    open_resume_chat()
                    global chatGPT_tab
                    chatGPT_tab = driver.current_window_handle
                except Exception as e:
                    print_lg("Opening OpenAI chatGPT tab failed!")

            # Start applying to jobs
            driver.switch_to.window(linkedIn_tab)

            if cycle_date_posted:
                date_options = ["Any time", "Past month", "Past week", "Past 24 hours"]
                global date_posted
                date_posted = date_options[date_options.index(date_posted)+1 if date_options.index(date_posted)+1 > len(date_options) else -1] if stop_date_cycle_at_24hr else date_options[0 if date_options.index(date_posted)+1 >= len(date_options) else date_options.index(date_posted)+1]
            if alternate_sortby:
                global sort_by
                sort_by = "Most recent" if sort_by == "Most relevant" else "Most relevant"

            (total_runs, success) = run(total_runs)
            if dailyEasyApplyLimitReached:
                break


        except NoSuchWindowException:   pass
        except Exception as e:
            critical_error_log("In Applier Main", e)
         #   pyautogui.alert(e,alert_title)
        finally:
            print_lg("\n\nTotal runs:                     {}".format(total_runs))
            print_lg("Jobs Easy Applied:              {}".format(easy_applied_count))
            print_lg("External job links collected:   {}".format(external_jobs_count))
            print_lg("                              ----------")
            print_lg("Total applied or collected:     {}".format(easy_applied_count + external_jobs_count))
            print_lg("\nFailed jobs:                    {}".format(failed_count))
            print_lg("Irrelevant jobs skipped:        {}\n".format(skip_count))
            if randomly_answered_questions: print_lg("\n\nQuestions randomly answered:\n  {}  \n\n".format(";\n".join(str(question) for question in randomly_answered_questions)))
            quote = choice([
                "You're one step closer than before.",
                "All the best with your future interviews.",
                "Keep up with the progress. You got this.",
                "If you're tired, learn to take rest but never give up.",
                "Success is not final, failure is not fatal: It is the courage to continue that counts. - Winston Churchill",
                "Believe in yourself and all that you are. Know that there is something inside you that is greater than any obstacle. - Christian D. Larson",
                "Every job is a self-portrait of the person who does it. Autograph your work with excellence.",
                "The only way to do great work is to love what you do. If you haven't found it yet, keep looking. Don't settle. - Steve Jobs",
                "Opportunities don't happen, you create them. - Chris Grosser",
                "The road to success and the road to failure are almost exactly the same. The difference is perseverance.",
                "Obstacles are those frightful things you see when you take your eyes off your goal. - Henry Ford",
                "The only limit to our realization of tomorrow will be our doubts of today. - Franklin D. Roosevelt"
                ])
            msg = f"\n{quote}\n\n\nBest regards,\n/\n\n"
          #  pyautogui.alert(msg, "Exiting..")
            print_lg(msg,"Closing the browser...")
            if tabs_count >= 10:
                msg = "NOTE: IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM!\n\nOr it's highly likely that application will just open browser and not do anything next time!"
                pyautogui.alert(msg,"Info")
                print_lg("\n"+msg)
            try: driver.quit()
            except Exception as e: critical_error_log("When quitting...", e)

            if success:
                print_lg("ALL THINGS ARE CLEAR")
                break

main()