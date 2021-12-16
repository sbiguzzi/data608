# Import basic libraries
import pandas as pd
from urllib.request import urlopen
import json
from datetime import date
import itertools

# Import world bank data
import wbgapi as wb

# Import graphing library
import plotly.express as px

# Import dash library
import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output

# geoJson file for map graph
with urlopen('https://raw.githubusercontent.com/sbiguzzi/data608/main/Final/custom.geo.json') as response:
    countries = json.load(response)
    
# Define line graph layout
line_layout = {
    'height':500,
    'plot_bgcolor':'#FFFFFF',
    'legend_title_text':'Regions',
    'font':{
        'family':"Seguo UI",
        'size':13,
        'color':'#000000'
    },
    'xaxis':{'fixedrange':True},
    'yaxis':{'fixedrange':True}
}

# Define map graph layout
layout_map = {
    'height':800,
    'margin':{"r":0,"l":0,"b":0},
    'font':{
        'family':"Seguo UI",
        'size':13,
        'color':'#000000'}}
      
# Initiate dash app
app = dash.Dash()

# building static dataframes
# Region dataframe
region_df = wb.economy.DataFrame(skipAggs=False).reset_index()
region_df = region_df[region_df['aggregate']==True][['id','name']]
region_df.rename(columns={'id':'region','name':'regionName'},inplace=True)

# Country dataframe
c_df = wb.economy.DataFrame(skipAggs=True).reset_index()
c_df.drop(['adminregion','lendingType','capitalCity','aggregate'],axis=1,inplace=True)
country_df = c_df.merge(region_df,on='region',how='left')
country_df.drop(['region'],axis=1,inplace=True)
country_df.rename(columns={'name':'countryName'},inplace=True)

# Creating time dataframe to hold WB years
time_df = pd.DataFrame(list(wb.time.list()))

# Topic dataframe
topic_df = pd.DataFrame(list(wb.topic.list()))

# Indicator dataframe
series_df = pd.DataFrame(list(wb.series.list())).rename(columns={'value':'name'}).reset_index(drop=True)

# building static filters for topics
topic = dict(zip(topic_df.value,topic_df.id))

# set initial dataframe
# use the api generator to form the rows
rows = []
for row in wb.data.fetch('SP.DYN.CBRT.IN',country_df['id'].tolist(),mrv=5):
    rows.append(row)

# create the dataframe from the rows
df = pd.DataFrame(rows)

# name the server
server = app.server

# Create the app layout
app.layout = html.Div([
          
    html.Div([
        
        # Setting page header
        html.H1("Visualizing World Bank Indicators",
                style={'textAlign': 'center','font-size':'45px',"text-decoration": "underline"}),
        
        # Setting page description
        dcc.Markdown('''
        This dashboard was created to visualize trends using World Bank indicators by region and country. The time frame spans all the years that the World Bank has data for. To use this dashboard select a World Bank indicator using the **Topic** filter. Select or type in the indicator you would like to see in the     **Indicator** filter. Finally use the year range slider to select the years for which you want to see data.  
        *Note: selecting the full date range could take a long time to load.*        
        ''',
            style = {'width':'76%','display':'inline-block','textAlign': 'center', 'padding-left':'10%'}),
    ]),
   
    #Creating filter section
    html.Div([
        
        # Creating topic filter
        html.Div([
            dcc.Store('memory-output'),
            html.H5("Topics:", style={'font-size':'16px',"text-decoration": "underline"}),
            dcc.Dropdown(
                id='memory-topic',
                options=[{'label': k, 'value': v} for k,v in topic.items()],
                value=8,
                disabled = False,
                multi = False,
                searchable = True,
                search_value = '',
                placeholder="Select a topic",
                clearable = True
            )], style={'width':'49%','display':'inline-block'}),

        # Creating metric filter
        html.Div([
            html.H5("Indicators:",style={'font-size':'16px',"text-decoration": "underline"}),
            dcc.Dropdown(
                id='memory-metric',
                options=[],
                value='SP.DYN.CBRT.IN',
                placeholder="Select an indicator",
                disabled = False,
                multi = False,
                searchable = True,
                search_value = '',
                clearable = True
            )], style={'width':'49%','display':'inline-block'}),

        # Creating year range slider filter
        html.Div([
            html.H5("Year ranges:",style={'font-size':'16px',"text-decoration": "underline"}),
            dcc.RangeSlider(
                id='memory-year',
                min=int(min(time_df['value'])),
                max=int(max(time_df['value'])),
                value=[int(max(time_df['value']))-5,int(max(time_df['value']))],
              marks={i: str(i) for i in range(1960,int(max(time_df['value'])))},
                allowCross=False)
            ], style={'width':'99%','display':'inline-block'})
    ]),
    
    # Creating section for the line and map graphs
    html.Div([
        
        # Setting section header
        html.H3(id='graph-header',style={'font-size':'24px','textAlign': 'center',"text-decoration": "underline"}),
        
        # Bucket for the line graph
        html.Div([
            dcc.Graph(id='line-graph',
                      config={'displayModeBar':False}
                     )
        ],style={'width': '50%', 'display': 'inline-block', 'vertical-align':'top','padding': '0 20'}),

        # Bucket for the choropleth map
        html.Div([
            dcc.Graph(id='map-graph')
        ],style={'width': '50%', 'display': 'inline-block', 'padding': '0 20'})         
    ]),

])

# App callbacks
# Create the list of indicators for a specific topic
@app.callback(
    Output('memory-metric', 'options'),
    [Input('memory-topic', 'value')])

def update_metrics(topic):
    
    metric_df = pd.DataFrame(list(wb.series.list(topic=int(topic)))).rename(columns={'value':'name'}).reset_index(drop=True)
    metric = dict(zip(metric_df.name,metric_df.id))
    
    return [{'label': k, 'value': v} for k,v in metric.items()]

@app.callback(
    Output('memory-output', 'data'),
    [Input('memory-metric', 'value'),
     Input('memory-year', 'value')])

def filtered_data(metric,year):
    
    # initiate the return dataframe
    return_df = pd.DataFrame({})
    
    # If metric is not selected
    if not metric:
        
        # Check if year is not selected
        if not year:
            
            # Set return_df equal to the memory data
            return_df = df.copy()
        
        # If year is selected
        elif year:
            
            # Set return data equal to the default metric but within the new year ranges
            rows = []
            for row in wb.data.fetch(metric,country_df['id'].tolist(),range(year[0],year[1],1)):
                rows.append(row)

            return_df = pd.DataFrame(rows)         
    
    # If metric is selected
    if metric:
        
        # If the year range is not changed
        if not year:
            
            # Set return data equal to the selected metric but with the default year range
            rows = []
            for row in wb.data.fetch(metric,country_df['id'].tolist(),mrv=5):
                rows.append(row)

            return_df = pd.DataFrame(rows)
        
        # If year range is changed
        if year:
            
            # Set return data equal to the selected metric and the new year range
            rows = []
            for row in wb.data.fetch(metric,country_df['id'].tolist(),range(year[0],year[1],1)):
                rows.append(row)

            return_df = pd.DataFrame(rows)          
        
    return return_df.to_dict('records')

# Updating line and map graph with new indicator selection
@app.callback(
    [Output('graph-header', 'children'),
     Output('line-graph', 'figure'),
     Output('map-graph', 'figure')],
    [Input('memory-output', 'data'),
     Input('memory-metric', 'value')])

def update_line_graph(data,metric):
    if data is None:
        raise dash.exceptions.PreventUpdate
     
    # Set the final_df equal to the return data from the filtered_data function
    final_df = pd.DataFrame(data)
    final_df.rename(columns={'value':metric},inplace=True)
    final_df['time'] = final_df['time'].replace({'YR':''},regex=True)
    final_df.sort_values(['time','economy'],inplace=True)
    final_df = final_df.merge(country_df,left_on='economy',right_on='id',how='left')
    final_df.drop(['id','longitude','latitude','incomeLevel','series'],axis=1,inplace=True)
    final_df.dropna(inplace=True)
    final_df.reset_index(drop=True,inplace=True)

    # Set the section header
    header = series_df[series_df['id'] == metric]['name'].to_string(index=False)+' from '+str(min(final_df['time']))+' to '+str(max(final_df['time']))    

    # Create cartesian product of years and regions
    line_data = []
    for element in itertools.product(*[final_df['regionName'].unique(),final_df['time'].unique()]):
        line_data.append(element)
    
    # Define line dataframe
    data_df = pd.DataFrame(line_data, columns =['regionName', 'time']).sort_values(['time','regionName'])
    group_df = final_df.groupby(['regionName','time']).median([metric]).reset_index()
    line_df = data_df.merge(group_df,on=['regionName','time'],how='left')
    
    # Define line graph
    line_fig = px.line(
        line_df,
        x = 'time', y = metric,
        title = 'Median by World Bank region',
        color = 'regionName',
        color_discrete_sequence = px.colors.qualitative.Bold,
        labels = {
            metric:series_df['name'][series_df['id'] == metric].to_string(header=False, index=False),
            'time':'Year',
            'regionName':'Region'
        },
        markers=True)
    
    # Update line graph layout
    line_fig.update_layout(line_layout)
    
    # Update line graph x and y axis
    line_fig.update_xaxes(tickangle=45, zeroline=True, linewidth=1, linecolor='black')
    line_fig.update_yaxes(showgrid=True, zeroline=True, linewidth=1, linecolor='black')
    
    # Define map dataframe
    map_df = country_df[['id','countryName']].merge(final_df[['time','countryName',metric]].reset_index(drop=True),on='countryName',how='inner')
    map_df.dropna(inplace=True)
    map_df.sort_values(['time','countryName'],inplace=True)
    map_df.reset_index(drop = True, inplace = True)
    
    # Define animated choropleth map
    map_graph = px.choropleth(
        map_df,
        geojson = countries, featureidkey = 'properties.wb_a3', locations='id',
        color = metric, color_continuous_scale = 'mint', projection = 'natural earth',
        labels = {
            'time':'Year',
            metric:'Indicator',
            'id':'Country'
        }, animation_frame = 'time',
        title = 'By countries and years')
    
    # Updating map layout
    map_graph.update_layout(layout_map)
    
    return (header,line_fig,map_graph)
    
if __name__ == '__main__':
    app.run_server(debug=True)