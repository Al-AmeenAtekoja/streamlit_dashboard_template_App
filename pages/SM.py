import streamlit as st
import pandas as pd
from io import BytesIO

st.markdown("# Social Media ❄️")
st.sidebar.markdown("# Social Media ❄️")

st.write("This is designed to cut some time for dashboard uploads " \
"to get the inital file into the template for uploading the file. ")

uploaded_file = st.file_uploader('Upload File Below:',type='.xlsx')

if uploaded_file is None:
        st.info('Upload an Excel File to begin.')
        st.stop()

with st.spinner('Putting in template', show_time=True):
        required_sheets = {
                'Social Media': dict(header=0),
                'Social Media Exposure':  dict(header = 0)
            }
        missing = []
        data ={}
        
        for sheet , kwargs in required_sheets.items():
                try:
                    data[sheet] =pd.read_excel(uploaded_file, sheet, **kwargs)
                except ValueError:
                    missing.append(sheet)
                except Exception as e:
                    st.error(f"Could not read sheet '{sheet}': {e}")
                    st.stop()
        
        if missing:
                st.error(
                    "The uploaded file is missing the following required sheet(s):"
                    + ", ".join(f"**{m}**" for m in missing)
                    + ". Please check the file and re-upload."
                )
                st.stop()
        
        sm = data['Social Media']
        sme = data['Social Media Exposure']

        
        
        st.success(f"Loaded {len(sm)} social media and {len(sme)} expsoure rows.")
        if st.button('Rerun'):
                st.rerun()

sm['Impressions'] = sm['Impressions'].fillna(0)
sm['Engagement'] = sm['Engagement'].fillna(0)
clean_platform = {'x': 'X'}
sm['Platform'] = sm['Platform'].replace(clean_platform)

new_sm = pd.DataFrame({
    'Event ID': '',
    'Data ID': sm['Data ID'],
    'Country': sm['Country'],
    'Platform': sm['Platform'],
    'Date': sm['Date'],
    'Account': sm['Account'],
    'Rating': sm['Rating'],
    'Impressions': sm['Impressions'],
    'Engagement': sm['Engagement'],
    'AVE ($)': sm['AVE ($)'],
    'Sponsor Value ($)': sm['Sponsor Value ($)'],
    'Url': sm['URL'],
    'Content': '',
    'Keywords': sm['Keywords'],
    'Multiple': sm['Multiple']
})

new_sme = pd.DataFrame({
    'Event ID': '',
    'Data ID': sme['Data ID'],
    'Sponsor': sme['Sponsor'],
    'Asset': sme['Asset'],
    'Team': '',
    'Participant': '',
    'Host': '',
    'Text': sme['Text'],
    'Headline': '',
    'Image': sme['Image'],
    'Discount %': sme['Discount %']
})


output = BytesIO()

with pd.ExcelWriter(output, engine='openpyxl') as writer:
    new_sm.to_excel(writer, sheet_name='Social Media', index=False)
    new_sme.to_excel(writer, sheet_name='Social Media Exposure', index=False, float_format="%.2f")

output.seek(0)

st.download_button(
      label = 'Download Social Media Static File',
      data=output,
      file_name="SM Upload.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
