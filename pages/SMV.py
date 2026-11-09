import logging
from io import BytesIO

import pandas as pd
import streamlit as st

logger = logging.getLogger(__name__)


def build_video_upload(mentions, exposure):
    """Convert validated source tables into the video upload workbook."""
    warnings = []
    mentions = mentions.copy()
    exposure = exposure.copy()

    # Normalize source names and fill missing author names before filtering rows.
    clean_platform = {
        'instagram.com': 'Instagram',
        'facebook.com': 'Facebook',
        'FaceBook': 'Facebook',
        'x.com': 'X',
        'tiktok.com': 'Tiktok',
        'threads.com': 'Threads',
        'youtube.com': 'Youtube'
    }
    mentions['Source'] = mentions['Source'].astype('string').str.strip().replace(clean_platform)
    if 'Author' not in mentions.columns:
        mentions['Author'] = pd.NA
    mentions['Author'] = mentions['Author'].fillna(mentions['Nickname'])
    monitored = mentions['Monitored'].astype('string').str.strip().str.casefold().eq('yes')
    smv = mentions.loc[monitored].copy()
    if smv.empty:
        raise ValueError("no rows are marked 'Yes' in the Monitored column")
    if (smv['Source'].isna() | smv['Source'].eq('')).any():
        raise ValueError('one or more monitored rows are missing a platform/source')

    # Support the known ID column variants while keeping the output column stable.
    mention_id_col = next(
        (col for col in ('Final Data ID', 'New Data ID', 'Data ID') if col in smv.columns),
        None
    )
    exposure_id_col = next(
        (col for col in ('Final Data ID', 'New Data ID', 'Data ID') if col in exposure.columns),
        None
    )
    if mention_id_col is None:
        smv['Data ID'] = ''
        warnings.append('No recognized ID column was found in Mentions; output IDs are blank.')
    else:
        smv['Data ID'] = smv[mention_id_col]
    if exposure_id_col is None:
        raise ValueError('the Total Exposure worksheet needs a Data ID column')

    # Coerce numeric inputs explicitly and reject non-empty values that cannot be parsed.
    for column in ('Views', 'Engagement'):
        original = smv[column]
        smv[column] = pd.to_numeric(original, errors='coerce')
        invalid_count = (original.notna() & smv[column].isna()).sum()
        if invalid_count:
            raise ValueError(f"{invalid_count} value(s) in Mentions.{column} are not numeric")

    # Infer missing engagement rates from the platform average; zero views are treated as missing.
    smv['Engagement Rate'] = smv['Engagement'].div(smv['Views'].where(smv['Views'].ne(0)))
    platform_avg = smv.groupby('Source', dropna=True)['Engagement Rate'].mean().to_dict()
    platform_avg['Threads'] = 0.073403
    smv['Engagement Rate'] = smv['Engagement Rate'].fillna(smv['Source'].map(platform_avg))
    estimated_views = smv['Engagement'].div(smv['Engagement Rate'].where(smv['Engagement Rate'].ne(0)))
    smv['Views'] = smv['Views'].fillna(estimated_views.round(0))

    # Require known pricing and parse dates before calculating the output cost.
    cpt_data = {
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
    smv['CPT'] = smv['Source'].map(cpt_data)
    unknown_platforms = smv.loc[smv['CPT'].isna(), 'Source'].drop_duplicates().tolist()
    if unknown_platforms:
        raise ValueError(f"unsupported platform value(s): {', '.join(map(str, unknown_platforms))}")

    original_dates = smv['Date']
    smv['Date'] = pd.to_datetime(original_dates, errors='coerce')
    invalid_dates = (original_dates.notna() & smv['Date'].isna()).sum()
    if invalid_dates:
        raise ValueError(f"{invalid_dates} date value(s) in Mentions could not be parsed")

    unresolved_metrics = (smv['Views'].isna() | smv['Engagement Rate'].isna()).sum()
    if unresolved_metrics:
        warnings.append(
            f"{unresolved_metrics} monitored row(s) have missing Views or Engagement Rate; "
            "their spot cost may be blank."
        )
    smv['Spot Cost'] = ((smv['Views'] / 1000) * smv['CPT']) * (1 + smv['Engagement Rate'])
    smv['Country'] = smv['Country'].fillna('Global')
    smv['Engagement'] = smv['Engagement'].round(0)
    smv['Views'] = smv['Views'].round(0)

    # Convert the cleaned mentions and exposure data to the target column layout.
    brand_col = next(
        (col for col in ('Brand', 'Brands', 'Sponsor', 'Sponsors') if col in exposure.columns),
        None
    )
    if brand_col is None:
        warnings.append('No recognized brand/sponsor column was found; output sponsors are blank.')

    original_visibility = exposure['Visibility']
    exposure['Visibility'] = pd.to_numeric(original_visibility, errors='coerce')
    invalid_visibility = (original_visibility.notna() & exposure['Visibility'].isna()).sum()
    if invalid_visibility:
        raise ValueError(f"{invalid_visibility} value(s) in Total Exposure.Visibility are not numeric")

    new_smv = pd.DataFrame({
        'Event ID': '',
        'Data ID': smv['Data ID'],
        'Country': smv['Country'],
        'Platform': smv['Source'],
        'Account': smv['Author'],
        'Video Title': smv['Title'],
        'Date': smv['Date'],
        'Duration': smv['Duration'],
        'Views': smv['Views'],
        'Engagement': smv['Engagement'],
        '30 Second Spot Cost': smv['Spot Cost'],
        'Url': smv['URL'],
        'Keywords': smv['Data ID'],
        'Multiple': 1
    })
    new_smve = pd.DataFrame({
        'Event ID': '',
        'Data ID': exposure[exposure_id_col],
        'Sponsor': exposure[brand_col] if brand_col else '',
        'Asset': 'All Assets',
        'Team': '',
        'Participant': '',
        'Host': '',
        '% Visibility': exposure['Visibility'],
        'SIQ+': '',
        'Exposure Type': 1,
        'No of Seconds': 0
    })

    # Build the downloadable Excel file in memory.
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        new_smv.to_excel(writer, sheet_name='Social Media Videos', index=False)
        new_smve.to_excel(writer, sheet_name='Social Media Video Exposure', index=False)
    output.seek(0)
    return new_smv, new_smve, output, warnings


st.markdown("# Social Media Video 🎉")
st.sidebar.markdown("# Social Media 🎉")
st.write("This is designed to cut some time for dashboard uploads " \
"to get the inital file into the template for uploading the file. ")

uploaded_files = st.file_uploader('Upload File Below:', type='.xlsx', accept_multiple_files=True)
required_sheets = ('Mentions', 'Total Exposure')
required_columns = {
    'Mentions': (
        'Source', 'Nickname', 'Monitored', 'Country', 'Title', 'Date', 'Duration',
        'Views', 'Engagement', 'URL'
    ),
    'Total Exposure': ('Visibility',)
}

if not uploaded_files:
    st.info('Upload an Excel file to begin.')

# Handle each uploaded workbook independently so a bad file does not stop the batch.
for i, uploaded_file in enumerate(uploaded_files):
    if uploaded_file is None:
        st.error('A selected upload could not be read. Please select the file again.')
        continue

    # Inspect the workbook before parsing, keeping missing-sheet errors distinct.
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

    # Validate all directly used headers before running the calculations.
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

    exposure_id_col = next(
        (col for col in ('Final Data ID', 'New Data ID', 'Data ID') if col in data['Total Exposure'].columns),
        None
    )
    if exposure_id_col is None:
        st.error(f"'{uploaded_file.name}' needs a Data ID column in Total Exposure.")
        continue

    st.success(
        f"Loaded {len(data['Mentions'])} mentions and "
        f"{len(data['Total Exposure'])} exposure rows."
    )
    if st.button('Rerun', key=f"rerun_{i}"):
        st.rerun()

    # Keep detailed diagnostics in logs and show validation or safe fallback messages in the app.
    try:
        new_smv, new_smve, output, warnings = build_video_upload(
            data['Mentions'], data['Total Exposure']
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

    # Display the converted data and expose the generated workbook for download.

    with st.expander('Final Results Check before Download'):
        st.write("SMV Data")
        st.dataframe(new_smv)
        st.write("Exposure Data")
        st.dataframe(new_smve.style.format({'% Visibility': '{:.4f}'}))

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
            "1. In downloaded file change date format to short date."
        )