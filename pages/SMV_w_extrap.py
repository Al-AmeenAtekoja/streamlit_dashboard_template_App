import logging
from io import BytesIO

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)

PLATFORM_ALIASES = {
    'instagram.com': 'Instagram',
    'facebook.com': 'Facebook',
    'FaceBook': 'Facebook',
    'x.com': 'X',
    'tiktok.com': 'Tiktok',
    'threads.com': 'Threads',
    'youtube.com': 'Youtube'
}
PLATFORM_CPT = {
    'Facebook': 7.80,
    'Instagram': 5.88,
    'Youtube': 8.07,
    'YouTube': 8.07,
    'X': 9.07,
    'Tiktok': 8.15,
    'TikTok': 8.15,
    'Threads': 4.00,
    'Pinterest': 3.67,
    'Bluesky': 4.00
}
ID_COLUMNS = ('Final Data ID', 'New Data ID', 'Data ID')
BRAND_COLUMNS = ('Brand', 'Brands', 'Sponsor', 'Sponsors')


def build_extrapolated_upload(mentions, exposure, extrapolation):
    """Prepare monitored and extrapolated rows for the video upload workbook."""
    warnings = []
    mentions = mentions.copy()
    exposure = exposure.copy()
    extrapolation = extrapolation.copy()

    # Normalize source names and fill missing author names before filtering.
    mentions['Source'] = mentions['Source'].astype('string').str.strip().replace(PLATFORM_ALIASES)
    if 'Author' not in mentions.columns:
        mentions['Author'] = pd.NA
    mentions['Author'] = mentions['Author'].fillna(mentions['Nickname'])
    monitored = mentions['Monitored'].astype('string').str.strip().str.casefold().eq('yes')
    smv = mentions.loc[monitored].copy()
    if smv.empty:
        raise ValueError("no rows are marked 'Yes' in the Monitored column")
    if (smv['Source'].isna() | smv['Source'].eq('')).any():
        raise ValueError('one or more monitored rows are missing a platform/source')

    # Standardize optional and alternate ID headers independently in each worksheet.
    mention_id_col = next((col for col in ID_COLUMNS if col in smv.columns), None)
    exposure_id_col = next((col for col in ID_COLUMNS if col in exposure.columns), None)
    extrapolation_id_col = next((col for col in ID_COLUMNS if col in extrapolation.columns), None)
    if mention_id_col is None:
        smv['Data ID'] = ''
        warnings.append('No recognized ID column was found in Mentions; output IDs are blank.')
    else:
        smv['Data ID'] = smv[mention_id_col]
    if exposure_id_col is None:
        raise ValueError('the Exposure worksheet needs a Data ID column')
    if extrapolation_id_col is None:
        raise ValueError('the Extrapolation1 worksheet needs a Data ID column')
    extrapolation['Data ID'] = extrapolation[extrapolation_id_col]

    # Parse numeric source fields and reject malformed non-empty values early.
    for frame, fields, label in (
        (smv, ('Views', 'Engagement'), 'Mentions'),
        (extrapolation, ('Average of Views', 'Average of Engagement', 'Average of Duration'), 'Extrapolation1')
    ):
        for column in fields:
            original = frame[column]
            frame[column] = pd.to_numeric(original, errors='coerce')
            invalid_count = (original.notna() & frame[column].isna()).sum()
            if invalid_count:
                raise ValueError(f"{invalid_count} value(s) in {label}.{column} are not numeric")

    extrapolation_sizes = pd.to_numeric(extrapolation['Extrapolate Size'], errors='coerce')
    invalid_sizes = extrapolation['Extrapolate Size'].notna() & extrapolation_sizes.isna()
    if invalid_sizes.any() or extrapolation_sizes.isna().any():
        raise ValueError('Extrapolation1.Extrapolate Size contains missing or non-numeric values')
    if extrapolation_sizes.lt(0).any():
        raise ValueError('Extrapolation1.Extrapolate Size cannot be negative')
    extrapolation['Multiple'] = extrapolation_sizes.round(0).replace(0, 1)

    # Calculate monitored engagement rates while treating zero views as unavailable.
    smv['Engagement Rate'] = smv['Engagement'].div(smv['Views'].where(smv['Views'].ne(0)))
    platform_rates = smv.groupby('Source', dropna=True)['Engagement Rate'].mean().to_dict()
    platform_rates['Threads'] = 0.073403
    smv['Engagement Rate'] = smv['Engagement Rate'].fillna(smv['Source'].map(platform_rates))
    smv['Views'] = smv['Views'].fillna(
        smv['Engagement'].div(smv['Engagement Rate'].where(smv['Engagement Rate'].ne(0))).round(0)
    )

    # Parse dates before deriving average dates used by extrapolated rows.
    original_dates = smv['Date']
    smv['Date'] = pd.to_datetime(original_dates, errors='coerce', format='mixed', dayfirst=True)
    invalid_dates = (original_dates.notna() & smv['Date'].isna()).sum()
    if invalid_dates:
        raise ValueError(f"{invalid_dates} date value(s) in Mentions could not be parsed")
    dates_by_source = smv.groupby('Source', dropna=True)['Date'].mean().dropna().to_dict()

    # Normalize extrapolation labels and calculate safe cost estimates.
    extrapolation['Source'] = (
        extrapolation['Row Labels'].astype('string').str.strip().replace(PLATFORM_ALIASES)
    )
    if (extrapolation['Source'].isna() | extrapolation['Source'].eq('')).any():
        raise ValueError('one or more extrapolated rows are missing a platform/source')
    extrapolation['Engagement'] = extrapolation['Average of Engagement']
    extrapolation['Views'] = extrapolation['Average of Views']
    extrapolation['Duration'] = extrapolation['Average of Duration']
    extrapolation['Engagement Rate'] = extrapolation['Engagement'].div(
        extrapolation['Views'].where(extrapolation['Views'].ne(0))
    )
    extrapolation['Engagement Rate'] = extrapolation['Engagement Rate'].fillna(
        extrapolation['Source'].map(platform_rates)
    )
    extrapolation['Views'] = extrapolation['Views'].fillna(
        extrapolation['Engagement'].div(
            extrapolation['Engagement Rate'].where(extrapolation['Engagement Rate'].ne(0))
        ).round(0)
    )

    # Reject unknown platforms and extrapolated platforms without a source date.
    smv['CPT'] = smv['Source'].map(PLATFORM_CPT)
    extrapolation['CPT'] = extrapolation['Source'].map(PLATFORM_CPT)
    unknown_platforms = pd.concat([smv['Source'], extrapolation['Source']]).drop_duplicates()
    unknown_platforms = unknown_platforms[
        ~unknown_platforms.isin(PLATFORM_CPT)
    ].dropna().tolist()
    if unknown_platforms:
        raise ValueError(f"unsupported platform value(s): {', '.join(map(str, unknown_platforms))}")

    extrapolation_dates = []
    for source in extrapolation['Source']:
        date_source = 'Instagram' if source == 'Threads' else source
        if date_source not in dates_by_source:
            raise ValueError(f"no valid Mentions date is available for extrapolated platform '{source}'")
        extrapolation_dates.append(dates_by_source[date_source])

    # Build costs and warn when missing metrics prevent a complete estimate.
    smv['Spot Cost'] = ((smv['Views'] / 1000) * smv['CPT']) * (1 + smv['Engagement Rate'])
    extrapolation['Spot Cost'] = (
        (extrapolation['Views'] / 1000) * extrapolation['CPT']
    ) * (1 + extrapolation['Engagement Rate'])
    unresolved_metrics = (
        smv['Views'].isna().sum() + extrapolation['Views'].isna().sum()
        + smv['Engagement Rate'].isna().sum() + extrapolation['Engagement Rate'].isna().sum()
    )
    if unresolved_metrics:
        warnings.append(
            f"{unresolved_metrics} metric value(s) could not be estimated; affected spot costs may be blank."
        )
    smv['Country'] = smv['Country'].fillna('Global')
    smv['Multiple'] = 1
    smv['Engagement'] = smv['Engagement'].round(0)
    smv['Views'] = smv['Views'].round(0)

    extrapolation_rows = pd.DataFrame({
        'Data ID': extrapolation['Data ID'],
        'Country': 'Global',
        'Source': extrapolation['Source'],
        'Author': 'Unspecified',
        'Title': '',
        'Date': extrapolation_dates,
        'Duration': extrapolation['Duration'],
        'Views': extrapolation['Views'].round(0),
        'Engagement': extrapolation['Engagement'].round(0),
        'Spot Cost': extrapolation['Spot Cost'],
        'URL': 'Unspecified',
        'Multiple': extrapolation['Multiple']
    })
    mention_rows = smv[
        ['Data ID', 'Country', 'Source', 'Author', 'Title', 'Date', 'Duration', 'Views',
         'Engagement', 'Spot Cost', 'URL', 'Multiple']
    ]
    final_mentions = pd.concat([mention_rows, extrapolation_rows], ignore_index=True)

    # Combine source and extrapolated exposure rows into the shared output schema.
    brand_col = next((col for col in BRAND_COLUMNS if col in exposure.columns), None)
    extrapolation_brand_col = next((col for col in BRAND_COLUMNS if col in extrapolation.columns), None)
    if brand_col is None and extrapolation_brand_col is None:
        warnings.append('No recognized brand/sponsor columns were found; output sponsors are blank.')

    exposure_visibility = pd.to_numeric(exposure['Visibility'], errors='coerce')
    invalid_visibility = exposure['Visibility'].notna() & exposure_visibility.isna()
    extrapolated_visibility = pd.to_numeric(extrapolation['Average of Visibility'], errors='coerce')
    invalid_extrapolated_visibility = (
        extrapolation['Average of Visibility'].notna() & extrapolated_visibility.isna()
    )
    if invalid_visibility.any() or invalid_extrapolated_visibility.any():
        raise ValueError('Visibility values in Exposure or Extrapolation1 must be numeric')

    base_exposure_rows = pd.DataFrame({
        'Data ID': exposure[exposure_id_col],
        'Sponsor': exposure[brand_col] if brand_col else '',
        'Visibility': exposure_visibility
    })
    extrapolated_exposure_rows = pd.DataFrame({
        'Data ID': extrapolation['Data ID'],
        'Sponsor': extrapolation[extrapolation_brand_col] if extrapolation_brand_col else '',
        'Visibility': extrapolated_visibility
    })
    final_exposure = pd.concat(
        [base_exposure_rows, extrapolated_exposure_rows], ignore_index=True
    )

    # Map the normalized tables to the upload template and create the workbook in memory.
    new_smv = pd.DataFrame({
        'Event ID': '',
        'Data ID': final_mentions['Data ID'],
        'Country': final_mentions['Country'],
        'Platform': final_mentions['Source'],
        'Account': final_mentions['Author'],
        'Video Title': final_mentions['Title'],
        'Date': final_mentions['Date'],
        'Duration': final_mentions['Duration'],
        'Views': final_mentions['Views'],
        'Engagement': final_mentions['Engagement'],
        '30 Second Spot Cost': final_mentions['Spot Cost'],
        'Url': final_mentions['URL'],
        'Keywords': final_mentions['Data ID'],
        'Multiple': final_mentions['Multiple']
    })
    new_smve = pd.DataFrame({
        'Event ID': '',
        'Data ID': final_exposure['Data ID'],
        'Sponsor': final_exposure['Sponsor'],
        'Asset': 'All Assets',
        'Team': '',
        'Participant': '',
        'Host': '',
        '% Visibility': final_exposure['Visibility'],
        'SIQ+': '',
        'Exposure Type': 1,
        'No of Seconds': 0
    })

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        new_smv.to_excel(writer, sheet_name='Social Media Videos', index=False)
        new_smve.to_excel(writer, sheet_name='Social Media Video Exposure', index=False)
    output.seek(0)
    return final_mentions, final_exposure, new_smve, new_smv, output, warnings


st.markdown("# Social Media Video with Extrapolation 👊")
st.sidebar.markdown("# Social Media Extrapolation 👊")
st.write("This is designed to cut some time for dashboard uploads " \
"to get the inital file into the template for uploading the file. ")
st.write(
    "For extrapolated rows create a sheet called 'Extrapolation1' and put the rows "
    "in that sheet in Cell A2 in the new sheet then upload"
)

uploaded_files = st.file_uploader('Upload File Below:', type='.xlsx', accept_multiple_files=True)
required_sheets = ('Mentions', 'Exposure', 'Extrapolation1')
required_columns = {
    'Mentions': (
        'Source', 'Nickname', 'Monitored', 'Country', 'Title', 'Date', 'Duration',
        'Views', 'Engagement', 'URL'
    ),
    'Exposure': ('Duration', 'Exposure', 'Visibility'),
    'Extrapolation1': (
        'Row Labels', 'Average of Duration', 'Average of Views', 'Average of Engagement',
        'Extrapolate Size', 'Average of Visibility'
    )
}

if not uploaded_files:
    st.info('Upload an Excel file to begin.')

# Process workbooks independently so a bad upload does not stop later files.
for i, uploaded_file in enumerate(uploaded_files):
    if uploaded_file is None:
        st.error('A selected upload could not be read. Please select the file again.')
        continue

    # Check workbook structure before parsing any sheet data.
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

    # Validate direct column dependencies and required data ID variants before conversion.
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

    missing_ids = [
        sheet for sheet in ('Exposure', 'Extrapolation1')
        if not any(column in data[sheet].columns for column in ID_COLUMNS)
    ]
    if missing_ids:
        st.error(
            f"'{uploaded_file.name}' needs a recognized Data ID column in: "
            + ', '.join(missing_ids)
            + '.'
        )
        continue

    st.success(
        f"Loaded {len(data['Mentions'])} mentions, {len(data['Exposure'])} exposure rows, "
        f"and {len(data['Extrapolation1'])} extrapolated rows."
    )
    if st.button('Rerun', key=f"rerun_{i}"):
        st.rerun()

    # Surface expected data problems to the user and retain tracebacks for unexpected failures.
    try:
        final_mentions, final_exposure, new_smve, new_smv, output, warnings = build_extrapolated_upload(
            data['Mentions'], data['Exposure'], data['Extrapolation1']
        )
    except ValueError as error:
        st.error(f"Could not process '{uploaded_file.name}': {error}.")
        continue
    except Exception:
        logger.exception('Could not process uploaded workbook %s', uploaded_file.name)
        st.error(
            f"Could not process '{uploaded_file.name}'. Check the workbook contents and try again."
        )
        continue

    for warning in warnings:
        st.warning(f"{uploaded_file.name}: {warning}")

    # Display processed data and provide the completed workbook.
    with st.expander('Final Results Check before Download'):
        st.write("OP Data")
        st.dataframe(final_mentions)
        st.write("Exposure Data")
        st.dataframe(final_exposure)

    st.download_button(
        label=f"Download Social Media Video File {i + 1}",
        data=output,
        file_name=f"SMV Upload {i + 1}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_{i}"
    )

st.markdown("## Important info below 🚨🚨🚨")
st.write(
    "After the file has been downloaded do these 3 things.\n"
    "1. In downloaded file change date format to short date.\n"
    "2. Change Duration format to time.\n"
    "3. Change Visibility to percentage and you're all good to upload!"
)