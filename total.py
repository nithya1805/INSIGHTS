import streamlit as st
import pandas as pd
from openai import OpenAI

st.set_page_config(page_title="Ritual Data Insights", layout="wide")
st.title("Ritual Data Insights Analyzer")

# -------------------------------
# Upload files and API key
# -------------------------------
st.sidebar.header("Upload Files and Enter API Key")
primary_file = st.sidebar.file_uploader("Upload Primary (Cleaned) Excel File", type=["xlsx"])
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
# Helper for gender distribution
# -------------------------------
def compute_gender_distribution(data, id_col="Individual ID", group_col="Group ID"):
    total_individuals = data[id_col].count() if id_col in data.columns else 0
    total_families = data[group_col].nunique() if group_col in data.columns else 0

    if "Gender" in data.columns:
        male_count = (data['Gender'].astype(str).str.strip() == "पुरुष").sum()
        female_count = (data['Gender'].astype(str).str.strip() == "महिला").sum()
        male_percent = (male_count / total_individuals * 100) if total_individuals > 0 else 0
        female_percent = (female_count / total_individuals * 100) if total_individuals > 0 else 0

        year_col_candidates = ["Year", "year", "Ritual Year", "RitualYear"]
        year_col = next((c for c in year_col_candidates if c in data.columns), None)

        year_male_str = year_female_str = ""
        if year_col:
            grouped = data.groupby([year_col, 'Gender']).size().unstack(fill_value=0)
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

    return total_individuals, total_families, gender_distribution

# -------------------------------
# Insights for Cleaned file
# -------------------------------
clean_individuals, clean_families, clean_gender = compute_gender_distribution(df)

if "Village/City" in df.columns and "Group ID" in df.columns:
    families = df[['Group ID', 'Village/City']].drop_duplicates(subset=['Group ID'])
    clean_villages = families.groupby('Village/City')['Group ID'].nunique().sort_values(ascending=False).head(5)
    clean_villages_str = "\n".join([f"{i+1}. {v} ({c})" for i, (v, c) in enumerate(clean_villages.items())])
else:
    clean_villages_str = "Village/City column or Group ID column not found."

if "Caste" in df.columns and "Group ID" in df.columns:
    families_caste = df[['Group ID', 'Caste']].drop_duplicates(subset=['Group ID'])
    clean_castes = families_caste.groupby('Caste')['Group ID'].nunique().sort_values(ascending=False).head(5)
    clean_castes_str = "\n".join([f"{i+1}. {c} ({cnt})" for i, (c, cnt) in enumerate(clean_castes.items())])
else:
    clean_castes_str = "Caste column or Group ID column not found."

year_col_candidates = ["Year", "year", "Ritual Year", "RitualYear"]
year_col = next((c for c in year_col_candidates if c in df.columns), None)
if year_col and "Group ID" in df.columns:
    families_year = df[[year_col, 'Group ID']].drop_duplicates(subset=['Group ID'])
    clean_years = families_year.groupby(year_col)['Group ID'].nunique().sort_values(ascending=False).head(5)
    clean_years_str = "\n".join([f"{i+1}. {y} ({cnt})" for i, (y, cnt) in enumerate(clean_years.items())])
else:
    clean_years_str = "Year column or Group ID column not found."

if "Ritual Name 1" in df.columns:
    clean_rituals = ", ".join(df["Ritual Name 1"].dropna().unique())
else:
    clean_rituals = "Ritual Name 1 column not found."

# -------------------------------
# Insights for Mapped file (Advanced Analysis)
# -------------------------------
mapped_individuals, mapped_families, mapped_gender = compute_gender_distribution(
    mapped_df, id_col="Individual ID", group_col="Final Merged Family Id"
)

mapped_insights = {
    "Most Repeated Group": "Not available",
    "First Last Appearance": "Not available",
    "Seasonal Frequency": "Not available",
    "Timeline": "Not available",
    "Average Family Size": "Not available",
    "Origin": "Not available"
}

if mapped_df is not None and "Final Merged Family Id" in mapped_df.columns and "Family Id" in mapped_df.columns:
    groups_df = mapped_df[mapped_df["Final Merged Family Id"].astype(str).str.startswith("GROUP")].copy()
    group_counts = groups_df.groupby("Final Merged Family Id")["Family Id"].nunique()

    if not group_counts.empty:
        most_repeated_group = group_counts.idxmax()
        num_families = group_counts.max()
        most_repeated_families = groups_df[groups_df["Final Merged Family Id"] == most_repeated_group]["Family Id"].unique()

        mapped_insights["Most Repeated Group"] = (
            f"Most repeated GROUP is {most_repeated_group} with {num_families} distinct families."
        )

        if "Date of Ritual" in mapped_df.columns:
            family_data = mapped_df[mapped_df["Family Id"].isin(most_repeated_families)].copy()

            # Hindi month mapping
            hindi_months = {
                'जनवरी': 'January','फरवरी': 'February','मार्च': 'March','अप्रैल': 'April','मई': 'May','जून': 'June',
                'जुलाई': 'July','अगस्त': 'August','सितंबर': 'September','अक्टूबर': 'October','नवंबर': 'November','दिसंबर': 'December'
            }
            def normalize_hindi_date(date_str):
                if pd.isna(date_str) or not isinstance(date_str, str): return None
                for hin, eng in hindi_months.items():
                    if hin in date_str: date_str = date_str.replace(hin, eng); break
                return date_str.strip()

            family_data["Date of Ritual"] = pd.to_datetime(
                family_data["Date of Ritual"].apply(normalize_hindi_date),
                format='%d %B %Y', dayfirst=True, errors='coerce'
            )
            valid_dates = family_data["Date of Ritual"].dropna()

            if not valid_dates.empty:
                first_date = valid_dates.min().strftime("%d %B %Y")
                last_date = valid_dates.max().strftime("%d %B %Y")
                mapped_insights["First Last Appearance"] = f"First Appearance: {first_date}\nLast Appearance: {last_date}"
            elif "Year" in family_data.columns:
                years = pd.to_numeric(family_data["Year"], errors="coerce").dropna()
                if not years.empty:
                    mapped_insights["First Last Appearance"] = (
                        f"First Appearance (Year): {int(years.min())}\nLast Appearance (Year): {int(years.max())}"
                    )

            # Seasonal frequency
            if not family_data["Date of Ritual"].isna().all():
                family_data["Month"] = family_data["Date of Ritual"].dt.month_name()
                month_counts = family_data.groupby("Month")["Family Id"].nunique()
                if not month_counts.empty:
                    most_common_month = month_counts.idxmax()
                    mapped_insights["Seasonal Frequency"] = f"Most common month: {most_common_month}"

            # Timeline
            valid_years = family_data["Date of Ritual"].dt.year.dropna()
            if valid_years.empty and "Year" in family_data.columns:
                valid_years = pd.to_numeric(family_data["Year"], errors="coerce").dropna()
            if not valid_years.empty:
                most_common_year = valid_years.value_counts().idxmax()
                timeline = " - ".join(map(str, sorted(valid_years.unique())))
                mapped_insights["Timeline"] = f"Most appeared year: {most_common_year}\nTimeline: {timeline}"

            # Average family size
            family_counts = family_data["Family Id"].value_counts()
            if not family_counts.empty:
                most_repeated_family = family_counts.idxmax()
                family_records = family_data[family_data["Family Id"] == most_repeated_family]
                total_individuals = family_records["Individual ID"].count()
                distinct_groups = family_records["Group ID"].nunique()
                if distinct_groups > 0:
                    avg_family_size = round(total_individuals / distinct_groups)
                    mapped_insights["Average Family Size"] = f"{avg_family_size} (across {distinct_groups} groups)"

            # Origin (ancestral location)
            first_appearance = family_data[family_data["Date of Ritual"].notna()].nsmallest(1, "Date of Ritual")
            location_columns = ['Village/City','Village','City','Native Place','Native']
            for col in location_columns:
                if col in first_appearance.columns and not first_appearance[col].isna().all():
                    location = first_appearance[col].iloc[0]
                    if pd.notna(location) and str(location).strip() != "":
                        mapped_insights["Origin"] = f"{location} (from earliest record)"
                        break

# -------------------------------
# OpenAI Descriptions
# -------------------------------
client = OpenAI(api_key=api_key)
prompts = {
    "Cleaned Individuals": f"Write a friendly description of Total Individuals: {clean_individuals}.",
    "Cleaned Families": f"Write a friendly description of Total Families: {clean_families}.",
    "Cleaned Gender": f"Write a friendly description of this gender distribution:\n{clean_gender}",
    "Cleaned Villages": f"Write a friendly description of top 5 villages:\n{clean_villages_str}",
    "Cleaned Castes": f"Write a friendly description of top 5 castes:\n{clean_castes_str}",
    "Cleaned Years": f"Write a friendly description of top 5 years:\n{clean_years_str}",
    "Cleaned Rituals": f"Write a friendly description of unique rituals:\n{clean_rituals}",
    "Mapped Individuals": f"Write a friendly description of Total Individuals: {mapped_individuals}.",
    "Mapped Families": f"Write a friendly description of Total Families: {mapped_families}.",
    "Mapped Gender": f"Write a friendly description of this gender distribution:\n{mapped_gender}",
    "Mapped Most Repeated Group": f"Write a friendly description:\n{mapped_insights['Most Repeated Group']}",
    "Mapped First Last Appearance": f"Write a friendly description:\n{mapped_insights['First Last Appearance']}",
    "Mapped Seasonal Frequency": f"Write a friendly description:\n{mapped_insights['Seasonal Frequency']}",
    "Mapped Timeline": f"Write a friendly description:\n{mapped_insights['Timeline']}",
    "Mapped Average Family Size": f"Write a friendly description:\n{mapped_insights['Average Family Size']}",
    "Mapped Origin": f"Write a friendly description:\n{mapped_insights['Origin']}",
}

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
col1, col2 = st.columns(2)

with col1:
    st.subheader("Cleaned File Insights")
    st.markdown(f"- Total Individuals: {clean_individuals}")
    st.markdown(f"- Total Families: {clean_families}")
    st.markdown(f"- Gender Distribution:\n```\n{clean_gender}\n```")
    st.markdown(f"- Top Villages:\n```\n{clean_villages_str}\n```")
    st.markdown(f"- Top Castes:\n```\n{clean_castes_str}\n```")
    st.markdown(f"- Top Years:\n```\n{clean_years_str}\n```")
    st.markdown(f"- Unique Rituals:\n```\n{clean_rituals}\n```")

with col2:
    st.subheader("Mapped File Insights")
    st.markdown(f"- Total Individuals: {mapped_individuals}")
    st.markdown(f"- Total Families: {mapped_families}")
    st.markdown(f"- Gender Distribution:\n```\n{mapped_gender}\n```")
    st.markdown(f"- Most Repeated Group:\n```\n{mapped_insights['Most Repeated Group']}\n```")
    st.markdown(f"- First/Last Appearance:\n```\n{mapped_insights['First Last Appearance']}\n```")
    st.markdown(f"- Seasonal Frequency:\n```\n{mapped_insights['Seasonal Frequency']}\n```")
    st.markdown(f"- Timeline:\n```\n{mapped_insights['Timeline']}\n```")
    st.markdown(f"- Average Family Size:\n```\n{mapped_insights['Average Family Size']}\n```")
    st.markdown(f"- Origin:\n```\n{mapped_insights['Origin']}\n```")
