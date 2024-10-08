import requests

# Base URL for the request
base_url = "http://127.0.0.1:5000/hud"

# List of test student names
test_students = [
    "A",
    "John Doe",
    "Jane Smith",
    "Alice Wonderland",
    "Bob",
    "InvalidName123",  # Example of an invalid name
    " "  # Example of a name with just a space
]

# Iterate through the test names and make requests
for student in test_students:
    # URL encode the student name
    encoded_student = requests.utils.quote(student)
    url = f"{base_url}?student={encoded_student}"

    try:
        # Make the GET request
        response = requests.get(url)

        # Print the response status code and content
        print(f"Testing with student='{student}'")
        print(f"Response Code: {response.status_code}")
        if response.status_code == 200:
            print("Response Content:", response.content)
        else:
            print("Error Message:", response.text)
        print("-" * 40)

    except Exception as e:
        print(f"An error occurred: {e}")
