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

def calculate_kpis_fixed(words, translations, source_counts, target_counts):
    total_glossary_terms = len(words)
    source_positive_terms = [w for w in words if source_counts.get(w, 0) > 0]
    numerator = sum(
        1 for w, t in zip(words, translations)
        if source_counts.get(w, 0) > 0 and target_counts.get(t, 0) > 0
    )
    denominator_utilization = total_glossary_terms
    denominator_coverage = len(source_positive_terms)

    utilization_rate = (numerator / denominator_utilization * 100) if denominator_utilization else 0
    coverage_rate = (numerator / denominator_coverage * 100) if denominator_coverage else 0

    total_source_counts = sum(source_counts.get(w, 0) for w in words)
    total_target_counts = sum(target_counts.get(t, 0) for t in translations)
    total_count_discrepancy = abs(total_source_counts - total_target_counts)

    return {
        'utilization_rate': utilization_rate,
        'coverage_rate': coverage_rate,
        'total_count_discrepancy': total_count_discrepancy,
        'total_source_counts': total_source_counts,
        'total_target_counts': total_target_counts
    }

def calculate_term_frequency_mismatch(words, translations, source_counts, target_counts):
    mismatch_rates = []
    for w, t in zip(words, translations):
        source_count = source_counts.get(w, 0)
        target_count = target_counts.get(t, 0)
        denominator = source_count if source_count > 0 else 1  # avoid division by zero
        mismatch = abs(target_count - source_count) / denominator
        mismatch_rates.append(mismatch)
    sum_mismatch = sum(mismatch_rates)
    average_mismatch = sum_mismatch / len(mismatch_rates) if mismatch_rates else 0
    return sum_mismatch, average_mismatch

def count_positive_terms(words, translations, source_counts, target_counts):
    source_positive_count = sum(1 for w in words if source_counts.get(w, 0) > 0)
    target_positive_count = sum(1 for t in translations if target_counts.get(t, 0) > 0)
    return source_positive_count, target_positive_count

def count_both_positive_terms(words, translations, source_counts, target_counts):
    count = sum(
        1 for w, t in zip(words, translations)
        if source_counts.get(w, 0) > 0 and target_counts.get(t, 0) > 0
    )
    return count

if st.button("Process Files"):
    if not glossary_file or not source_pdf or not target_pdf:
        st.error("Please upload glossary, source PDF, and target PDF files.")
    else:
        try:
            # Read glossary Excel
            try:
                df = pd.read_excel(glossary_file)
                total_glossary_terms = len(df)  # Total terms excluding header
                st.write(f"Total number of glossary terms (excluding header): {total_glossary_terms}")
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
            kpis = calculate_kpis_fixed(words, translations, source_counts, target_counts)
            sum_mismatch, average_mismatch = calculate_term_frequency_mismatch(words, translations, source_counts, target_counts)
            source_positive_count, target_positive_count = count_positive_terms(words, translations, source_counts, target_counts)
            both_positive_count = count_both_positive_terms(words, translations, source_counts, target_counts)

            st.subheader("KPIs (Source & Target)")
            st.markdown(f"""
            - **Glossary Utilization Rate:** {kpis['utilization_rate']:.2f} %  
            - **Glossary Translation Coverage Rate:** {kpis['coverage_rate']:.2f} %  
            - **Total Count Discrepancy:** {kpis['total_count_discrepancy']}  
            - **Total Source Terms Count:** {kpis['total_source_counts']}  
            - **Total Translated Terms Count:** {kpis['total_target_counts']}  
            - **Sum of Term Frequency Mismatch Rates:** {sum_mismatch:.2f}  
            - **Average Term Frequency Mismatch Rate:** {average_mismatch:.2f}  
            - **Number of Source Terms with Count > 0:** {source_positive_count}  
            - **Number of Target Terms with Count > 0:** {target_positive_count}  
            - **Number of Terms with Both Source and Target Count > 0:** {both_positive_count}  
            """)

            st.subheader("KPI Descriptions")
            st.markdown("""
            - **Glossary Utilization Rate:**  
             (Number of glossary terms with both source count > 0 and target count > 0) / (Total glossary terms) × 100  
             The percentage of glossary entries for which the source term appears at least once in the source document and the corresponding translated term also appears at least once in the target document. This KPI measures how effectively the glossary terms are being applied in the translation when they are present in the source text. In other words, it reflects the proportion of glossary terms used in the source text that have been correctly utilized in the translation, indicating adherence to the glossary during the translation process.

            - **Glossary Translation Coverage Rate:**  
             (Number of glossary terms with both source count > 0 and target count > 0) / (Number of glossary terms with source count > 0) × 100  
             The percentage of glossary terms that appear in the source document and whose approved translations also appear in the target document, regardless of how many times they occur. This KPI measures the extent to which glossary terms present in the source text are covered by their translations in the target text. In other words, it shows how comprehensively the glossary terms from the source are represented in the translation, indicating the coverage of glossary terms in the translated content.

            - **Total Count Discrepancy:**  
              The absolute difference between the total occurrences of all source terms and the total occurrences of all translated terms in the target document.

            - **Total Source Terms Count:**  
              The total number of occurrences of all glossary terms in the source document.

            - **Total Translated Terms Count:**  
              The total number of occurrences of all translated glossary terms in the target document.

            - **Sum of Term Frequency Mismatch Rates:**  
              The total sum of the relative differences in term frequencies between the source and target texts across all glossary terms.

            - **Average Term Frequency Mismatch Rate:**  
              The average relative difference in term frequencies per glossary term, measures how much, on average, the frequency of glossary terms in the translation deviates from the source.
                A value of 0 means perfect frequency match; between 0 and 1 indicates moderate variation; above 1 signals significant overuse or underuse.
                High values may reveal inconsistencies, omissions, or stylistic differences affecting translation quality.
            - **Number of Source Terms with Count > 0:**  
              The count of glossary terms that appear at least once in the source document.

            - **Number of Target Terms with Count > 0:**  
              The count of glossary terms that appear at least once in the target document.

            - **Number of Terms with Both Source and Target Count > 0:**  
              The count of glossary terms that appear at least once in both the source and target documents.
            """)
        
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

                # KPIs for Source vs Benchmark (same as Source vs Target)
                kpis_benchmark = calculate_kpis_fixed(words, translations, source_counts, benchmark_counts)
                sum_mismatch_bench, average_mismatch_bench = calculate_term_frequency_mismatch(
                    words, translations, source_counts, benchmark_counts
                )
                source_positive_count_bench, benchmark_positive_count = count_positive_terms(
                    words, translations, source_counts, benchmark_counts
                )
                both_positive_count_bench = count_both_positive_terms(
                    words, translations, source_counts, benchmark_counts
                )

                st.subheader("KPIs (Source & Benchmark)")
                st.markdown(f"""
                - **Glossary Utilization Rate:** {kpis_benchmark['utilization_rate']:.2f} %  
                - **Glossary Translation Coverage Rate:** {kpis_benchmark['coverage_rate']:.2f} %  
                - **Total Count Discrepancy:** {kpis_benchmark['total_count_discrepancy']}  
                - **Total Source Terms Count:** {kpis_benchmark['total_source_counts']}  
                - **Total Translated Terms Count:** {kpis_benchmark['total_target_counts']}  
                - **Sum of Term Frequency Mismatch Rates:** {sum_mismatch_bench:.2f}  
                - **Average Term Frequency Mismatch Rate:** {average_mismatch_bench:.2f}  
                - **Number of Source Terms with Count > 0:** {source_positive_count_bench}  
                - **Number of Benchmark Terms with Count > 0:** {benchmark_positive_count}  
                - **Number of Terms with Both Source and Benchmark Count > 0:** {both_positive_count_bench}  
                """)

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
