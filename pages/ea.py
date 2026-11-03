import streamlit as st
import pandas as pd
import time
#from streamlit_dynamic_filters import DynamicFilters

# --- Constants ----------------------------------------------------------
# Named so it's obvious these are deliberate scalings, not typos.
# If the business rules ever change, there's one place to edit.
MULTIPLY_BY_10 = 10
MULTIPLY_BY_100 = 100

# --- Dictionairy and Lists ----------------------------------------------------------
pos_dict = {
    'A':1.5,
    'AL':1.4,
    'AR':1.3,
    'B':1.2,
    'BR':1.1,
    'C':1,
    'D':0.9,
    'DR':0.8,
    'E':0.7
}

score_dict = {
    0: 1,
    41472: 1,
    82944: 1,
    124416: 1,
    165888: 1,
    207360: 1,
    248832: 1.5,
    290304: 1.5,
    331776: 1.5,
    373248: 1.5,
    414720: 1.5,
    456192: 1.5,
    497664: 1.5,
    539136: 2,
    580608: 2,
    622080: 2,
    663552: 2,
    705024: 2,
    746496: 2,
    787968: 2,
    829440: 2.1,
    870912: 2.2,
    912384: 2.3,
    953856: 2.4,
    995328: 2.5,
    1036800: 2.6,
    1078272: 2.7,
    1119744: 2.8,
    1161216: 2.9,
    1202688: 3,
    1244160: 3.1,
    1285632: 3.2,
    1327104: 3.3,
    1368576: 3.4,
    1410048: 3.5,
    1451520: 3.6,
    1492992: 3.7,
    1534464: 3.8,
    1575936: 3.9,
    1617408: 4,
    1658880: 4.1,
    1700352: 4.2,
    1741824: 4.3,
    1783296: 4.4,
    1824768: 4.5,
    1866240: 4.6,
    1907712: 4.7,
    1949184: 4.8,
    1990656: 4.9,
    2032128: 5,
    2073600: 5
}
count_dict = {
    1: {'Clutter Score': 0.5, 'Asset Score': 0.5},
    2: {'Clutter Score': 0.4, 'Asset Score': 1.0},
    3: {'Clutter Score': 0.3, 'Asset Score': 1.5},
    4: {'Clutter Score': 0.2, 'Asset Score': 2.0},
    5: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    6: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    7: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    8: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    9: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    10: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    11: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    12: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    13: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    14: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    15: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    16: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    17: {'Clutter Score': 0.1, 'Asset Score': 2.5},
    18: {'Clutter Score': 0.1, 'Asset Score': 2.5}
}

bins = [
    0, 41472, 82944, 124416, 165888, 207360, 248832,
    290304, 331776, 373248, 414720, 456192, 497664,
    539136, 580608, 622080, 663552, 705024, 746496,
    787968, 829440, 870912, 912384, 953856, 995328,
    1036800, 1078272, 1119744, 1161216, 1202688,
    1244160, 1285632, 1327104, 1368576, 1410048,
    1451520, 1492992, 1534464, 1575936, 1617408,
    1658880, 1700352, 1741824, 1783296, 1824768,
    1866240, 1907712, 1949184, 1990656, 2032128,
    2073600
]

scores = [
    1, 1, 1, 1, 1, 1,
    1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5,
    2, 2, 2, 2, 2, 2, 2,
    2.1, 2.2, 2.3, 2.4, 2.5,
    2.6, 2.7, 2.8, 2.9, 3.0,
    3.1, 3.2, 3.3, 3.4, 3.5,
    3.6, 3.7, 3.8, 3.9, 4.0,
    4.1, 4.2, 4.3, 4.4, 4.5,
    4.6, 4.7, 4.8, 4.9, 5.0
]
# --- Page header --------------------------------------------------------
# st.markdown + unsafe_allow_html works on every Streamlit version,
# whereas st.title(text_alignment=...) only works on very recent ones.
st.markdown(
    "<h1 style='text-align:center'>Automated exposure calcs</h1>",
    unsafe_allow_html=True,
)


# --- File upload --------------------------------------------------------
uploaded_file = st.file_uploader('Upload Raw exposure file below:', '.xlsx')

# Show nothing until a file is actually uploaded. On first page load
# uploaded_file is None, which is not an error — the user just hasn't
# done anything yet.
if uploaded_file is None:
    st.info('Upload an Excel file to begin.')
    st.stop()

with st.spinner('Performing calcs...', show_time=True):
    # Describe every sheet we need and the read kwargs for each.
    # Looping over this dict avoids four near-identical try/except blocks.
    required_sheets = {
        'Projects':        dict(header=0),
        'Summary':         dict(usecols=['Event', 'Total Frames'], header=1),
        'Brand Weight':    dict(header=0),
        'Location Weight': dict(header=0),
    }

    missing = []
    data = {}

    for sheet, kwargs in required_sheets.items():
        try:
            data[sheet] = pd.read_excel(uploaded_file, sheet, **kwargs)
        except ValueError:
            # pandas/openpyxl raise ValueError when a sheet name is absent.
            missing.append(sheet)
        except Exception as e:
            # Anything else (corrupt file, wrong format) — report and stop.
            st.error(f"Could not read sheet '{sheet}': {e}")
            st.stop()

    # Report every missing sheet at once rather than one per rerun.
    if missing:
        st.error(
            "The uploaded file is missing the following required sheet(s): "
            + ", ".join(f"**{m}**" for m in missing)
            + ". Please check the file and re-upload."
        )
        st.stop()

    # Unpack for readability below.
    projects        = data['Projects']
    total_frames    = data['Summary']
    brand_weight    = data['Brand Weight']
    location_weight = data['Location Weight']

    st.success(f"Loaded {len(projects)} projects and {len(total_frames)} summary rows.")


# --- Cleanup ------------------------------------------------------------

# Spelling/case fixes applied to raw Project data.
# Kept as explicit dicts so non-devs can see exactly what's normalised.
clean_brand = {'Stark': 'STARK',
               'Castore England': 'Castore',
               'Castore New Zealand': 'Castore'}
clean_location = {
    'player Clothing': 'Player Clothing',
    'Player clothing': 'Player Clothing',
    'Screen graphic':  'Screen Graphic',
    'Clock signage':   'Clock Signage',
}


def clean_columns(df):
    """Strip leading/trailing whitespace from every column name.

    Excel files routinely end up with 'Brand ' or 'Brand\\xa0' as headers,
    which silently breaks dict lookups. Normalising once at load time
    prevents a whole class of confusing KeyErrors later.
    """
    df.columns = df.columns.str.strip()
    return df


# Apply cleanup to all four frames, not just brand_weight, so any
# whitespace quirks in other sheets are handled consistently.
for df_name in ('projects', 'total_frames', 'brand_weight', 'location_weight'):
    locals()[df_name] = clean_columns(locals()[df_name])

# Normalise label values (not just headers).
projects['Brand']    = projects['Brand'].replace(clean_brand)
projects['Location'] = projects['Location'].replace(clean_location)

# Drop rows where Summary has no Event or Total Frames.
total_frames = total_frames.dropna()


# --- SOV calculation ----------------------------------------------------

cols = ['Project Name', 'Image', 'Brand', 'Location']

# Keep only the columns we need for the pivot.
project_piv = projects.drop(columns=[x for x in projects.columns if x not in cols])

# 'CC' = a unique combination of Project + Image + Brand.
# Used to work out how many distinct exposures share the same creative,
# so each can carry an equal share of the SOV.
project_piv['CC'] = (
    project_piv['Project Name'] + project_piv['Image'] + project_piv['Brand']
)


def count_cc(df):
    """Count how many rows share each CC value."""
    cc_list = df['CC'].tolist()
    cc_dict = {}
    for cc in cc_list:
        cc_dict[cc] = cc_dict.get(cc, 0) + 1
    return cc_dict


cc_dict = count_cc(project_piv)

# SOV = 1 / (number of rows sharing this CC). Rows in the same CC group
# each get an equal slice.
# cc_dict values are always >= 1 (a CC exists only if it appeared), so
# no ZeroDivisionError guard is needed here.
project_piv['SOV'] = project_piv['CC'].apply(lambda x: 1 / cc_dict[x])

# Collapse to one row per Project + Brand + Location, summing SOV.
project_piv1 = project_piv.pivot_table(
    index=['Project Name', 'Brand', 'Location'], aggfunc='sum'
)
project_piv1 = project_piv1.drop(columns=['CC', 'Image']).reset_index()


# --- Visibility calculation --------------------------------------------

def vis_calcs(piv, frame, brand, loc):
    """Attach Visibility % and build brand/location lookup dicts.

    Visibility % = SOV for this row, as a fraction of the total frames
    the project ran for, expressed as a percentage.
    """
    # Assumes each Event appears exactly once in Summary (upstream guarantee).
    frame_dict = dict(zip(frame['Event'], frame['Total Frames']))
    brand_dict = dict(zip(brand['Brand'], brand['Average of Brand Weight']))
    loc_dict   = dict(zip(loc['Location Weight'], loc['Average of Location Weight']))

    piv['Visibility %'] = piv.apply(
        lambda x: (x['SOV'] / frame_dict[x['Project Name']]) * MULTIPLY_BY_100,
        axis=1,
    )
    return piv, brand_dict, loc_dict


project_piv2, brand_weight_dict, location_weight_dict = vis_calcs(
    project_piv1, total_frames, brand_weight, location_weight
)

# Rebuild CC (Project + Brand, no Image) on the aggregated frame.
# This is the grouping used to work out SOV % later.
project_piv2['CC'] = project_piv2['Project Name'] + project_piv2['Brand']


# --- Intermediate debug tables -----------------------------------------
# Hidden behind an expander so non-technical users don't see them unless
# something looks wrong. Useful when a calc produces an unexpected value.
with st.expander("Intermediate results (for debugging)"):
    st.write("Initial upload")
    st.dataframe(projects)
    st.write("Pivot after dropping unused columns")
    st.dataframe(project_piv)
    st.write("Pivot after aggregation, before visibility calcs")
    st.dataframe(project_piv1)


# --- Mismatch validation -----------------------------------------------
# Two directions to check for each lookup:
#   missing: values in Projects that aren't in the weight sheet -> KeyError
#   unused:  values in the weight sheet that no project uses   -> stale data
# We run both before any lookup happens, so the user gets a clear list
# of what to fix instead of a Python traceback.

def report_mismatches(label, project_values, weight_values):
    missing = sorted(set(project_values) - set(weight_values))
    unused  = sorted(set(weight_values) - set(project_values))

    if missing:
        st.error(
            f"These {label}s appear in the Projects sheet but are missing "
            f"from the weight sheet: {missing}. "
            f"Add them to the weight sheet or update cleanup rules."
        )
    if unused:
        st.warning(
            f"These {label}s are in the weight sheet but not used by any "
            f"project: {unused}. Check for typos or stale entries."
        )
    return bool(missing)


bad = report_mismatches('Brand', project_piv2['Brand'], brand_weight['Brand'])
bad |= report_mismatches(
    'Location', project_piv2['Location'], location_weight['Location Weight']
)

# Also verify every Project Name has a matching Event in Summary.
# Without this, vis_calcs raises a KeyError for the first missing one
# rather than telling the user the whole list.
missing_events = sorted(
    set(project_piv2['Project Name']) - set(total_frames['Event'])
)
if missing_events:
    st.error(
        "These Project Names have no matching Event in the Summary sheet: "
        f"{missing_events}"
    )
    bad = True

if bad:
    st.stop()


# --- SOV % and weighted columns ----------------------------------------

# Sum Visibility % per CC (Project + Brand) so we can express each row's
# share of the total visibility for that CC.
cc_vis_dict = {}
for _, row in project_piv2.iterrows():
    cc_vis_dict[row['CC']] = cc_vis_dict.get(row['CC'], 0) + row['Visibility %']


def brand_loc_calcs(piv, brand_dict, loc_dict, cc_vis_dict):
    """Attach SOV %, Brand Weight and Location Weight columns."""
    piv['SOV %'] = piv.apply(
        lambda x: x['Visibility %'] / cc_vis_dict[x['CC']] * MULTIPLY_BY_100,
        axis=1,
    )
    piv['Brand Weight'] = piv.apply(
        lambda x: brand_dict[x['Brand']] * MULTIPLY_BY_10, axis=1
    )
    piv['Location Weight'] = piv.apply(
        lambda x: loc_dict[x['Location']] * MULTIPLY_BY_10, axis=1
    )
    return piv


final_piv = brand_loc_calcs(
    project_piv2, brand_weight_dict, location_weight_dict, cc_vis_dict
)

# --- SIQ Calcs ----------------------------------------

# Pivot and addition of Brand and Asset Score for each row 

siq_scoring = (
    projects
    .groupby(['Project', 'Project Name', 'Image', 'Brand'])
    .size()
    .reset_index(name='Count')
)
siq_scoring['ClutterCC']= siq_scoring['Project']+siq_scoring['Project Name']+siq_scoring['Image']
siq_scoring['Brand-Asset CC']= siq_scoring['Project']+siq_scoring['Project Name']+siq_scoring['Image']+siq_scoring['Brand']
clutter_dict = dict(zip(siq_scoring['ClutterCC'].value_counts().keys(),siq_scoring['ClutterCC'].value_counts().values))
brand_dict = dict(zip(siq_scoring['Brand-Asset CC'].value_counts().keys(),siq_scoring['Brand-Asset CC'].value_counts().values))
siq_scoring['Clutter Count'] = siq_scoring['ClutterCC'].apply(lambda x: clutter_dict[x])
siq_scoring['Brand Assets'] = siq_scoring['Count']
siq_scoring['Clutter Score'] = siq_scoring['Clutter Count'].apply(lambda x: count_dict[x]['Clutter Score'])
siq_scoring['Asset Score'] = siq_scoring['Brand Assets'].apply(lambda x: count_dict[x]['Asset Score'])

# Sorting by Size adding Size Score and Calculation of SIQ for non null rows

projects_sorted=projects.sort_values(by=['Size C'], ascending=False).reset_index()
projects_sorted = projects_sorted.drop(columns=['index'])
projects_sorted['Position Score'] = projects_sorted['Position'].apply(lambda x: x if pd.isnull(x) else pos_dict[x])

projects_sorted['Size Score'] = pd.cut(
    projects_sorted['Size C'],
    bins=bins,
    labels=scores,
    include_lowest=True,
    ordered=False
).astype(float)

clutter_score_dict = dict(zip(siq_scoring['ClutterCC'], siq_scoring['Clutter Score']))
brand_score_dict = dict(zip(siq_scoring['Brand-Asset CC'], siq_scoring['Asset Score']))

projects_sorted['ClutterCC']= projects_sorted['Project']+projects_sorted['Project Name']+projects_sorted['Image']
projects_sorted['BrandCC']= projects_sorted['Project']+projects_sorted['Project Name']+projects_sorted['Image']+projects_sorted['Brand']
projects_sorted['Clutter Score'] = projects_sorted['ClutterCC'].apply(lambda x: clutter_score_dict[x])
projects_sorted['Asset Score'] = projects_sorted['BrandCC'].apply(lambda x: brand_score_dict[x])
projects_sorted = projects_sorted.assign(SIQ = lambda row: row['Position Score']+ row['Size Score']+row['Clutter Score']+ row['Asset Score'] *0.7)


#

na = projects_sorted.loc[projects_sorted['SIQ'].isna()]
na = na.drop(columns=['User Name', 'Instances', 'Size', 'ClutterCC', 'BrandCC','Clutter Score', 'Asset Score'])
not_na = projects_sorted.loc[projects_sorted['SIQ'].notnull()]
not_na = not_na.drop(columns=['User Name', 'Instances', 'Size', 'ClutterCC', 'BrandCC'])

# SIQ's for Brand-loc, Brand , Location

brand_loc = pd.pivot_table(
    not_na, index=['Brand', 'Location'], values='SIQ', aggfunc='mean'
)
brand_loc = brand_loc.reset_index()
brand_loc['CC'] = brand_loc['Brand']+brand_loc['Location']
brand_loc['SIQ'] = round(brand_loc['SIQ'],2)

brand = pd.pivot_table(
    not_na, index=['Brand'], values='SIQ', aggfunc='mean'
)
brand = brand.reset_index()
brand['SIQ'] = round(brand['SIQ'],2)

loc = pd.pivot_table(
    not_na, index=['Location'], values='SIQ', aggfunc='mean'
)
loc = loc.reset_index()
loc['SIQ'] = round(loc['SIQ'],2)
brand['Adjusted_SIQ'] = brand['SIQ'] *0.6
loc['Adjusted_SIQ'] = loc['SIQ'] *0.4

na['brandlocCC'] = na['Brand']+na['Location']

brandloc_dict = dict(zip(brand_loc['CC'], brand_loc['SIQ']))
brand_dict = dict(zip(brand['Brand'], brand['Adjusted_SIQ']))
loc_dict = dict(zip(loc['Location'], loc['Adjusted_SIQ']))

na['SIQ'] = na.apply(lambda x: brandloc_dict[x['brandlocCC']] if x['brandlocCC'] in brandloc_dict.keys() else brand_dict[x['Brand']] + loc_dict[x['Location']], axis=1)
na = na.drop(columns=['brandlocCC'])
final_table = pd.concat([not_na, na])
final = pd.pivot_table(
    final_table, index=['Project Name', 'Brand', 'Location'], values='SIQ', aggfunc='mean'
).reset_index()
final['SIQ'] = round(final['SIQ'],2)

final['CC'] = final['Project Name']+final['Brand']+final['Location']
final_piv['CC1'] = final_piv['Project Name']+final_piv['Brand']+final_piv['Location']

final_siq_dict = dict(zip(final['CC'], final['SIQ']))
final_piv['SIQ'] = final_piv['CC1'].apply(lambda x: round(final_siq_dict[x],2))
final_piv = final_piv.rename(columns={'Project Name':'Data ID','Brand':'Sponsor','Location':'Asset'})

final_piv = final_piv.drop(columns=['SOV', 'CC', 'Brand Weight', 'Location Weight', 'CC1', 'SOV %'])
final_piv['Event ID'] = ''
final_piv['Participant'] = ''
final_piv['Host'] = ''
final_piv['Exposure Type'] = 1
final_piv['No of Seconds'] = 0
final_piv['Live Exposure'] = ''
final_piv= final_piv.iloc[:, [5,0,1,2,3,4,6,7,8,9,10]]

# --- Filtering and display ---------------------------------------------

#dynamic_filters = DynamicFilters(final_piv, filters=['Sponsor', 'Asset'])
#dynamic_filters.display_filters(location='columns',num_columns=2)
#filtered_df = dynamic_filters.filter_df()

st.subheader("Final Results")
st.dataframe(
    filtered_df.style.format({
        'Visibility %':    '{:.2f}',
        'SOV %':           '{:.2f}',
        'Brand Weight':    '{:.2f}',
        'Location Weight': '{:.4f}',
        'SOV':             '{:.2f}',
        'SIQ':             '{:.2f}',
    })
)


# --- Download ----------------------------------------------------------
# Cache the CSV conversion so reruns don't re-encode the same frame.
# Exporting filtered_df (not final_piv) so the download matches what's
# on screen.
@st.cache_data
def convert_for_download(df):
    return df.to_csv().encode("utf-8")


csv = convert_for_download(final_piv)

st.download_button(
    label="Download CSV",
    data=csv,
    file_name="Broadcast Exposure.csv",
    mime="text/csv",
)
