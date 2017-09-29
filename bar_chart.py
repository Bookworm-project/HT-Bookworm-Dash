import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly
import plotly.graph_objs as go
from plotly import figure_factory as FF
import pandas as pd
import functools
from common import app
from common import graphconfig
from tools import get_facet_group_options
import bwypy

app.config.supress_callback_exceptions=True

bwypy.set_options(database='Bookworm2016', endpoint='https://bookworm.htrc.illinois.edu/cgi-bin/dbbindings.py')
bw = bwypy.BWQuery(verify_fields=False)

facet_opts = get_facet_group_options(bw)

# This will cache identical calls
@functools.lru_cache(maxsize=32)
def get_results(group):
    bw.counttype = ['WordCount', 'TextCount']
    bw.groups = ['*'+group]
    bw.search_limits = { group + '__id' : {"$lt": 60 } }
    return bw.run()

bw_date = bwypy.BWQuery(verify_fields=False)

@functools.lru_cache(maxsize=32)
def get_date_distribution(group, facet):
    bw_date.groups = ['date_year']
    bw_date.counttype = ['TextCount']
    bw_date.search_limits = { group: facet }
    results = bw_date.run()
    df = results.frame(index=False)
    df.date_year = pd.to_numeric(df.date_year)
    df2 = df.query('(date_year > 1800) and (date_year < 2016)').sort_values('date_year', ascending=True)
    df2['smoothed'] = df2.TextCount.rolling(10, 0).mean()
    return df2

header = '''
# Bookworm Bar Chart
Select a field and see the raw counts in the Bookworm database
'''

controls = html.Div([
        dcc.Markdown(header),
        html.Label("Facet Group"),
        dcc.Dropdown(id='group-dropdown', options=facet_opts, value='language'),
        html.Label("Number of results to show"),
        dcc.Slider(id='trim-slider', min=10, max=60, value=20, step=5,
                   marks={str(n): str(n) for n in range(10, 61, 10)}),
        html.Label("Ignore unknown values:", style={'padding-top': '15px'}),
        dcc.RadioItems(
            id='drop-radio',
            options=[
                {'label': u'Yes', 'value': 'drop'},
                {'label': u'No', 'value': 'keep'}
            ],
            value='drop'
        ),
        html.Label("Count by:"),
        dcc.RadioItems(id='counttype-dropdown', options=[
                {'label': u'# of Texts', 'value': 'TextCount'},
                {'label': u'# of Words', 'value': 'WordCount'}
            ], value='TextCount')
    ],
    className='col-md-3')

app.layout = html.Div([
    
    html.Div([
                controls,
                html.Div([dcc.Graph(id='bar-chart-main-graph', config=graphconfig)], className='col-md-9')
            ],
            className='row'),
    html.Div([
                html.Div([html.H2("Data"), dcc.Graph(id='bar-data-table')], id='data-table', className='col-md-5'),
                html.Div([dcc.Graph(id='date-distribution')], id='graph-wrapper', className='col-md-7')
             ],
            className='row')

], className='container-fluid')

@app.callback(
    Output('bar-chart-main-graph', 'figure'),
    [Input('group-dropdown', 'value'), Input('trim-slider', 'value'),
     Input('drop-radio', 'value'), Input('counttype-dropdown', 'value')]
)
def update_figure(group, trim_at, drop_radio, counttype):
    bw.groups = [group]
    results = get_results(group)

    df = results.frame(index=False, drop_unknowns=(drop_radio=='drop'))
    df = df.copy()
    df_trimmed = df.head(trim_at)
        
    data = [
        go.Bar(
            x=df_trimmed[group],
            y=df_trimmed[counttype]
        )
    ]
    
    return {
            'data': data,
            'layout': {
                'yTitle': counttype,
                'title': group.replace('_', ' ').title()
            }
        }

@app.callback(
    Output('bar-data-table', 'figure'),
    [Input('group-dropdown', 'value'), Input('drop-radio', 'value')]
)
def update_table(group, drop_radio):
    results = get_results(group)
    df = results.frame(index=False, drop_unknowns=(drop_radio=='drop'))
    df = df.copy()
    return FF.create_table(df)
    #return html.Table(
        # Header
        #[html.Tr([html.Th(col) for col in df.columns])] +
        # Body
        #[html.Tr([
        #            html.Td(df.iloc[i][col]) for col in df.columns
        #        ]) for i in range(min(len(df), 100))]
    #)

@app.callback(
    Output('date-distribution', 'figure'),
    [Input('bar-chart-main-graph', 'hoverData'), Input('group-dropdown', 'value')])
def print_hover_data(clickData, group):
    if clickData:
        facet_value = clickData['points'][0]['x']
        df = get_date_distribution(group, facet_value)
        df = df.copy()
        data = [
            go.Scatter(
                x=df['date_year'],
                y=df['smoothed']
            )
        ]
        return {
            'data': data,
            'layout': {
                'height': 300,
                'yaxis': {'range': [0, int(df.smoothed.max())+100]},
                'title': 'Date Distribution for ' + facet_value.replace('_', ' ').title()
            }
        }
    else:
        data = [
            go.Scatter(
                x=list(range(1800, 2016)),
                y=[0]*(2013-1800)
            )
        ]
        return {
            'data': data,
            'layout': {
                'height': 300,
                'yaxis': {'range': [0, 100000]},
                'title': 'Select a ' + group.replace('_', ' ') + ' to see date distribution'            }
        }
    
if __name__ == '__main__':
    # app.scripts.config.serve_locally = False
    app.config.supress_callback_exceptions = True
    app.run_server(debug=True, port=8080, threaded=True, host='0.0.0.0')
