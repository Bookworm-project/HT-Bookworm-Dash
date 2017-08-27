# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import  State, Event, Input, Output
import plotly
import plotly.graph_objs as go
import pandas as pd
import functools
from common import app
import bwypy

app.config.supress_callback_exceptions=True
#_globals = dict(last=time.time(), term='')

bwypy.set_options(database='Bookworm2016', endpoint='https://bookworm.htrc.illinois.edu/cgi-bin/dbbindings.py')
bw = bwypy.BWQuery(verify_fields=False)
bw.counttype = ['WordsPerMillion']

header = '''
# Bookworm Map
See where a word occurs in the 15 million volume [HathiTrust[(https://www.hathitrust.org) collection.

Locations correspond to the places that volumes were published in.
'''

country_codes = pd.read_csv('data/country_codes.csv')
state_codes = pd.read_csv('data/state_codes_us.csv')

@functools.lru_cache(maxsize=32)
def get_word_by_us_state(word):
    bw.search_limits = { 'word':[word], 'publication_country': 'USA' }
    bw.groups = ['*publication_country', 'publication_state']
    results = bw.run()
    df = results.frame(index=False, drop_unknowns=True)
    data = pd.merge(df, state_codes)
    return data

@functools.lru_cache(maxsize=32)
def get_word_by_country(word):
    bw.search_limits = { 'word':[word] }
    bw.groups = ['publication_country']
    results = bw.run()
    df = results.frame(index=False, drop_unknowns=True)
    data = pd.merge(df, country_codes)
    return data

def build_map(word, compare_word=None, type='scattergeo', scope='country'):
    import pandas as pd
    import numpy as np

    transform = lambda x: np.log(1+x/maxval)
    
    if scope == 'country':
        data = get_word_by_country(word)
        if compare_word:
            data2 = get_word_by_country(compare_word)
        field = 'publication_country'
        scope = 'world'
        projection = 'Mercator'
        locationmode = 'ISO-3'
    elif scope == 'state':
        data = get_word_by_us_state(word)
        if compare_word:
            data2 = get_word_by_us_state(compare_word)
        field = 'publication_state'
        scope = 'usa'
        projection = 'albers usa'
        locationmode = 'USA-states'
        
    if compare_word and (compare_word.strip() != ''):
        data = pd.merge(data,data2, on=[field, 'code'])
        if type == 'scattergeo':
            data = data[(data['WordsPerMillion_x'] != 0) & (data['WordsPerMillion_y'] != 0)]
        maxval = data[['WordsPerMillion_x', 'WordsPerMillion_y']].max().max()
        logcounts = 40*(data['WordsPerMillion_x'].apply(transform) - data['WordsPerMillion_y'].apply(transform))
        text = ( data[field]
                 + "<br> Words Per Million<br>    '{}': ".format(word) 
                 + data['WordsPerMillion_x'].round(1).astype(str) 
                 + "<br>    '{}': ".format(compare_word) 
                 + data['WordsPerMillion_y'].round(1).astype(str)
                )
        title = "\'%s\' vs. '%s' Mentions in Library Volumes" % (word, compare_word)
    else:
        if type == 'scattergeo':
            data = data[(data['WordsPerMillion'] != 0)]
        counts = data['WordsPerMillion'].astype(int)
        maxval = counts.max()
        logcounts = 40*counts.apply(transform)
        text = data[field] + '<br> Words Per Million:' + data['WordsPerMillion'].round(2).astype('str')
        title = "\'%s\' Mentions in Library Volumes" % word
        
    if compare_word:
        counts2 = data2['WordsPerMillion'].astype(int)
    
   
    plotdata = [ dict(
            type=type,
            hoverinfo = "location+text",
            locationmode = locationmode,
            locations = data['code'],
            text = text,
            marker = dict(
                line = dict(width=0.5, color='rgb(40,40,40)'),
                )
            )]
    
    if type == 'choropleth':
        plotdata[0]['z'] = logcounts
        #plotdata[0]['colorscale'] = scl,
        plotdata[0]['autocolorscale'] = False
        plotdata[0]['showscale'] = False
        plotdata[0]['zauto'] = False
        plotdata[0]['zmax'] = logcounts.abs().max()
        plotdata[0]['zmin'] = -logcounts.abs().max()
    elif type == 'scattergeo':
        plotdata[0]['marker']['size'] = logcounts.abs()
        plotdata[0]['marker']['color'] = logcounts
        plotdata[0]['marker']['cauto'] = False
        plotdata[0]['marker']['cmax'] = logcounts.abs().max()
        plotdata[0]['marker']['cmin'] = -logcounts.abs().max()
    
    layout = dict(
            title = title,
            margin=go.Margin(
            l=10,r=10, b=10, t=50, pad=4
        ),
            geo = dict(
                scope=scope,
                projection=dict( type=projection ),
                showframe = False,
                showcoastlines = True,
                showland = True,
                landcolor = "rgb(229, 229, 229)",
                countrycolor = "rgb(255, 255, 255)" ,
                coastlinecolor = "rgb(255, 255, 255)",
                showlakes = True,
                lakecolor = 'rgb(255, 255, 255)')
            )
    return (plotdata, layout)

# Initial search
plotdata, layout = build_map('color', None, 'scattergeo', 'country')

app.layout = html.Div([
     html.Div([
        html.Div([
                dcc.Markdown(header),
                html.Div(
                    [html.Label("Search For a Term"), dcc.Input(id='search-term', type='text', value='color')],
                    className="form-group"
                ),
                html.Div(
                    [html.Label("Optional: Compare to another term"), dcc.Input(id='compare-term', type='text', value='')],
                    className="form-group"
                ),
                html.Div(
                    [html.Label("Type of Map"),
                     html.Div(dcc.RadioItems(
                        id='map_type',
                        options=[
                            {'label': u'Scatter', 'value': 'scattergeo'},
                            {'label': u'Color', 'value': 'choropleth'}
                        ],
                        value='scattergeo'
                    ), className='radio')],
                    className="form-group"
                ),
                html.Div(
                    [html.Label("Map Scope"),
                     html.Div(dcc.RadioItems(
                        id='map_scope',
                        options=[
                            {'label': u'World', 'value': 'country'},
                            {'label': u'USA', 'value': 'state'}
                        ],
                        value='country'
                    ), className='radio')],
                    className="form-group"
                ),
                html.Button('Search', id='word_search_button')
            ],
            className='col-md-3'),
        html.Div(
            [dcc.Graph(id='main-map-graph', figure=dict( data=plotdata, layout=layout ), animate=False)],
            className='col-md-9')
    ], className='row'),
        html.Div([], id='test-path'),
    ], className='container')


@app.callback(
    Output('main-map-graph', 'figure'),
    events=[Event('word_search_button', 'click')],
    state=[State('search-term', 'value'), State('compare-term', 'value'),
           State('map_type', 'value'), State('map_scope', 'value')]
)
def map_search(word, compare_word, maptype, mapscope):
    plotdata, layout = build_map(word, compare_word, maptype, mapscope)
    fig = dict( data=plotdata, layout=layout )
    return fig

@app.callback(dash.dependencies.Output('test-path', 'children'),
              [dash.dependencies.Input('url', 'pathname')])
def display_path(pathname):
    print(path)

if __name__ == '__main__':
    app.config.supress_callback_exceptions = True
    app.run_server(debug=True, port=8080, threaded=True, host='0.0.0.0')