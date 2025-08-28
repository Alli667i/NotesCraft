import google.generativeai as genai
from dotenv import load_dotenv
import os
from Instructions_for_Notes_genearation import for_detail_notes
import re
import json


load_dotenv()




GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")



# def validate_and_fix_json(ai_output: str):
#     """
#     Extracts objects from AI output (even if broken JSON) and returns valid JSON list.
#     Handles:
#     - Nested quotes in text
#     - Multi-line text
#     - Stray characters
#     """
#     # Remove stray characters like '-' outside objects
#     cleaned = re.sub(r'[\n\s]*[-]+[\s,]*', '', ai_output)
#
#     # Regex to capture type and text
#     # Non-greedy match for text to handle multi-line fields
#     pattern = r'"type"\s*:\s*"([^"]+)"\s*,\s*"text"\s*:\s*"([\s\S]*?)"(?=\s*(?:,\s*"?type"?\s*:|\s*\}))'
#
#     matches = re.findall(pattern, cleaned)
#     if not matches:
#         return {"error": "No valid objects found. AI output too malformed.", "original_output": ai_output}
#
#     result = []
#     for idx, (typ, text) in enumerate(matches):
#         # Escape inner quotes
#         text = text.replace('"', '\\"')
#         result.append({"type": typ.strip(), "text": text.strip()})
#
#     return result

def validate_and_fix_json(ai_output: str):
    """
    Validates and fixes AI JSON output.
    Handles:
    - Proper JSON directly (no regex needed)
    - Broken JSON with stray characters
    - Multi-line text fields
    """

    # Step 1: Try parsing directly
    try:
        parsed = json.loads(ai_output)
        # Ensure it’s always a list of objects
        if isinstance(parsed, dict):
            return [parsed]
        elif isinstance(parsed, list):
            return parsed
    except Exception:
        pass  # fall back to regex repair if json.loads fails

    # Step 2: Cleanup obvious junk
    cleaned = re.sub(r'[\n\s]*[-]+[\s,]*', '', ai_output)

    # Step 3: Regex to capture "type" and "text"
    pattern = r'"type"\s*:\s*"([^"]+)"\s*,\s*"text"\s*:\s*"([\s\S]*?)"(?=\s*(?:,\s*"?type"?\s*:|\s*\}))'
    matches = re.findall(pattern, cleaned)

    if not matches:
        return {
            "error": "No valid objects found. AI output too malformed.",
            "original_output": ai_output
        }

    # Step 4: Build list of dicts (no manual escaping!)
    result = []
    for typ, text in matches:
        result.append({"type": typ.strip(), "text": text.strip()})

    return result



# This function clean the raw json response given by the LLM
def clean_raw_json(raw_data):
    return raw_data.replace("```json", '').replace("```", '').replace("'", "").replace('[', '').replace(']', '')

# This function takes the text extracted(in the form of json array)  from the document given by the user and takes a name for the Word file that will be generated for the notes and pass over everything to the word file generating function
def generate_notes_from_content(book_text):

    genai.configure(api_key=GOOGLE_API_KEY)

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=for_detail_notes
    )

    collect_response = []  # This list will  collect all the responses from LLM (as there will be multiple responses of json arrays  so list will store each as an individual item)

    cleaned_response = []  # This list will store the LLM response after cleaning it ( by removing necessary things from our json array)

    # content_fixed = json.loads(book_text) # This convert the received json array into a dictionary to extract content from it

    content_fixed = book_text

    for topic, content in content_fixed.items():  # This loop gets the content from the  dictionary and pass it over to LLM one by one
        response = model.generate_content(f"{topic} {content}")
        collect_response.append(response.text)


    for each in collect_response: # This loop will

        cleaned = clean_raw_json(each)

        cleaned_response.append(cleaned)

    # This variable will combine all the items of the list making it a single json array
    connect_all_json = ",".join(cleaned_response)


    # This will add [] brackets to the json array
    full_json_array = "[" + connect_all_json + "]"

    print(type(full_json_array))

    print(f"Generated raw Notes: {full_json_array}")

    #This will verify if the whole json is correct and good to use if yes then return it as it is else it will fix it and assign to this variable
    final_json_array = validate_and_fix_json(full_json_array)

    print(type(final_json_array))

    print(f"Notes validated: {final_json_array}")

    # It will convert dictionary to json string

    json_str = json.dumps(final_json_array)

    generated_json_for_word = json.loads(json_str)

    print(type(generated_json_for_word))

    print(f"Final array for word doc: {generated_json_for_word}")

    return generated_json_for_word
