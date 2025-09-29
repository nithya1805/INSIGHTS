import streamlit as st
import pandas as pd
import time
from openai import OpenAI

st.set_page_config(page_title="Ritual Data Insights", layout="wide")
st.title("Ritual Data Insights Analyzer")

# -------------------------------
# Upload files and API key
# -------------------------------
st.sidebar.header("Upload Files and Enter API Key")
primary_file = st.sidebar.file_uploader("Upload Primary Excel File", type=["xlsx"])
mapped_file = st.sidebar.file_uploader("Upload Mapped Excel File", type=["xlsx"])
api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")

# Require both files
if not primary_file or not mapped_file:
    st.warning("Please upload both Primary Excel and Mapped Excel files to proceed.")
    st.stop()

if not api_key:
    st.warning("Please enter your OpenAI API key to generate descriptions.")
    st.stop()

# -------------------------------
# Read Excel files
# -------------------------------
df = pd.read_excel(primary_file)
df.columns = df.columns.str.strip()

mapped_df = pd.read_excel(mapped_file)
mapped_df.columns = mapped_df.columns.str.strip()

# -------------------------------
# Basic counts
# -------------------------------
total_individuals = df['Individual ID'].count()
total_families = df['Group ID'].nunique()

# -------------------------------
# Gender distribution
# -------------------------------
if "Gender" in df.columns:
    male_count = (df['Gender'].astype(str).str.strip() == "पुरुष").sum()
    female_count = (df['Gender'].astype(str).str.strip() == "महिला").sum()
    male_percent = (male_count / total_individuals * 100) if total_individuals > 0 else 0
    female_percent = (female_count / total_individuals * 100) if total_individuals > 0 else 0

    year_col_candidates = ["Year", "year", "Ritual Year", "RitualYear"]
    year_col = next((c for c in year_col_candidates if c in df.columns), None)

    year_male_str = year_female_str = ""
    if year_col:
        grouped = df.groupby([year_col, 'Gender']).size().unstack(fill_value=0)
        if "पुरुष" in grouped.columns:
            year_high_male = grouped["पुरुष"].idxmax()
            male_val = grouped["पुरुष"].max()
            year_male_str = f"; Year with highest male count: {year_high_male} ({male_val} पुरुष)"
        if "महिला" in grouped.columns:
            year_high_female = grouped["महिला"].idxmax()
            female_val = grouped["महिला"].max()
            year_female_str = f"; Year with highest female count: {year_high_female} ({female_val} महिला)"

    gender_distribution = (
        f"Gender Distribution :\n"
        f"  Males   - {male_count} | Percentage: {male_percent:.2f}%{year_male_str}\n"
        f"  Females - {female_count} | Percentage: {female_percent:.2f}%{year_female_str}"
    )
else:
    gender_distribution = "Gender column not found in the data."

# -------------------------------
# Top Villages
# -------------------------------
if "Village/City" in df.columns and "Group ID" in df.columns:
    families = df[['Group ID', 'Village/City']].drop_duplicates(subset=['Group ID'])
    village_counts = families.groupby('Village/City')['Group ID'].nunique().sort_values(ascending=False).head(5)
    top_villages_description = "\n".join([f"{i+1}. {v} ({c})" for i, (v, c) in enumerate(village_counts.items())])
else:
    top_villages_description = "Village/City column or Group ID column not found."

# -------------------------------
# Top Castes
# -------------------------------
if "Caste" in df.columns and "Group ID" in df.columns:
    families_caste = df[['Group ID', 'Caste']].drop_duplicates(subset=['Group ID'])
    caste_counts = families_caste.groupby('Caste')['Group ID'].nunique().sort_values(ascending=False).head(5)
    top_castes_description = "\n".join([f"{i+1}. {c} ({cnt})" for i, (c, cnt) in enumerate(caste_counts.items())])
else:
    top_castes_description = "Caste column or Group ID column not found."

# -------------------------------
# Top Years
# -------------------------------
year_col_candidates = ["Year", "year", "Ritual Year", "RitualYear"]
year_col = next((c for c in year_col_candidates if c in df.columns), None)

if year_col and "Group ID" in df.columns:
    families_year = df[[year_col, 'Group ID']].drop_duplicates(subset=['Group ID'])
    year_counts = families_year.groupby(year_col)['Group ID'].nunique().sort_values(ascending=False).head(5)
    top_years_description = "\n".join([f"{i+1}. {y} ({cnt})" for i, (y, cnt) in enumerate(year_counts.items())])
else:
    top_years_description = "Year column or Group ID column not found."

# -------------------------------
# Unique Rituals
# -------------------------------
if "Ritual Name 1" in df.columns:
    unique_rituals_list = ", ".join(df["Ritual Name 1"].dropna().unique())
    unique_rituals_description = f"{unique_rituals_list}"
else:
    unique_rituals_description = "Ritual Name 1 column not found."

# -------------------------------
# Seasonal Trends
# -------------------------------
if "Month" in df.columns and "Group ID" in df.columns:
    hindi_to_english = {
        "जनवरी": "January", "फ़रवरी": "February", "मार्च": "March",
        "अप्रैल": "April", "मई": "May", "जून": "June",
        "जुलाई": "July", "अगस्त": "August", "सितंबर": "September",
        "अक्टूबर": "October", "नवंबर": "November", "दिसंबर": "December"
    }
    df["Month"] = df["Month"].astype(str).str.strip().map(hindi_to_english)
    df = df[df["Month"].notna()]
    families_month = df[['Group ID', 'Month']].drop_duplicates(subset=['Group ID', 'Month'])
    month_counts = families_month.groupby("Month")['Group ID'].nunique()
    if not month_counts.empty:
        most_month = month_counts.idxmax()
        avg_value = month_counts.mean()
        avg_month = (month_counts - avg_value).abs().idxmin()
        seasonal_description = f"Most Rituals: {most_month}\nAverage Month: {avg_month}"
    else:
        seasonal_description = "No valid month data available."
else:
    seasonal_description = "Month column not found."

# -------------------------------
# Repeated Families
# -------------------------------
if "Final Merged Family Id" in mapped_df.columns:
    groups_only = mapped_df["Final Merged Family Id"].dropna().astype(str)
    groups_only = groups_only[groups_only.str.startswith("GROUP")]
    repeated_families_count = groups_only.nunique()
    repeated_families_description = f"{repeated_families_count}"
else:
    repeated_families_description = "Mapped file missing 'Final Merged Family Id' column."
    repeated_families_count = None

# -------------------------------
# OpenAI Descriptions
# -------------------------------
client = OpenAI(api_key=api_key)
prompts = {
    "Individuals": f"Write a friendly description of Total Individuals: {total_individuals}.",
    "Families": f"Write a friendly description of Total Families: {total_families}.",
    "Gender": f"Write a friendly description of this gender distribution:\n{gender_distribution}",
    "Villages": f"Write a friendly description of top 5 villages:\n{top_villages_description}",
    "Castes": f"Write a friendly description of top 5 castes:\n{top_castes_description}",
    "Years": f"Write a friendly description of top 5 years:\n{top_years_description}",
    "Rituals": f"Write a friendly description of unique rituals:\n{unique_rituals_description}",
    "Seasonal": f"Write a friendly description of seasonal ritual trend:\n{seasonal_description}"
}
if repeated_families_count:
    prompts["Repeated"] = f"Explain repeated families: {repeated_families_count}"

st.subheader("Generated Descriptions:")
for key, prompt in prompts.items():
    try:
        with st.spinner(f"Generating description for {key}..."):
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )
            text = response.choices[0].message.content.strip()
            st.markdown(f"**{key}:** {text}")
    except Exception as e:
        st.error(f"Error generating description for {key}: {str(e)}")

# -------------------------------
# Display Raw Insights
# -------------------------------
st.subheader("Raw Data Insights")
st.markdown(f"- Total Individuals: {total_individuals}")
st.markdown(f"- Total Families: {total_families}")
st.markdown(f"- Gender Distribution:\n```\n{gender_distribution}\n```")
st.markdown(f"- Top Villages:\n```\n{top_villages_description}\n```")
st.markdown(f"- Top Castes:\n```\n{top_castes_description}\n```")
st.markdown(f"- Top Years:\n```\n{top_years_description}\n```")
st.markdown(f"- Unique Rituals:\n```\n{unique_rituals_description}\n```")
st.markdown(f"- Seasonal Trends:\n```\n{seasonal_description}\n```")
if repeated_families_description:
    st.markdown(f"- Repeated Families: {repeated_families_description}")
