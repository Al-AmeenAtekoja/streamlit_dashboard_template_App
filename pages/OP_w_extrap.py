
import streamlit as st
import pandas as pd
from io import BytesIO


# Main page content
st.markdown("# Online Press with Extrapolation 😎")
st.sidebar.markdown("# Online Press with Extrapolation 😎")

st.write("This is designed to cut some time for dashboard uploads " \
"to get the inital file into the template for uploading the file. ")

uploaded_file = st.file_uploader('Upload File Below:',type='.xlsx', accept_multiple_files=True)

if uploaded_file is None:
        st.info('Upload an Excel File to begin.')
        st.stop()

with st.spinner('Putting in template', show_time=True):
        required_sheets = {
                'MuckRuck Data': dict(header=0),
                'Total Exposure':  dict(header = 0),
                'Extrapolation': dict(header=8, usecols=['Data ID', 'Brand', 'Articles', 'Reach', 'Discount'])
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
        extrap = data['Extrapolation']

        
        st.success(f"Loaded {len(muckruck)} muckruck and {len(exposure)} Exposure rows.")
        if st.button('Rerun'):
                st.rerun()

data_id_col = next(
      (col for col in ['Final Data ID', 'New Data ID'] if col in muckruck.columns),
      None
)
brand_col = next(
      (col for col in ['Brand', 'Brands', 'Sponsor'] if col in exposure.columns),
      None
)

extrap_mr = extrap.copy().dropna()
extrap_exposure = extrap.copy().dropna()

extrap_exposure = extrap_exposure.drop(columns=['Articles', 'Reach'])
extrap_mr = extrap_mr.drop(columns=['Brand', 'Discount'])
extrap_mr = extrap_mr.rename({'Articles': 'Multiple', 'Data ID': 'New Data ID'}, axis=1)
final_mr = pd.concat([muckruck, extrap_mr])
final_exposure = pd.concat([exposure, extrap_exposure])

new_muckruck = pd.DataFrame({
      'Event ID': '',
      'Data ID' : final_mr[data_id_col] if data_id_col else '',
      'Country': final_mr['Country'],
      'Publication': final_mr['Publication'],
      'Headline': final_mr['Headline'],
      'Date': final_mr['Date'],
      'Rating': final_mr['Rating'],
      'Reach': final_mr['Reach'],
      'AVE ($)': final_mr['AVE ($)'],
      'Sponsor Value ($)': final_mr['Sponsor Value ($)'],
      'Url': final_mr['URL'],
      'Keywords': final_mr['Keywords'],
      'Multiple': final['Multiple']
})

new_exposure = pd.DataFrame({
    'Event ID': '',
    'Data ID': final_exposure['Data ID'],
    'Sponsor': final_exposure[brand_col] if brand_col else '',
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
    new_exposure.to_excel(writer, sheet_name='Online Press Exposure', index=False)

output.seek(0)

st.subheader("Final Results")
st.dataframe(new_muckruck)
st.dataframe(new_exposure)

st.download_button(
      label = 'Download OP File',
      data=output,
      file_name="OP Upload.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
       
