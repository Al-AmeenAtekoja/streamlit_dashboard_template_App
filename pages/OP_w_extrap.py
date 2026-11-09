
import logging
from io import BytesIO

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)
ID_COLUMNS = ('Final Data ID', 'New Data ID', 'Data ID')
BRAND_COLUMNS = ('Brand', 'Brands', 'Sponsor', 'Sponsors')


# Main page content
st.markdown("# Online Press with Extrapolation 😎")
st.sidebar.markdown("# Online Press with Extrapolation 😎")
st.write("This is designed to cut some time for dashboard uploads " \
"to get the inital file into the template for uploading the file. ")

uploaded_files = st.file_uploader('Upload File Below:', type='.xlsx', accept_multiple_files=True)
required_sheets = ('MuckRuck Data', 'Total Exposure', 'Extrapolation')
required_columns = {
    'MuckRuck Data': (
        'Country', 'Publication', 'Headline', 'Date', 'Rating', 'Reach', 'AVE ($)',
        'Sponsor Value ($)', 'URL', 'Keywords', 'Multiple'
    ),
    'Total Exposure': ('Discount',),
    'Extrapolation': ('Articles', 'Reach', 'Discount')
}

if not uploaded_files:
    st.info('Upload an Excel file to begin.')

# Process each workbook independently so one invalid upload does not block the rest.
for i, uploaded_file in enumerate(uploaded_files):
    if uploaded_file is None:
        st.error('A selected upload could not be read. Please select the file again.')
        continue

    # The extrapolation worksheet has its headers on row nine; the others start on row one.
    try:
        with st.spinner('Putting in template', show_time=True):
            with pd.ExcelFile(uploaded_file) as workbook:
                missing_sheets = [sheet for sheet in required_sheets if sheet not in workbook.sheet_names]
                if not missing_sheets:
                    data = {
                        'MuckRuck Data': workbook.parse('MuckRuck Data', header=0),
                        'Total Exposure': workbook.parse('Total Exposure', header=0),
                        'Extrapolation': workbook.parse('Extrapolation', header=8, usecols=['Data ID', 'Brand','Articles','Reach', 'Discount'])
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

    # Validate direct column requirements and supported ID/sponsor aliases before conversion.
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

    muckruck = data['MuckRuck Data'].copy()
    exposure = data['Total Exposure'].copy()
    extrap = data['Extrapolation'].dropna(how='all').copy()
    muckruck_id_col = next((col for col in ID_COLUMNS if col in muckruck.columns), None)
    exposure_id_col = next((col for col in ID_COLUMNS if col in exposure.columns), None)
    extrap_id_col = next((col for col in ID_COLUMNS if col in extrap.columns), None)
    exposure_brand_col = next((col for col in BRAND_COLUMNS if col in exposure.columns), None)
    extrap_brand_col = next((col for col in BRAND_COLUMNS if col in extrap.columns), None)

    if exposure_id_col is None or extrap_id_col is None:
        missing_id_sheets = []
        if exposure_id_col is None:
            missing_id_sheets.append('Total Exposure')
        if extrap_id_col is None:
            missing_id_sheets.append('Extrapolation')
        st.error(
            f"'{uploaded_file.name}' needs a recognized Data ID column in: "
            + ', '.join(missing_id_sheets)
            + '.'
        )
        continue

    # Reject incomplete extrapolation rows instead of silently dropping them.
    required_extrap_values = ('Data ID', 'Articles', 'Reach')
    extrap_id_col = next((col for col in ID_COLUMNS if col in extrap.columns), None)
    extrap['Data ID'] = extrap[extrap_id_col]
    incomplete_rows = extrap[list(required_extrap_values)].isna().any(axis=1)
    blank_ids = extrap['Data ID'].astype('string').str.strip().eq('').fillna(True)
    incomplete_rows |= blank_ids
    if incomplete_rows.any():
        worksheet_rows = ', '.join(str(index + 10) for index in extrap.index[incomplete_rows])
        st.error(
            f"'{uploaded_file.name}' has incomplete extrapolation rows (worksheet rows "
            f"{worksheet_rows}); Data ID, Articles, and Reach are required."
        )
        continue

    # Normalize numeric inputs and distinguish blanks from malformed values.
    numeric_errors = []
    for frame, column, label, required in (
        (extrap, 'Articles', 'Extrapolation.Articles', True),
        (extrap, 'Reach', 'Extrapolation.Reach', True),
        (extrap, 'Discount', 'Extrapolation.Discount', False),
        (exposure, 'Discount', 'Total Exposure.Discount', False)
    ):
        original = frame[column]
        frame[column] = pd.to_numeric(original, errors='coerce')
        invalid = original.notna() & frame[column].isna()
        if invalid.any():
            numeric_errors.append(f"{label} contains {int(invalid.sum())} non-numeric value(s)")
        if required and frame[column].isna().any():
            numeric_errors.append(f"{label} contains missing value(s)")
    if numeric_errors:
        st.error(f"Could not process '{uploaded_file.name}': " + '; '.join(numeric_errors) + '.')
        continue

    warnings = []
    if muckruck_id_col is None:
        muckruck['Data ID'] = ''
        warnings.append('No recognized ID column was found in MuckRuck Data; those output IDs are blank.')
    else:
        muckruck['Data ID'] = muckruck[muckruck_id_col]
    exposure['Data ID'] = exposure[exposure_id_col]
    exposure['Brand'] = exposure[exposure_brand_col] if exposure_brand_col else ''
    extrap['Brand'] = extrap[extrap_brand_col] if extrap_brand_col else ''
    if exposure_brand_col is None and extrap_brand_col is None:
        warnings.append('No recognized brand/sponsor column was found; exposure sponsors are blank.')

    st.success(
        f"Loaded {len(muckruck)} MuckRuck, {len(exposure)} exposure, "
        f"and {len(extrap)} extrapolation rows."
    )
    if st.button('Rerun', key=f"rerun_{i}"):
        st.rerun()

    # Combine the extrapolated article rows with source data, applying template defaults.
    try:
        extrap_mr = pd.DataFrame({
            'Data ID': extrap['Data ID'],
            'Country': 'Global',
            'Publication': 'Unspecified',
            'Headline': 'Unspecified',
            'Date': pd.NaT,
            'Rating': 'Neutral',
            'Reach': extrap['Reach'].round(0),
            'AVE ($)': 0,
            'Sponsor Value ($)': 0,
            'URL': 'Unspecified',
            'Keywords': extrap['Data ID'],
            'Multiple': extrap['Articles']
        })
        final_mr = pd.concat([muckruck, extrap_mr], ignore_index=True, sort=False)
        final_mr['Country'] = final_mr['Country'].fillna('Global')
        final_mr['Publication'] = final_mr['Publication'].fillna('Unspecified')
        final_mr['Headline'] = final_mr['Headline'].fillna('Unspecified')
        final_mr['URL'] = final_mr['URL'].fillna('Unspecified')
        final_mr['Rating'] = final_mr['Rating'].fillna('Neutral')
        final_mr['AVE ($)'] = final_mr['AVE ($)'].fillna(0)
        final_mr['Sponsor Value ($)'] = final_mr['Sponsor Value ($)'].fillna(0)

        # Use the average source date for extrapolated rows, when source dates are valid.
        original_dates = muckruck['Date']
        muckruck['Date'] = pd.to_datetime(original_dates, errors='coerce')
        invalid_dates = (original_dates.notna() & muckruck['Date'].isna()).sum()
        if invalid_dates:
            raise ValueError(f"{invalid_dates} date value(s) in MuckRuck Data could not be parsed")
        average_date = muckruck['Date'].mean()
        final_mr['Date'] = pd.to_datetime(final_mr['Date'], errors='coerce').fillna(average_date)
        if pd.isna(average_date) and len(extrap_mr):
            warnings.append('No valid source date was available; extrapolated output dates are blank.')

        extrap_exposure = extrap[['Data ID', 'Brand', 'Discount']].copy()
        exposure_rows = exposure[['Data ID', 'Brand', 'Discount']]
        final_exposure = pd.concat([exposure_rows, extrap_exposure], ignore_index=True, sort=False)
        final_exposure = final_exposure.groupby(
            ['Data ID', 'Brand'], as_index=False, dropna=False
        )['Discount'].sum()

        # Map consolidated data into the two required upload-template sheets.
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
            'Sponsor': final_exposure['Brand'],
            'Asset': '',
            'Team': '',
            'Participant': '',
            'Host': '',
            'Text': '',
            'Headline': '',
            'Image': '',
            'Discount %': final_exposure['Discount']
        })

        # Generate the Excel download in memory so no temporary file is needed.
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            new_muckruck.to_excel(writer, sheet_name='Online Press', index=False)
            new_exposure.to_excel(writer, sheet_name='Online Press Exposure', index=False)
        output.seek(0)
    except ValueError as error:
        st.error(f"Could not process '{uploaded_file.name}': {error}.")
        continue
    except Exception:
        logger.exception('Could not prepare output for uploaded workbook %s', uploaded_file.name)
        st.error(
            f"Could not prepare output for '{uploaded_file.name}'. "
            "Check the workbook contents and try again."
        )
        continue

    for warning in warnings:
        st.warning(f"{uploaded_file.name}: {warning}")

    # Preview generated sheets before offering the workbook for download.
    with st.expander('Final Results Check before Download', key=f'expander_{i}'):
        st.write("OP Data")
        st.dataframe(new_muckruck)
        st.write("Exposure Data")
        st.dataframe(new_exposure)

    st.download_button(
        label=f'Download OP File {i + 1}',
        data=output,
        file_name=f"OP Upload {i + 1}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_{i}"
    )

    # Remind users to format the downloaded date column before uploading it elsewhere.
    st.markdown("## Important info below 🚨🚨🚨")
    st.write(
        "After the file has been downloaded do these 3 things.\n"
        "1. In downloaded file change date format to short date."
    )