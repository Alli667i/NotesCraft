import google.generativeai as genai
import requests
from dotenv import load_dotenv
import os
from Instructions_for_Notes_genearation import for_detail_notes
import re
import json


load_dotenv()




GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

def safe_get_text(response):
    try:
        if not response:
            return None

        if hasattr(response, "candidates") and response.candidates:
            for candidate in response.candidates:
                if hasattr(candidate, "content") and candidate.content and candidate.content.parts:
                    return "".join([getattr(p, "text", "") for p in candidate.content.parts])
        return None
    except Exception as e:
        print(f"⚠️ Error extracting text: {e}")
        return None

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

    total_tokens_used = 0

    total_input_tokens_used = 0

    total_output_tokens_used = 0


    for number ,(topic, content) in enumerate(book_text.items() , start=1):  # This loop gets the content from the  dictionary and pass it over to LLM one by one
        response = model.generate_content(f"{topic} {content}")
        response_validated = safe_get_text(response)
        collect_response.append(response_validated)

        print(f"Input Tokens for request({number}):", response.usage_metadata.prompt_token_count)

        print(f"Output Tokens for request({number}):", response.usage_metadata.candidates_token_count)

        print(f"Total Tokens for request({number}):{response.usage_metadata.total_token_count}\n")

        total_input_tokens_used += response.usage_metadata.prompt_token_count

        total_output_tokens_used += response.usage_metadata.candidates_token_count

        total_tokens_used += response.usage_metadata.total_token_count


    for each in collect_response: # This loop will

        cleaned = clean_raw_json(each)

        cleaned_response.append(cleaned)

    # This variable will combine all the items of the list making it a single json array

    connect_all_json = ",".join(cleaned_response)


    # This will add [] brackets to the json array
    full_json_array = "[" + connect_all_json + "]"


    print(f"\nTotal Tokens Used: {total_tokens_used}")

    print(f"\nTotal Input Tokens Used: {total_input_tokens_used}")

    print(f"\nTotal Output Tokens Used: {total_output_tokens_used}")


    print(f"\nGenerated raw Notes: {full_json_array}")

    #This will verify if the whole json is correct and good to use if yes then return it as it is else it will fix it and assign to this variable
    final_json_array = validate_and_fix_json(full_json_array)


    # print(f"Notes validated: {final_json_array}")

    # It will convert dictionary to json string

    json_str = json.dumps(final_json_array)

    generated_json_for_word = json.loads(json_str)


    print(f"\nFinal Notes Generated: {generated_json_for_word}")

    return generated_json_for_word
