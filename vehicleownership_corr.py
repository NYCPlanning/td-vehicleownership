# -*- coding: utf-8 -*-
"""
Vehicle Ownership (Correlation)
"""
import pandas as pd
import requests
import geopandas as gpd

import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = 'browser'

path = 'C:/Users/M_Free/Desktop/td-vehicleownership/'

# DCP proxy
usernm = pd.read_csv('C:/Users/M_Free/Desktop/key.csv',dtype=str).loc[0,'username']
passwd = pd.read_csv('C:/Users/M_Free/Desktop/key.csv',dtype=str).loc[0,'password']
p={'http':'http://'+str(usernm)+':'+str(passwd)+'@dcpproxy1.dcp.nycnet:8080',
    'https':'http://'+str(usernm)+':'+str(passwd)+'@dcpproxy1.dcp.nycnet:8080'}

# Census API
key = pd.read_csv('C:/Users/M_Free/Desktop/key_census.csv',dtype=str).loc[0, 'key']
state = '36'
county = '005,047,061,081,085'

# CTs and CDTAs
ct_df = pd.read_csv('C:/Users/M_Free/OneDrive - NYC O365 HOSTED/Projects/Geographies/ct10toct20tocdta.csv', dtype = 'str')
ct_df['Prop'] = ct_df['Prop'].astype('float')

all_cdta = list(ct_df['CDTA'].unique())
del_cdta = ['BK55', 'BK56', 'BX26', 'BX27', 'BX28', 'MN64', 'QN80', 'QN81', 'QN82', 'QN83', 'QN84', 'SI95']
cdta_li = [x for x in all_cdta if x not in del_cdta] 

# Output DF 
corr_df = pd.DataFrame(index = cdta_li)

# define correlation function 
def get_corr(df, cdta, y_var):
    x = df.loc[df['CDTA'] == cdta, '% Households w/ Vehicle']
    y = df.loc[df['CDTA'] == cdta, ('% ' + y_var)]
    col = x.corr(y)
    return col

#%% Data Cleaning

mode_dict = {'B01001_001E': 'Population',
             'B08201_001E': 'Households',
             'B08201_002E': 'Households No Vehicle',
             'B08301_001E': 'Workers 16+',
             'B08301_002E': 'Auto',
             'B08301_010E': 'Public Transit',
             'B08301_018E': 'Bike',
             'B08301_019E': 'Walk',
             'B08301_021E': 'WFH'}

name = 'GEO_ID,' + ','.join(list(mode_dict.keys()))
url = f'https://api.census.gov/data/2019/acs/acs5?get={name}&for=tract:*&in=state:{state}&in=county:{county}&key={key}'
r = requests.get(url, proxies = p)

# import ACS data and rename columns
mode_df = pd.read_json(r.content)
mode_df = mode_df.rename(columns = mode_df.iloc[0]).drop(mode_df.index[0])
mode_df.rename(columns = mode_dict, inplace = True)

# remove country code from census tract id 
mode_df['GEO_ID'] = mode_df['GEO_ID'].str.split('S').str.get(-1).astype('int64')

# convert all columns to int and then GEO_ID to string
mode_df = mode_df.astype('int64')
mode_df['GEO_ID'] = mode_df['GEO_ID'].astype('str')

# delete old columns 
mode_df = mode_df.drop(['state', 'county','tract'], axis = 1)

# convert 2010 CTs to 2020 CTS/CDTAs
mode_df.rename(columns = {'GEO_ID': 'CT2010'}, inplace = True)
mode_df = pd.merge(mode_df, ct_df, how = 'left', on = 'CT2010')

for val in mode_dict.values():
    mode_df[val] = mode_df[val].multiply(mode_df['Prop'], axis = 'index')

# calculate vehicle ownership and travel mode %s
mode_df['% Households w/ Vehicle'] = (mode_df['Households'] - mode_df['Households No Vehicle']) / mode_df['Households']
mode_df['% Auto'] = mode_df['Auto'] / mode_df['Workers 16+']
mode_df['% Public Transit'] = mode_df['Public Transit'] / mode_df['Workers 16+']
mode_df['% Active Transport'] = (mode_df['Bike'] + mode_df['Walk']) / mode_df['Workers 16+']

# drop rows with 0 households, 0 workers, or CDTAs without a CD approximation
mode_df = mode_df.loc[~((mode_df['Households'] == 0) | (mode_df['Workers 16+'] == 0))]
mode_df = mode_df.loc[~(mode_df.CDTA.isin(del_cdta))]

mode_df = mode_df.sort_values(by = ['CDTA']).reset_index()

# export df
# mode_df.to_csv(path + 'output/mode_cor.csv', index = False)
            
#%% Scatterplot 

mode_df['Boro'] = mode_df['CDTA'].apply(lambda x: x[:2])
mode_df['Hover'] = '<b>CDTA: </b>' + mode_df['CDTAName'] + '<br><b>Census Tract: </b>' + mode_df['CT2020'] +'<br><b>Total Households: </b>' + mode_df['Households'].map('{:,.0f}'.format) + '<br><b>Households with a Vehicle: </b>' + mode_df['% Households w/ Vehicle'].map('{:.0%}'.format) + '<br><b>Total Workers: </b>' + mode_df['Workers 16+'].map('{:,.0f}'.format)  + '<br><b>Workers Commuting by Auto: </b>'+ mode_df['% Auto'].map('{:.0%}'.format)
cdta_li = list(mode_df['CDTA'].unique())

fig = go.Figure()

for boro in ['BK', 'BX', 'MN', 'QN', 'SI']:
    for cdta in cdta_li:
        fig.add_trace(go.Scatter(name = cdta,
                                  x =  mode_df.loc[(mode_df['Boro'] == boro) & (mode_df['CDTA'] == cdta), '% Households w/ Vehicle'], 
                                  y =  mode_df.loc[(mode_df['Boro'] == boro) & (mode_df['CDTA'] == cdta), '% Auto'],
                                  mode = 'markers',
                                  marker = {'line': {'width': .2},
                                            'size': mode_df.loc[(mode_df['Boro'] == boro) & (mode_df['CDTA'] == cdta), 'Households'],
                                            'sizemode': 'area',
                                            'sizeref': 2.*max(mode_df['Households'])/(15.**2),
                                            'sizemin': 1.5},
                                  hoverinfo = 'text',
                                  hovertext =  mode_df.loc[(mode_df['Boro'] == boro) & (mode_df['CDTA'] == cdta), 'Hover'],
                                  legendgroup = boro,
                                  legendgrouptitle_text = boro))
       
fig.update_layout(template = 'plotly_dark',
                  title = {'text': '<b>Vehicle Ownership vs. Commute by Auto</b>'},
                  xaxis = {'title': '% of Households w/ Vehicles',
                           'tickformat': ',.0%',
                           'range': [0,1]},
                  yaxis = {'title' : '% of Workers Commuting by Auto',
                           'tickformat': ',.0%',
                           'range': [0,1]},
                  legend = {'groupclick': 'toggleitem'})

fig.add_annotation(text = 'Data Source: <a href="https://www.census.gov/programs-surveys/acs/microdata/access.2019.html" target="blank">2015-2019 ACS</a> | <a href="https://raw.githubusercontent.com/NYCPlanning/td-trends/main/commute/temp/mode.csv" target="blank">Download Chart Data</a>',
                   font_size = 12,
                   showarrow = False, 
                   x = 1, 
                   xanchor = 'right',
                   xref = 'paper',
                   y = -.1,
                   yanchor = 'top',
                   yref = 'paper')

fig.update_layout(modebar_remove = ['select', 'zoomIn', 'zoomOut', 'autoScale', 'lasso2d'])

# fig.show()

# fig.write_html(path + 'output/auto_corr.html',
#                 include_plotlyjs = 'cdn',
#                 config = {'displaylogo': False})

#%% Correlation

mode_corr_df = mode_df.loc[mode_df.index.repeat(mode_df.Households)] 

mode_corr_df['CT2020'].value_counts()
mode_li = ['Auto', 'Public Transit', 'Active Transport']

for mode in mode_li:
    corr_df['Corr ' + mode] = ''
    for cdta in cdta_li: 
        col = get_corr(mode_corr_df, cdta, mode)
        corr_df.loc[cdta, 'Corr ' + mode] = col 
        
corr_df = corr_df.astype(float)

corr_df.reset_index(inplace = True)
corr_df = corr_df.rename(columns = {'index': 'CDTA'})

# corr_df.to_csv(path + 'output/corr.csv', index = False)   

#%% Output

cols = list(mode_dict.values())
cols.append('CDTA')

output_df = mode_df[cols].groupby(['CDTA']).sum().reset_index()
output_df = output_df.merge(corr_df, on = 'CDTA')

#%% Mapping

cdta_gdf = gpd.read_file('C:/Users/M_Free/OneDrive - NYC O365 HOSTED/Projects/Geographies/cdta20.geojson', driver = 'GeoJSON')        
cdta_gdf.rename(columns = {'cdta2020': 'CDTA'}, inplace = True)
cdta_gdf = cdta_gdf.merge(output_df, on = 'CDTA')

cdta_gdf['Corr Auto'] = cdta_gdf['Corr Auto'].astype(float)

cdta_gdf.to_file(path + 'output/output_test.json', driver = 'GeoJSON')

# bins_li = [-.25, 0, .25, .5, .75, 1]    
# cdta_gdf.plot(column = 'Auto',
#               scheme = 'user_defined',
#               cmap = 'PRGn',
#               classification_kwds = {'bins': bins_li},
#               legend = True)

#efe6d3
#d4eae6
#91d3c8
#4aae9f
#018571
