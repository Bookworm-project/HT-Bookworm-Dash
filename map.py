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
from common import graphconfig
import bwypy
import json

app.config.supress_callback_exceptions=True

bwypy.set_options(database='Bookworm2016', endpoint='https://bookworm.htrc.illinois.edu/cgi-bin/dbbindings.py')
bw_map = bwypy.BWQuery(verify_fields=False)
bw_map.counttype = ['WordsPerMillion']
bw_map.json['words_collation'] = 'case_insensitive'

bw_html = bwypy.BWQuery(verify_fields=False)
bw_html.json['method'] = 'search_results'
bw_html.json['words_collation'] = 'case_insensitive'

keys = ['word', 'compare_word', 'type', 'scope']
defaults = ['color', 'colour', 'scattergeo', 'country']
# Future support for pre-load param insertion
params = None
if params is not None:
    q = dict(zip(keys,params))
else:
    q = dict(zip(keys,defaults))

header = '''
# Bookworm Map
See where a word occurs in the 15 million volume [HathiTrust](https://www.hathitrust.org) collection.

Locations correspond to the places that volumes were published in.
'''

country_codes = pd.read_csv('data/country_codes.csv')
state_codes = pd.read_csv('data/state_codes_us.csv')

@functools.lru_cache(maxsize=32)
def get_word_by_us_state(word):
    words = [token.strip() for token in word.split(',')]
    bw_map.search_limits = { 'word':word.split(','), 'publication_country': 'USA' }
    bw_map.groups = ['*publication_country', 'publication_state']
    results = bw_map.run()
    df = results.frame(index=False, drop_unknowns=True)
    data = pd.merge(df, state_codes)
    return data

@functools.lru_cache(maxsize=32)
def get_word_by_country(word):
    words = [token.strip() for token in word.split(',')]
    bw_map.search_limits = { 'word':words }
    bw_map.groups = ['publication_country']
    results = bw_map.run()
    df = results.frame(index=False, drop_unknowns=True)
    data = pd.merge(df, country_codes)
    return data

def build_map(word, compare_word=None, type='scattergeo', scope='country'):
    import pandas as pd
    import numpy as np

    transform = lambda x: np.log(1+x/maxval)
    
    if scope == 'country':
        data = get_word_by_country(word).copy()
        if compare_word:
            data2 = get_word_by_country(compare_word).copy()
        field = 'publication_country'
        scope = 'world'
        projection = 'Mercator'
        locationmode = 'ISO-3'
    elif scope == 'state':
        data = get_word_by_us_state(word).copy()
        if compare_word:
            data2 = get_word_by_us_state(compare_word).copy()
        field = 'publication_state'
        scope = 'usa'
        projection = 'albers usa'
        locationmode = 'USA-states'
    
    if compare_word and (compare_word.strip() != ''):
        sizemod = 45
        data = pd.merge(data,data2, on=[field, 'code'])
        if type == 'scattergeo':
            data = data[(data['WordsPerMillion_x'] != 0) & (data['WordsPerMillion_y'] != 0)]
        maxval = data[['WordsPerMillion_x', 'WordsPerMillion_y']].max().max()
        logcounts = sizemod*(data['WordsPerMillion_x'].apply(transform) - data['WordsPerMillion_y'].apply(transform))
        text = ( data[field]
                 + "<br> Words Per Million<br>    '{}': ".format(word) 
                 + data['WordsPerMillion_x'].round(1).astype(str) 
                 + "<br>    '{}': ".format(compare_word) 
                 + data['WordsPerMillion_y'].round(1).astype(str)
                )
        title = "\'%s\' vs. '%s' in the HathiTrust" % (word, compare_word)
    else:
        sizemod = 40
        if type == 'scattergeo':
            data = data[(data['WordsPerMillion'] != 0)]
        counts = data['WordsPerMillion'].astype(int)
        maxval = counts.max()
        logcounts = sizemod*counts.apply(transform)
        text = data[field] + '<br> Words Per Million:' + data['WordsPerMillion'].round(2).astype('str')
        title = "\'%s\' in the HathiTrust" % word
        
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

app.layout = html.Div([
     html.Div([
        html.Div([
                dcc.Markdown(header),
                html.Div(
                    [html.Label("Search For a Term"),
                        html.Br(),
                        dcc.Input(id='search-term', type='text', value=q['word'],
                            style={'color': 'darkorange','font-weight':'bold'}),
                     dcc.Input(id='map-search-term-hidden', type='hidden',
                               value=json.dumps(dict(word=q['word'], compare=q['compare_word']))),
                     html.Br(),
                        html.Small("Combine search words with a comma. Only single word queries supported."),
                            ],
                    className="form-group"
                ),
                html.Div(
                    [html.Label("Optional: Compare to another term"),
                        dcc.Input(id='compare-term', type='text', value=q['compare_word'],
                            style={'color': 'navy','font-weight':'bold'})],
                    className="form-group"
                ),
                html.Button('Update Words', id='word_search_button', className='btn btn-primary'),
                html.Div(
                    [html.Label("Type of Map"),
                     html.Div(dcc.RadioItems(
                        id='map_type',
                        options=[
                            {'label': u'Scatter', 'value': 'scattergeo'},
                            {'label': u'Color', 'value': 'choropleth'}
                        ],
                        value=q['type']
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
                        value=q['scope']
                    ), className='radio')],
                    className="form-group"
                )
            ],
            className='col-md-3'),
        html.Div(
            [dcc.Graph(id='main-map-graph', animate=False, config=graphconfig)],
            className='col-md-9')
    ], className='row'),
      html.Div([
        html.Div([
            dcc.Markdown("""**Example Books**
            Choose a place on the map to see matching books from there. All search and compare words included in matches.
            """),
            html.Div(id='select-data'),
        ], className='col-md-offset-4 col-md-8')
      ], className='row')
    ], className='container-fluid')

@app.callback(
    Output('select-data', 'children'),
    [Input('main-map-graph', 'clickData')],
    state=[State('search-term', 'value'), State('compare-term', 'value'),
           State('map_scope', 'value')])
def display_click_data(clickData, word, compare_word, mapscope):
    import json
    import re
    try:
        limit = clickData['points'][0]['text'].split('<br>')[0]
    except:
        return html.Ul(html.Li(html.Em("Nothing selected")))
    if compare_word and compare_word.strip() != '':
        word = word + "," + compare_word
    q = word.split(",")
        
    bw_html.search_limits = { 'publication_' + mapscope : [limit], 'word': q }
    results = bw_html.run()
    
    # Format results
    links = []
    for result in results.json():
        try:
            groups = re.search("href=(.*)><em>(.*?)</em> \((.*?)\)", result).groups()
            link = html.Li(html.A(href=groups[0], target='_blank', children=["%s (%s)" % (groups[1], groups[2])]))
            links.append(link)
        except:
            raise
    return html.Ul(links)

@app.callback(
    Output('map-search-term-hidden', 'value'),
    events=[Event('word_search_button', 'click')],
    state=[State('search-term', 'value'), State('compare-term', 'value')]
)
def update_hidden_search_term(word, compare):
    return json.dumps(dict(word=word, compare=compare))

@app.callback(
    Output('main-map-graph', 'figure'),
    [Input('map-search-term-hidden', 'value'),
           Input('map_type', 'value'), Input('map_scope', 'value')]
)
def map_search(word_query, maptype, mapscope):
    word_query=json.loads(word_query)
    word = word_query['word']
    compare_word = word_query['compare']
    plotdata, layout = build_map(word, compare_word, maptype, mapscope)
    fig = dict( data=plotdata, layout=layout )
    return fig

if __name__ == '__main__':
    app.config.supress_callback_exceptions = True
    app.run_server(debug=True, port=8080, threaded=True, host='0.0.0.0')
