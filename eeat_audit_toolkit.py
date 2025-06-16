# Generating the final version of the Streamlit E-E-A-T Audit Toolkit with all features.

import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import spacy
from urllib.parse import urlparse
from fpdf import FPDF
import datetime

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Dandelion API Token
DANDELION_TOKEN = "928aeec989914427a4a2c1ddc0f5edf1"

st.set_page_config(page_title="E-E-A-T Audit Toolkit", layout="wide")
st.title("🔍 E-E-A-T Audit Toolkit")
st.markdown("Analyze Experience, Expertise, Authoritativeness, and Trustworthiness signals from any web page.")

url = st.text_input("Enter a URL to audit", "https://example.com")

def extract_dandelion_entities(text, token):
    endpoint = "https://api.dandelion.eu/datatxt/nex/v1/"
    params = {
        "text": text,
        "lang": "en",
        "min_confidence": 0.6,
        "include": "types,abstract,categories",
        "token": token
    }
    try:
        response = requests.get(endpoint, params=params)
        data = response.json()
        entities = [ann['spot'] for ann in data.get("annotations", [])]
        return entities
    except:
        return []

def generate_reputation_searches(domain):
    return {
        "Reddit": f"https://www.google.com/search?q=site:reddit.com+{domain}",
        "Wikipedia": f"https://www.google.com/search?q=site:wikipedia.org+{domain}",
        "TrustPilot": f"https://www.google.com/search?q=site:trustpilot.com+{domain}",
        "Quora": f"https://www.google.com/search?q=site:quora.com+{domain}"
    }

def estimate_domain_authority(domain):
    if "wikipedia" in domain:
        return 90
    elif "gov" in domain or "edu" in domain:
        return 80
    elif "wordpress.com" in domain or "medium.com" in domain:
        return 60
    else:
        return 40

def export_to_pdf(results, filename="eeat_audit_report.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="E-E-A-T Audit Report", ln=True, align='C')
    pdf.ln(10)
    for key, val in results.items():
        if isinstance(val, list):
            val = ", ".join(val)
        pdf.multi_cell(0, 10, txt=f"{key}: {val}")
    pdf.ln(5)
    pdf.cell(200, 10, txt=f"Generated on: {datetime.datetime.now()}", ln=True)
    pdf.output(filename)
    return filename

def score_experience(has_author, has_bio, updated_text):
    score = 0
    if has_author:
        score += 2
    if has_bio:
        score += 1
    if updated_text != "Not found":
        score += 2
    return min(score, 5)

def score_expertise(entity_count):
    if entity_count >= 10:
        return 5
    elif entity_count >= 7:
        return 4
    elif entity_count >= 5:
        return 3
    elif entity_count >= 3:
        return 2
    elif entity_count >= 1:
        return 1
    else:
        return 0

def score_authoritativeness(schema_types):
    score = 0
    if "Organization" in schema_types:
        score += 2
    if "Person" in schema_types:
        score += 2
    if "WebPage" in schema_types:
        score += 1
    return min(score, 5)

def score_trustworthiness(external_links):
    if len(external_links) >= 10:
        return 5
    elif len(external_links) >= 7:
        return 4
    elif len(external_links) >= 4:
        return 3
    elif len(external_links) >= 2:
        return 2
    elif len(external_links) >= 1:
        return 1
    else:
        return 0

if st.button("Run Audit"):
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)

        author = soup.find(attrs={"class": lambda x: x and "author" in x.lower()})
        bio = soup.find(attrs={"class": lambda x: x and "bio" in x.lower()})
        has_author = bool(author)
        has_bio = bool(bio)

        date_tags = soup.find_all(['time', 'span', 'p'])
        updated_text = "Not found"
        for tag in date_tags:
            if 'update' in tag.get_text().lower():
                updated_text = tag.get_text()
                break

        doc = nlp(text[:1000])
        spacy_entities = [(ent.text, ent.label_) for ent in doc.ents]
        entity_count = len(spacy_entities)

        dandelion_entities = extract_dandelion_entities(text[:1000], DANDELION_TOKEN)
        entity_count += len(dandelion_entities)

        links = [a['href'] for a in soup.find_all('a', href=True)]
        external = [l for l in links if 'http' in l and url not in l]

        schemas = soup.find_all('script', type='application/ld+json')
        schema_types = []
        for tag in schemas:
            try:
                data = json.loads(tag.string)
                if isinstance(data, dict):
                    t = data.get('@type', '')
                    if isinstance(t, list):
                        schema_types.extend(t)
                    else:
                        schema_types.append(t)
            except:
                continue

        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        reputation_links = generate_reputation_searches(domain)
        domain_authority = estimate_domain_authority(domain)

        # Scoring
        exp_score = score_experience(has_author, has_bio, updated_text)
        expertise_score = score_expertise(entity_count)
        auth_score = score_authoritativeness(schema_types)
        trust_score = score_trustworthiness(external)
        total_score = exp_score + expertise_score + auth_score + trust_score

        # Show Scores
        st.subheader("📊 E-E-A-T Scores")
        st.progress(exp_score / 5, text=f"Experience: {exp_score}/5")
        st.progress(expertise_score / 5, text=f"Expertise: {expertise_score}/5")
        st.progress(auth_score / 5, text=f"Authoritativeness: {auth_score}/5")
        st.progress(trust_score / 5, text=f"Trustworthiness: {trust_score}/5")
        st.success(f"🧠 Total E-E-A-T Score: {total_score}/20")

        st.subheader("🔗 SERP Reputation Checks")
        for label, link in reputation_links.items():
            st.markdown(f"[{label} Search]({link})")

        # Report dictionary
        report_data = {
            "URL": url,
            "Author Found": str(has_author),
            "Bio Found": str(has_bio),
            "Last Updated Text": updated_text,
            "Entities (spaCy + Dandelion)": list(set([e[0] for e in spacy_entities] + dandelion_entities))[:10],
            "Schema Types Found": list(set(schema_types)),
            "External Links Count": len(external),
            "Domain Authority Estimate": domain_authority,
            "Experience Score": f"{exp_score}/5",
            "Expertise Score": f"{expertise_score}/5",
            "Authoritativeness Score": f"{auth_score}/5",
            "Trustworthiness Score": f"{trust_score}/5",
            "Total E-E-A-T Score": f"{total_score}/20"
        }

        # Download button
        filename = "eeat_audit_report.pdf"
        export_to_pdf(report_data, filename)
        with open(filename, "rb") as file:
            st.download_button("📄 Download PDF Report", file, file_name=filename)

    except Exception as e:
        st.error(f"Error: {str(e)}")

