# -*- coding: utf-8 -*-
'''
A common server than can be imported, rather than indivudally initialized.
'''
import dash
import bwypy

app = dash.Dash(url_base_pathname='/app/', csrf_protect=False)
app.config.supress_callback_exceptions = True

app.css.append_css({
    "external_url" : "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css"
})