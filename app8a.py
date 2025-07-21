import streamlit as st
import pandas as pd
import pdfplumber
import re
from collections import Counter

st.set_page_config(page_title="PDF Glossary Checker", layout="centered")

st.title("Glossary Checker")

# File uploads
glossary_file = st.file_uploader("Upload Glossary (Excel .xlsx)", type=["xlsx"])
source_pdf = st.file_uploader("Upload Source Language PDF", type=["pdf"])
target_pdf = st.file_uploader("Upload Target Language PDF", type=["pdf"])
benchmark_pdf = st.file_uploader("Upload Benchmark PDF (optional)", type=["pdf"])

def extract_text_from_pdf(file):
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + " "
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text.lower()

def normalize_text(text):
    return text.lower().strip()

def count_terms(text, terms):
    counter = Counter()
    for term in terms:
        pattern = r'\b' + re.escape(term.lower()) + r'\b'
        matches = re.findall(pattern, text)
        counter[term] = len(matches)
    return counter

def calculate_kpis(words, translations, source_counts, target_counts):
    utilized_terms_count = sum(
        1 for w, t in zip(words, translations)
        if source_counts.get(w, 0) > 0 and target_counts.get(t, 0) > 0
    )
    total_glossary_terms = len(words)
    utilization_rate = (utilized_terms_count / total_glossary_terms * 100) if total_glossary_terms else 0

    total_source_counts = sum(source_counts.get(w, 0) for w in words)
    total_target_counts = sum(target_counts.get(t, 0) for t in translations)
    total_count_discrepancy = abs(total_source_counts - total_target_counts)

    return {
        'utilization_rate': utilization_rate,
        'total_count_discrepancy': total_count_discrepancy,
        'total_source_counts': total_source_counts,
        'total_target_counts': total_target_counts
    }

def calculate_translation_coverage_rate(words, translations, source_counts, target_counts):
    source_positive_terms = [(w, t) for w, t in zip(words, translations) if source_counts.get(w, 0) > 0]
    translated_positive_count = sum(1 for w, t in source_positive_terms if target_counts.get(t, 0) > 0)
    total_source_positive = len(source_positive_terms)
    coverage_rate = (translated_positive_count / total_source_positive * 100) if total_source_positive else 0
    return coverage_rate

if st.button("Process Files"):
    if not glossary_file or not source_pdf or not target_pdf:
        st.error("Please upload glossary, source PDF, and target PDF files.")
    else:
        try:
            # Read glossary Excel
            try:
                df = pd.read_excel(glossary_file)
            except Exception as e:
                st.error(f"Error reading Excel file: {e}")
                st.stop()

            if not {'word', 'translations'}.issubset(set(df.columns.str.lower())):
                st.error("Glossary Excel must contain 'word' and 'translations' columns.")
                st.stop()

            df.columns = [col.lower() for col in df.columns]
            words = df['word'].astype(str).tolist()
            translations = df['translations'].astype(str).tolist()

            # Extract text from PDFs
            try:
                source_text = extract_text_from_pdf(source_pdf)
            except Exception as e:
                st.error(f"Error reading source PDF: {e}")
                st.stop()

            try:
                target_text = extract_text_from_pdf(target_pdf)
            except Exception as e:
                st.error(f"Error reading target PDF: {e}")
                st.stop()

            benchmark_text = ""
            if benchmark_pdf:
                try:
                    benchmark_text = extract_text_from_pdf(benchmark_pdf)
                except Exception as e:
                    st.error(f"Error reading benchmark PDF: {e}")
                    st.stop()

            # Normalize terms and texts
            words = [normalize_text(w) for w in words]
            translations = [normalize_text(t) for t in translations]
            source_text = normalize_text(source_text)
            target_text = normalize_text(target_text)
            benchmark_text = normalize_text(benchmark_text) if benchmark_pdf else ""

            # Count occurrences
            source_counts = count_terms(source_text, words)
            target_counts = count_terms(target_text, translations)
            benchmark_counts = count_terms(benchmark_text, translations) if benchmark_pdf else None

            # Combine results for source and target
            combined_results = []
            for w, t in zip(words, translations):
                w_count = source_counts.get(w, 0)
                t_count = target_counts.get(t, 0)
                if w_count > 0 or t_count > 0:
                    combined_results.append({
                        'Word': w,
                        'Count in Source': w_count,
                        'Translation': t,
                        'Count in Target': t_count
                    })

            st.subheader("Word and Translation Counts (Source & Target)")
            st.dataframe(pd.DataFrame(combined_results))

            if benchmark_pdf:
                benchmark_results = []
                for w, t in zip(words, translations):
                    w_count = source_counts.get(w, 0)
                    b_count = benchmark_counts.get(t, 0)
                    if w_count > 0 or b_count > 0:
                        benchmark_results.append({
                            'Word': w,
                            'Count in Source': w_count,
                            'Translation': t,
                            'Count in Benchmark': b_count
                        })
                st.subheader("Word and Translation Counts (Source & Benchmark)")
                st.dataframe(pd.DataFrame(benchmark_results))

            # Calculate KPIs
            kpis_source_target = calculate_kpis(words, translations, source_counts, target_counts)
            coverage_rate = calculate_translation_coverage_rate(words, translations, source_counts, target_counts)

            st.subheader("KPIs (Source & Target)")
            st.markdown(f"""
            - **Glossary Utilization Rate:** {kpis_source_target['utilization_rate']:.2f} %  
            - **Glossary Translation Coverage Rate:** {coverage_rate:.2f} %  
            - **Total Count Discrepancy:** {kpis_source_target['total_count_discrepancy']}  
            - **Total Source Terms Count:** {kpis_source_target['total_source_counts']}  
            - **Total Translated Terms Count:** {kpis_source_target['total_target_counts']}  
            """)

            st.subheader("KPI Descriptions")
            st.markdown("""
            - **Glossary Utilization Rate:**  
              The percentage of glossary entries whose source terms appear at least once in the source document and whose corresponding translated terms also appear at least once in the target document.

            - **Glossary Translation Coverage Rate:**  
              The percentage of glossary terms that appear in the source document and whose translations also appear in the target document.  
              This metric reflects how well the glossary terms present in the source are covered by their translations.

            - **Total Count Discrepancy:**  
              The absolute difference between the total occurrences of all source terms and the total occurrences of all translated terms in the target document.

            - **Total Source Terms Count:**  
              The total number of occurrences of all glossary terms in the source document.

            - **Total Translated Terms Count:**  
              The total number of occurrences of all translated glossary terms in the target document.
            """)

            if benchmark_pdf:
                kpis_benchmark = calculate_kpis(words, translations, source_counts, benchmark_counts)
                st.subheader("KPIs (Source & Benchmark)")
                st.markdown(f"""
                - **Glossary Utilization Rate:** {kpis_benchmark['utilization_rate']:.2f} %  
                - **Total Count Discrepancy:** {kpis_benchmark['total_count_discrepancy']}  
                - **Total Source Terms Count:** {kpis_benchmark['total_source_counts']}  
                - **Total Translated Terms Count:** {kpis_benchmark['total_target_counts']}  
                """)

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
