# -*- coding: utf-8 -*-
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly
import plotly.graph_objs as go
import pandas as pd
from common import app
from tools import load_page
import json

page_info = [
    {"name":"Bar Chart", "slug":"bar", "path":'bar_chart' },
    {"name":"Map Search", "slug":"map", "path":'map' },
    {"name":"Heat Map", "slug":"heatmap", "path":'heatmap' }
]
pages = { page['slug']: load_page(page['path']+'.py') for page in page_info }

header_bar = html.Nav(className='navbar navbar-dark bg-dark navbar-expand-lg', children=[
            dcc.Link("Bookworm Playground", href=app.url_base_pathname, className="navbar-brand", style=dict(color='#fff')),
            html.Ul(className="navbar-nav", children=
                    [html.Li(
                        dcc.Link(page['name'], href=app.url_base_pathname+page['slug'], className='nav-link'), className='nav-item active'
                    ) for page in page_info]
                   )
    ])

footer = '''This is an set of experimental tools for exploring [HathiTrust+Bookworm Project](https://analytics.hathitrust.org/bookworm).

See the main HT+BW visualization at the [HathiTrust Research Center](https://analytics.hathitrust.org/bookworm).
            For expert use, there is an [advanced visualization page](https://bookworm.htrc.illinois.edu/advanced).
            Consult the [API documentation](https://bookworm-project.github.io/Docs/API.html) for more information on the Bookworm query language. Finally, if you're looking for tools for quantitative querying of the API, see the [BookwormPython](https://github.com/organisciak/BookwormPython) library.
            
HT+BW is supported by NEH grant #HK-50176-14. If you have any questions, email [Peter.Organisciak@du.edu](mailto:Peter.Organisciak@du.edu).
            '''

app.layout = html.Div([
        # represents the URL bar, doesn't render anything
        dcc.Location(id='url', refresh=False),
        header_bar,
        html.Div(id='page-content'),
        html.Hr(),
        html.Div(dcc.Markdown(footer), className='container')
])

# Future support for params with /q= at the end
def parse_path(pathname):
    try:
        pathparts = pathname.strip('/').split('/')
    except:
        return None, None
    if pathparts[-1].startswith('q='):
        params = pathparts[-1][2:].split(',')
        pathparts = pathparts[:-1]
    else:
        params = None
    return params, pathparts
        
@app.callback(dash.dependencies.Output('page-content', 'children'),
              [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname):
    try:
        params, pathparts = parse_path(pathname)

        if not (pathparts[0] == app.url_base_pathname.strip('/')):
            raise Exception('Unknown page')
        if (len(pathparts) == 1):
            return pages['map']
        if pathparts[1] in pages:
            return pages[pathparts[1]]
        else:
            raise Exception('Unknown page')
    except:
        return dcc.Link('No content here. return to app root', href='/app/')

if __name__ == '__main__':
    # app.scripts.config.serve_locally = False
    app.config.supress_callback_exceptions = True
    app.run_server(debug=True, port=8080, threaded=True, host='0.0.0.0')
