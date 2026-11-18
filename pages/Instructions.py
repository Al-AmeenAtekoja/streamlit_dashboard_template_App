import streamlit as st

st.markdown("# Instructions 🛑")

st.write("Some Instructions on how to use the tool and how to get your file in the correct format before uploading.")

st.markdown("## Steps")
st.write("""Most files require two tabs one containing the media data and the exposure data.
        1. For files with no extrapolation you should have two sheets in the file.
         1(i) For OP files ensure the tabs are named 'MuckRuck Data' & 'Total Exposure'. 
         1(ii) For SM files ensure the tabs are named 'Social Media' & 'Social Media Exposure.'
         1(iii) For SMV files ensure the tabs are named 'Mentions' & 'Total Exposure.'""")