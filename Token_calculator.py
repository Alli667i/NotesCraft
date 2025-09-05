# def token_estimate(sys_ext, in_ext, out_ext, sys_notes, in_notes, out_notes, ratio=1.3):
#     # Step 1: Extraction
#     step1 = int((sys_ext + in_ext + out_ext) * ratio)
#
#     # Step 2: Notes
#     step2 = int((sys_notes + in_notes + out_notes) * ratio)
#
#     # Total
#     total = step1 + step2
#     return step1, step2, total
#
#
# # --- Main program ---
# print("🔢 Token Calculator for Notescraft (Extraction + Notes Generation)")
#
# # Step 1: Extraction
# sys_ext  = int(input("Enter system words for extraction: "))
# in_ext   = int(input("Enter input words for extraction: "))
# out_ext  = int(input("Enter output words from extraction: "))
#
# # Step 2: Notes
# sys_notes = int(input("Enter system words for notes: "))
# in_notes  = int(input("Enter input words for notes: "))
# out_notes = int(input("Enter output words from notes: "))
#
# # Calculate
# s1, s2, total = token_estimate(sys_ext, in_ext, out_ext, sys_notes, in_notes, out_notes)
#
# # Show result
# print("\n--- Results ---")
# print(f"Extraction Step Tokens : {s1}")
# print(f"Notes Step Tokens      : {s2}")
# print(f"Total Tokens           : {total}")


# Gemini Free Tier Limits
RPD = 250          # Requests per day
RPM = 10           # Requests per minute
TPM = 250_000      # Tokens per minute

def calculate_pages(requests_per_page, tokens_per_page):
    # Daily limit (based on requests)
    max_pages_day = RPD // requests_per_page

    # Minute limit (based on requests)
    max_pages_minute_req = RPM // requests_per_page

    # Minute limit (based on tokens)
    max_pages_minute_tok = TPM // tokens_per_page

    # Actual pages per minute (minimum of both limits)
    max_pages_minute = min(max_pages_minute_req, max_pages_minute_tok)

    return max_pages_day, max_pages_minute


if __name__ == "__main__":
    # Take user input
    requests_per_page = int(input("Enter requests per page: "))
    tokens_per_page = int(input("Enter tokens per page: "))

    pages_day, pages_minute = calculate_pages(requests_per_page, tokens_per_page)

    print("\n=== Gemini Free Tier Page Processing ===")
    print(f"📘 Max pages per day    : {pages_day}")
    print(f"⏱️ Max pages per minute : {pages_minute}")
