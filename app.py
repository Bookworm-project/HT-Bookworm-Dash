# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

import plotly
import plotly.graph_objs as go

import pandas as pd

from common import app, bw
from tools import load_page

page_info = [
    {"name":"Bar Chart", "slug":"bar", "path":'bar_chart' }
]
pages = { page['slug']: load_page(page['path']+'.py') for page in page_info }

header_bar = html.Nav(className='navbar navbar-default', children=[
    html.Div(className='container-fluid', children=[
            html.Div([dcc.Link("Bookworm Playground", href=app.url_base_pathname, className="navbar-brand")], className="navbar-header"),
            html.Ul(className="nav navbar-nav", children=[
                html.Li(dcc.Link(page['name'], href=app.url_base_pathname+page['slug'])) for page in page_info
                ])
            ])
    ])

app.layout = html.Div([
        # represents the URL bar, doesn't render anything
        dcc.Location(id='url', refresh=False),
        header_bar,
        html.Div(id='page-content'),
        html.Hr(),
        html.P("Footer placeholder")
])

@app.callback(dash.dependencies.Output('page-content', 'children'),
              [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname):
    try:
        if not pathname.startswith(app.url_base_pathname):
            raise Exception('Unknown page')
        slug = pathname[len(app.url_base_pathname):].strip('/')
        if slug == '':
            return pages['bar']
        elif slug in pages:
            return pages[slug]
        else:
            raise Exception('Unknown page')
    except:
        return dcc.Link('No content here. return to app root', href='/app/'),

if __name__ == '__main__':
    # app.scripts.config.serve_locally = False
    app.config.supress_callback_exceptions = True
    app.run_server(debug=True, port=8080, threaded=True, host='0.0.0.0')
