import logging
from io import BytesIO

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

st.markdown("# Social Media ❄️")
st.sidebar.markdown("# Social Media ❄️")

st.write("This is designed to cut some time for dashboard uploads " \
"to get the inital file into the template for uploading the file. ")

uploaded_files = st.file_uploader('Upload File Below:', type='.xlsx', accept_multiple_files=True)

required_sheets = ('Social Media', 'Social Media Exposure')
required_columns = {
    'Social Media': (
        'Country', 'Platform', 'Date', 'Account', 'Rating', 'Impressions', 'Engagement',
        'AVE ($)', 'Sponsor Value ($)', 'URL', 'Keywords', 'Multiple'
    ),
    'Social Media Exposure': ('Asset', 'Text', 'Image', 'Discount %')
}
id_columns = ('Final Data ID', 'New Data ID', 'Data ID')
brand_columns = ('Brand', 'Brands', 'Sponsor', 'Sponsors')

if not uploaded_files:
    st.info('Upload an Excel file to begin.')

# Process each workbook independently so one invalid upload does not block the rest.
for i, uploaded_file in enumerate(uploaded_files):
    if uploaded_file is None:
        st.error('A selected upload could not be read. Please select the file again.')
        continue

    # Read the expected worksheets and distinguish workbook errors from missing sheets.
    try:
        with st.spinner('Putting in template', show_time=True):
            with pd.ExcelFile(uploaded_file) as workbook:
                missing_sheets = [sheet for sheet in required_sheets if sheet not in workbook.sheet_names]
                if not missing_sheets:
                    data = {sheet: workbook.parse(sheet_name=sheet, header=0) for sheet in required_sheets}
    except Exception:
        logger.exception('Could not read uploaded workbook %s', uploaded_file.name)
        st.error(
            f"Could not read '{uploaded_file.name}'. Check that it is a valid, "
            "unprotected .xlsx workbook and try again."
        )
        continue

    if missing_sheets:
        st.error(
            f"'{uploaded_file.name}' is missing required worksheet(s): "
            + ', '.join(missing_sheets)
            + '. Please check the workbook and re-upload.'
        )
        continue

    # Check required headers before accessing source columns below.
    missing_columns = {
        sheet: [column for column in columns if column not in data[sheet].columns]
        for sheet, columns in required_columns.items()
    }
    missing_columns = {sheet: columns for sheet, columns in missing_columns.items() if columns}
    if missing_columns:
        details = '; '.join(
            f"{sheet}: {', '.join(columns)}" for sheet, columns in missing_columns.items()
        )
        st.error(
            f"'{uploaded_file.name}' is missing required column(s): {details}. "
            "Please check the worksheet headers and re-upload."
        )
        continue

    sm = data['Social Media']
    sme = data['Social Media Exposure']
    st.success(f"Loaded {len(sm)} social media and {len(sme)} exposure rows.")
    if st.button('Rerun', key=f"rerun_{i}"):
        st.rerun()

    # Resolve each sheet's optional ID and sponsor aliases independently.
    sm_id_col = next((col for col in id_columns if col in sm.columns), None)
    exposure_id_col = next((col for col in id_columns if col in sme.columns), None)
    brand_col = next((col for col in brand_columns if col in sme.columns), None)
    if sm_id_col is None:
        st.warning(f"'{uploaded_file.name}' has no recognized Social Media ID column; output IDs will be blank.")
    if exposure_id_col is None:
        st.warning(f"'{uploaded_file.name}' has no recognized exposure ID column; output IDs will be blank.")
    if brand_col is None:
        st.warning(f"'{uploaded_file.name}' has no recognized brand/sponsor column; output sponsors will be blank.")

    # Normalize source values and prepare the two upload-template tables.
    try:
        sm = sm.copy()
        sm['Impressions'] = sm['Impressions'].fillna(0)
        sm['Engagement'] = sm['Engagement'].fillna(0)
        sm['Platform'] = sm['Platform'].replace({'x': 'X'})

        new_sm = pd.DataFrame({
            'Event ID': '',
            'Data ID': sm[sm_id_col] if sm_id_col else '',
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
            'Data ID': sme[exposure_id_col] if exposure_id_col else '',
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

        # Build the download workbook in memory and catch writer/engine failures here.
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            new_sm.to_excel(writer, sheet_name='Social Media', index=False)
            new_sme.to_excel(writer, sheet_name='Social Media Exposure', index=False)
        output.seek(0)
    except Exception:
        logger.exception('Could not prepare output for uploaded workbook %s', uploaded_file.name)
        st.error(
            f"Could not prepare output for '{uploaded_file.name}'. "
            "Check the workbook contents and try again."
        )
        continue

    # Show the converted data and make the generated workbook available for download.
    with st.expander('Final Results Check before Download'):
        st.write("SM Static Data")
        st.dataframe(new_sm)
        st.write("Exposure Data")
        st.dataframe(new_sme)

    st.download_button(
        label=f"Download Social Media Static File {i + 1}",
        data=output,
        file_name=f"SM Upload {i + 1}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_{i}"
    )

    st.markdown("## Important info below 🚨🚨🚨")
    st.write(
            "After the file has been downloaded do these 3 things.\n"
            "1. In downloaded file change date format to short date."
        )
