from common import app

def load_page(path):
    with open(path, 'r') as _f:
        _source = _f.read()
        _example = _source

        _example = _example.replace('from common import', '# from common import')

        if 'import dash\n' not in _example:
            raise Exception("Didn't import dash")

        # return the layout instead of assigning it to the global app
        if 'app.layout = ' not in _example:
            raise Exception("app.layout not assigned")
        _example = _example.replace('app.layout = ', 'layout = ')

        # Remove the "# Run the server" commands
        if 'app.run_server' not in _example:
            raise Exception("app.run_server missing")
        _example = _example.replace(
            '\n    app.run_server',
            'print("Running")\n    # app.run_server'
        )

        scope = {'app': app }
        exec(_example, scope)

    return scope['layout']