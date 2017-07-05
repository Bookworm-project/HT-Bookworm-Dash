# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import plotly
import plotly.graph_objs as go
import bwypy

import pandas as pd

# For simple memoization
import functools

bwypy.set_options(database='bookworm4m', endpoint='https://bookworm.htrc.illinois.edu/cgi-bin/dbbindings.py')

app = dash.Dash()

app.css.append_css({
    "external_url" : "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css"
})



bw = bwypy.BWQuery(verify_fields=False)

group_options = [{'label': name.replace('_', ' ').title(), 'value': name} for name in bw.fields().name]

# This will cache identical calls
@functools.lru_cache(maxsize=32)
def get_results(group):
    bw.groups = [group]
    return bw.run()

bw_date = bwypy.BWQuery(verify_fields=False)
bw_date.groups = ['date_year']
bw_date.counttype = ['TextCount']

@functools.lru_cache(maxsize=32)
def get_date_distribution(group, facet):
    bw_date.search_limits = { group: facet}
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

controls_left = html.Div([
        html.Label("Facet Group"),
        dcc.Dropdown(id='group-dropdown', options=group_options, value='language'),
        html.Label("Number of results to show"),
        dcc.Slider(id='trim-slider', min=5, max=60, value=20, step=2,
                   marks={str(n): str(n) for n in range(5, 60, 5)})
        ],
        style={'width': '48%', 'display': 'inline-block', 'padding': '10px 5px'})

controls_right = html.Div([
            html.Label("Ignore unknown values:"),
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
        style={'width': '48%', 'display': 'inline-block','padding': '10px 5px'})

app.layout = html.Div([
    dcc.Markdown(header),
    html.Div([controls_left, controls_right],
        style={ 'borderBottom': 'thin lightgrey solid',
                'backgroundColor': 'rgb(250, 250, 250)',
                'padding': '10px 10px'}),
    dcc.Graph(id='example-graph'),
    html.H2("Data"),
    html.Div(id='data-table', children=[html.Table()],
            style={'width': '48%', 'display': 'inline-block','padding': '10px 5px'}),
    html.Div(id='graph-wrapper',
             children=[dcc.Graph(id='date-distribution', animate=False)],
             style={'width': '48%', 'display': 'inline-block',
                    'padding': '10px 5px', 'vertical-align': 'top'}
            )

], className='container')

@app.callback(
    Output('example-graph', 'figure'),
    [Input('group-dropdown', 'value'), Input('trim-slider', 'value'),
     Input('drop-radio', 'value'), Input('counttype-dropdown', 'value')]
)
def update_figure(group, trim_at, drop_radio, counttype):
    bw.groups = [group]
    results = get_results(group)
    
    df = results.frame(index=False, drop_unknowns=(drop_radio=='drop'))
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
    Output('data-table', 'children'),
    [Input('group-dropdown', 'value'), Input('drop-radio', 'value')]
)
def update_table(group, drop_radio):
    results = get_results(group)
    df = results.frame(index=False, drop_unknowns=(drop_radio=='drop'))
    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in df.columns])] +

        # Body
        [html.Tr([
                    html.Td(df.iloc[i][col]) for col in df.columns
                ]) for i in range(min(len(df), 100))]
    )

@app.callback(
    Output('date-distribution', 'figure'),
    [Input('example-graph', 'hoverData'), Input('group-dropdown', 'value')])
def print_hover_data(hoverData, group):
    if hoverData:
        facet_value = hoverData['points'][0]['x']
        df = get_date_distribution(group, facet_value)
        data = [
            go.Scatter(
                x=df['date_year'],
                y=df['smoothed']
            )
        ]
        return {
            'data': data,
            'layout': {
                'yaxis': {'range': [0, int(df.smoothed.max())+100]},
                'title': 'Date Distribution for ' + group.replace('_', ' ').title()
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
                'yaxis': {'range': [0, 100000]},
                'title': 'Select a ' + group.replace('_', ' ') + ' to see date distribution'            }
        }

if __name__ == '__main__':
    app.run_server(debug=True)