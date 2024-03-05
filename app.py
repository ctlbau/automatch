import dash
import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output

# Import your page layouts and callbacks
from pages import deck_page, match_page

# Choose a theme from https://bootswatch.com/ or use the default Bootstrap theme
app = dash.Dash(
    __name__, 
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    use_pages=True,
    suppress_callback_exceptions=True
                )

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dcc.Store(id='drivers-to-match-store'),  # Store here to share data between pages
    html.Div(id='page-content')
])

@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/deck_page':
        return deck_page.layout
    elif pathname == '/match_page':
        return match_page.layout
    else:
        return '404'

if __name__ == '__main__':
    app.run_server(debug=True)