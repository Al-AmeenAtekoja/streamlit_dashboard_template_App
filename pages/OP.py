
import streamlit as st
import pandas as pd
from io import BytesIO
#import openpyxl
#from pyxlsb import open_workbook as open_xlsb

# Main page content
st.markdown("# Online Press 🎈")
st.sidebar.markdown("# Online Press 🎈")

st.write("This is designed to cut some time for dashboard uploads " \
"to get the inital file into the template for uploading the file. ")

uploaded_files = st.file_uploader('Upload File Below:',type='.xlsx', accept_multiple_files=True)

for uploaded_file in uploaded_files: 
    if uploaded_file is None:
            st.info('Upload an Excel File to begin.')
            st.stop()

    with st.spinner('Putting in template', show_time=True):
            required_sheets = {
                    'MuckRuck Data': dict(header=0),
                    'Total Exposure':  dict(header = 0)
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
            
            muckruck = data['MuckRuck Data']
            exposure = data['Total Exposure']
            

            for i in range(len(uploaded_files)):
                st.success(f"Loaded {len(muckruck)} projects and {len(exposure)} summary rows.")
                if st.button('Rerun', key="delete_" + i):
                        st.rerun()

    data_id_col = next(
        (col for col in ['Final Data ID', 'New Data ID'] if col in muckruck.columns),
        None
    )
    brand_col = next(
        (col for col in ['Brand', 'Brands', 'Sponsor'] if col in exposure.columns),
        None
    )
    new_muckruck = pd.DataFrame({
        'Event ID': '',
        'Data ID' : muckruck[data_id_col] if data_id_col else '',
        'Country': muckruck['Country'],
        'Publication': muckruck['Publication'],
        'Headline': muckruck['Headline'],
        'Date': muckruck['Date'],
        'Rating': muckruck['Rating'],
        'Reach': muckruck['Reach'],
        'AVE ($)': muckruck['AVE ($)'],
        'Sponsor Value ($)': muckruck['Sponsor Value ($)'],
        'Url': muckruck['URL'],
        'Keywords': muckruck['Keywords'],
        'Multiple': 1
    })

    new_exposure = pd.DataFrame({
        'Event ID': '',
        'Data ID': exposure['Data ID'],
        'Sponsor': exposure[brand_col] if brand_col else '',
        'Asset': '',
        'Team': '',
        'Participant': '',
        'Host': '',
        'Text': '',
        'Headline': '',
        'Image': '',
        'Discount %': exposure['Discount']
    })
    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        new_muckruck.to_excel(writer, sheet_name='Online Press', index=False)
        new_exposure.to_excel(writer, sheet_name='Online Press Exposure', index=False, float_format="%.2f")

    output.seek(0)

    for i in range(len(uploaded_files)):
        st.download_button(
            label = 'Download OP File',
            data=output,
            file_name="OP Upload.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key='delete_'+i)
       
