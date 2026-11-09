
import logging
import streamlit as st
import pandas as pd
from io import BytesIO

logger = logging.getLogger(__name__)


# Main page content
st.markdown("# Online Press 🎈")
st.sidebar.markdown("# Online Press 🎈")

st.write("This is designed to cut some time for dashboard uploads " \
"to get the inital file into the template for uploading the file. ")

uploaded_files = st.file_uploader('Upload File Below:',type='.xlsx', accept_multiple_files=True)

if not uploaded_files:
    st.info('Upload an Excel file to begin.')

# Process each upload independently so one invalid file does not block the rest.
for i, uploaded_file in enumerate(uploaded_files): 
    if uploaded_file is None:
            st.error('A selected upload could not be read. Please select the file again.')
            continue

    with st.spinner('Putting in template', show_time=True):
            # Both source worksheets are required before the upload can be converted.
            required_sheets = {
                    'MuckRuck Data': 0,
                    'Total Exposure': 0
                }
            required_columns = {
                    'MuckRuck Data': (
                        'Country', 'Publication', 'Headline', 'Date', 'Rating', 'Reach',
                        'AVE ($)', 'Sponsor Value ($)', 'URL', 'Keywords'
                    ),
                    'Total Exposure': ('Data ID', 'Discount')
                }
            data = {}
            try:
                    with pd.ExcelFile(uploaded_file) as workbook:
                        # Check names first to distinguish missing sheets from unreadable files.
                            missing_sheets = [
                                sheet for sheet in required_sheets if sheet not in workbook.sheet_names
                            ]
                            if not missing_sheets:
                                    data = {
                                        sheet: workbook.parse(sheet_name=sheet, header=header)
                                        for sheet, header in required_sheets.items()
                                    }
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

                    # Validate headers before the transformation indexes individual columns.
            missing_columns = {
                sheet: [column for column in columns if column not in data[sheet].columns]
                for sheet, columns in required_columns.items()
            }
            missing_columns = {
                sheet: columns for sheet, columns in missing_columns.items() if columns
            }
            if missing_columns:
                    details = '; '.join(
                        f"{sheet}: {', '.join(columns)}"
                        for sheet, columns in missing_columns.items()
                    )
                    st.error(
                        f"'{uploaded_file.name}' is missing required column(s): {details}. "
                        "Please check the worksheet headers and re-upload."
                    )
                    continue
            
            muckruck = data['MuckRuck Data']
            exposure = data['Total Exposure']
            

            st.success(f"Loaded {len(muckruck)} projects and {len(exposure)} summary rows.")
            if st.button('Rerun', key=f"rerun_{i}"):
                    st.rerun()

    # Accept common alternate names used for the same source fields.
    data_id_col = next(
        (col for col in ['Final Data ID', 'New Data ID', 'Data ID'] if col in muckruck.columns),
        None
    )
    brand_col = next(
        (col for col in ['Brand', 'Brands', 'Sponsor','Sponsors'] if col in exposure.columns),
        None
    )
    # These aliases are optional; warn when absent because the corresponding output is blank.
    if data_id_col is None:
        st.warning(
            f"'{uploaded_file.name}' has no recognized MuckRuck ID column; "
            "the output Data ID field will be blank."
        )
    if brand_col is None:
        st.warning(
            f"'{uploaded_file.name}' has no recognized brand/sponsor column; "
            "the output Sponsor field will be blank."
        )
    final_exposure = pd.pivot_table(
          exposure, index=['Data ID', 'Brand'], values=['Discount'], aggfunc='sum'
    ).reset_index()

    try:
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
        # Build the download workbook in memory instead of writing a temporary file.
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            new_muckruck.to_excel(writer, sheet_name='Online Press', index=False)
            new_exposure.to_excel(writer, sheet_name='Online Press Exposure', index=False)

        output.seek(0)
    except Exception:
        logger.exception('Could not prepare output for uploaded workbook %s', uploaded_file.name)
        st.error(
            f"Could not prepare output for '{uploaded_file.name}'. "
            "Check the workbook contents and try again."
        )
        continue

    st.subheader("Final Results")
    st.dataframe(new_muckruck)
    st.dataframe(new_exposure)

    st.download_button(
        label = f"Download OP File{i+1}",
        data=output,
        file_name=f"OP Upload {i+1}.xlsx",
        mime=f"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key= f"download_{i}")