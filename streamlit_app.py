import streamlit as st
import re
import pandas as pd
from firebase_admin import credentials, firestore, initialize_app, get_app
from datetime import datetime

def init_firebase():
    try:
        # Attempt to get an existing app, if it fails, initialize a new one
        return get_app()
    except ValueError:
        # Initialize Firebase Admin using Streamlit secrets
        firebase_creds = credentials.Certificate({
            "type": st.secrets["gcp_service_account"]["type"],
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": st.secrets["gcp_service_account"]["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
            "universe_domain": st.secrets["gcp_service_account"]["universe_domain"]
        })
        return initialize_app(firebase_creds)
    
# Initialize Firebase
default_app = init_firebase()
db = firestore.client()
scoreboard_ref = db.collection('scoreboard')

def validate_int_sequence(value):
    # Validates that the sequence is exactly 10000 digits and contains only integers
    return re.fullmatch(r'\d{10000}', value)

def validate_github_url(url):
    # This regex matches typical GitHub repository URLs
    return re.match(r'https://github\.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/?$', url)

def calculate_matches(sequence, predefined_sequence):
    # Placeholder for calculating matches against a predefined sequence
    return sum(1 for a, b in zip(sequence, predefined_sequence) if a == b)

# Placeholder for predefined sequence
flatland_test = st.secrets["secure_data"]["flatland_test"]

st.title('Flatland Submission')

st.write("""
More details about the task: https://trokas.github.io/ai_primer/Project.html.
- **Sequence Format:** Enter your sequence as a continuous string of digits without any spaces or commas.
- **Repository:** Make sure your GitHub repository is public or accessible via the link you provide.
- **Accuracy:** Your submission should contain number of angles the figure has in provided test set. You can concatenate predictions using `''.join([str(round(p)) for p in pred])`.
- **Updates:** The scoreboard updates instantly after each submission to reflect the most recent scores.
""")

with st.form("student_form"):
    student_name = st.text_input("Student Name", '')
    git_repo = st.text_input("GitHub Repo Link", '')
    integer_sequence = st.text_input("Enter a sequence of 10000 integers (no separators)", '')

    submitted = st.form_submit_button("Submit")

    if submitted:
        if not student_name or not git_repo or not integer_sequence:
            st.error("All fields are required.")
        elif not validate_int_sequence(integer_sequence):
            st.error("The integer sequence must be exactly 10000 digits long and only contain digits.")
        elif not validate_github_url(git_repo):
            st.error("The GitHub URL is not valid. It should be formatted like 'https://github.com/[username]/[repo]'.")
        else:
            # Calculate match score
            matches = calculate_matches(integer_sequence, flatland_test)
            accuracy = matches / len(flatland_test)
            st.success(f"{student_name}, your submission was successful! You got {accuracy:.02%} accuracy.")
            
            # Add to Firestore database
            doc_ref = scoreboard_ref.document(student_name)
            doc_ref.set({
                'student_name': student_name,
                'github_repo': git_repo,
                'score': accuracy,
                'last_submission': datetime.now().isoformat()
            })

            st.write('Scoreboard Updated!')

# To display the scoreboard as a nice table:
scoreboard = scoreboard_ref.get()
if scoreboard:
    scoreboard_data = [
        {'Student Name': doc.to_dict()['student_name'],
        'GitHub Repo': f"<a href='{doc.to_dict()['github_repo']}' target='_blank'>{doc.to_dict()['github_repo']}</a>",
        'Score': f"{doc.to_dict()['score']:.02%}",  # Format score as a percentage string
        'Last Submission': doc.to_dict().get('last_submission', None)} for doc in scoreboard]
    df_scoreboard = pd.DataFrame(scoreboard_data)

    # Filter to only the latest entry per student
    df_scoreboard['Last Submission'] = pd.to_datetime(df_scoreboard['Last Submission'])
    latest_entries = df_scoreboard.sort_values('Last Submission').drop_duplicates('Student Name', keep='last')
    latest_entries = latest_entries.sort_values(by='Score', ascending=False).reset_index(drop=True)

    # st.table(latest_entries)

    html = latest_entries.to_html(escape=False, index=False)
    st.markdown(html, unsafe_allow_html=True)

