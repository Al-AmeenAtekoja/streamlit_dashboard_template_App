import streamlit as st

st.markdown("# Instructions 🛑", text_alignment='center')

st.write("Some Instructions on how to use the tool and how to get your file in the correct format before uploading.")

st.markdown("## Standard Files")
st.markdown("##### Most files require two tabs one containing the media data and the exposure data")
st.write(
    "1. Ensure the file you want to upload is either a xlsx or xlsm file.\n"
    "2. For OP files ensure the tabs are named 'MuckRuck Data' & 'Total Exposure'.\n" 
    "3. For SM files ensure the tabs are named 'Social Media' & 'Social Media Exposure.'\n"
    "4. For SMV files ensure the tabs are named 'Mentions' & 'Total Exposure.'\n")

st.markdown("## Files with Extrapolated rows")