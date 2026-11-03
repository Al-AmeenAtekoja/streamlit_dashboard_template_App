import streamlit as st

# Define the pages
main_page = st.Page("OP.py", title="Online Press", icon="🎈")
page_2 = st.Page("SM.py", title="Social Media", icon="❄️")
page_3 = st.Page("SMV.py", title="Social Media Video", icon="🎉")
page_4 = st.Page('SMV_w_extrap.py', title='Social Media Video with extrapolation', icon="👊")
page_5 = st.Page('ea.py', title='Exposure Calcs with SIQ+')

# Set up navigation
pg = st.navigation([main_page, page_2, page_3,page_4, page_5])

# Run the selected page
pg.run()