# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import  State, Input, Output
import plotly
import plotly.graph_objs as go
import pandas as pd
import functools
from common import app
from common import graphconfig
import bwypy
import numpy as np
import pandas as pd
import itertools
import json
from tools import get_facet_group_options, pretty_facet, errorfig, logging_config
import logging
from logging.config import dictConfig

dictConfig(logging_config)
logger = logging.getLogger()

app.config.supress_callback_exceptions=True

bwypy.set_options(database='Bookworm2016', endpoint='https://bookworm.htrc.illinois.edu/cgi-bin/dbbindings.py')
bw_heatmap = bwypy.BWQuery(verify_fields=False)
bw_heatmap.counttype = ['WordsPerMillion']
bw_heatmap.json['words_collation'] = 'case_insensitive'

bw_html = bwypy.BWQuery(verify_fields=False)
bw_html.json['method'] = 'search_results'
bw_html.json['words_collation'] = 'case_insensitive'

hard_min_year = 1650
hard_max_year = 2015
default_min_year = 1900
default_max_year = 2000

header = '''
# Bookworm Heatmap
See where a word occurs across facets.
'''

facet_opts = get_facet_group_options(bw_heatmap)

@functools.lru_cache(maxsize=32)
def get_heatmap_values(query, facet, max_facet_values=15, hard_min_year=1650, hard_max_year=2015):
    words = [token.strip() for token in query.split(',')]
    bw_heatmap.search_limits = { 'word': words, facet+'__id': { '$lt':max_facet_values+1 }, 
                        'date_year': { '$lt': hard_max_year, '$gt': hard_min_year } }
    bw_heatmap.groups = [facet, 'date_year']

    # Get and format results
    results = bw_heatmap.run()
    df = results.frame(index=False, drop_unknowns=True)
    df.date_year = df.date_year.astype(float).astype(int)
    df = df[df[facet] != '0']
    return df

def format_heatmap_data(data, word, log, smoothing, soft_min_year, soft_max_year, facet_query=None):
    facet = data.columns.values[0]
    if log:
        data.WordsPerMillion = data.WordsPerMillion.add(1).apply(np.log)
    if facet_query is not None:
        data = data[data[facet].isin(list(facet_query))]
    years = pd.Series(range(soft_min_year,soft_max_year))
    fullyears = pd.Series(range(data.date_year.min(),data.date_year.max()))
    all_keys = pd.DataFrame(list(itertools.product(data[facet].unique(), fullyears)), columns=[facet, 'date_year'])

    df2 = pd.merge(all_keys, data, how='left').fillna(0)
    if smoothing:
        df2.WordsPerMillion = df2.WordsPerMillion.rolling(5, min_periods=1).mean()
    df2 = df2[(df2.date_year > soft_min_year) & (df2.date_year < soft_max_year)]

    groups = df2.groupby(facet)
    labels = []
    counts = []
    for g in groups:
        labels.append(g[0])
        counts.append(g[1]['WordsPerMillion'])
        
    data = [go.Heatmap(z=counts,
                   x=years,
                   y=labels,
                   showscale=False
                  )
       ]
    
    layout = go.Layout(
        title='"%s" by %s' % (word, pretty_facet(facet))
    )

    return (data, layout)

#df = get_heatmap_values('cookie', 'class', 15)
#plotdata, layout = format_heatmap_data(df, 'cookie', True, 10, 1900, 2000)

app.layout = html.Div([
     html.Div([
        html.Div([
                dcc.Markdown(header),
            
                html.Div(
                    [html.Div(html.Label("Search For a Term: ")),
                     html.Div(dcc.Input(id='search-term', type='text', value='computer')),
                     dcc.Input(id='search-term-hidden', type='hidden', value=json.dumps(dict(word='computer', compare=''))),
                     html.Small("Combine search words with a comma. Only single word queries supported."),
                     ],
                ),
                html.Div(
                    [
                        html.Label("Optional: Compare to another term", style={'display':'None'}),
                        dcc.Input(id='compare-term', type='hidden', value='colour'),
                        html.Button('Update word', id='word_search_button', className='btn btn-primary'),
                    ],
                    className="form-group"
                ),
                html.Div(
                    [html.Label("Facet by:"),
                     dcc.Dropdown(id='group-dropdown', options=facet_opts, value='class')
                    ]
                ),
                html.Div(
                    [dcc.Dropdown(
                        options=[],
                        multi=True,
                        id="facet-values"
                    )]
                ),
                html.Div(
                    [
                        html.Label("Select Years"),
                        dcc.RangeSlider(
                            count=1,
                            min=hard_min_year,
                            max=hard_max_year,
                            step=1,
                            value=[default_min_year, default_max_year],
                            id='year-slider'
                        ),
                        html.Span(id='year-display')
                    ],
                    className="form-group"
                ),
                html.Br()
            ],
            className='col-md-3'),
        html.Div(
            [dcc.Graph(id='main-heatmap-graph', animate=False, config=graphconfig)],
            className='col-md-9')
    ], className='row'),
      html.Div([
        html.Div([
            dcc.Markdown("""**Example Books**
            Choose a place on the heatmap to see matching books.
            """),
            html.Div(id='heatmap-select-data'),
        ], className='col-md-offset-4 col-md-8')
      ], className='row')
    ], className='container-fluid')


@app.callback(
    Output("facet-values", "options"),
    [Input('group-dropdown', 'value')]
)
def set_facet_value_options(facet):
    def trim(w, n=20):
        if len(w)>n:
            return w[:n]+'…'
        else:
            return w
    return [{'label': trim(x), 'value': x} for x in bw_heatmap.field_values(facet, 40) if x.strip() != '']

@app.callback(
    Output("facet-values", "value"),
    [Input("facet-values", "options")]
)
def set_facet_value_defaults(options):
    return [option['value'] for option in options[:10]]
    
@app.callback(
    Output('heatmap-select-data', 'children'),
    [Input('main-heatmap-graph', 'clickData')],
    state=[State('search-term-hidden', 'value'),
           State('group-dropdown', 'value')])
def display_click_data(clickData, word_query, facet):
    import re
    word_query=json.loads(word_query)
    word = word_query['word']
    compare_word = word_query['compare']
    try:
        facet_value_select = clickData['points'][0]['y']
        year_select = int(clickData['points'][0]['x'])
    except:
        return html.Ul(html.Li(html.Em("Nothing selected")))
    if compare_word and compare_word.strip() != '':
        word = word + "," + compare_word
    q = word.split(",")
        
    bw_html.search_limits = { facet: [facet_value_select], 'date_year':year_select, 'word': q }
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
    print(links)
    return html.Ul(links)

@app.callback(
    Output('year-display', 'children'),
    [Input('year-slider', "value")]
)
def display_year(years):
    return "%d - %d" % tuple(years)

@app.callback(
    Output('search-term-hidden', 'value'),
    [Input('word_search_button', 'n_clicks')],
    state=[State('search-term', 'value'), State('compare-term', 'value')]
)
def update_hidden_search_term(n_clicks, word, compare):
    return json.dumps(dict(word=word, compare=compare))

@app.callback(
    Output('main-heatmap-graph', 'figure'),
    [Input('search-term-hidden', 'value'),
           Input('group-dropdown', 'value'), Input("facet-values", "value"),
           Input('year-slider', "value")]
)
def heatmap_search(word_query, facet, facet_query, years):
    try:
        word_query=json.loads(word_query)
        word = word_query['word']
        compare_word = word_query['compare']
        max_facet_values = 30

        # Display params
        log = True
        smoothing = 10
        df = get_heatmap_values(word, facet, max_facet_values,
                                hard_min_year=hard_min_year, hard_max_year=hard_max_year)
        # Important, break reference to cached version
        df = df.copy()
        plotdata, layout = format_heatmap_data(df, word, log, smoothing, years[0], years[1], tuple(facet_query))
        fig = dict( data=plotdata, layout=layout )
    except:
        logging.exception(json.dumps(dict(page='heatmap', word_query=word_query, facet=facet,
                                      facet_query=facet_query, years=years)))
        fig = errorfig()
    return fig

if __name__ == '__main__':
    app.config.supress_callback_exceptions = True
    app.run_server(debug=True, port=8080, threaded=True, host='0.0.0.0')
