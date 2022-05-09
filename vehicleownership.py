# -*- coding: utf-8 -*-
"""
Vehicle Ownership 
"""
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
import plotly.subplots as ps
import plotly.io as pio
from sklearn.linear_model import LinearRegression
pio.renderers.default = 'browser'

# DCP proxy
usernm = pd.read_csv('C:/Users/M_Free/Desktop/key.csv',dtype=str).loc[0,'username']
passwd = pd.read_csv('C:/Users/M_Free/Desktop/key.csv',dtype=str).loc[0,'password']
p={'http':'http://'+str(usernm)+':'+str(passwd)+'@dcpproxy1.dcp.nycnet:8080',
    'https':'http://'+str(usernm)+':'+str(passwd)+'@dcpproxy1.dcp.nycnet:8080'}

# Census API
key = pd.read_csv('C:/Users/M_Free/Desktop/key_census.csv',dtype=str).loc[0, 'key']
state = '36'
county = '005,047,061,081,085'

# Files
path = 'C:/Users/M_Free/Desktop/td-vehicleownership/'

# Regression Variables and Results 
boro_li = ['Bronx', 'Brooklyn', 'Manhattan', 'Queens', 'Staten Island']
mode_li = ['Auto', 'Public Transit', 'Active Transport']

reg_df = pd.DataFrame(columns = ['geo', 'y_var','r_sq', 'b0', 'b1', 'b0b1'])
reg_df = reg_df.set_index(['geo', 'y_var'])

def reg_analysis_nyc(df, y_var):
    x = np.array(df['% Households w/ Vehicle']).reshape(-1,1)
    y = np.array(df['% ' + y_var])
    weights = np.array(df['Households'])
    reg = LinearRegression().fit(x, y, sample_weight = weights)
    r_sq = reg.score(x,y)
    b0 = reg.intercept_
    b1 = reg.coef_
    b0b1 = b0 + b1[0]
    row = {'r_sq': r_sq, 'b0': b0, 'b1': b1[0], 'b0b1': b0b1}
    return row

def reg_analysis_boro(df, boro, y_var):
    x = np.array(df.loc[df['Boro'] == boro,'% Households w/ Vehicle']).reshape(-1,1)
    y = np.array(df.loc[df['Boro'] == boro, ('% ' + y_var)])
    weights = np.array(df.loc[df['Boro'] == boro, 'Households'])
    reg = LinearRegression().fit(x, y, sample_weight = weights)
    r_sq = reg.score(x,y)
    b0 = reg.intercept_
    b1 = reg.coef_
    b0b1 = b0 + b1[0]
    row = {'r_sq': r_sq, 'b0': b0, 'b1': b1[0], 'b0b1': b0b1}
    return row

# Visual Elements 
boro_colors = {'Bronx':'rgba(114,158,206,0.5)',
               'Brooklyn':'rgba(255,158,74,0.5)',
               'Manhattan':'rgba(103,191,92,0.5)',
               'Queens':'rgba(237,102,93,0.5)',
               'Staten Island':'rgba(173,139,201,0.5)'}

#%% Travel Mode: Data Cleaning and Regression 

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

# replace country codes with borough names
col = mode_df['county']
mode_df['Boro'] = np.select([col == 5,col == 47, col == 61, col == 81, col == 85],
                            ['Bronx', 'Brooklyn', 'Manhattan', 'Queens', 'Staten Island'])

# delete old columns 
mode_df = mode_df.drop(['state', 'county','tract'], axis = 1)

# calculate vehicle ownership and travel mode %s
mode_df['% Households w/ Vehicle'] = (mode_df['Households'] - mode_df['Households No Vehicle']) / mode_df['Households']
mode_df['% Auto'] = mode_df['Auto'] / mode_df['Workers 16+']
mode_df['% Public Transit'] = mode_df['Public Transit'] / mode_df['Workers 16+']
mode_df['% Active Transport'] = (mode_df['Bike'] + mode_df['Walk']) / mode_df['Workers 16+']

# drop rows with 0 households or workers 16+
mode_df = mode_df.loc[~((mode_df['Households'] == 0) | (mode_df['Workers 16+'] == 0))]

# export df
# mode_df.to_csv(path + 'output/mode.csv', index = False)

# add hover text
mode_df['CT'] = mode_df['GEO_ID'].str[5:11]
hover_template = '<b>Census Tract: </b>' + mode_df['CT'] +'<br><b>Total Households: </b>' + mode_df['Households'].map('{:,.0f}'.format) + '<br><b>Households with a Vehicle: </b>' + mode_df['% Households w/ Vehicle'].map('{:.0%}'.format) + '<br><b>Total Workers: </b>' + mode_df['Workers 16+'].map('{:,.0f}'.format)
mode_df['Hover_Auto'] =  hover_template + '<br><b>Workers Commuting by Auto: </b>'+ mode_df['% Auto'].map('{:.0%}'.format)
mode_df['Hover_Public Transit'] = hover_template + '<br><b>Workers Commuting by Public Transit: </b>'+ mode_df['% Public Transit'].map('{:.0%}'.format) 
mode_df['Hover_Active Transport'] = hover_template + '<br><b>Workers Commuting by Active Transport: </b>'+ mode_df['% Active Transport'].map('{:.0%}'.format) 

# run regression model 
for mode in mode_li:
    row = reg_analysis_nyc(mode_df, mode)
    reg_df.loc[('New York City', mode),:] = list(row.values())

for boro in boro_li:
    for mode in mode_li:
        row = reg_analysis_boro(mode_df, boro, mode)
        reg_df.loc[(boro, mode), :] = list(row.values())

#%% Travel Mode: Visualization

fig = ps.make_subplots(rows = 1,
                       cols = 3,
                       shared_yaxes = True,
                       x_title = '<b>% of Commuters by Mode</b>',
                       y_title = '<b>% of Households with a Vehicle</b>',
                       subplot_titles = mode_li)

# create NYC scatterplots for each mode 
for mode in mode_li:
    for boro, color in boro_colors.items():
        fig.add_trace(go.Scatter(name = 'Census Tracts',
                                 x = mode_df.loc[mode_df['Boro'] == boro, '% Households w/ Vehicle'], 
                                 y = mode_df.loc[mode_df['Boro'] == boro, '% ' + mode], 
                                 mode = 'markers',
                                 marker = {'color': color,
                                           'line': {'width': .2},
                                           'size': mode_df.loc[mode_df['Boro'] == boro, 'Households'],
                                           'sizemode': 'area',
                                           'sizeref': 2.*max(mode_df.loc[mode_df['Boro'] == boro, 'Households'])/(15.**2),
                                           'sizemin': 1.5},
                                 hoverinfo = 'text',
                                 hovertext = mode_df.loc[mode_df['Boro'] == boro, 'Hover_' + mode],
                                 legendgroup = 'New York City',
                                 showlegend = False),
                      row = 1,
                      col = mode_li.index(mode) + 1)

# add NYC legend marker 
count = 0        
for mode in mode_li:
    fig.add_trace(go.Scatter(name = 'Census Tracts', 
                             x = [-1],
                             y = [-1],
                             mode = 'markers',
                             marker = {'color': 'rgba(0,0,0,0.5)',
                                       'size': 15},    
                             legendgroup = 'New York City',
                             legendgrouptitle_text = 'New York City',
                             showlegend = True if count < 1 else False))
    count = count + 1
    
# count = 0
# for mode in mode_li:
#     for boro, color in boro_colors.items():
#         fig.add_trace(go.Scatter(name = 'Census Tracts',
#                                  x = mode_df.loc[mode_df['Boro'] == boro, '% Households w/ Vehicle'], 
#                                  y = mode_df.loc[mode_df['Boro'] == boro, '% ' + mode], 
#                                  mode = 'markers',
#                                  marker = {'color': color,
#                                            'line': {'width': .2},
#                                            'size': mode_df.loc[mode_df['Boro'] == boro, 'Households'],
#                                            'sizemode': 'area',
#                                            'sizeref': 2.*max(mode_df.loc[mode_df['Boro'] == boro, 'Households'])/(15.**2),
#                                            'sizemin': 1.5},
#                                  hoverinfo = 'text',
#                                  hovertext = mode_df.loc[mode_df['Boro'] == boro, 'Hover_' + mode],
#                                  legendgroup = 'New York City',
#                                  legendgrouptitle_text = 'New York City',
#                                  showlegend = True if count < 5 else False),
#                       row = 1,
#                       col = mode_li.index(mode) + 1)
#         count = count + 1

# create borough scatterplots for each mode 
count = 0
for mode in mode_li:
    for boro, color in boro_colors.items():
        fig.add_trace(go.Scatter(name = 'Census Tracts',
                                 x = mode_df.loc[mode_df['Boro'] == boro, '% Households w/ Vehicle'], 
                                 y = mode_df.loc[mode_df['Boro'] == boro, '% ' + mode], 
                                 mode = 'markers',
                                 marker = {'color': color,
                                           'line': {'width': .2},
                                           'size': mode_df.loc[mode_df['Boro'] == boro, 'Households'],
                                           'sizemode': 'area',
                                           'sizeref': 2.*max(mode_df.loc[mode_df['Boro'] == boro, 'Households'])/(15.**2),
                                           'sizemin': 1.5},
                                 hoverinfo = 'text',
                                 hovertext = mode_df.loc[mode_df['Boro'] == boro, 'Hover_' + mode],
                                 legendgroup = boro,
                                 legendgrouptitle_text = boro,
                                 showlegend = True if count < 5 else False,
                                 visible = 'legendonly'),
                      row = 1,
                      col = mode_li.index(mode) + 1)
        count = count + 1
                        
# add NYC line of best fit for each mode 
count = 0
for mode in mode_li:
    fig.add_trace(go.Scatter(name = 'Line of Best Fit*',
                             x = [0,1],
                             y = [reg_df.loc[('New York City', mode),'b0'], reg_df.loc[('New York City', mode), 'b0b1']],
                             mode = 'lines',
                             line = {'color': 'rgba(0,0,0,0.5)',
                                     'width': 2},
                             hoverinfo = 'text',
                             hovertext = '<b>R<sup>2</sup> : </b>' + str(round(reg_df.loc[('New York City', mode),'r_sq'], 2)), 
                             legendgroup = 'New York City',
                             showlegend = True if count < 1 else False),
                  row = 1, 
                  col = mode_li.index(mode) + 1)
    count = count + 1

# add boro line of best fit for each mode 
count = 0
for mode in mode_li:
    for boro, color in boro_colors.items():
        fig.add_trace(go.Scatter(name = 'Line of Best Fit*',
                                 x = [0,1],
                                 y = [reg_df.loc[(boro, mode), 'b0'], reg_df.loc[(boro, mode), 'b0b1']],
                                 mode = 'lines',
                                 line = {'color': color,
                                         'width': 2},
                                 hoverinfo = 'text',
                                 hovertext = '<b>R<sup>2</sup> : </b>' + str(round(reg_df.loc[(boro, mode),'r_sq'], 2)), 
                                 legendgroup = boro,
                                 showlegend = True if count < 1 else False,
                                 visible = 'legendonly'),
                      row = 1, 
                      col = mode_li.index(mode) + 1)
    count = count + 1
    
# edit x axis for each subplot 
for mode in mode_li:
    fig.update_xaxes(patch = {'title': {'font_size': 14},
                              'tickformat': ',.0%',
                              'tickfont_size': 12,
                              'range': [-.01,1.01],
                              'fixedrange': True},
                     row = 1,
                     col = mode_li.index(mode) +1)

# edit overall layout
fig.update_layout(template = 'plotly_white',
                  title = {'text': '<b>Vehicle Ownership vs. Commute Mode</b>',
                           'font_size': 22,
                           'x': .15,
                           'xanchor': 'center',
                           'y': .95,
                           'yanchor': 'top'},
                  yaxis = {'title': {'font_size': 14},
                           'tickformat': ',.0%',
                           'tickfont_size': 12,
                           'range':[-.01,1.01],
                           'fixedrange': True},
                  legend = {'traceorder': 'grouped',
                            'orientation': 'h',
                            'title_text': '', 
                            'font_size': 12,
                            'x': .75, 
                            'xanchor': 'center',
                            'y': 1.13,
                            'yanchor': 'top'},
                  margin = {'b': 100,
                            'l': 80,
                            'r': 40,
                            't': 115},
                  hoverlabel = {'font_size': 14}, 
                  font = {'family': 'Arial',
                          'color': 'black'},
                  dragmode = False)

# edit subplot titles 
for mode in mode_li:
    fig.layout.annotations[mode_li.index(mode)].update(y = 1, 
                                                       yanchor = 'top',
                                                       yref = 'paper',
                                                       yshift = -20,
                                                       bgcolor = 'rgba(162,162,162,0.4)',
                                                       text = '<b>' + mode + '</b>',
                                                       font = {'size': 14,
                                                               'family': 'Arial'})
     
# add source
fig.add_annotation(text = '*Hover over line end points for the R-Squared value<br>Data Source: <a href="https://www.census.gov/programs-surveys/acs/microdata/access.2019.html" target="blank">2015-2019 ACS</a> | <a href="https://raw.githubusercontent.com/NYCPlanning/td-trends/main/commute/temp/mode.csv" target="blank">Download Chart Data</a>',
                   font_size = 12,
                   showarrow = False, 
                   x = 1, 
                   xanchor = 'right',
                   xref = 'paper',
                   y = -.1,
                   yanchor = 'top',
                   yref = 'paper')

fig.show()

# fig.write_html(path + 'output/mode.html',
#               include_plotlyjs='cdn',
#               config={'displayModeBar':False})

# https://nycplanning.github.io/td-vehicleownership/output/mode.html                      