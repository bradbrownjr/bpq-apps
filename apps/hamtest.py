#!/usr/bin/env python3
"""
Ham Radio License Test Application for Packet Radio
---------------------------------------------------
A simple text-based ham radio license test application designed for use over
AX.25 packet radio via linbpq BBS software.

Features:
- Plain ASCII text interface (no control codes)
- Practice tests for Technician, General, and Extra class licenses
- Reali        if len(subelement_keys) != spec['subelements']:
            print("Warning: Expected {} subelements, found {}".format(spec['subelements'], len(subelement_keys)))ic exam simulation with proper question distribution
- Scoring with pass/fail indication
- ASCII art logo and simple menu navigation
- Link to ARRL test session locator for successful candidates

Author: Brad Brown KC1JMH
Date: October 2025
"""

import sys

# Check Python version
if sys.version_info < (3, 5):
    print("Error: This script requires Python 3.5 or later.")
    print("Your version: Python {}.{}.{}".format(
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro
    ))
    print("\nPlease run with: python3 hamtest.py")
    sys.exit(1)

import os
import json
import random
import textwrap
from collections import defaultdict
import urllib.request
import urllib.error
import re

# Configuration
# -------------
QUESTION_POOLS_DIR = os.path.join(os.path.dirname(__file__), "question_pools")
LINE_WIDTH = 78  # Maximum line width for text wrapping
ARRL_TEST_LOCATOR = "http://www.arrl.org/find-an-amateur-radio-license-exam-session"
GITHUB_REPO_URL = "https://api.github.com/repos/russolsen/ham_radio_question_pool/contents"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/russolsen/ham_radio_question_pool/master"

# Exam specifications
EXAM_SPECS = {
    'technician': {
        'name': 'Technician Class',
        'description': 'Entry-level license with VHF/UHF and limited HF privileges',
        'questions': 35,
        'pass_score': 26,  # 74% of 35
        'subelements': 35,
        'file': 'technician.json'
    },
    'general': {
        'name': 'General Class', 
        'description': 'Mid-level license with significant HF privileges',
        'questions': 35,
        'pass_score': 26,  # 74% of 35
        'subelements': 35,
        'file': 'general.json'
    },
    'extra': {
        'name': 'Amateur Extra Class',
        'description': 'Highest license class with all amateur privileges',
        'questions': 50,
        'pass_score': 37,  # 74% of 50
        'subelements': 50,
        'file': 'extra.json'
    }
}


class HamTestApp:
    """Ham Radio License Test Application"""
    
    def __init__(self):
        self.question_pools = {}
        self.current_exam = None
        self.github_directories = {}  # Cache for GitHub directory info
        self.ensure_question_pools_dir()
        self.load_question_pools()
        
    def ensure_question_pools_dir(self):
        """Ensure the question_pools directory exists"""
        if not os.path.exists(QUESTION_POOLS_DIR):
            os.makedirs(QUESTION_POOLS_DIR)
            print("Created directory: {}".format(QUESTION_POOLS_DIR))
    
    def get_github_directories(self):
        """Get list of directories from GitHub repository"""
        if self.github_directories:
            return self.github_directories
            
        try:
            print("Checking GitHub repository for current exam pools...")
            with urllib.request.urlopen(GITHUB_REPO_URL, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # Look for directories that match exam patterns
            patterns = {
                'technician': re.compile(r'^technician-(\d{4})-(\d{4})$'),
                'general': re.compile(r'^general-(\d{4})-(\d{4})$'),
                'extra': re.compile(r'^extra-(\d{4})-(\d{4})$')
            }
            
            for item in data:
                if item['type'] == 'dir':
                    dir_name = item['name']
                    for exam_type, pattern in patterns.items():
                        match = pattern.match(dir_name)
                        if match:
                            start_year, end_year = int(match.group(1)), int(match.group(2))
                            # Store the most recent directory for each exam type
                            if (exam_type not in self.github_directories or 
                                start_year > self.github_directories[exam_type]['start_year']):
                                self.github_directories[exam_type] = {
                                    'directory': dir_name,
                                    'start_year': start_year,
                                    'end_year': end_year
                                }
            
            print("Found {} current exam pools on GitHub".format(len(self.github_directories)))
            return self.github_directories
            
        except Exception as e:
            print("Warning: Could not check GitHub repository: {}".format(e))
            return {}
    
    def download_question_pool(self, exam_type):
        """Download question pool from GitHub"""
        directories = self.get_github_directories()
        if exam_type not in directories:
            print("No current {} exam pool found on GitHub".format(exam_type))
            return False
        
        directory = directories[exam_type]['directory']
        filename = "{}.json".format(exam_type)
        url = "{}/{}/{}".format(GITHUB_RAW_URL, directory, filename)
        local_path = os.path.join(QUESTION_POOLS_DIR, filename)
        
        try:
            print("Downloading {} question pool from {}...".format(exam_type, directory))
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read()
            
            with open(local_path, 'wb') as f:
                f.write(data)
            
            print("Successfully downloaded {}".format(filename))
            print("Question pool courtesy of: https://github.com/russolsen/ham_radio_question_pool")
            return True
            
        except Exception as e:
            print("Error downloading {}: {}".format(filename, e))
            return False
        
    def load_question_pools(self):
        """Load question pools from JSON files, downloading if necessary"""
        for exam_type, spec in EXAM_SPECS.items():
            file_path = os.path.join(QUESTION_POOLS_DIR, spec['file'])
            
            # Try to load existing file first
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.question_pools[exam_type] = json.load(f)
                    print("Loaded {} questions for {}".format(len(self.question_pools[exam_type]), spec['name']))
                    continue  # Successfully loaded, move to next exam type
                except Exception as e:
                    print("Error loading existing {}: {}".format(spec['file'], e))
                    # File exists but is corrupted, try to download fresh copy
            
            # File doesn't exist or is corrupted, try to download
            print("Question pool for {} not found locally".format(spec['name']))
            if self.download_question_pool(exam_type):
                # Try to load the downloaded file
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.question_pools[exam_type] = json.load(f)
                    print("Loaded {} questions for {}".format(len(self.question_pools[exam_type]), spec['name']))
                except Exception as e:
                    print("Error loading downloaded {}: {}".format(spec['file'], e))
            else:
                print("Could not obtain question pool for {}".format(spec['name']))
                print("Please check your internet connection or download manually from:")
                print("https://github.com/russolsen/ham_radio_question_pool")
    
    def display_logo(self):
        """Display ASCII art logo"""
        print("")
        print("  _    _          __  __ _______ ______  _____ _______ ")
        print(" | |  | |   /\\   |  \\/  |__   __|  ____|/ ____|__   __|")
        print(" | |__| |  /  \\  | \\  / |  | |  | |__  | (___    | |   ")
        print(" |  __  | / /\\ \\ | |\\/| |  | |  |  __|  \\___ \\   | |   ")
        print(" | |  | |/ ____ \\| |  | |  | |  | |____ ____) |  | |   ")
        print(" |_|  |_/_/    \\_\\_|  |_|  |_|  |______|_____/   |_|   ")
        print("")
        print(" Ham Radio License Test Practice")
        print(" Technician, General, and Extra class exams")
    
    def display_main_menu(self):
        """Display the main menu"""
        print("\n" + "="*78)
        print("AMATEUR RADIO LICENSE TEST PRACTICE")
        print("="*78)
        print()
        
        # Get current exam directory info for display
        directories = self.get_github_directories()
        
        for i, (exam_type, spec) in enumerate(EXAM_SPECS.items(), 1):
            available = "✓" if exam_type in self.question_pools else "✗"
            print("{}. {} [{}]".format(i, spec['name'], available))
            
            # Wrap the description text
            wrapped_desc = textwrap.fill(
                spec['description'], 
                width=LINE_WIDTH-6, 
                initial_indent="   ", 
                subsequent_indent="   "
            )
            print(wrapped_desc)
            
            if exam_type in self.question_pools:
                print("   {} questions, {} needed to pass (74%)".format(spec['questions'], spec['pass_score']))
                
                # Show exam validity period if available
                if exam_type in directories:
                    dir_info = directories[exam_type]
                    print("   Current exam pool: {}-{}".format(dir_info['start_year'], dir_info['end_year']))
            else:
                print("   Question pool not available")
                if exam_type in directories:
                    dir_info = directories[exam_type]
                    print("   Available to download: {}-{} pool".format(dir_info['start_year'], dir_info['end_year']))
            print()
        
        print("4. About Ham Radio Licensing")
        print("5. Update Question Pools")
        print("Q. Quit")
        print()
    
    def display_about(self):
        """Display information about ham radio licensing"""
        about_text = """
ABOUT AMATEUR RADIO LICENSING
=============================

Amateur radio operators in the United States must be licensed by the Federal
Communications Commission (FCC). There are three license classes currently
available:

TECHNICIAN CLASS (Entry Level)
- 35-question multiple choice exam
- Full privileges on all amateur bands above 30 MHz
- Limited privileges on some HF (high frequency) bands
- Great for local communications, repeaters, and emergency services

GENERAL CLASS (Intermediate Level)  
- Requires passing Technician exam first
- Additional 35-question multiple choice exam
- Access to significant portions of all amateur HF bands
- Enables worldwide communications via HF radio

AMATEUR EXTRA CLASS (Advanced Level)
- Requires passing Technician and General exams first  
- 50-question multiple choice exam covering advanced topics
- Full privileges on all amateur frequency bands
- Access to exclusive band segments

EXAM INFORMATION
- All exams are multiple choice with 4 possible answers
- Passing score is 74% (can miss 9 questions on Tech/General, 13 on Extra)
- Exams are administered by volunteer examiners (VEs)
- Current license fee is $35 (plus any VE session fees)
- Licenses are valid for 10 years

GETTING STARTED
- Study using question pools (same questions used on actual exams)
- Take practice tests until consistently scoring above 74%
- Find a local test session or take the exam online
- Start with Technician class and upgrade later if desired

For more information and to find test sessions near you, visit:
""" + ARRL_TEST_LOCATOR + """

QUESTION POOL SOURCE
Question pools courtesy of: https://github.com/russolsen/ham_radio_question_pool
"""

        # Wrap and display the text
        for line in about_text.split('\n'):
            if line.strip():
                wrapped = textwrap.fill(line, width=LINE_WIDTH)
                print(wrapped)
            else:
                print()
        
        print("\nPress Enter to return to main menu...")
        input()
    
    def update_question_pools(self):
        """Force update of all question pools from GitHub"""
        print("\nUpdating question pools from GitHub...")
        print("="*50)
        
        # Clear cached directory info to force fresh lookup
        self.github_directories = {}
        
        updated_count = 0
        for exam_type in EXAM_SPECS.keys():
            if self.download_question_pool(exam_type):
                updated_count += 1
        
        if updated_count > 0:
            print("\nSuccessfully updated {} question pool(s)".format(updated_count))
            print("Reloading question pools...")
            self.question_pools = {}
            self.load_question_pools()
        else:
            print("\nNo question pools were updated")
        
        input("\nPress Enter to continue...")
    
    def select_exam(self):
        """Allow user to select an exam type"""
        while True:
            try:
                choice = input("Select exam (1-5, Q): ").strip().upper()
                
                if choice == 'Q':
                    return None
                elif choice == '5':
                    self.update_question_pools()
                    return 'menu'
                elif choice == '4':
                    self.display_about()
                    return 'menu'
                elif choice in ['1', '2', '3']:
                    exam_types = list(EXAM_SPECS.keys())
                    selected_exam = exam_types[int(choice) - 1]
                    
                    if selected_exam not in self.question_pools:
                        print("\nThe {} question pool is not available.".format(EXAM_SPECS[selected_exam]['name']))
                        print("Would you like to try downloading it now? (y/n): ", end='')
                        
                        download_choice = input().strip().lower()
                        if download_choice in ['y', 'yes']:
                            if self.download_question_pool(selected_exam):
                                # Try to load the downloaded file
                                file_path = os.path.join(QUESTION_POOLS_DIR, EXAM_SPECS[selected_exam]['file'])
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        self.question_pools[selected_exam] = json.load(f)
                                    print("Successfully loaded {} question pool!".format(EXAM_SPECS[selected_exam]['name']))
                                    return selected_exam
                                except Exception as e:
                                    print("Error loading downloaded file: {}".format(e))
                            else:
                                print("Download failed. Please check your internet connection.")
                        
                        input("Press Enter to continue...")
                        return 'menu'
                    
                    return selected_exam
                else:
                    print("Please enter 1, 2, 3, 4, 5, or 6.")
                    
            except (ValueError, KeyboardInterrupt):
                print("Please enter 1, 2, 3, 4, 5, or 6.")
    
    def create_exam(self, exam_type):
        """Create a randomized exam from the question pool"""
        if exam_type not in self.question_pools:
            return None
            
        questions = self.question_pools[exam_type]
        spec = EXAM_SPECS[exam_type]
        
        # Group questions by subelement
        subelements = defaultdict(list)
        for question in questions:
            subelement = question['id'][:3]  # First 3 characters (e.g., 'T1A')
            subelements[subelement].append(question)
        
        # Select one question randomly from each subelement
        exam_questions = []
        subelement_keys = sorted(subelements.keys())
        
        if len(subelement_keys) < spec['subelements']:
            print("Warning: Expected {} subelements, found {}".format(spec['subelements'], len(subelement_keys)))
        
        # Select required number of questions
        for i in range(spec['questions']):
            if i < len(subelement_keys):
                subelement = subelement_keys[i]
                question = random.choice(subelements[subelement])
                exam_questions.append(question.copy())
        
        # Shuffle the questions and randomize answer order
        random.shuffle(exam_questions)
        
        for question in exam_questions:
            # Randomize answer order
            correct_answer = question['answers'][question['correct']]
            random.shuffle(question['answers'])
            question['correct'] = question['answers'].index(correct_answer)
        
        return exam_questions
    
    def display_question(self, question_num, total_questions, question):
        """Display a single question"""
        print("\nQuestion {} of {}".format(question_num, total_questions))
        print("="*50)
        
        # Wrap question text
        wrapped_question = textwrap.fill(
            question['question'], 
            width=LINE_WIDTH,
            initial_indent="",
            subsequent_indent=""
        )
        print(wrapped_question)
        print()
        
        # Display answer choices
        for i, answer in enumerate(question['answers']):
            letter = chr(ord('A') + i)
            wrapped_answer = textwrap.fill(
                answer,
                width=LINE_WIDTH-4,
                initial_indent="{}. ".format(letter),
                subsequent_indent="   "
            )
            print(wrapped_answer)
        print()
    
    def get_user_answer(self):
        """Get user's answer choice"""
        while True:
            try:
                answer = input("Your answer (A, B, C, D, or Q to quit): ").strip().upper()
                if answer in ['A', 'B', 'C', 'D']:
                    return ord(answer) - ord('A')  # Convert to 0-based index
                elif answer == 'Q':
                    return None  # Quit signal
                else:
                    print("Please enter A, B, C, D, or Q to quit.")
            except (KeyboardInterrupt, EOFError):
                return None
    
    def run_exam(self, exam_type):
        """Run a complete exam"""
        spec = EXAM_SPECS[exam_type]
        print("\nPreparing {} Practice Exam...".format(spec['name']))
        print("This exam has {} questions.".format(spec['questions']))
        print("You need {} correct answers to pass (74%).".format(spec['pass_score']))
        print("\nPress Enter to begin, or 'q' to return to menu...")
        
        user_input = input().strip().lower()
        if user_input == 'q':
            return
        
        # Create the exam
        exam_questions = self.create_exam(exam_type)
        if not exam_questions:
            print("Error creating exam.")
            return
        
        # Administer the exam
        user_answers = []
        correct_count = 0
        
        for i, question in enumerate(exam_questions, 1):
            self.display_question(i, len(exam_questions), question)
            
            user_answer = self.get_user_answer()
            if user_answer is None:  # User quit
                print("\nExam stopped. Returning to main menu...")
                return
            
            user_answers.append(user_answer)
            
            # Check if answer is correct
            is_correct = user_answer == question['correct']
            if is_correct:
                correct_count += 1
            
            # Show immediate feedback
            correct_letter = chr(ord('A') + question['correct'])
            user_letter = chr(ord('A') + user_answer)
            
            if is_correct:
                print("✓ Correct! The answer is {}.".format(correct_letter))
            else:
                print("✗ Incorrect. The correct answer is {}, you answered {}.".format(correct_letter, user_letter))
            
            # Show progress
            print("Score so far: {}/{} ({:.1f}%)".format(correct_count, i, correct_count/i*100))
            
            if i < len(exam_questions):
                input("\nPress Enter for next question...")
        
        # Display final results
        self.display_exam_results(exam_type, correct_count, len(exam_questions))
    
    def display_exam_results(self, exam_type, correct_count, total_questions):
        """Display final exam results"""
        spec = EXAM_SPECS[exam_type]
        percentage = (correct_count / total_questions) * 100
        passed = correct_count >= spec['pass_score']
        
        print("\n" + "="*78)
        print("EXAM RESULTS")
        print("="*78)
        print("License Class: {}".format(spec['name']))
        print("Questions Answered: {}".format(total_questions))
        print("Correct Answers: {}".format(correct_count))
        print("Score: {:.1f}%".format(percentage))
        print("Passing Score: 74% ({} correct)".format(spec['pass_score']))
        print()
        
        if passed:
            print("🎉 CONGRATULATIONS! YOU PASSED! 🎉")
            print()
            print("You have demonstrated the knowledge required for the")
            print("{} amateur radio license.".format(spec['name']))
            print()
            print("NEXT STEPS:")
            print("1. Find a Volunteer Examiner (VE) test session in your area")
            print("2. Bring required identification and any certificates of completion")
            print("3. Pay the $35 FCC application fee (plus any VE session fees)")
            print("4. Take the actual exam with volunteer examiners")
            print()
            print("To find test sessions near you, visit:")
            print(ARRL_TEST_LOCATOR)
            
            # Suggest next license level
            if exam_type == 'technician':
                print("\nOnce you get your Technician license, consider upgrading")
                print("to General class for HF (shortwave) privileges!")
            elif exam_type == 'general':
                print("\nOnce you get your General license, consider upgrading")
                print("to Amateur Extra class for full amateur radio privileges!")
                
        else:
            missed = total_questions - correct_count
            need_more = spec['pass_score'] - correct_count
            
            print("❌ Sorry, you did not pass this time.")
            print()
            print("You missed {} questions.".format(missed))
            print("You need {} more correct answers to pass.".format(need_more))
            print()
            print("STUDY SUGGESTIONS:")
            print("- Review the question pool and study materials")
            print("- Take more practice exams until consistently scoring >74%")
            print("- Consider taking a license preparation class")
            print("- Use ARRL study guides or online training courses")
            print()
            print("Don't give up! Many successful hams needed multiple attempts.")
        
        print("\nPress Enter to return to main menu...")
        input()
    
    def run(self):
        """Main application loop"""
        self.display_logo()
        
        # Show initial status
        if not self.question_pools:
            print("\nNo question pools are currently loaded.")
            print("The application will attempt to download them from GitHub...")
        
        while True:
            self.display_main_menu()
            exam_choice = self.select_exam()
            
            if exam_choice is None:  # Quit
                break
            elif exam_choice == 'menu':  # Return to menu
                continue
            else:
                self.run_exam(exam_choice)
        
        print("\n73! (Best wishes in amateur radio)")
        print("Thanks for using the Ham Radio License Tester!")


def main():
    """Main entry point"""
    try:
        app = HamTestApp()
        app.run()
    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print("\nError: {}".format(e))
        print("Please report this issue if it persists.")


if __name__ == "__main__":
    main()
