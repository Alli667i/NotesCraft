import json
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()




GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# This function clean the raw json response given by the LLM
def clean_raw_json(raw_data):
    return raw_data.replace("```json", '').replace("```", '').replace("'", "").replace('[', '').replace(']', '')

# This function takes the text extracted(in the form of json array)  from the document given by the user and takes a name for the Word file that will be generated for the notes and pass over everything to the word file generating function
def generate_notes_from_content(user_instruction,book_text):

    genai.configure(api_key=GOOGLE_API_KEY)

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=user_instruction
    )

    collect_response = []  # This list will  collect all the responses from LLM (as there will be multiple responses of json arrays  so list will store each as an individual item)

    cleaned_response = []  # This list will store the LLM response after cleaning it ( by removing necessary things from our json array)

    content_fixed = json.loads(book_text) # This convert the received json array into a dictionary to extract content from it

    for topic, content in content_fixed.items():  # This loop gets the content from the  dictionary and pass it over to LLM one by one
        response = model.generate_content(f"{topic} {content}")
        collect_response.append(response.text)


    for each in collect_response: # This loop will
        cleaned = clean_raw_json(each)
        cleaned_response.append(cleaned)

    json_combined = ",".join(cleaned_response)  # This variable will combine all the items of the list making it a single json array

    content = "[" + json_combined + "]"


    generated_json_for_word = json.loads(content)



    return generated_json_for_word
