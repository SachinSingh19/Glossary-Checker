import streamlit as st
import pandas as pd
import PyPDF2
from collections import Counter

st.set_page_config(page_title="PDF Glossary Checker", layout="centered")

st.title("PDF Glossary Checker")

# File uploads
glossary_file = st.file_uploader("Upload Glossary (Excel .xlsx)", type=["xlsx"])
source_pdf = st.file_uploader("Upload Source Language PDF", type=["pdf"])
target_pdf = st.file_uploader("Upload Target Language PDF", type=["pdf"])
benchmark_pdf = st.file_uploader("Upload Benchmark PDF (optional)", type=["pdf"])

def extract_text_from_pdf(file):
    text = ""
    try:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
    return text.lower()

def count_terms(text, terms):
    counter = Counter()
    for term in terms:
        counter[term] = text.count(term.lower())
    return counter

def calculate_kpis(words, translations, source_counts, target_counts):
    translated_terms_count = sum(1 for row in translations if target_counts.get(row, 0) > 0)
    total_translated_terms = len(translations)
    utilization_rate = (translated_terms_count / total_translated_terms * 100) if total_translated_terms else 0

    accurate_translations = sum(1 for w, t in zip(words, translations)
                                if source_counts.get(w, 0) == target_counts.get(t, 0) and source_counts.get(w, 0) > 0)
    accuracy_rate = (accurate_translations / total_translated_terms * 100) if total_translated_terms else 0

    total_source_counts = sum(source_counts.get(w, 0) for w in words)
    total_target_counts = sum(target_counts.get(t, 0) for t in translations)
    total_count_discrepancy = abs(total_source_counts - total_target_counts)

    total_source_terms = len(words)
    coverage_rate = (translated_terms_count / total_source_terms * 100) if total_source_terms else 0

    return {
        'utilization_rate': utilization_rate,
        'accuracy_rate': accuracy_rate,
        'total_count_discrepancy': total_count_discrepancy,
        'coverage_rate': coverage_rate,
        'total_source_counts': total_source_counts,
        'total_target_counts': total_target_counts
    }

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

            # Normalize column names
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

            # Display source-target table
            st.subheader("Word and Translation Counts (Source & Target)")
            st.dataframe(pd.DataFrame(combined_results))

            # If benchmark uploaded, show benchmark counts table
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

            # Calculate KPIs for source-target
            kpis_source_target = calculate_kpis(words, translations, source_counts, target_counts)

            st.subheader("KPIs (Source & Target)")
            st.markdown(f"""
            - **Glossary Utilization Rate:** {kpis_source_target['utilization_rate']:.2f} %  
            - **Translation Accuracy Rate:** {kpis_source_target['accuracy_rate']:.2f} %  
            - **Total Count Discrepancy:** {kpis_source_target['total_count_discrepancy']}  
            - **Translation Coverage Rate:** {kpis_source_target['coverage_rate']:.2f} %  
            - **Total Source Terms Count:** {kpis_source_target['total_source_counts']}  
            - **Total Translated Terms Count:** {kpis_source_target['total_target_counts']}  
            """)

            # Calculate KPIs for benchmark if available
            if benchmark_pdf:
                kpis_benchmark = calculate_kpis(words, translations, source_counts, benchmark_counts)
                st.subheader("KPIs (Source & Benchmark)")
                st.markdown(f"""
                - **Glossary Utilization Rate:** {kpis_benchmark['utilization_rate']:.2f} %  
                - **Translation Accuracy Rate:** {kpis_benchmark['accuracy_rate']:.2f} %  
                - **Total Count Discrepancy:** {kpis_benchmark['total_count_discrepancy']}  
                - **Translation Coverage Rate:** {kpis_benchmark['coverage_rate']:.2f} %  
                - **Total Source Terms Count:** {kpis_benchmark['total_source_counts']}  
                - **Total Translated Terms Count:** {kpis_benchmark['total_target_counts']}  
                """)

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
