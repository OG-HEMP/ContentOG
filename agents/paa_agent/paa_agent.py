from skills.paa_extraction.paa_extraction import extract_paa_questions

class PaaAgent:
    def run(self):
        print("Agent: PAA Agent is running...")
        questions = extract_paa_questions("placeholder keyword")
        print(f"Agent: Extracted {len(questions)} PAA questions")
