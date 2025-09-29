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
# STEP 1: Read Primary Excel
# -------------------------------
df = pd.read_excel("output/Datiya_Gaon_ki_Bahi_No-16_cleaned.xlsx")
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
    # Mapping Hindi month names to English
    hindi_to_english = {
        "जनवरी": "January",
        "फ़रवरी": "February",
        "मार्च": "March",
        "अप्रैल": "April",
        "मई": "May",
        "जून": "June",
        "जुलाई": "July",
        "अगस्त": "August",
        "सितंबर": "September",
        "अक्टूबर": "October",
        "नवंबर": "November",
        "दिसंबर": "December"
    }

    # Clean and translate Month column
    df["Month"] = df["Month"].astype(str).str.strip().map(hindi_to_english)

    # Drop rows with unrecognized months
    df = df[df["Month"].notna()]

    # Count distinct families (Group ID) per month
    families_month = df[['Group ID', 'Month']].drop_duplicates(subset=['Group ID', 'Month'])
    month_counts = families_month.groupby("Month")['Group ID'].nunique()

    if not month_counts.empty:
        most_month = month_counts.idxmax()  # Month with max families
        avg_value = month_counts.mean()     # Average across months
        avg_month = (month_counts - avg_value).abs().idxmin()  # Closest month to average

        seasonal_description = (
            f"Seasonal Frequency: {most_month}\n"
            f"The month that came as average is: {avg_month}"
        )
    else:
        seasonal_description = "No valid month data available to calculate seasonal trends."
else:
    seasonal_description = "Month column not found; cannot compute seasonal ritual trends."

# -------------------------------
# STEP 9: Repeated Families (from mapped excel if present)
# -------------------------------
mapped_file = "MAPPED_FAMILIES/Datiya_Gaon_ki_Bahi_No-16_mapped.xlsx"  # name of mapped excel file
mapped_df = None
if os.path.exists(mapped_file):
    mapped_df = pd.read_excel(mapped_file)
    mapped_df.columns = mapped_df.columns.str.strip()

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
client = OpenAI(api_key="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")  # replace with your valid API key

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
    """Make API call to OpenAI with retry logic and rate limit handling."""
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
            if hasattr(e, 'response') and e.response.status_code == 429:  # Rate limit
                retry_after = int(e.response.headers.get('retry-after', 60))
                print(f"Rate limit reached. Waiting for {retry_after} seconds...")
                time.sleep(retry_after)
            elif attempt == max_retries - 1:  # Last attempt
                print(f"Failed after {max_retries} attempts. Error: {str(e)}")
                return f"[Could not generate description: {str(e)}]"
            else:
                wait_time = initial_delay * (2 ** attempt)  # Exponential backoff
                print(f"Attempt {attempt + 1} failed. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

# Generate descriptions with error handling
for key, prompt in prompts.items():
    print(f"Generating description for {key}...")
    try:
        descriptions[key] = get_openai_response(prompt)
        print(f"  - Success!")
    except Exception as e:
        descriptions[key] = f"[Error generating description: {str(e)}]"
        print(f"  - Error: {str(e)}")

# -------------------------------
# STEP 12: Output all results
# -------------------------------
print(f"Total Individuals: {total_individuals}")
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
    
    # Analyze most repeated family group
    if mapped_df is not None and "Final Merged Family Id" in mapped_df.columns and "Family Id" in mapped_df.columns:
        # Filter only GROUP rows
        groups_df = mapped_df[mapped_df["Final Merged Family Id"].astype(str).str.startswith("GROUP")].copy()
        
        # Count unique Family IDs in each group
        group_counts = groups_df.groupby("Final Merged Family Id")["Family Id"].nunique()
        
        if not group_counts.empty:
            # Find the group with maximum unique families
            most_repeated_group = group_counts.idxmax()
            num_families = group_counts.max()
            
            # Get all Family IDs from the most repeated group
            most_repeated_families = groups_df[groups_df["Final Merged Family Id"] == most_repeated_group]["Family Id"].unique()
            
            # Create a description of the most repeated group
            print("\n" + "="*60)
            print("MOST REPEATED FAMILY GROUP INSIGHTS")
            print("="*60)
            print(f"Most repeated GROUP is {most_repeated_group} with {num_families} distinct families.")
            
            # Now find first and last appearance for these families using the mapped dataset
            first_last_desc = "No data available."
            
            if mapped_df is not None and "Family Id" in mapped_df.columns and "Date of Ritual" in mapped_df.columns:
                print("\n=== ANALYZING FAMILY APPEARANCES USING MAPPED DATASET ===")
                print(f"Number of families in group: {len(most_repeated_families)}")
                print("Sample family IDs in group:", [str(fid) for fid in most_repeated_families[:5]])
                
                # Filter the mapped dataset for these families
                family_data = mapped_df[mapped_df["Family Id"].isin(most_repeated_families)].copy()
                print(f"Found {len(family_data)} records for these families in the mapped dataset")
                
                if len(family_data) > 0:
                    # Define Hindi to English month mapping
                    hindi_months = {
                        'जनवरी': 'January', 'फरवरी': 'February', 'मार्च': 'March',
                        'अप्रैल': 'April', 'मई': 'May', 'जून': 'June',
                        'जुलाई': 'July', 'अगस्त': 'August', 'सितंबर': 'September',
                        'अक्टूबर': 'October', 'नवंबर': 'November', 'दिसंबर': 'December'
                    }
                    
                    # Function to normalize date text
                    def normalize_hindi_date(date_str):
                        if pd.isna(date_str) or not isinstance(date_str, str):
                            return None
                        for hin, eng in hindi_months.items():
                            if hin in date_str:
                                date_str = date_str.replace(hin, eng)
                                break
                        return date_str.strip()
                    
                    # Apply date normalization
                    normalized_dates = family_data["Date of Ritual"].apply(normalize_hindi_date)
                    
                    # Parse dates with dayfirst=True for day-month-year format
                    family_data["Date of Ritual"] = pd.to_datetime(
                        normalized_dates,
                        format='%d %B %Y',
                        dayfirst=True,
                        errors='coerce'
                    )
                    
                    # Get valid dates (non-NaT)
                    valid_dates = family_data["Date of Ritual"].dropna()
                    
                    if len(valid_dates) > 0:
                        first_date = valid_dates.min().strftime("%d %B %Y")
                        last_date = valid_dates.max().strftime("%d %B %Y")
                        first_last_desc = f"First Appearance: {first_date}\nLast Appearance: {last_date}"
                    else:
                        # If no valid dates, try with Year column if available
                        if "Year" in family_data.columns:
                            years = pd.to_numeric(family_data["Year"], errors="coerce").dropna()
                            if not years.empty:
                                first_year = int(years.min())
                                last_year = int(years.max())
                                first_last_desc = f"First Appearance (Year): {first_year}\nLast Appearance (Year): {last_year}"
                                print(f"Using Year column - First: {first_year}, Last: {last_year}")
                            else:
                                print("No valid dates or years found in the mapped dataset")
                        else:
                            print("No valid dates and no Year column found in the mapped dataset")
                else:
                    print("No records found for these families in the mapped dataset")
            
            print(first_last_desc)
            
            # Analyze seasonal frequency for this group
            if 'Date of Ritual' in family_data.columns and not family_data['Date of Ritual'].isna().all():
                # Extract month from valid dates
                family_data["Month"] = family_data["Date of Ritual"].dt.month_name()
                
                # Count occurrences of each month across all families
                # Count distinct families per month
                distinct_month_counts = family_data.groupby("Month")["Family Id"].nunique()

                print(distinct_month_counts)

                
                if not distinct_month_counts.empty:
                    # Filter out months with zero occurrences
                    month_counts = distinct_month_counts[distinct_month_counts > 0]
                    most_common_month = month_counts.idxmax()
                    count = month_counts.max()
                    total = month_counts.sum()
                    percentage = (count / total) * 100
                    
                    # Calculate average month (weighted by occurrences)
                    month_to_num = {'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 
                                  'June': 6, 'July': 7, 'August': 8, 'September': 9, 'October': 10, 
                                  'November': 11, 'December': 12}
                    num_to_month = {v: k for k, v in month_to_num.items()}
                    
                    # Calculate weighted average month
                    weighted_sum = 0
                    for month, cnt in month_counts.items():
                        weighted_sum += month_to_num[month] * cnt
                    
                    avg_month_num = round(weighted_sum / total)
                    avg_month = num_to_month.get(avg_month_num, 'Unknown')
                    
                    print("\n=== SEASONAL FREQUENCY FOR THIS GROUP ===")
                    print(f"Most common month for this group: {most_common_month} ({count} out of {total} records, {percentage:.1f}%)")
                    
                    # Print month distribution in a clean format (only months with occurrences)
                    print("\nMonth distribution for this group:")
                    for month, cnt in month_counts.sort_index().items():
                        print(f"{month}: {cnt}")
                    
                    print(f"\nSeasonal Frequency: {most_common_month}")
                    print(f"The month that came as average is: {avg_month}")
                    
                    # Long Traditional Timeline Analysis
                    print("\n=== LONG TRADITIONAL TIMELINE ===")
                    
                    # Extract years from valid dates
                    valid_years = family_data[family_data['Date of Ritual'].notna()]['Date of Ritual'].dt.year
                    
                    # Also check Year column if available and dates are missing
                    if valid_years.empty and 'Year' in family_data.columns:
                        valid_years = pd.to_numeric(family_data['Year'], errors='coerce').dropna()
                    
                    if not valid_years.empty:
                        # Convert to integers and drop any NaN values
                        valid_years = valid_years.dropna().astype(int)
                        
                        # Find most frequent year
                        year_counts = valid_years.value_counts()
                        most_common_year = year_counts.idxmax()
                        
                        # Get unique years and sort them
                        unique_years = sorted(valid_years.unique())
                        
                        # Format the timeline string
                        timeline = " - ".join(map(str, unique_years))
                        
                        print(f"Most appeared year: {most_common_year}")
                        print(f"Timeline: {timeline}")
                        
                        # Calculate Average Family Size
                        print("\n=== AVERAGE FAMILY SIZE ===")
                        
                        # Find the most repeated family
                        family_counts = family_data['Family Id'].value_counts()
                        if not family_counts.empty:
                            most_repeated_family = family_counts.idxmax()
                            repeat_count = family_counts.max()
                            
                            # Get all records for the most repeated family
                            family_records = family_data[family_data['Family Id'] == most_repeated_family]
                            
                            # Count total individuals (non-null Individual IDs)
                            total_individuals = family_records['Individual ID'].count()
                            
                            # Count distinct Group IDs
                            distinct_groups = family_records['Group ID'].nunique()
                            
                            # Calculate average family size (rounded to nearest integer)
                            if distinct_groups > 0:
                                avg_family_size = round(total_individuals / distinct_groups)
                                print(f"Total individuals in most repeated family: {total_individuals}")
                                print(f"Number of distinct Group IDs: {distinct_groups}")
                                print(f"Average Family Size: {avg_family_size}")
                            else:
                                print("No valid Group IDs found for calculation")
                        else:
                            print("No family data available for calculation")
                        
                        # Find Origin (Ancestral Location)
                        print("\n=== ORIGIN (ANCESTRAL LOCATION) ===")
                        
                        # Get the earliest date record
                        if 'Date of Ritual' in family_data.columns and not family_data['Date of Ritual'].isna().all():
                            # Get the row with the earliest date
                            first_appearance = family_data[family_data['Date of Ritual'].notna()].nsmallest(1, 'Date of Ritual')
                            
                            # Try to get the location from common location columns
                            location_columns = ['Village/City', 'Village', 'City', 'Native Place', 'Native']
                            location = None
                            
                            for col in location_columns:
                                if col in first_appearance.columns and not first_appearance[col].isna().any():
                                    location = first_appearance[col].iloc[0]
                                    if pd.notna(location) and str(location).strip() != '':
                                        break
                            
                            if location is not None and str(location).strip() != '':
                                print(f"Origin (Ancestral Location): {location}")
                                print(f"First Appearance: {first_appearance['Date of Ritual'].iloc[0].strftime('%d %B %Y')}")
                            else:
                                print("Origin location not found in the data")
                        else:
                            print("No valid date data available to determine origin location")
                    else:
                        print("No valid year data available for timeline analysis.")
                    
            
else:
    print("Mapped excel not found or 'Final Merged Family Id' column missing; skipping repeated families insight.\n")
