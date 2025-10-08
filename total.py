import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import io
import time
from datetime import datetime
from openai import OpenAI

# Set console to use UTF-8 encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Initialize OpenAI client
client = OpenAI(api_key="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")  # replace with your valid API key

# Set page config
st.set_page_config(
    page_title="Ritual Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    </style>
""", unsafe_allow_html=True)

# Set title and description
st.title("📊 Ritual Analytics Dashboard")
st.markdown("""
    Upload your ritual data file to analyze family patterns, seasonal trends, and more.
    The app supports Excel files with the required columns for analysis.
""")

# File uploader in sidebar
with st.sidebar:
    st.header("Upload Data")
    uploaded_file = st.file_uploader("Choose an Excel file", type=["xlsx", "xls"])
    
    st.markdown("---")
    st.info("ℹ️ Make sure your Excel file contains the required columns:")
    st.markdown("""
    - Family Id
    - Individual ID
    - Group ID
    - Date of Ritual
    - Gender
    - Village/City (optional)
    - Native Place (optional)
    """)

# Initialize session state
if 'df' not in st.session_state:
    st.session_state.df = None
if 'analysis_done' not in st.session_state:
    st.session_state.analysis_done = False

# Main app logic
def main():
    if uploaded_file is not None:
        try:
            # Read the uploaded file
            df = pd.read_excel(uploaded_file)
            df.columns = df.columns.str.strip()
            
            # Store in session state
            st.session_state.df = df
            
            # Show data preview
            with st.expander("📄 View Raw Data"):
                st.dataframe(df.head())
                
            # Show basic info
            st.subheader("📊 Data Overview")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Individuals", len(df))
            with col2:
                st.metric("Total Families", df['Family Id'].nunique() if 'Family Id' in df.columns else "N/A")
            with col3:
                st.metric("Total Groups", df['Group ID'].nunique() if 'Group ID' in df.columns else "N/A")
            
            # Add analysis button
            if st.button("🚀 Run Analysis"):
                with st.spinner("Analyzing data..."):
                    analyze_data(df)
                    st.session_state.analysis_done = True
                    st.experimental_rerun()
            
            # Show analysis results if available
            if st.session_state.analysis_done:
                show_analysis_results()
                
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    else:
        st.info("👈 Please upload a file to get started")

def analyze_data(df):
    """Process the data and store results in session state."""
    if df is None or df.empty:
        st.error("No data available for analysis.")
        return

    # Store the original dataframe in session state
    st.session_state.original_df = df.copy()
    
    # Initialize analysis results dictionary if it doesn't exist
    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = {}
    
    # Clean column names by stripping whitespace
    df.columns = df.columns.str.strip()
    
    # Basic statistics
    total_individuals = df['Individual ID'].count()
    total_families = df['Group ID'].nunique()
    
    st.session_state.analysis_results['total_individuals'] = total_individuals
    st.session_state.analysis_results['total_families'] = total_families
    
    # Gender distribution with Year-wise info
    if "Gender" in df.columns:
        male_count = (df['Gender'].astype(str).str.strip() == "पुरुष").sum()
        female_count = (df['Gender'].astype(str).str.strip() == "महिला").sum()
        male_percent = (male_count / total_individuals * 100) if total_individuals > 0 else 0
        female_percent = (female_count / total_individuals * 100) if total_individuals > 0 else 0
        
        gender_distribution = {
            'male_count': male_count,
            'female_count': female_count,
            'male_percent': male_percent,
            'female_percent': female_percent
        }
        
        # Year-wise analysis
        year_col_candidates = ["Year", "year", "Ritual Year", "RitualYear"]
        year_col = next((col for col in year_col_candidates if col in df.columns), None)
        
        if year_col:
            gender_distribution['year_col'] = year_col
            # Group by year and gender
            gender_year_counts = df.groupby([year_col, 'Gender']).size().unstack(fill_value=0)
            
            if "पुरुष" in gender_year_counts.columns:
                year_high_male = gender_year_counts["पुरुष"].idxmax()
                male_val = gender_year_counts["पुरुष"].max()
                gender_distribution['year_high_male'] = year_high_male
                gender_distribution['male_val'] = male_val
                
            if "महिला" in gender_year_counts.columns:
                year_high_female = gender_year_counts["महिला"].idxmax()
                female_val = gender_year_counts["महिला"].max()
                gender_distribution['year_high_female'] = year_high_female
                gender_distribution['female_val'] = female_val
        
        st.session_state.analysis_results['gender_distribution'] = gender_distribution
    
    # Top Villages
    if "Village/City" in df.columns and "Group ID" in df.columns:
        families = df[['Group ID', 'Village/City']].drop_duplicates(subset=['Group ID'])
        village_counts = families.groupby('Village/City')['Group ID'].nunique().sort_values(ascending=False).head(5)
        st.session_state.analysis_results['top_villages'] = village_counts.to_dict()
    
    # Top Castes
    if "Caste" in df.columns and "Group ID" in df.columns:
        families_caste = df[['Group ID', 'Caste']].drop_duplicates(subset=['Group ID'])
        caste_counts = families_caste.groupby('Caste')['Group ID'].nunique().sort_values(ascending=False).head(5)
        st.session_state.analysis_results['top_castes'] = caste_counts.to_dict()
    
    # Top Years
    year_col_candidates = ["Year", "year", "Ritual Year", "RitualYear"]
    year_col = next((col for col in year_col_candidates if col in df.columns), None)
    
    if year_col and "Group ID" in df.columns:
        families_year = df[[year_col, 'Group ID']].drop_duplicates(subset=['Group ID', year_col])
        year_counts = families_year.groupby(year_col)['Group ID'].nunique().sort_values(ascending=False).head(5)
        st.session_state.analysis_results['top_years'] = year_counts.to_dict()
        st.session_state.analysis_results['year_col'] = year_col
    
    # Unique Rituals
    if "Ritual Name 1" in df.columns:
        unique_rituals = df["Ritual Name 1"].dropna().unique()
        st.session_state.analysis_results['unique_rituals'] = list(unique_rituals)
    
    # Seasonal Ritual Trends
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
        
        # Count distinct families (Group ID) per month  
        families_month = df[['Group ID', 'Month']].drop_duplicates(subset=['Group ID', 'Month'])
        month_counts = families_month.groupby("Month")['Group ID'].nunique()
        
        if not month_counts.empty:
            most_month = month_counts.idxmax()  # Month with max families
            avg_value = month_counts.mean()     # Average across months
            avg_month = (month_counts - avg_value).abs().idxmin()  # Closest month to average
            
            seasonal_data = {
                'most_month': most_month,
                'avg_month': avg_month,
                'month_counts': month_counts.to_dict()
            }
            st.session_state.analysis_results['seasonal_trends'] = seasonal_data
    
    # Repeated Families Analysis
    mapped_file = "MAPPED_FAMILIES/Bahi No 1 Baniya_Mapped.xlsx"
    mapped_df = None
    if os.path.exists(mapped_file):
        try:
            mapped_df = pd.read_excel(mapped_file)
            mapped_df.columns = mapped_df.columns.str.strip()
            st.session_state.mapped_df = mapped_df  # Store for later use
            
            if "Final Merged Family Id" in mapped_df.columns:
                groups_only = mapped_df["Final Merged Family Id"].dropna().astype(str)
                groups_only = groups_only[groups_only.str.startswith("GROUP")]
                repeated_families_count = groups_only.nunique()
                st.session_state.analysis_results['repeated_families_count'] = repeated_families_count
                
                # Store the most repeated family group information
                if not groups_only.empty:
                    group_counts = groups_only.value_counts()
                    most_repeated_group = group_counts.idxmax()
                    num_families = group_counts.max()
                    
                    repeated_data = {
                        'repeated_families_count': repeated_families_count,
                        'most_repeated_group': most_repeated_group,
                        'num_families_in_group': int(num_families)
                    }
                    st.session_state.analysis_results['repeated_families'] = repeated_data
        except Exception as e:
            st.error(f"Error processing mapped families file: {str(e)}")
    
    # Generate AI descriptions
    generate_ai_descriptions()
    
    st.session_state.analysis_complete = True

def get_openai_response(prompt, max_retries=3, initial_delay=1):
    """Make API call to OpenAI with retry logic and rate limit handling."""
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300
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


def generate_ai_descriptions():
    """Generate AI-powered descriptions for the analysis results."""
    if 'analysis_results' not in st.session_state:
        return
    
    # Check if descriptions already exist in session state
    if 'ai_descriptions' in st.session_state:
        return
    
    # Initialize descriptions dictionary
    st.session_state.ai_descriptions = {}
    
    # Get analysis results
    results = st.session_state.analysis_results
    
    # Generate description for total individuals
    if 'total_individuals' in results:
        prompt = f"Write a short, friendly description of Total Individuals: {results['total_individuals']}."
        st.session_state.ai_descriptions['individuals'] = get_openai_response(prompt)
    
    # Generate description for total families
    if 'total_families' in results:
        prompt = f"Write a short, friendly description of Total Families: {results['total_families']}."
        st.session_state.ai_descriptions['families'] = get_openai_response(prompt)
    
    # Generate description for gender distribution
    if 'gender_distribution' in results:
        gd = results['gender_distribution']
        gender_text = (
            f"Gender Distribution:\n"
            f"  Males   - {gd.get('male_count', 0)} | Percentage: {gd.get('male_percent', 0):.2f}%"
        )
        if 'year_high_male' in gd:
            gender_text += f"; Year with highest male count: {gd['year_high_male']} ({gd.get('male_val', 0)} पुरुष)"
        
        gender_text += (
            f"\n  Females - {gd.get('female_count', 0)} | Percentage: {gd.get('female_percent', 0):.2f}%"
        )
        if 'year_high_female' in gd:
            gender_text += f"; Year with highest female count: {gd['year_high_female']} ({gd.get('female_val', 0)} महिला)"
        
        prompt = f"Write a short, friendly description of this gender distribution in Hindi:\n{gender_text}"
        st.session_state.ai_descriptions['gender'] = get_openai_response(prompt)
    
    # Generate description for top villages
    if 'top_villages' in results and results['top_villages']:
        villages_text = "Top Villages (by number of families):\n"
        for i, (village, count) in enumerate(results['top_villages'].items(), 1):
            villages_text += f"  Top {i}: {village} ({count} families)\n"
        
        prompt = f"Write a short, friendly description in Hindi about the importance of these top villages:\n{villages_text}"
        st.session_state.ai_descriptions['villages'] = get_openai_response(prompt)
    
    # Generate description for top castes
    if 'top_castes' in results and results['top_castes']:
        castes_text = "Top Castes (by number of families):\n"
        for i, (caste, count) in enumerate(results['top_castes'].items(), 1):
            castes_text += f"  Top {i}: {caste} ({count} families)\n"
        
        prompt = f"Write a short, friendly description in Hindi about the importance of these top castes:\n{castes_text}"
        st.session_state.ai_descriptions['castes'] = get_openai_response(prompt)
    
    # Generate description for top years
    if 'top_years' in results and results['top_years']:
        years_text = "Top Years (by number of families):\n"
        for i, (year, count) in enumerate(results['top_years'].items(), 1):
            years_text += f"  Top {i}: {year} ({count} families)\n"
        
        prompt = f"Write a short, friendly description in Hindi about the significance of these top years:\n{years_text}"
        st.session_state.ai_descriptions['years'] = get_openai_response(prompt)
    
    # Generate description for unique rituals
    if 'unique_rituals' in results and results['unique_rituals']:
        rituals_text = "Unique Rituals:\n" + "\n".join([f"  - {ritual}" for ritual in results['unique_rituals']])
        prompt = f"Write a short, friendly description in Hindi about the cultural significance of these unique rituals:\n{rituals_text}"
        st.session_state.ai_descriptions['rituals'] = get_openai_response(prompt)
    
    # Generate description for seasonal trends
    if 'seasonal_trends' in results:
        st_data = results['seasonal_trends']
        seasonal_text = (
            f"Seasonal Trends:\n"
            f"  Most active month: {st_data.get('most_month', 'N/A')}\n"
            f"  Average month: {st_data.get('avg_month', 'N/A')}\n"
            "\nMonthly Distribution (number of families):\n"
        )
        
        # Add monthly distribution
        month_order = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        
        for month in month_order:
            count = st_data.get('month_counts', {}).get(month, 0)
            seasonal_text += f"  {month}: {count}\n"
        
        prompt = f"Write a short, friendly description in Hindi explaining these seasonal ritual trends:\n{seasonal_text}"
        st.session_state.ai_descriptions['seasonal'] = get_openai_response(prompt)
    
    # Generate description for repeated families
    if 'repeated_families' in results:
        rf = results['repeated_families']
        
        prompt = (
            f"Write a short, friendly description in Hindi about repeated families in ritual records. "
            f"There are {rf.get('repeated_families_count', 0)} repeated family groups found. "
            "Explain why identifying repeated families matters and what insights can be gained from this analysis."
        )
        st.session_state.ai_descriptions['repeated_families'] = get_openai_response(prompt)
        
        # Additional analysis for the most repeated family group
        if 'mapped_df' in st.session_state and 'most_repeated_group' in rf:
            analyze_most_repeated_group(rf['most_repeated_group'])

def analyze_most_repeated_group(group_id):
    # This function is not implemented in the provided code
    pass

def show_analysis_results():
    """Display the analysis results in a user-friendly format."""
    if 'analysis_results' not in st.session_state:
        st.warning("Please run the analysis first.")
        return
    
    results = st.session_state.analysis_results
    
    st.success("✅ Analysis completed successfully!")
    
    # Add tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview", 
        "👨‍👩‍👧‍👦 Family Analysis", 
        "📅 Seasonal Trends", 
        "🌍 Origin Analysis"
    ])
    
    with tab1:  # Overview Tab
        st.subheader("📊 Data Overview")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Individuals", results.get('total_individuals', 0))
        with col2:
            st.metric("Total Families", results.get('total_families', 0))
        with col3:
            st.metric("Total Groups", results.get('total_groups', 0))
        
        st.markdown("---")
        
        # Add some visualizations
        if 'gender_distribution' in results:
            import plotly.express as px
            
            gender_data = {
                'Gender': ['Male', 'Female'],
                'Count': [results['gender_distribution']['male_count'], results['gender_distribution']['female_count']]
            }
            
            fig = px.pie(
                gender_data, 
                values='Count', 
                names='Gender',
                title='Gender Distribution',
                hole=0.3
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:  # Family Analysis Tab
        st.subheader("👨‍👩‍👧‍👦 Family Analysis")
        
        if 'repeated_families' in st.session_state.analysis_results:
            rf = st.session_state.analysis_results['repeated_families']
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Repeated Families Count", rf.get('repeated_families_count', 0))
            with col2:
                st.metric("Most Repeated Group", rf.get('most_repeated_group', 'N/A'))
            with col3:
                st.metric("Number of Families in Group", rf.get('num_families_in_group', 0))
            
            st.markdown("---")
            st.write(st.session_state.ai_descriptions.get('repeated_families', ''))
        else:
            st.warning("Family analysis data not available.")
    
    with tab3:  # Seasonal Trends Tab
        st.subheader("📅 Seasonal Trends")
        
        if 'seasonal_trends' in st.session_state.analysis_results:
            st_data = st.session_state.analysis_results['seasonal_trends']
            
            st.metric("Most Active Month", st_data.get('most_month', 'N/A'))
            
            # Display month distribution as a bar chart
            if st_data.get('month_counts'):
                import plotly.express as px
                
                months = list(st_data['month_counts'].keys())
                counts = list(st_data['month_counts'].values())
                
                fig = px.bar(
                    x=months,
                    y=counts,
                    title='Rituals by Month',
                    labels={'x': 'Month', 'y': 'Count'}
                )
                st.plotly_chart(fig, use_container_width=True)
            st.write(st.session_state.ai_descriptions.get('seasonal', ''))
        else:
            st.warning("Seasonal analysis data not available.")
    
    with tab4:  # Origin Analysis Tab
        st.subheader("🌍 Origin Analysis")
        
        if 'origin_data' in st.session_state.analysis_results:
            od = st.session_state.analysis_results['origin_data']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Origin Location", od.get('origin_location', 'N/A'))
            with col2:
                st.metric("First Appearance", od.get('first_appearance', 'N/A'))
            
            # Add a map visualization if location data is available
            # This is a placeholder - you would need geocoding for actual map display
            if od.get('origin_location') and od.get('origin_location') != 'N/A':
                st.info(f"Map display for {od.get('origin_location')} would appear here with proper geocoding setup.")
        else:
            st.warning("Origin analysis data not available.")

if __name__ == "__main__":
    main()
