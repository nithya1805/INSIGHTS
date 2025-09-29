import os
import sys
import io
import time
import pandas as pd
from openai import OpenAI

# Set console to use UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# -------------------------------
# STEP 1: Read Primary Excel (user input)
# -------------------------------
input_path = input("Enter the path of the primary Excel file: ").strip()

if not os.path.exists(input_path):
    print(f"Error: File not found at '{input_path}'")
    sys.exit(1)

df = pd.read_excel(input_path)
df.columns = df.columns.str.strip()

# -------------------------------
# STEP 2: Counts
# -------------------------------
total_individuals = df['Individual ID'].count()
total_families = df['Group ID'].nunique()

# -------------------------------
# STEP 3: Gender Distribution with Year-wise info
# -------------------------------
if "Gender" in df.columns:
    male_count = (df['Gender'].astype(str).str.strip() == "पुरुष").sum()
    female_count = (df['Gender'].astype(str).str.strip() == "महिला").sum()
    male_percent = (male_count / total_individuals * 100) if total_individuals > 0 else 0
    female_percent = (female_count / total_individuals * 100) if total_individuals > 0 else 0

    # Year-wise analysis
    year_col_candidates = ["Year", "year", "Ritual Year", "RitualYear"]
    year_col = None
    for c in year_col_candidates:
        if c in df.columns:
            year_col = c
            break

    year_male_str = ""
    year_female_str = ""
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
# STEP 4: Top 5 Villages
# -------------------------------
if "Village/City" in df.columns and "Group ID" in df.columns:
    families = df[['Group ID', 'Village/City']].drop_duplicates(subset=['Group ID'])
    village_counts = families.groupby('Village/City')['Group ID'].nunique().sort_values(ascending=False).head(5)
    top_villages_description = "Top Villages :\n"
    for i, (village, count) in enumerate(village_counts.items(), 1):
        top_villages_description += f"  Top{i} : {village} ({count})\n"
else:
    top_villages_description = "Village/City column or Group ID column not found; cannot compute top villages."

# -------------------------------
# STEP 5: Top 5 Castes
# -------------------------------
if "Caste" in df.columns and "Group ID" in df.columns:
    families_caste = df[['Group ID', 'Caste']].drop_duplicates(subset=['Group ID'])
    caste_counts = families_caste.groupby('Caste')['Group ID'].nunique().sort_values(ascending=False).head(5)
    top_castes_description = "Top 5 Castes based on number of families:\n"
    for i, (caste, count) in enumerate(caste_counts.items(), 1):
        top_castes_description += f"  Top{i} : {caste} ({count})\n"
else:
    top_castes_description = "Caste column or Group ID column not found; cannot compute top castes."

# -------------------------------
# STEP 6: Top 5 Years
# -------------------------------
year_col_candidates = ["Year", "year", "Ritual Year", "RitualYear"]
year_col = None
for c in year_col_candidates:
    if c in df.columns:
        year_col = c
        break

if year_col and "Group ID" in df.columns:
    families_year = df[[year_col, 'Group ID']].drop_duplicates(subset=['Group ID'])
    year_counts = families_year.groupby(year_col)['Group ID'].nunique().sort_values(ascending=False).head(5)
    top_years_description = "Top Years :\n"
    for i, (year, count) in enumerate(year_counts.items(), 1):
        top_years_description += f"  Top{i} : {year} ({count})\n"
else:
    top_years_description = "Year column or Group ID column not found; cannot compute top years."

# -------------------------------
# STEP 7: Unique Rituals
# -------------------------------
if "Ritual Name 1" in df.columns:
    unique_rituals = df["Ritual Name 1"].dropna().unique()
    unique_rituals_list = ", ".join(map(str, unique_rituals))
    unique_rituals_description = f"Unique Rituals are : {unique_rituals_list}"
else:
    unique_rituals_description = "Ritual Name 1 column not found; cannot compute unique rituals."
    unique_rituals_list = ""

# -------------------------------
# STEP 8: Seasonal Ritual Trends
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
        seasonal_description = (
            f"Seasonal Frequency: {most_month}\n"
            f"The month that came as average is: {avg_month}"
        )
    else:
        seasonal_description = "No valid month data available to calculate seasonal trends."
else:
    seasonal_description = "Month column not found; cannot compute seasonal ritual trends."

# -------------------------------
# STEP 9: Repeated Families (user input)
# -------------------------------
mapped_file = input("Enter the path of the mapped Excel file (or press Enter to skip): ").strip()
mapped_df = None
if mapped_file == "":
    mapped_df = None
elif os.path.exists(mapped_file):
    mapped_df = pd.read_excel(mapped_file)
    mapped_df.columns = mapped_df.columns.str.strip()
else:
    print(f"Mapped file not found at '{mapped_file}'. Skipping repeated families analysis.")
    mapped_df = None

if mapped_df is not None and "Final Merged Family Id" in mapped_df.columns:
    groups_only = mapped_df["Final Merged Family Id"].dropna().astype(str)
    groups_only = groups_only[groups_only.str.startswith("GROUP")]
    repeated_families_count = groups_only.nunique()
    repeated_families_description = f"Repeated families : {repeated_families_count}"
else:
    repeated_families_count = None
    repeated_families_description = None

# -------------------------------
# STEP 10: OpenAI client
# -------------------------------
api_key = input("Enter your OpenAI API key: ").strip()
client = OpenAI(api_key=api_key)

# -------------------------------
# STEP 11: Generate friendly descriptions
# -------------------------------
prompts = {
    "individuals": f"Write a short, friendly description of Total Individuals: {total_individuals}.",
    "families": f"Write a short, friendly description of Total Families: {total_families}.",
    "gender": f"Write a short, friendly description of this gender distribution:\n{gender_distribution}",
    "villages": f"Write a short, friendly description (a few sentences) about the importance of these top 5 villages:\n{top_villages_description}",
    "castes": f"Write a short, friendly description (a few sentences) about the importance of these top 5 castes:\n{top_castes_description}",
    "years": f"Write a short, friendly description (a few sentences) about the importance of these top 5 years:\n{top_years_description}",
    "rituals": f"Write a short, friendly description (a few sentences) about the cultural importance of these unique rituals:\n{unique_rituals_description}",
    "seasonal": f"Write a short, friendly description (a few sentences) explaining the seasonal ritual trend:\n{seasonal_description}"
}

if repeated_families_count is not None:
    prompts["repeated"] = (
        f"Write a short, friendly description (a few sentences) about repeated families "
        f"in ritual records. There are {repeated_families_count} repeated families found. "
        f"Explain why identifying repeated families matters."
    )

descriptions = {}

def get_openai_response(prompt, max_retries=3, initial_delay=1):
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if hasattr(e, 'response') and e.response.status_code == 429:
                retry_after = int(e.response.headers.get('retry-after', 60))
                print(f"Rate limit reached. Waiting for {retry_after} seconds...")
                time.sleep(retry_after)
            elif attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts. Error: {str(e)}")
                return f"[Could not generate description: {str(e)}]"
            else:
                wait_time = initial_delay * (2 ** attempt)
                print(f"Attempt {attempt + 1} failed. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

for key, prompt in prompts.items():
    print(f"Generating description for {key}...")
    descriptions[key] = get_openai_response(prompt)
    print(f"  - Success!")

# -------------------------------
# STEP 12: Output all results
# -------------------------------
print(f"\nTotal Individuals: {total_individuals}")
print("Description:", descriptions["individuals"], "\n")

print(f"Total Families: {total_families}")
print("Description:", descriptions["families"], "\n")

print(gender_distribution)
print("Description:", descriptions["gender"], "\n")

print(top_villages_description)
print("Description:", descriptions["villages"], "\n")

print(top_castes_description)
print("Description:", descriptions["castes"], "\n")

print(top_years_description)
print("Description:", descriptions["years"], "\n")

print(unique_rituals_description)
print("Description:", descriptions["rituals"], "\n")

print(seasonal_description)
print("Description:", descriptions["seasonal"], "\n")

if repeated_families_description:
    print(repeated_families_description)
    print("Description:", descriptions["repeated"], "\n")
