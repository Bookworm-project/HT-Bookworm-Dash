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

page_info = [
    {"name":"Bar Chart", "slug":"bar", "path":'bar_chart' },
    {"name":"Map Search", "slug":"map", "path":'map' }
    #{"name":"Word Stats", "slug":"word", "path":'word_stats' }
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

footer = '''This is an experimental spin-off of the [HathiTrust+Bookworm Project](https://analytics.hathitrust.org/bookworm).

See the main HT+BW visualization at the [HathiTrust Research Center](https://analytics.hathitrust.org/bookworm).
            For expert use, there is an [advanced visualization page](https://bookworm.htrc.illinois.edu/advanced).
            Consult the [API documentation](https://bookworm-project.github.io/Docs/API.html) for more information on the Bookworm query language. Finally, if you're looking for tools for quantitative querying of the API, see the [BookwormPython](https://github.com/organisciak/BookwormPython) library.
            
If you have any questions, email [Peter.Organisciak@du.edu](mailto:Peter.Organisciak@du.edu).
            '''

app.layout = html.Div([
        # represents the URL bar, doesn't render anything
        dcc.Location(id='url', refresh=False),
        header_bar,
        html.Div(id='page-content'),
        html.Hr(),
        html.Div(dcc.Markdown(footer), className='container')
])

@app.callback(dash.dependencies.Output('page-content', 'children'),
              [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname):
    try:
        pathparts = pathname.strip('/').split('/')
        if not (pathparts[0] == app.url_base_pathname.strip('/')):
            raise Exception('Unknown page')
        if (len(pathparts) == 1):
            return pages['bar']
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
