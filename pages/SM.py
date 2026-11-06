import streamlit as st
import pandas as pd
from io import BytesIO

st.markdown("# Social Media ❄️")
st.sidebar.markdown("# Social Media ❄️")

st.write("This is designed to cut some time for dashboard uploads " \
"to get the inital file into the template for uploading the file. ")


uploaded_files = st.file_uploader('Upload File Below:',type='.xlsx', accept_multiple_files=True)

for i, uploaded_file in enumerate(uploaded_files):
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
            if st.button('Rerun',  key=f"rerun_{i}"):
                    st.rerun()

    sm['Impressions'] = sm['Impressions'].fillna(0)
    sm['Engagement'] = sm['Engagement'].fillna(0)
    clean_platform = {'x': 'X'}
    sm['Platform'] = sm['Platform'].replace(clean_platform)


    data_id_col = next(
        (col for col in ['Final Data ID', 'New Data ID'] if col in sm.columns),
        None
    )
    brand_col = next(
        (col for col in ['Brand', 'Brands', 'Sponsor'] if col in sme.columns),
        None
    )
    new_sm = pd.DataFrame({
        'Event ID': '',
        'Data ID': sm[data_id_col] if data_id_col else '',
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
        'Data ID': sme[data_id_col] if data_id_col else '',
        'Sponsor': sme[brand_col] if brand_col else '',
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
            label = f"Download Social Media Static File File{i+1}",
            data=output,
            file_name=f"SM Upload {i+1}.xlsx",
            mime=f"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key= f"download_{i}")
