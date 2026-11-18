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

st.write(
    "1. In the file you wish to upload created a sheet called 'Extrapolation1.\n"
    "2. The sheet containing the extrapolated rows copy and paste into newly created sheet in cell A1. \n"
    "3. The sheet that contains all the exposure should be renamed to 'Total Exposure"
    "4. For OP with Extrap you should have the tabs 'MuckRuck Data', 'Total Exposure', 'Extrapolation1' and for SMV with Extrap you should have 'Mentions', 'Total Exposure', 'Extrapolation1'"
)