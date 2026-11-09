
import logging
from io import BytesIO

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)
ID_COLUMNS = ('Final Data ID', 'New Data ID', 'Data ID')
BRAND_COLUMNS = ('Brand', 'Brands', 'Sponsor', 'Sponsors')


def find_column(frame, candidates):
    """Return the first supported alias present in a DataFrame."""
    return next((column for column in candidates if column in frame.columns), None)


# Main page content
st.markdown("# Online Press with Extrapolation 😎")
st.sidebar.markdown("# Online Press with Extrapolation 😎")
st.write("This is designed to cut some time for dashboard uploads " \
"to get the inital file into the template for uploading the file. ")

uploaded_file = st.file_uploader('Upload File Below:', type='.xlsx')

if uploaded_file is None:
    st.info('Upload an Excel file to begin.')
else:
    required_sheets = ('MuckRuck Data', 'Total Exposure', 'Extrapolation')
    required_columns = {
        'MuckRuck Data': (
            'Country', 'Publication', 'Headline', 'Date', 'Rating', 'Reach', 'AVE ($)',
            'Sponsor Value ($)', 'URL', 'Keywords', 'Multiple'
        ),
        'Total Exposure': ('Discount',),
        'Extrapolation': ('Data ID', 'Brand', 'Articles', 'Reach', 'Discount')
    }

    # Read the first two sheets from row one and the extrapolation headers from row nine.
    try:
        with st.spinner('Putting in template', show_time=True):
            with pd.ExcelFile(uploaded_file) as workbook:
                missing_sheets = [sheet for sheet in required_sheets if sheet not in workbook.sheet_names]
                if not missing_sheets:
                    data = {
                        'MuckRuck Data': workbook.parse('MuckRuck Data', header=0),
                        'Total Exposure': workbook.parse('Total Exposure', header=0),
                        'Extrapolation': workbook.parse('Extrapolation', header=8)
                    }
    except Exception:
        logger.exception('Could not read uploaded workbook %s', uploaded_file.name)
        st.error(
            f"Could not read '{uploaded_file.name}'. Check that it is a valid, "
            "unprotected .xlsx workbook and try again."
        )
    else:
        if missing_sheets:
            st.error(
                f"'{uploaded_file.name}' is missing required worksheet(s): "
                + ', '.join(missing_sheets)
                + '. Please check the workbook and re-upload.'
            )
        else:
            # Validate worksheet headers before any downstream column selection.
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
            else:
                muckruck = data['MuckRuck Data'].copy()
                exposure = data['Total Exposure'].copy()
                extrap = data['Extrapolation'].copy()

                # Discard only fully blank trailing rows; report partially filled extrapolation rows.
                extrap = extrap.dropna(how='all').copy()
                required_extrap_values = ('Data ID', 'Articles', 'Reach')
                incomplete_rows = extrap[list(required_extrap_values)].isna().any(axis=1)
                if incomplete_rows.any():
                    row_numbers = ', '.join(str(index + 10) for index in extrap.index[incomplete_rows])
                    st.error(
                        f"'{uploaded_file.name}' has incomplete extrapolation rows "
                        f"(worksheet rows {row_numbers}); Data ID, Articles, and Reach are required."
                    )
                else:
                    # Source ID aliases can differ by sheet, so normalize them separately.
                    muckruck_id_col = find_column(muckruck, ID_COLUMNS)
                    exposure_id_col = find_column(exposure, ID_COLUMNS)
                    if exposure_id_col is None:
                        st.error(f"'{uploaded_file.name}' needs a Data ID column in Total Exposure.")
                    else:
                        warnings = []
                        if muckruck_id_col is None:
                            muckruck['Data ID'] = ''
                            warnings.append('No recognized ID column was found in MuckRuck Data; those output IDs are blank.')
                        else:
                            muckruck['Data ID'] = muckruck[muckruck_id_col]
                        exposure['Data ID'] = exposure[exposure_id_col]

                        # Convert numeric fields explicitly to catch malformed values before export.
                        numeric_fields = (
                            (extrap, 'Articles', 'Extrapolation', True),
                            (extrap, 'Reach', 'Extrapolation', True),
                            (extrap, 'Discount', 'Extrapolation', False),
                            (exposure, 'Discount', 'Total Exposure', False)
                        )
                        invalid_values = []
                        for frame, column, sheet, required in numeric_fields:
                            original = frame[column]
                            frame[column] = pd.to_numeric(original, errors='coerce')
                            invalid = original.notna() & frame[column].isna()
                            if invalid.any():
                                invalid_values.append(
                                    f"{sheet}.{column} has {int(invalid.sum())} non-numeric value(s)"
                                )
                            if required and frame[column].isna().any():
                                invalid_values.append(f"{sheet}.{column} has missing value(s)")

                        if invalid_values:
                            st.error(
                                f"Could not process '{uploaded_file.name}': "
                                + '; '.join(invalid_values)
                                + '.'
                            )
                        else:
                            # Align sponsor names and IDs before combining source and extrapolated rows.
                            exposure_brand_col = find_column(exposure, BRAND_COLUMNS)
                            if exposure_brand_col is None:
                                exposure['Sponsor'] = ''
                                warnings.append('No recognized sponsor column was found in Total Exposure; those sponsors are blank.')
                            else:
                                exposure['Sponsor'] = exposure[exposure_brand_col]
                            extrap['Sponsor'] = extrap['Brand']

                            try:
                                extrap_mr = extrap.drop(columns=['Brand', 'Discount']).copy()
                                extrap_mr['Reach'] = extrap_mr['Reach'].round(0)
                                extrap_mr = extrap_mr.rename({'Articles': 'Multiple'}, axis=1)
                                extrap_mr['Country'] = 'Global'
                                extrap_mr['Keywords'] = extrap_mr['Data ID']

                                final_mr = pd.concat([muckruck, extrap_mr], ignore_index=True, sort=False)
                                final_mr['Country'] = final_mr['Country'].fillna('Global')

                                extrap_exposure = extrap[['Data ID', 'Sponsor', 'Discount']].copy()
                                final_exposure = pd.concat(
                                    [exposure[['Data ID', 'Sponsor', 'Discount']], extrap_exposure],
                                    ignore_index=True,
                                    sort=False
                                )

                                # Map the combined rows into the two upload-template worksheets.
                                new_muckruck = pd.DataFrame({
                                    'Event ID': '',
                                    'Data ID': final_mr['Data ID'],
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
                                    'Sponsor': final_exposure['Sponsor'],
                                    'Asset': '',
                                    'Team': '',
                                    'Participant': '',
                                    'Host': '',
                                    'Text': '',
                                    'Headline': '',
                                    'Image': '',
                                    'Discount %': final_exposure['Discount']
                                })

                                # Keep workbook-generation failures within the same recovery boundary.
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
                            else:
                                for warning in warnings:
                                    st.warning(f"{uploaded_file.name}: {warning}")
                                st.success(
                                    f"Loaded {len(muckruck)} MuckRuck, {len(exposure)} exposure, "
                                    f"and {len(extrap)} extrapolation rows."
                                )
                                if st.button('Rerun'):
                                    st.rerun()

                                # Show the completed tables and provide the generated workbook.
                                st.subheader("Final Results")
                                st.dataframe(new_muckruck)
                                st.dataframe(new_exposure)
                                st.download_button(
                                    label='Download OP File',
                                    data=output,
                                    file_name='OP Upload.xlsx',
                                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                                )

st.markdown("## Important info below 🚨🚨🚨")
st.write(
    "After the file has been downloaded do these 3 things.\n"
    "1. In downloaded file change date format to short date."
)