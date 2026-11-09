
import streamlit as st
import pandas as pd
from io import BytesIO


# Main page content
st.markdown("# Online Press with Extrapolation 😎")
st.sidebar.markdown("# Online Press with Extrapolation 😎")

st.write("This is designed to cut some time for dashboard uploads " \
"to get the inital file into the template for uploading the file. ")

uploaded_file = st.file_uploader('Upload File Below:',type='.xlsx')

if uploaded_file is None:
        st.info('Upload an Excel File to begin.')
        st.stop()

with st.spinner('Putting in template', show_time=True):
    # The extrapolation worksheet has its headers on row nine; the others start on row one.
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
        
        # Stop before transformation if any required worksheet could not be found.
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
      (col for col in ['Final Data ID', 'New Data ID', 'Data ID'] if col in muckruck.columns),
      None
)
# Use the first recognized source headers when mapping optional IDs and sponsors.
brand_col = next(
      (col for col in ['Brand', 'Brands', 'Sponsor'] if col in exposure.columns),
      None
)

# Prepare complete extrapolation rows separately for the mentions and exposure outputs.
extrap_mr = extrap.copy().dropna()
extrap_exposure = extrap.copy().dropna()

extrap_exposure = extrap_exposure.drop(columns=['Articles', 'Reach'])
extrap_mr = extrap_mr.drop(columns=['Brand', 'Discount'])
extrap_mr['Reach'] = round(extrap_mr['Reach'],0)
extrap_mr = extrap_mr.rename({'Articles': 'Multiple', 'Data ID': 'New Data ID'}, axis=1)
extrap_mr['Keywords'] = extrap_mr['New Data ID']

# Append extrapolated articles and use Global where no country was supplied.
final_mr = pd.concat([muckruck, extrap_mr])
final_mr['Country'] = final_mr['Country'].fillna(value='Global')
final_mr['Publication'] = final_mr['Publication'].fillna(value='Unspecified')
final_mr['Headline'] = final_mr['Headline'].fillna(value='Unspecified')
final_mr['URL'] = final_mr['URL'].fillna(value='Unspecified')
final_mr['Rating'] = final_mr['Rating'].fillna(value='Neutral')
final_mr['AVE ($)'] = final_mr['AVE ($)'].fillna(value=0)
final_mr['Sponsor Value ($)'] = final_mr['Sponsor Value ($)'].fillna(value=0)
pen_exposure = pd.concat([exposure, extrap_exposure])
final_exposure = pd.pivot_table(
      pen_exposure, index=['Data ID', 'Brand'], values=['Discount'], aggfunc='sum'
).reset_index()
final_exposure['Date'] = final_exposure['Date'].fillna(final_exposure['Date'].mean())

# Map the combined source data to the upload template's required columns.
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
      'Multiple': final_mr['Multiple']
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
    'Discount %': final_exposure['Discount']
})
# Build the Excel download in memory rather than creating a temporary file.
output = BytesIO()

with pd.ExcelWriter(output, engine='openpyxl') as writer:
    new_muckruck.to_excel(writer, sheet_name='Online Press', index=False)
    new_exposure.to_excel(writer, sheet_name='Online Press Exposure', index=False)

output.seek(0)

# Preview both output sheets before making the workbook available for download.
st.subheader("Final Results")
st.dataframe(new_muckruck)
st.dataframe(new_exposure)

st.download_button(
      label = 'Download OP File',
      data=output,
      file_name="OP Upload.xlsx",
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
       
st.markdown("## Important info below 🚨🚨🚨")
st.write(
    "After the file has been downloaded do these 3 things.\n"
    "1. In downloaded file change date format to short date."
)