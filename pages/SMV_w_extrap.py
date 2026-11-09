import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

st.markdown("# Social Media Video with Extrapolation 👊")
st.sidebar.markdown("# Social Media Extrapolation 👊")


st.write("This is designed to cut some time for dashboard uploads " \
"to get the inital file into the template for uploading the file. ")
st.write("For extrapolated rows create a sheet called 'Extrapolation1' and put the rows in that sheet in Cell A2 in the new sheet then upload")


uploaded_files = st.file_uploader('Upload File Below:',type='.xlsx', accept_multiple_files=True)

for i, uploaded_file in enumerate(uploaded_files):
    if uploaded_file is None:
            st.info('Upload an Excel File to begin.')
            st.stop()

    with st.spinner('Putting in template', show_time=True):
            required_sheets = {
                    'Mentions': dict(header=0),
                    'Exposure':  dict(header = 0 ),#usecols=['Data ID', 'Duration', 'Exposure', 'Brands', 'Visibility']),
                    'Extrapolation1': dict(header = 0)
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
            
            smv_mentions = data['Mentions']
            smv_exposure = data['Exposure']
            smv_extrapolation = data['Extrapolation1']
            
            
            st.success(f"Loaded {len(smv_mentions)} mentions, {len(smv_exposure)} exposure and {len(smv_extrapolation)} extrapolated rows.")
            if st.button('Rerun',  key=f"rerun_{i}"):
                    st.rerun()

    clean_platform = {
        'instagram.com': 'Instagram',
        'facebook.com': 'Facebook',
        'x.com':  'X',
        'tiktok.com':   'Tiktok',
        'threads.com': 'Threads',
        'youtube.com' : 'Youtube'}

    smv_mentions['Source']    = smv_mentions['Source'].replace(clean_platform)
    smv_mentions['Author'] = smv_mentions.apply(lambda row: row['Nickname'] if pd.isnull(row['Author'])  else row['Author'], axis=1)
    smv_monitored = smv_mentions.loc[smv_mentions['Monitored']=='Yes']
    cols = ['Data ID', 'Country', 'Source', 'Author', 'Title', 'Date', 'Duration', 'Views', 'Engagement', 'URL']
    not_cols = [c for c in smv_monitored.columns if c not in cols]
    smv = smv_monitored.drop(columns=not_cols)

    smv['Engagement Rate'] = smv['Engagement']/ smv['Views']

    platform_avg = pd.pivot_table(
        smv, index='Source', values='Engagement Rate', aggfunc='mean'
    )
    platform_avg = platform_avg.reset_index()

    d = {'Source' : ['Threads'], 'Engagement Rate': [0.073403]}
    threads = pd.DataFrame(data=d)

    plat_avg = pd.concat([platform_avg,threads])
    plat_avg = plat_avg.reset_index()
    plat_avg = plat_avg.drop(columns=['index'])
    plat_dict = dict(zip(plat_avg.Source, plat_avg['Engagement Rate']))

    smv['Engagement Rate'] = smv['Engagement Rate'].fillna(smv['Source'].map(plat_dict))
    smv['Views'] = smv['Views'].fillna(round(smv['Engagement']/smv['Engagement Rate'],0))
    cpt_data = {
        'Facebook':7.80,
        'Instagram':5.88,
        'Youtube':8.07,
        'YouTube':8.07,
        'X':9.07,
        'Tiktok':8.15,
        'TikTok':8.15,
        'Threads':4.00,
        'Pinterest':3.67,
        'Bluesky':4.00
    }
    smv['CPT'] = smv['Source'].apply(lambda x: cpt_data[x])
    smv['Spot Cost'] = round(((smv['Views']/1000) * smv['CPT']) * (1+smv['Engagement Rate']),0)
    smv['Country'] = smv['Country'].fillna('Global')
    smv['Date'] = pd.to_datetime(smv['Date'], format='mixed', dayfirst=True)

    date_piv = pd.pivot_table(
        smv, index='Source', values='Date', aggfunc='mean'
    )
    date_piv = date_piv.reset_index()
    date_piv['new date'] = date_piv['Date'].apply(lambda x: str(x).split(' ')[0])
    date_piv = date_piv.drop(columns=['Date'])
    date_dict = dict(zip(date_piv.Source, date_piv['new date']))

    smv['Multiple'] = 1

    smv_extrapolation['Country'] = 'Global'
    smv_extrapolation['Title']= ''
    smv_extrapolation['Date'] = ''
    smv_extrapolation['URL'] = 'Unspecified'
    smv_extrapolation['Author'] = 'Unspecified'
    smv_extrapolation = smv_extrapolation.rename({'Average of Duration': 'Duration', 'Average of Views': 'Views', 'Average of Engagement': 'Engagement', 'Row Labels': 'Source'},axis=1)

    smv_extrapolation['Engagement Rate'] = smv_extrapolation['Engagement']/ smv_extrapolation['Views']
    smv_extrapolation['CPT'] = smv_extrapolation['Source'].apply(lambda x: cpt_data[x])
    smv_extrapolation['Spot Cost'] = round(((smv_extrapolation['Views']/1000) * smv_extrapolation['CPT']) * (1+smv_extrapolation['Engagement Rate']),0)
    smv_extrapolation['Date'] = smv_extrapolation['Source'].apply(lambda x: pd.to_datetime(date_dict['Instagram'], format='mixed', dayfirst=True) if x == 'Threads' else pd.to_datetime(date_dict[x], format = 'mixed', dayfirst=True))
    smv_extrapolation['Extrapolate Size'] = smv_extrapolation['Extrapolate Size'].apply(lambda x: 1 if round(x,0)==0 else round(x,0))
    smv_extrapolation2 = smv_extrapolation.iloc[:,[0,12,11,16,17,1,10,3,2,4,13,14,15,9]]
    smv_extrapolation2 = smv_extrapolation2.rename({'Extrapolate Size' : 'Multiple'}, axis=1)

    cols = ['Data ID', 'Sponsors', 'Average of Visibility']
    smv_extrap_exposure = smv_extrapolation.drop(columns=[c for c in smv_extrapolation.columns if c not in cols])
    smv_exposure = smv_exposure.drop(columns=['Duration','Exposure'])
    smv_extrap_exposure = smv_extrap_exposure.rename({'Average of Visibility': 'Visibility', 'Sponsors': 'Brands'},axis=1)

    final_smv_exposure = pd.concat([smv_exposure, smv_extrap_exposure])
    final_smv_mentions = pd.concat([smv, smv_extrapolation2])
    final_smv_mentions['Engagement'] = round(final_smv_mentions['Engagement'],0)
    final_smv_mentions['Views'] = round(final_smv_mentions['Views'],0)

    brand_col = next(
        (col for col in ['Brand', 'Brands', 'Sponsor', 'Sponsors'] if col in final_smv_exposure.columns),
        None
    )

    data_id_col = next(
            (col for col in ['Final Data ID', 'New Data ID', 'Data ID'] if col in final_smv_mentions.columns),
            None
        )

    new_smv = pd.DataFrame({
        'Event ID':'',
        'Data ID': final_smv_mentions[data_id_col] if data_id_col else '',
        'Country': final_smv_mentions['Country'],
        'Platform': final_smv_mentions['Source'],
        'Account': final_smv_mentions['Author'],
        'Video Title': final_smv_mentions['Title'],
        'Date':final_smv_mentions['Date'],
        'Duration': final_smv_mentions['Duration'],
        'Views': final_smv_mentions['Views'],
        'Engagement': final_smv_mentions['Engagement'],
        '30 Second Spot Cost': final_smv_mentions['Spot Cost'],
        'Url': final_smv_mentions['URL'],
        'Keywords': final_smv_mentions['Data ID'],
        'Multiple': final_smv_mentions['Multiple']
    })

    new_smve = pd.DataFrame({
        'Event ID': '',
        'Data ID': final_smv_exposure[data_id_col] if data_id_col else '',
        'Sponsor': final_smv_exposure[brand_col]if brand_col else '',
        'Asset': 'All Assets',
        'Team': '',
        'Participant': '',
        'Host': '',
        '% Visibility': round(final_smv_exposure['Visibility'],4),
        'SIQ+': '',
        'Exposure Type': 1,
        'No of Seconds':0
    })

    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        new_smv.to_excel(writer, sheet_name='Social Media Videos', index=False)
        new_smve.to_excel(writer, sheet_name='Social Media Video Exposure', index=False, float_format="%.2f")

    output.seek(0)


    st.download_button(
            label = f"Download Social Media Video File {i+1}",
            data=output,
            file_name=f"SMV Upload {i+1}.xlsx",
            mime=f"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key= f"download_{i}")
st.markdown("## Important info below 🚨🚨🚨")

st.write( "After the file has been downloaded do these 3 things.\n1. In downloaded file change date format to short date.\n2. Change Duration format to time.\n3. Change Visbility to percentage and you're all good to upload!")